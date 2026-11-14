from __future__ import annotations

import os
import re
import html
import uuid
from pathlib import Path
import streamlit as st

from config import get_settings
from src.doc_assistant.ingestion.loader import load_uploaded_file
from src.doc_assistant.rag.answer import AnswerService
from src.doc_assistant.rag.chunking import chunk_pages
from src.doc_assistant.rag.embeddings import SentenceTransformerEmbedder
from src.doc_assistant.rag.retriever import Retriever
from src.doc_assistant.storage.sqlite_store import SQLiteStore
from src.doc_assistant.export.pdf_report import build_smart_docs_pdf

st.set_page_config(
    page_title="DocuMind | Document Intelligence",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Streamlit secrets are read server-side only. No key is exposed to browser code.
try:
    for key in ("GEMINI_API_KEY", "GEMINI_MODEL", "OLLAMA_ENABLED", "OLLAMA_BASE_URL", "OLLAMA_MODEL"):
        if st.secrets.get(key) is not None:
            os.environ[key] = str(st.secrets[key])
except Exception:
    pass

settings = get_settings()

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');
:root {
  --bg:#071714; --panel:rgba(20,48,42,.72); --panel2:rgba(28,62,53,.58);
  --line:rgba(205,235,220,.13); --ink:#edf7f0; --muted:#a2b8aa;
  --mint:#a7e6c2; --accent:#72d6ad; --gold:#d4c18b;
}
html, body, [class*="css"] { font-family:'DM Sans',sans-serif; }
.stApp {
  background:
    radial-gradient(ellipse at 80% 12%,rgba(167,190,112,.19),transparent 34%),
    radial-gradient(ellipse at 25% 40%,rgba(49,125,101,.22),transparent 42%),
    linear-gradient(135deg,#061411 0%,#0b211c 48%,#101d18 100%);
  color:var(--ink);
}
.block-container { max-width:1500px; padding-top:1.2rem; padding-bottom:3rem; }
[data-testid="stHeader"] { background:transparent; }
[data-testid="stToolbar"] { right:1rem; }
[data-testid="stSidebar"] {
  background:linear-gradient(180deg,rgba(9,30,25,.98),rgba(11,35,29,.96));
  border-right:1px solid var(--line);
}
[data-testid="stSidebar"] * { color:#e5f2e9; }
[data-testid="stSidebar"] [data-testid="stFileUploader"] section {
  background:rgba(255,255,255,.045); border:1px dashed rgba(177,220,194,.35);
}
[data-testid="stSidebar"] [data-testid="stFileUploader"] small,
[data-testid="stSidebar"] [data-testid="stFileUploader"] span { color:#c2d8c9 !important; }
[data-testid="stSidebar"] button { border-radius:11px; }
.hero {
  position:relative; overflow:hidden; padding:26px 30px; border-radius:22px;
  color:#f4fff7; background:linear-gradient(115deg,rgba(19,54,45,.88),rgba(41,83,68,.74) 58%,rgba(119,126,76,.55));
  border:1px solid rgba(221,245,225,.18);
  box-shadow:0 18px 55px rgba(0,0,0,.22),inset 0 1px 0 rgba(255,255,255,.10);
  backdrop-filter:blur(18px); margin-bottom:20px;
}
.hero:after {
  content:""; position:absolute; width:260px; height:260px; right:7%; top:-155px;
  border:1px solid rgba(255,255,255,.20); border-radius:50%;
  box-shadow:0 0 0 32px rgba(255,255,255,.035),0 0 0 68px rgba(255,255,255,.025);
}
.hero-kicker { text-transform:uppercase; letter-spacing:2px; font-size:10px; font-weight:700; color:#b9dfc7; }
.hero h1 { font-family:'Manrope',sans-serif; font-size:34px; letter-spacing:-1.2px; margin:6px 0 5px; color:#f4fff7; }
.hero p { color:#d3e7d9; font-size:14px; margin:0; max-width:760px; }
.hero-pill {
  display:inline-block; margin-top:15px; padding:6px 11px;
  border:1px solid rgba(255,255,255,.22); border-radius:30px;
  font-size:10px; color:#effff3; background:rgba(255,255,255,.07);
}
.section-title { font-family:'Manrope',sans-serif; color:#eff8f1; font-weight:800; font-size:19px; letter-spacing:-.4px; }
.subtle { color:#a7bdb0; font-size:13px; }
.panel, .answer-card, .stat {
  background:linear-gradient(145deg,rgba(27,59,51,.76),rgba(18,43,37,.78));
  border:1px solid var(--line); border-radius:17px; padding:18px 20px;
  box-shadow:0 12px 32px rgba(0,0,0,.13),inset 0 1px 0 rgba(255,255,255,.045);
  backdrop-filter:blur(14px);
}
.stat { padding:15px 17px; min-height:88px; }
.stat-label { color:#a8c2b2; font-size:10px; text-transform:uppercase; letter-spacing:1.1px; font-weight:700; }
.stat-value { color:#f0fff4; font-family:'Manrope',sans-serif; font-size:25px; font-weight:800; margin-top:4px; }
.answer-card { background:linear-gradient(135deg,rgba(36,83,66,.96),rgba(21,57,47,.96)); border:1px solid rgba(167,230,194,.38); border-left:5px solid #8fdbb1; border-radius:16px; padding:26px 30px; margin:10px 0 18px; box-shadow:0 14px 36px rgba(0,0,0,.22),inset 0 1px 0 rgba(255,255,255,.08); }\n.answer-text { color:#f4fff7; font-family:'Manrope',sans-serif; font-size:22px; font-weight:700; line-height:1.65; letter-spacing:-.25px; }\n@media (max-width:800px) { .answer-card { padding:20px; } .answer-text { font-size:18px; } }
.stMarkdown, .stMarkdown p, .stMarkdown li, .stCaption, label { color:#e5f1e8; }
.stCaption, [data-testid="stCaptionContainer"] { color:#a9bdaf !important; }
div[data-testid="stTextArea"] textarea, div[data-testid="stTextInput"] input {
  border-radius:12px; border:1px solid rgba(194,224,203,.20);
  background:rgba(6,22,18,.72); color:#f0fff4;
}
div[data-testid="stTextArea"] textarea::placeholder { color:#8fa99a; }
.stButton>button {
  border-radius:11px; font-weight:700; min-height:42px;
  border:1px solid rgba(190,231,202,.20);
  background:rgba(164,218,183,.10); color:#effff3;
}
.stButton>button[kind="primary"] {
  background:linear-gradient(110deg,#4a9d78,#72c69a); color:#092017; border:0;
}
.stButton>button:hover { border-color:rgba(178,235,196,.55); color:white; }
.stButton>button[kind="primary"]:hover { color:#071a12; filter:brightness(1.07); }
div[data-testid="stExpander"] {
  background:rgba(17,43,36,.75); border:1px solid var(--line); border-radius:12px;
}
div[data-testid="stExpander"] summary, div[data-testid="stExpander"] p { color:#e7f4eb; }
div[data-testid="stAlert"] { border-radius:12px; background:rgba(25,58,48,.75); color:#eaf7ed; }
hr { border-color:rgba(211,237,219,.13) !important; }
[data-testid="stFileUploader"] section { border-radius:12px; }
footer {visibility:hidden;} #MainMenu {visibility:hidden;}
@media (max-width:800px) {
  .hero {padding:22px;} .hero h1 {font-size:28px;}
  .block-container {padding-left:1rem;padding-right:1rem;}
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <div class="hero-kicker">Your private knowledge workspace</div>
  <h1>Welcome to DocuMind<span style="color:#b8e7c5">.</span></h1>
  <p>Bring your documents together, ask questions in plain language, and explore answers backed by traceable source evidence.</p>
  <span class="hero-pill">DOCUMENT INTELLIGENCE &nbsp;·&nbsp; GEMINI-POWERED &nbsp;·&nbsp; SOURCE-TRACEABLE</span>
</div>
""", unsafe_allow_html=True)

if "documind_session_id" not in st.session_state:
    st.session_state["documind_session_id"] = uuid.uuid4().hex
if "documind_latest" not in st.session_state:
    st.session_state["documind_latest"] = None

@st.cache_resource(show_spinner="Loading semantic search model…")
def get_embedder(model_name: str):
    return SentenceTransformerEmbedder(model_name)

@st.cache_resource
def get_store(db_path: str):
    return SQLiteStore(db_path)

def initialize(session_id: str):
    os.makedirs("data/sessions", exist_ok=True)
    session_db = os.path.join("data", "sessions", f"{session_id}.db")
    return get_store(session_db), get_embedder(settings.embedding_model)

def render_sources(results):
    for index, item in enumerate(results, start=1):
        meta = item.metadata
        with st.expander(
            f"Source {index}  ·  {meta['filename']}  ·  Page {meta['page']}  ·  Match {item.score:.2f}",
            expanded=(index == 1),
        ):
            st.caption(f"Retrieved passage · Chunk {item.chunk_id}")
            st.write(item.text)

try:
    store, embedder = initialize(st.session_state["documind_session_id"])
except Exception as exc:
    st.error(f"Unable to initialize DocuMind: {exc}")
    st.info("Check server logs, available memory and model-download access.")
    st.stop()

retriever = Retriever(store, embedder)
answer_service = AnswerService(settings)
docs = store.list_documents()
model_label = (
    settings.gemini_model if settings.gemini_api_key
    else settings.ollama_model if settings.ollama_enabled
    else "Evidence-only"
)

with st.sidebar:
    st.markdown("## ◈ DocuMind")
    st.caption("DOCUMENT WORKSPACE")
    st.markdown("### Workspace")
    workspace = st.radio(
        "Select workspace",
        ["Ask documents", "Smart Docs"],
        index=0,
        key="documind_workspace",
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.markdown("### Add to your knowledge base")
    uploaded_files = st.file_uploader(
        "Choose documents",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True,
        max_upload_size=20,
        help="PDF, DOCX and TXT · maximum 20 MB per file.",
    )
    st.caption("Maximum file size: **20 MB per file**")
    if st.button("＋  Index selected documents", type="primary", use_container_width=True, disabled=not uploaded_files):
        progress = st.progress(0, text="Preparing your documents…")
        added_chunks, errors = 0, []
        for i, uploaded in enumerate(uploaded_files):
            try:
                pages = load_uploaded_file(uploaded.name, uploaded.getvalue())
                chunks = chunk_pages(
                    pages, chunk_size=settings.chunk_size,
                    overlap=settings.chunk_overlap, filename=uploaded.name,
                )
                if not chunks:
                    errors.append(f"{uploaded.name}: no extractable text found.")
                else:
                    vectors = embedder.encode([chunk.text for chunk in chunks])
                    store.add_document(uploaded.name, chunks, vectors)
                    added_chunks += len(chunks)
            except Exception as exc:
                errors.append(f"{uploaded.name}: {exc}")
            progress.progress((i + 1) / len(uploaded_files), text=f"Indexed {uploaded.name}")
        progress.empty()
        if added_chunks:
            st.success(f"Successfully indexed {added_chunks} passages.")
        for error in errors:
            st.warning(error)
        st.rerun()

    st.markdown("---")
    st.markdown("### Your documents")
    st.caption(f"{len(docs)} file(s) in this session")
    if not docs:
        st.markdown("<div class='subtle'>Your workspace is empty. Add a document to get started.</div>", unsafe_allow_html=True)
    for doc in docs:
        c1, c2 = st.columns([5, 1])
        c1.markdown(f"📄 **{doc['filename']}**")
        if c2.button("×", key=f"delete_{doc['id']}", help="Remove document"):
            store.delete_document(doc["id"])
            st.rerun()
    if docs and st.button("Clear workspace", use_container_width=True):
        store.clear()
        st.session_state["documind_latest"] = None
        st.rerun()
    st.markdown("---")
    st.markdown("### Gemini connection")
    st.caption("Test the Gemini API directly, without document retrieval.")
    if st.button("Test Gemini connection", use_container_width=True, key="test_gemini_connection"):
        if not settings.gemini_api_key:
            st.error("GEMINI_API_KEY is missing from Streamlit Cloud Secrets.")
        else:
            try:
                with st.spinner(f"Testing {settings.gemini_model}…"):
                    test_reply = answer_service._call_gemini(
                        "Reply with exactly this text and nothing else: DOCUMIND_GEMINI_OK",
                        max_output_tokens=40,
                    )
                if "DOCUMIND_GEMINI_OK" in test_reply:
                    st.success(f"Gemini is working. Model: {settings.gemini_model}")
                    st.caption(f"Test response: {test_reply}")
                else:
                    st.warning("Gemini returned a response, but it did not match the expected test text.")
                    st.code(test_reply[:500])
            except Exception as exc:
                st.error("Gemini connection test failed.")
                st.code(str(exc)[:700])

    st.markdown("### System status")
    st.caption(f"Answer engine · `{model_label}`")
    st.caption(f"Embeddings · `{settings.embedding_model.split('/')[-1]}`")
    st.caption("Files are isolated by browser session in this demo.")
    st.caption("Use fictional documents only. Do not upload confidential company data.")

# Overview metrics
m1, m2, m3 = st.columns(3)
for col, label, value in [
    (m1, "Documents indexed", str(len(docs))),
    (m2, "Knowledge passages", str(store.count_chunks())),
    (m3, "AI answer engine", "Gemini" if settings.gemini_api_key else ("Ollama" if settings.ollama_enabled else "Evidence")),
]:
    with col:
        st.markdown(f"<div class='stat'><div class='stat-label'>{label}</div><div class='stat-value'>{value}</div></div>", unsafe_allow_html=True)

if workspace == "Smart Docs":
    st.markdown("<div class='section-title'>Smart Docs</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='subtle'>Summarise lengthy documents, create structured SOPs, or explain existing procedures in plain language.</div>",
        unsafe_allow_html=True,
    )
    smart_task = st.radio(
        "What should DocuMind do?",
        ["Summarise document", "Create an SOP", "Explain an existing SOP"],
        horizontal=True,
        key="smart_docs_task",
    )
    descriptions = {
        "Summarise document": "Generate an executive summary, section-by-section breakdown, and key takeaways.",
        "Create an SOP": "Draft a structured SOP with purpose, responsibilities, inputs, ordered steps, decision points, records, and escalation paths.",
        "Explain an existing SOP": "Explain the procedure in plain language, including roles, checks, sequence, and cautions.",
    }
    st.info(descriptions[smart_task])
    smart_file = st.file_uploader(
        "Upload a source document",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=False,
        key="smart_docs_upload",
        max_upload_size=20,
        help="PDF, DOCX and TXT · maximum 20 MB.",
    )
    smart_context = st.text_area(
        "Additional instructions (optional)",
        placeholder="Example: Focus on operating limits, maintenance responsibilities, safety checks and escalation criteria.",
        height=85,
        key="smart_docs_context",
    )
    if st.button("Generate with Smart Docs  →", type="primary", use_container_width=True, disabled=not smart_file):
        st.session_state["smart_docs_result"] = None
        if not settings.gemini_api_key:
            st.error("Smart Docs requires GEMINI_API_KEY in the app's server-side Streamlit Secrets.")
        else:
            try:
                pages = load_uploaded_file(smart_file.name, smart_file.getvalue())
                full_text = "\n\n".join(
                    f"[Page {page.page}]\n{page.text}" for page in pages if page.text.strip()
                )
                if not full_text.strip():
                    st.error("No readable text was found. Scanned/image-only PDFs are not supported yet.")
                else:
                    with st.spinner("Processing the document in sections and preparing your output…"):
                        from src.doc_assistant.rag.smart_docs import SmartDocsService
                        service = SmartDocsService(settings)
                        result = service.run(
                            full_text,
                            task=smart_task,
                            instructions=smart_context.strip(),
                        )
                    pdf_bytes = build_smart_docs_pdf(
                        markdown_text=result,
                        source_filename=smart_file.name,
                        task=smart_task,
                        instructions=smart_context.strip(),
                    )
                    st.session_state["smart_docs_result"] = {
                        "filename": smart_file.name,
                        "task": smart_task,
                        "text": result,
                        "pdf": pdf_bytes,
                    }
            except Exception as exc:
                error_message = str(exc)
                if "Gemini API HTTP 503" in error_message:
                    st.warning(
                        "Gemini is temporarily overloaded. DocuMind retried the request automatically, "
                        "but the service remained unavailable. Your document is still selected; try "
                        "Generate again after a short pause."
                    )
                    with st.expander("Technical details"):
                        st.code(error_message[:600])
                elif "Gemini API HTTP 429" in error_message:
                    st.warning(
                        "The Gemini free-tier request limit may have been reached. Wait for the quota "
                        "to reset, then try again."
                    )
                    with st.expander("Technical details"):
                        st.code(error_message[:600])
                else:
                    st.error(f"Smart Docs could not complete the request: {error_message[:600]}")

    smart_result = st.session_state.get("smart_docs_result")
    if smart_result:
        st.markdown("---")
        st.markdown("### Generated output")
        st.caption(f"{smart_result['task']} · Source: {smart_result['filename']}")
        st.markdown(smart_result["text"])
        safe_source = re.sub(r"[^A-Za-z0-9_-]+", "_", Path(smart_result["filename"]).stem).strip("_") or "document"
        safe_task = re.sub(r"[^A-Za-z0-9_-]+", "_", smart_result["task"]).strip("_").lower()
        st.download_button(
            "Download PDF report",
            data=smart_result["pdf"],
            file_name=f"DocuMind_{safe_source}_{safe_task}.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True,
        )
        with st.expander("View generated Markdown"):
            st.markdown(smart_result["text"])
else:
    st.markdown("<div class='section-title'>Ask your documents</div>", unsafe_allow_html=True)
    st.markdown("<div class='subtle'>Ask a question and get an answer grounded in your indexed documents.</div>", unsafe_allow_html=True)
    with st.form("document_question_form", clear_on_submit=True):
        question = st.text_area(
            "Your question",
            placeholder="For example: How many annual leave days does an eligible employee receive?",
            height=90,
        )
        ask = st.form_submit_button("Ask DocuMind  →", type="primary", use_container_width=True)
    if ask and question.strip():
        if not store.count_chunks():
            st.warning("Upload and index a document first.")
            st.session_state["documind_latest"] = None
        else:
            with st.spinner("Finding evidence and generating your answer…"):
                closest_hits = retriever.search(question.strip(), top_k=settings.default_top_k)
                hits = [hit for hit in closest_hits if hit.score >= settings.default_min_score]
                answer = answer_service.answer(question.strip(), hits)
            st.session_state["documind_latest"] = {
                "answer": answer,
                "hits": hits,
                "closest_hits": closest_hits[:3],
                "minimum_score": settings.default_min_score,
            }

    latest = st.session_state.get("documind_latest")
    if latest:
        st.markdown("### Answer")
        # Keep citation validation internally, but present a clean answer to readers.
        # The expandable source panel below preserves document-level traceability.
        display_answer = re.sub(r"\s*\[S\d+\]", "", latest["answer"].text, flags=re.IGNORECASE).strip()
        display_answer = re.sub(r"\s+([.,;:])", r"\1", display_answer)
        st.markdown(
            f"<div class='answer-card'><div class='answer-text'>{html.escape(display_answer)}</div></div>",
            unsafe_allow_html=True,
        )
        if latest["answer"].mode == "no-evidence":
            st.caption("No sufficiently relevant evidence was found.")
            closest = latest.get("closest_hits", [])
            if closest:
                best = closest[0]
                minimum = latest.get("minimum_score", settings.default_min_score)
                st.warning(
                    f"The closest passage scored {best.score:.3f}; the configured minimum is "
                    f"{minimum:.3f}. The passage was not sent to Gemini because it did not meet "
                    "the relevance cutoff."
                )
                with st.expander("Inspect closest passages (below relevance cutoff)"):
                    render_sources(closest)
        else:
            st.caption("AI generation did not complete. Retrieved evidence is shown above.")
            if latest["answer"].error:
                with st.expander("Generation diagnostic"):
                    st.code(latest["answer"].error)
        if latest["hits"]:
            with st.expander(f"View source evidence ({len(latest['hits'])})"):
                render_sources(latest["hits"])


st.markdown("""
<div style="text-align:center;color:#8a96a8;font-size:12px;padding:26px 0 8px">
  DOCUMIND · ENTERPRISE DOCUMENT INTELLIGENCE · PORTFOLIO EDITION
</div>
""", unsafe_allow_html=True)
