from types import SimpleNamespace

from src.doc_assistant.rag.answer import AnswerService


def test_citation_validation():
    assert AnswerService._citations_valid("The answer is 20 days [S1].", 1)
    assert not AnswerService._citations_valid("The answer is 20 days [S2].", 1)
    assert not AnswerService._citations_valid("No citation here", 1)


def test_gemini_is_primary_when_configured(monkeypatch):
    calls = []

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "candidates": [{
                    "content": {
                        "parts": [{"text": "The policy provides 20 days [S1]."}]
                    }
                }]
            }

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse()

    monkeypatch.setattr("src.doc_assistant.rag.answer.requests.post", fake_post)
    settings = SimpleNamespace(
        gemini_api_key="test-key",
        gemini_model="gemini-3.8-flash",
        ollama_enabled=True,
        ollama_base_url="http://localhost:11434",
        ollama_model="llama3.2:3b",
    )
    hit = SimpleNamespace(
        metadata={"filename": "policy.txt", "page": 1},
        text="Annual leave entitlement is 20 days.",
    )

    result = AnswerService(settings).answer("How much annual leave?", [hit])

    assert result.mode == "gemini"
    assert "[S1]" in result.text
    assert len(calls) == 1
    assert calls[0][1]["headers"]["x-goog-api-key"] == "test-key"



def test_gemini_retries_temporary_503_then_succeeds(monkeypatch):
    import src.doc_assistant.rag.answer as answer_module

    calls = []
    delays = []

    class FakeResponse:
        def __init__(self, status_code, payload):
            self.status_code = status_code
            self.ok = status_code < 400
            self._payload = payload
            self.reason = "Service Unavailable"
            self.headers = {}

        def json(self):
            return self._payload

    success = {
        "candidates": [{
            "content": {"parts": [{"text": "The policy provides 20 days [S1]."}]}
        }]
    }

    def fake_post(url, **kwargs):
        calls.append(url)
        if len(calls) == 1:
            return FakeResponse(503, {"error": {"message": "Model is temporarily overloaded"}})
        return FakeResponse(200, success)

    monkeypatch.setattr(answer_module.requests, "post", fake_post)
    monkeypatch.setattr(answer_module.time, "sleep", lambda delay: delays.append(delay))

    settings = SimpleNamespace(
        gemini_api_key="test-key",
        gemini_model="gemini-3.8-flash",
        ollama_enabled=False,
        ollama_base_url="http://localhost:11434",
        ollama_model="llama3.2:3b",
    )
    result = AnswerService(settings)._call_gemini("test prompt")

    assert result == "The policy provides 20 days [S1]."
    assert len(calls) == 2
    assert delays == [2]
