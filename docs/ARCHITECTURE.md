# Architecture

## Request lifecycle

1. **Ingestion:** the application accepts PDF, DOCX and TXT files and extracts text. PDF page metadata is retained where available.
2. **Chunking:** extracted text is split into overlapping passages. Each passage retains filename and page metadata.
3. **Embedding:** a Sentence Transformers model converts passages and the user's question into vectors.
4. **Retrieval:** semantic similarity ranks stored passages; the configured top-k and minimum-score threshold filter the candidates.
5. **Generation:** the Ollama model receives the question and retrieved evidence, with instructions to stay within that evidence.
6. **Evidence display:** the UI displays the generated response and the retrieved passages for human verification.

## Components

- **Streamlit:** browser UI and session state.
- **Ingestion layer:** file-type-specific text extraction.
- **Chunking and embedding:** transforms extracted text into searchable passages.
- **SQLite store:** persists document and passage metadata plus vectors.
- **Retriever:** selects relevant passages for a question.
- **Answer service:** uses Ollama when configured and falls back to an evidence-only response when generation is unavailable.

## Grounding controls and limitations

Retrieval-augmented generation can reduce unsupported answers, but does not guarantee factual correctness. A similarity threshold can reject weak matches; source metadata helps users inspect evidence; and generation instructions can request abstention. These controls should be evaluated with a representative test set. A citation being present does not by itself prove that the cited passage entails the answer.

## Portfolio scope

This is a demonstrator, not a production enterprise deployment. A production system would need authentication, robust tenant isolation, authorization checks, encrypted storage, audit logging, retention/deletion controls, malware scanning, rate limiting, monitoring and operational backups.
