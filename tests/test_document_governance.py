from types import SimpleNamespace

from src.doc_assistant.storage.sqlite_store import SQLiteStore


def test_document_governance_metadata_and_text_round_trip(tmp_path):
    store = SQLiteStore(str(tmp_path / "documind.db"))
    chunks = [SimpleNamespace(text="The process owner reviews the request.", page=2)]
    store.add_document("procedure.txt", chunks, [[1.0, 0.0]])

    records = store.list_document_records()
    assert len(records) == 1
    record = records[0]
    assert record["status"] == "Draft"
    assert record["category"] == "Unclassified"

    store.update_document_metadata(
        record["id"], "Process Office", "Approved", "2.1", "2027-01-31", "Procedure"
    )
    updated = store.list_document_records()[0]
    assert updated["owner"] == "Process Office"
    assert updated["status"] == "Approved"
    assert updated["version"] == "2.1"
    assert updated["review_date"] == "2027-01-31"
    assert updated["category"] == "Procedure"

    document_text = store.get_document_texts()[0]
    assert document_text["filename"] == "procedure.txt"
    assert "[Page 2]" in document_text["text"]
    assert "process owner" in document_text["text"]


def test_invalid_governance_values_are_rejected(tmp_path):
    store = SQLiteStore(str(tmp_path / "documind.db"))
    chunks = [SimpleNamespace(text="A document.", page=1)]
    document_id = store.add_document("sample.txt", chunks, [[1.0, 0.0]])

    try:
        store.update_document_metadata(document_id, "", "Published", "1.0", "", "Other")
    except ValueError as exc:
        assert "Invalid document status" in str(exc)
    else:
        raise AssertionError("Unsupported lifecycle status should be rejected.")
