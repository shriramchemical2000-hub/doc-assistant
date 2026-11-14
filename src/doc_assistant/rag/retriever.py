from __future__ import annotations

from dataclasses import dataclass
import re
import numpy as np


@dataclass(frozen=True)
class SearchHit:
    chunk_id: int
    text: str
    metadata: dict
    score: float


# Common question words add little value to lexical matching. Keep policy terms
# such as "leave", "days", "employee" and "eligible".
_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "does",
    "for", "from", "how", "i", "in", "is", "it", "of", "on", "or", "the",
    "this", "to", "was", "what", "when", "where", "which", "who", "with",
}


def _terms(text: str) -> set[str]:
    return {
        token for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) > 1 and token not in _STOP_WORDS
    }


class Retriever:
    """Hybrid retrieval combining embedding similarity with keyword coverage."""

    def __init__(self, store, embedder):
        self.store = store
        self.embedder = embedder

    def search(self, question: str, top_k: int = 5) -> list[SearchHit]:
        query_vector = self.embedder.encode([question])[0]

        # Fetch a wider semantic candidate set, then rerank it with lexical
        # coverage so exact policy wording is not lost to embedding dilution.
        candidate_k = max(50, top_k * 10)
        rows = self.store.search_chunks(query_vector, top_k=candidate_k)
        query_terms = _terms(question)

        ranked = []
        for row in rows:
            semantic_score = max(0.0, min(1.0, float(row["score"])))
            passage_terms = _terms(row["text"])
            lexical_score = (
                len(query_terms & passage_terms) / len(query_terms)
                if query_terms else 0.0
            )
            # Both components are normalized to [0, 1]. Lexical coverage
            # receives more weight for policy lookups; semantic matching still
            # helps when the question paraphrases the document.
            score = 0.65 * lexical_score + 0.35 * semantic_score
            ranked.append((score, row))

        ranked.sort(key=lambda item: item[0], reverse=True)
        return [
            SearchHit(
                chunk_id=row["id"],
                text=row["text"],
                metadata={"filename": row["filename"], "page": row["page"]},
                score=float(score),
            )
            for score, row in ranked[:max(0, top_k)]
        ]
