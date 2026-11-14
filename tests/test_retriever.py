from src.doc_assistant.rag.retriever import Retriever


class FakeEmbedder:
    def encode(self, texts):
        return [[1.0, 0.0] for _ in texts]


class FakeStore:
    def search_chunks(self, query_vector, top_k):
        return [
            {
                "id": 1,
                "text": "General office conduct and attendance requirements.",
                "filename": "handbook.docx",
                "page": 1,
                "score": 0.20,
            },
            {
                "id": 2,
                "text": "Eligible full-time employees receive 20 days of annual leave per leave year.",
                "filename": "handbook.docx",
                "page": 1,
                "score": 0.08,
            },
        ][:top_k]


def test_hybrid_retrieval_ranks_exact_policy_passage_first():
    retriever = Retriever(FakeStore(), FakeEmbedder())

    hits = retriever.search(
        "How many days of annual leave does an eligible full-time employee receive?",
        top_k=2,
    )

    assert hits[0].chunk_id == 2
    assert hits[0].score > hits[1].score
    assert hits[0].score > 0.18
