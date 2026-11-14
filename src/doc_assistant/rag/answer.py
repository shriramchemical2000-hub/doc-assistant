from __future__ import annotations

from dataclasses import dataclass
import re
import time
import requests

# Retry only temporary service/network failures. Persistent quota and configuration
# errors are surfaced promptly instead of keeping the user waiting.
_GEMINI_RETRY_DELAYS = (2, 5)
_GEMINI_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


@dataclass(frozen=True)
class AnswerResult:
    text: str
    mode: str
    error: str = ""


class AnswerService:
    def __init__(self, settings):
        self.settings = settings

    @staticmethod
    def _evidence_only(hits, error: str = "") -> AnswerResult:
        if not hits:
            return AnswerResult(
                "I couldn't find sufficiently relevant information in the indexed documents. "
                "Try rephrasing your question or adding a more relevant document.",
                "no-evidence",
                error,
            )
        lines = ["I couldn't generate an AI response. The retrieved evidence is shown below:"]
        for i, hit in enumerate(hits, 1):
            lines.append(f"\n[S{i}] {hit.metadata['filename']} (page {hit.metadata['page']}):\n{hit.text}")
        return AnswerResult("\n".join(lines), "evidence-only", error)

    @staticmethod
    def _extract_text(payload: dict) -> str:
        candidates = payload.get("candidates") or []
        if not candidates:
            feedback = payload.get("promptFeedback") or {}
            reason = feedback.get("blockReason") or "not supplied"
            raise ValueError(f"Gemini returned no candidates. Block reason: {reason}")
        candidate = candidates[0]
        parts = (candidate.get("content") or {}).get("parts") or []
        generated = "\n".join(part.get("text", "") for part in parts if isinstance(part, dict)).strip()
        if not generated:
            reason = candidate.get("finishReason", "unknown")
            raise ValueError(f"Gemini returned an empty response (finish reason: {reason}).")
        return generated

    def _call_gemini(self, prompt: str, max_output_tokens: int = 1400) -> str:
        model = self.settings.gemini_model
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": max_output_tokens},
        }

        for attempt in range(len(_GEMINI_RETRY_DELAYS) + 1):
            try:
                response = requests.post(
                    url,
                    headers={"x-goog-api-key": self.settings.gemini_api_key},
                    json=payload,
                    timeout=(15, 120),
                )
            except requests.RequestException:
                if attempt >= len(_GEMINI_RETRY_DELAYS):
                    raise
                time.sleep(_GEMINI_RETRY_DELAYS[attempt])
                continue

            if getattr(response, "ok", True) is False:
                status = getattr(response, "status_code", 0)
                try:
                    detail = (response.json().get("error") or {}).get("message", "")
                except (ValueError, AttributeError):
                    detail = getattr(response, "text", "")[:400]
                reason = detail or getattr(response, "reason", "Unknown API error")

                if status in _GEMINI_RETRYABLE_STATUS and attempt < len(_GEMINI_RETRY_DELAYS):
                    # Respect a short numeric Retry-After header when supplied,
                    # but cap it so a free demo does not appear frozen.
                    headers = getattr(response, "headers", {}) or {}
                    retry_after = headers.get("Retry-After")
                    try:
                        delay = min(max(float(retry_after), 1.0), 10.0) if retry_after else _GEMINI_RETRY_DELAYS[attempt]
                    except (TypeError, ValueError):
                        delay = _GEMINI_RETRY_DELAYS[attempt]
                    time.sleep(delay)
                    continue

                retry_note = (
                    f" after {attempt + 1} attempts"
                    if status in _GEMINI_RETRYABLE_STATUS and attempt > 0
                    else ""
                )
                raise RuntimeError(f"Gemini API HTTP {status}{retry_note}: {reason}")

            return self._extract_text(response.json())

        raise RuntimeError("Gemini request failed after retry attempts.")

    def answer(self, question: str, hits) -> AnswerResult:
        if not hits:
            return self._evidence_only(hits)
        evidence = "\n\n".join(
            f"[S{i}] File: {hit.metadata['filename']} | Page: {hit.metadata['page']}\n{hit.text}"
            for i, hit in enumerate(hits, 1)
        )
        prompt = (
            "You are DocuMind, a precise document question-answering assistant. Answer using ONLY the "
            "supplied evidence. Give the direct answer first. Every factual claim must have an inline "
            "citation such as [S1], and cite at least one source. If the evidence does not contain the "
            "answer, say it is not specified. Never guess.\n\n"
            f"QUESTION:\n{question}\n\nEVIDENCE:\n{evidence}\n\nANSWER:"
        )
        gemini_error = ""
        if self.settings.gemini_api_key:
            try:
                generated = self._call_gemini(prompt)
                if self._citations_valid(generated, len(hits)):
                    return AnswerResult(generated, "gemini")
                gemini_error = "Gemini responded, but its answer did not contain a valid source citation."
            except (requests.RequestException, ValueError, RuntimeError, KeyError, IndexError, TypeError) as exc:
                gemini_error = str(exc)[:700]
        else:
            gemini_error = "GEMINI_API_KEY is not configured in the app's server-side secrets."

        if self.settings.ollama_enabled:
            try:
                response = requests.post(
                    self.settings.ollama_base_url.rstrip("/") + "/api/generate",
                    json={"model": self.settings.ollama_model, "prompt": prompt, "stream": False},
                    timeout=(10, 180),
                )
                response.raise_for_status()
                generated = response.json().get("response", "").strip()
                if generated and self._citations_valid(generated, len(hits)):
                    return AnswerResult(generated, "ollama")
            except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
                gemini_error += f" Local fallback: {str(exc)[:300]}"
        return self._evidence_only(hits, gemini_error)

    @staticmethod
    def _citations_valid(text: str, count: int) -> bool:
        cited = [int(value) for value in re.findall(r"\[S(\d+)\]", text)]
        return bool(cited) and all(1 <= value <= count for value in cited)
