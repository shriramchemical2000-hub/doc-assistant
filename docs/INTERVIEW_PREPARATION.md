# Interview preparation — DocuMind

This document is optional preparation material for the project author. It is intentionally separate from the recruiter-facing README.

## 60-second project explanation

"DocuMind is a document question-answering application built with retrieval-augmented generation. It ingests PDF, DOCX and text files, extracts and chunks the content while preserving source metadata, embeds the chunks, and retrieves relevant passages for each question. An Ollama-hosted language model uses those passages to formulate an answer, and the interface displays the supporting evidence so a user can verify it. The goal is to make document exploration easier while reducing unsupported answers."

## Questions to practise

### 1. What problem does the project solve?
It provides a natural-language interface over a collection of documents, so users can locate and understand relevant information without manually searching every file.

### 2. What is RAG?
Retrieval-Augmented Generation retrieves relevant external context for a question and supplies that context to a language model before generation. The model is expected to answer using the retrieved material.

### 3. Why chunk documents?
Embedding an entire long document as one vector can blur distinct topics and exceed practical context limits. Chunking creates smaller searchable passages and lets retrieval return focused evidence.

### 4. Why use chunk overlap?
Overlap helps preserve context across chunk boundaries. Too much overlap increases storage and can return redundant passages, so chunk size and overlap should be tuned.

### 5. What are embeddings?
Embeddings are numeric vectors that represent semantic features of text. Similar meanings can be close in vector space even when they use different words.

### 6. How does semantic retrieval work?
The system embeds the question, compares it with stored passage vectors using a similarity measure, ranks the passages and selects the strongest matches.

### 7. Why preserve page numbers and filenames?
They make retrieved evidence traceable. Users can inspect the original source rather than blindly trusting generated prose.

### 8. How does the system reduce hallucinations?
It retrieves evidence, applies a relevance threshold, instructs the model to stay within the supplied context, validates source identifiers where implemented, and exposes passages for verification. These safeguards reduce risk but do not guarantee correctness.

### 9. Why Ollama instead of a hosted API?
Ollama lets the project operator run an open model on infrastructure they control and avoids depending on a third-party inference API quota. The trade-off is server cost, resource requirements and model operations.

### 10. Does Ollama run on the recruiter's laptop?
No. In the intended hosted deployment, Ollama runs on the application server. A visitor only uses a browser.

### 11. What are the limitations?
The model can still produce incorrect interpretations; retrieval can miss relevant evidence; scanned PDFs need OCR; and the portfolio version needs additional security and multi-tenant controls before real enterprise use.

### 12. How would you improve it?
Evaluate retrieval with a labelled question/passage dataset; add hybrid keyword and vector search; rerank retrieved passages; support OCR; add document-level access control; introduce observability and latency metrics; and build a robust evaluation suite for groundedness and citation correctness.

## Be precise in interviews

Do not claim that RAG eliminates hallucinations, that the system is production-secure, or that the public demo is deployed unless those statements have been verified. Explain which parts are implemented, which are tested, and which are planned.
