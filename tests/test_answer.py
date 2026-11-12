from src.doc_assistant.rag.answer import AnswerService


def test_citation_validation():
    assert AnswerService._citations_valid("The answer is 20 days [S1].", 1)
    assert not AnswerService._citations_valid("The answer is 20 days [S2].", 1)
    assert not AnswerService._citations_valid("No citation here", 1)
