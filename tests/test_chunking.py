from src.doc_assistant.ingestion.loader import Page
from src.doc_assistant.rag.chunking import chunk_pages


def test_chunk_pages_preserves_page_and_filename():
    pages = [Page("one two three four five six", 2)]
    chunks = chunk_pages(pages, chunk_size=3, overlap=1, filename="policy.txt")
    assert [chunk.text for chunk in chunks] == ["one two three", "three four five", "five six"]
    assert all(chunk.page == 2 for chunk in chunks)
    assert all(chunk.filename == "policy.txt" for chunk in chunks)


def test_chunking_rejects_invalid_overlap():
    try:
        chunk_pages([Page("hello", 1)], chunk_size=3, overlap=3)
    except ValueError:
        return
    raise AssertionError("Expected invalid overlap to raise ValueError")
