from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    database_path: str
    upload_dir: str
    embedding_model: str
    gemini_api_key: str
    gemini_model: str
    ollama_enabled: bool
    ollama_base_url: str
    ollama_model: str
    default_top_k: int
    default_min_score: float
    chunk_size: int
    chunk_overlap: int


def get_settings() -> Settings:
    return Settings(
        database_path=os.getenv("DATABASE_PATH", "data/assistant.db"),
        upload_dir=os.getenv("UPLOAD_DIR", "data/uploads"),
        embedding_model=os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
        gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
        # Hosted free-tier deployment uses Gemini. Docker Compose explicitly enables Ollama.
        ollama_enabled=os.getenv("OLLAMA_ENABLED", "false").lower() == "true",
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        ollama_model=os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
        default_top_k=int(os.getenv("DEFAULT_TOP_K", "5")),
        default_min_score=float(os.getenv("DEFAULT_MIN_SCORE", "0.18")),
        chunk_size=int(os.getenv("CHUNK_SIZE", "900")),
        chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "150")),
    )
