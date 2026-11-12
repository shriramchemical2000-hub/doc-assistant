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
