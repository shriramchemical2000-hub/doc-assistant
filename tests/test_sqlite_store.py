from src.doc_assistant.ingestion.loader import Page
from src.doc_assistant.rag.chunking import chunk_pages
from src.doc_assistant.storage.sqlite_store import SQLiteStore


def test_store_add_search_delete(tmp_path):
    store = SQLiteStore(str(tmp_path / "test.db"))
    chunks = chunk_pages([Page("annual leave is twenty days", 1)], chunk_size=20, overlap=0, filename="handbook.txt")
    store.add_document("handbook.txt", chunks, [[1.0, 0.0, 0.0]])
    assert store.count_chunks() == 1
    hits = store.search_chunks([1.0, 0.0, 0.0], top_k=3)
    assert hits[0]["filename"] == "handbook.txt"
    assert hits[0]["score"] > 0.99
    doc_id = store.list_documents()[0]["id"]
    store.delete_document(doc_id)
    assert store.count_chunks() == 0
