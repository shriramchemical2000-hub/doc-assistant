from src.doc_assistant.ingestion.loader import load_uploaded_file


def test_load_txt():
    pages = load_uploaded_file("note.txt", b"Hello DocuMind")
    assert len(pages) == 1
    assert pages[0].text == "Hello DocuMind"
    assert pages[0].page == 1


def test_reject_unsupported_file():
    try:
        load_uploaded_file("note.csv", b"a,b")
    except ValueError as exc:
        assert "Unsupported" in str(exc)
        return
    raise AssertionError("Expected unsupported extension to raise ValueError")
