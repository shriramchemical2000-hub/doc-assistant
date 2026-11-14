# Architecture

## Product workspaces

DocuMind is department-neutral and exposes six workflows:

1. **Ask documents:** retrieval-augmented Q&A over indexed documents, with source passages and citation validation.
2. **Smart Docs:** map-reduce summarisation, enterprise-wide SOP drafting and plain-language SOP explanation.
3. **Document Comparison:** compare two uploaded versions and produce a structured change report.
4. **Gap & Conflict Review:** analyse indexed documents for evidence-backed inconsistencies, unclear responsibilities and missing process details.
5. **Training Assistant:** generate source-grounded training guides, FAQs, knowledge quizzes and quick-reference checklists.
6. **Document Governance:** maintain lightweight metadata for document owner, lifecycle status, version, review date and category.

## Request lifecycle

1. **Ingestion:** the application accepts PDF, DOCX and TXT files and extracts text. PDF page metadata is retained where available.
2. **Chunking:** extracted text is split into overlapping passages. Each passage retains filename and page metadata.
3. **Embedding:** a Sentence Transformers model converts passages and the user's question into vectors.
4. **Retrieval:** hybrid retrieval combines semantic similarity and lexical keyword coverage to rank passages.
5. **Generation:** Gemini receives the task and relevant source text. Prompts instruct it to distinguish source facts from uncertainty and not invent missing requirements.
6. **Evidence and export:** Q&A displays retrieved passages; generated workflows provide Markdown output and downloadable PDF reports where supported.

## Components

- **Streamlit:** browser UI and session state.
- **Ingestion layer:** PDF, DOCX and TXT text extraction.
- **Chunking and embedding:** transforms extracted text into searchable passages.
- **SQLite store:** persists document metadata, governance fields, passages and vectors for the current demo session.
- **Retriever:** combines lexical coverage with semantic similarity.
- **Answer service:** uses Gemini as the hosted primary model, optionally falls back to Ollama when enabled, and finally returns evidence-only output if generation is unavailable.
- **Smart Docs service:** map-reduce processing for long documents and structured SOP generation.
- **Enterprise tools service:** document comparison, cross-document review and training-content generation.
- **PDF export:** converts generated Markdown reports into downloadable PDF documents.

## Grounding controls and limitations

Retrieval-augmented generation can reduce unsupported answers, but does not guarantee factual correctness. Source metadata helps users inspect evidence; citation validation rejects references outside the retrieved source set; and generation instructions request abstention when evidence is missing. Comparison and gap-review findings are analytical suggestions, not compliance determinations. A citation or quoted excerpt does not by itself prove that the source entails a conclusion. Human review is required before operational use.

## Demo data boundaries

The included `sample_documents/` files are fictional and designed to demonstrate version comparison and cross-document review. The current app uses browser-session-isolated SQLite workspaces. Governance metadata is a lightweight register, not a formal approval workflow or enterprise records-management platform.

## Free hosted deployment

The public portfolio demo is designed for Streamlit Community Cloud plus the Gemini API free tier. The API key is stored in the host's server-side Secrets settings, not in the repository or browser. Free-tier quotas and hosting resources are limited and may change. The free Gemini tier may use submitted content to improve Google's products, so the public demo should use fictional or public documents only.

## Portfolio scope

This is a demonstrator, not a production enterprise deployment. A production system would need authentication, robust tenant isolation, authorization checks, encrypted storage, audit logging, retention/deletion controls, malware scanning, rate limiting, monitoring, backups and formal approval workflows.
