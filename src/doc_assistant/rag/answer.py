from __future__ import annotations

from dataclasses import dataclass
import re
import requests


@dataclass(frozen=True)
class AnswerResult:
    text: str
    mode: str


class AnswerService:
    def __init__(self, settings):
        self.settings = settings

    @staticmethod
    def _evidence_only(hits) -> AnswerResult:
        if not hits:
            return AnswerResult(
                "I couldn't find sufficiently relevant information in the indexed documents. "
                "Try rephrasing your question or adding a more relevant document.",
                "no-evidence",
            )
        lines = ["I couldn't generate a model response. Here are the most relevant passages I found:"]
        for i, hit in enumerate(hits, 1):
            lines.append(f"\n[S{i}] {hit.metadata['filename']} (page {hit.metadata['page']}):\n{hit.text}")
        return AnswerResult("\n".join(lines), "evidence-only")

    def answer(self, question: str, hits) -> AnswerResult:
        if not hits:
            return self._evidence_only(hits)

        evidence = "\n\n".join(
            f"[S{i}] File: {hit.metadata['filename']} | Page: {hit.metadata['page']}\n{hit.text}"
            for i, hit in enumerate(hits, 1)
        )
        prompt = (
            "You are DocuMind, a document question-answering assistant. Answer only from the evidence below. "
            "If the evidence does not answer the question, say so clearly. Cite supporting passages using "
            "[S1], [S2], etc. Do not invent facts or citations. Keep the answer concise and useful.\n\n"
            f"QUESTION:\n{question}\n\nEVIDENCE:\n{evidence}\n\nANSWER:"
        )

        # Gemini is the primary hosted engine. The API key is read server-side from secrets/env.
        if self.settings.gemini_api_key:
            try:
                model = self.settings.gemini_model
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
                response = requests.post(
                    url,
                    headers={"x-goog-api-key": self.settings.gemini_api_key},
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1024},
                    },
                    timeout=(10, 90),
                )
                response.raise_for_status()
                payload = response.json()
                parts = payload["candidates"][0]["content"]["parts"]
                generated = "\n".join(part.get("text", "") for part in parts).strip()
                if generated and self._citations_valid(generated, len(hits)):
                    return AnswerResult(generated, "gemini")
            except (requests.RequestException, ValueError, KeyError, IndexError, TypeError):
                pass

        # Optional local fallback for Docker/local development.
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
            except (requests.RequestException, ValueError, KeyError, TypeError):
                pass

        return self._evidence_only(hits)

    @staticmethod
    def _citations_valid(text: str, count: int) -> bool:
        cited = [int(value) for value in re.findall(r"\[S(\d+)\]", text)]
        return bool(cited) and all(1 <= value <= count for value in cited)
