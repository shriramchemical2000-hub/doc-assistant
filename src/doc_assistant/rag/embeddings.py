from __future__ import annotations


class SentenceTransformerEmbedder:
    """Small wrapper that loads the embedding model only when first used."""
    def __init__(self, model_name: str):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name)

    def encode(self, texts):
        if not texts:
            return []
        vectors = self.model.encode(list(texts), normalize_embeddings=True, convert_to_numpy=True)
        return vectors.tolist()
