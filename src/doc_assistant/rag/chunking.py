from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    text: str
    page: int
    filename: str


def chunk_pages(pages, chunk_size: int = 900, overlap: int = 150, filename: str = "document") -> list[Chunk]:
    """Split extracted page text into overlapping word-window chunks."""
    if chunk_size < 1:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be non-negative and smaller than chunk_size")

    chunks: list[Chunk] = []
    step = chunk_size - overlap
    for page in pages:
        words = page.text.split()
        for start in range(0, len(words), step):
            segment = words[start:start + chunk_size]
            if not segment:
                continue
            chunks.append(Chunk(" ".join(segment), int(page.page), filename))
            if start + chunk_size >= len(words):
                break
    return chunks
