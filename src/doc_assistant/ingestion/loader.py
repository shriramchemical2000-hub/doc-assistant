from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from docx import Document
from pypdf import PdfReader


@dataclass(frozen=True)
class Page:
    text: str
    page: int


def load_uploaded_file(filename: str, content: bytes) -> list[Page]:
    """Extract text from a supported uploaded file, retaining page numbers."""
    suffix = Path(filename).suffix.lower()
    if not content:
        raise ValueError("The uploaded file is empty.")

    if suffix == ".pdf":
        reader = PdfReader(BytesIO(content))
        pages = [Page((page.extract_text() or "").strip(), i)
                 for i, page in enumerate(reader.pages, start=1)]
        return [page for page in pages if page.text]

    if suffix == ".docx":
        document = Document(BytesIO(content))
        paragraphs = [p.text.strip() for p in document.paragraphs if p.text.strip()]
        # DOCX paragraphs do not expose reliable printed page boundaries.
        text = "\n".join(paragraphs)
        return [Page(text, 1)] if text else []

    if suffix == ".txt":
        try:
            text = content.decode("utf-8-sig").strip()
        except UnicodeDecodeError:
            text = content.decode("utf-8", errors="replace").strip()
        return [Page(text, 1)] if text else []

    raise ValueError("Unsupported file type. Upload a PDF, DOCX or TXT file.")
