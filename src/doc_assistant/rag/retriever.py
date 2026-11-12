from __future__ import annotations

from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class SearchHit:
    chunk_id: int
    text: str
    metadata: dict
    score: float


class Retriever:
    def __init__(self, store, embedder):
        self.store = store
        self.embedder = embedder

    def search(self, question: str, top_k: int = 5) -> list[SearchHit]:
        query_vector = self.embedder.encode([question])[0]
        rows = self.store.search_chunks(query_vector, top_k=top_k)
        return [SearchHit(chunk_id=row["id"], text=row["text"],
                          metadata={"filename": row["filename"], "page": row["page"]},
                          score=float(row["score"])) for row in rows]
