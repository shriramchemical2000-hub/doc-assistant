from __future__ import annotations

import os
import uuid
import streamlit as st

from config import get_settings
from src.doc_assistant.ingestion.loader import load_uploaded_file
from src.doc_assistant.rag.answer import AnswerService
from src.doc_assistant.rag.chunking import chunk_pages
from src.doc_assistant.rag.embeddings import SentenceTransformerEmbedder
from src.doc_assistant.rag.retriever import Retriever
from src.doc_assistant.storage.sqlite_store import SQLiteStore

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
:root { --ink:#172033; --muted:#68758a; --line:#e6eaf0; --brand:#315efb; --teal:#0c9b8e; }
html, body, [class*="css"] { font-family:'DM Sans',sans-serif; }
.stApp { background: #f6f8fc; }
.block-container { max-width: 1440px; padding-top: 1.35rem; padding-bottom: 3rem; }
[data-testid="stSidebar"] { background: #101a2d; border-right: 1px solid #253149; }
[data-testid="stSidebar"] * { color: #eaf0fb !important; }
[data-testid="stSidebar"] [data-testid="stFileUploader"] section { background:#1b2941; border:1px dashed #50617e; }
[data-testid="stSidebar"] button { border-radius:10px; }
.hero {
  position:relative; overflow:hidden; padding:30px 34px; border-radius:22px;
  color:white; background:linear-gradient(115deg,#101a2d 0%,#1d3560 55%,#315efb 100%);
  box-shadow:0 16px 38px rgba(25,48,91,.16); margin-bottom:22px;
}
.hero:after { content:""; position:absolute; width:280px; height:280px; right:5%; top:-150px;
  border:1px solid rgba(255,255,255,.18); border-radius:50%; box-shadow:0 0 0 35px rgba(255,255,255,.035),0 0 0 70px rgba(255,255,255,.025); }
.hero-kicker { text-transform:uppercase; letter-spacing:2px; font-size:11px; font-weight:700; color:#b9cbff; }
.hero h1 { font-family:'Manrope',sans-serif; font-size:36px; letter-spacing:-1.4px; margin:7px 0 5px; color:white; }
.hero p { color:#d7e2fb; font-size:15px; margin:0; max-width:720px; }
.hero-pill { display:inline-block; margin-top:18px; padding:6px 11px; border:1px solid rgba(255,255,255,.25);
  border-radius:30px; font-size:11px; color:#eff4ff; background:rgba(255,255,255,.08); }
.section-title { font-family:'Manrope',sans-serif; color:#172033; font-weight:800; font-size:19px; letter-spacing:-.4px; }
.subtle { color:#718096; font-size:13px; }
.panel { background:white; border:1px solid #e6eaf0; border-radius:17px; padding:19px 20px; }
.stat { background:white; border:1px solid #e6eaf0; border-radius:15px; padding:14px 17px; }
.stat-label { color:#718096; font-size:11px; text-transform:uppercase; letter-spacing:1px; font-weight:700; }
.stat-value { color:#172033; font-family:'Manrope',sans-serif; font-size:24px; font-weight:800; margin-top:3px; }
.answer-card { background:white; border:1px solid #e3e9f3; border-left:4px solid #315efb; border-radius:15px; padding:20px 22px; }
div[data-testid="stTextArea"] textarea { border-radius:12px; border:1px solid #dce3ee; background:#fff; }
.stButton>button { border-radius:10px; font-weight:700; min-height:42px; }
div[data-testid="stExpander"] { background:white; border:1px solid #e6eaf0; border-radius:12px; }
div[data-testid="stAlert"] { border-radius:12px; }
footer {visibility:hidden;}
#MainMenu {visibility:hidden;}
@media (max-width: 800px) { .hero {padding:24px;} .hero h1 {font-size:29px;} }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <div class="hero-kicker">Enterprise knowledge, made accessible</div>
  <h1>DocuMind<span style="color:#91b1ff">.</span></h1>
  <p>Your document intelligence workspace. Ask questions across PDFs, Word files and text documents — with answers grounded in traceable source evidence.</p>
  <span class="hero-pill">SOURCE-GROUNDED ANSWERS · RETRIEVAL-AUGMENTED GENERATION</span>
</div>
""", unsafe_allow_html=True)

if "documind_session_id" not in st.session_state:
    st.session_state["documind_session_id"] = uuid.uuid4().hex
if "documind_history" not in st.session_state:
    st.session_state["documind_history"] = []

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
            st.caption(f"Evidence reference [S{index}]  |  Chunk {item.chunk_id}")
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
        st.session_state["documind_history"] = []
        st.rerun()
    st.markdown("---")
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

st.write("")
main_col, guide_col = st.columns([1.7, 1], gap="large")

with main_col:
    st.markdown("<div class='section-title'>Ask your documents</div>", unsafe_allow_html=True)
    st.markdown("<div class='subtle'>Ask a focused question. DocuMind will retrieve relevant passages and show exactly where the evidence came from.</div>", unsafe_allow_html=True)
    question = st.text_area(
        "Question",
        placeholder="For example: What is the annual leave entitlement, and are there any eligibility conditions?",
        height=105,
        label_visibility="collapsed",
    )
    ask_col, clear_col = st.columns([1, 5])
    with ask_col:
        ask = st.button("Ask DocuMind  →", type="primary", disabled=not question.strip(), use_container_width=True)
    with clear_col:
        if st.button("Clear question", use_container_width=False):
            st.session_state["documind_history"] = []
            st.rerun()

    if ask:
        if not store.count_chunks():
            st.warning("Add and index a document before asking a question.")
        else:
            with st.spinner("Searching your documents and preparing an evidence-based response…"):
                hits = retriever.search(question, top_k=settings.default_top_k)
                hits = [hit for hit in hits if hit.score >= settings.default_min_score]
                answer = answer_service.answer(question, hits)
            st.session_state["documind_history"].insert(0, {
                "question": question, "answer": answer, "hits": hits,
            })

    if st.session_state["documind_history"]:
        for item in st.session_state["documind_history"]:
            st.markdown("#### Question")
            st.markdown(f"**{item['question']}**")
            st.markdown("#### DocuMind response")
            st.markdown("<div class='answer-card'>", unsafe_allow_html=True)
            st.write(item["answer"].text)
            st.markdown("</div>", unsafe_allow_html=True)
            mode = item["answer"].mode
            if mode == "ollama":
                st.caption(f"Generated by the server-hosted Ollama model · {settings.ollama_model}. Verify the cited passages.")
            elif mode == "gemini":
                st.caption("Generated by Gemini using retrieved evidence. Verify the cited passages.")
            elif mode == "no-evidence":
                st.caption("No sufficiently relevant evidence was retrieved.")
            else:
                st.caption("Evidence-only response: the generation service was unavailable or not configured.")
            if item["hits"]:
                st.markdown("**Retrieved source evidence**")
                render_sources(item["hits"])
            st.markdown("---")
    else:
        st.markdown("""
        <div class="panel" style="margin-top:16px">
          <div style="font-weight:700;color:#26334b;margin-bottom:6px">Your answers, with receipts.</div>
          <div class="subtle">Once you index a document, ask about policies, procedures, definitions, responsibilities or specific facts. Source passages appear beneath each response.</div>
        </div>
        """, unsafe_allow_html=True)

with guide_col:
    st.markdown("<div class='section-title'>How DocuMind works</div>", unsafe_allow_html=True)
    st.markdown("""
    <div class="panel">
      <div style="font-weight:700;color:#26334b">01 &nbsp; Ingest</div>
      <div class="subtle">Extract text and page metadata from PDF, DOCX and TXT files.</div>
      <hr style="border:0;border-top:1px solid #edf0f5;margin:14px 0">
      <div style="font-weight:700;color:#26334b">02 &nbsp; Understand</div>
      <div class="subtle">Create overlapping text chunks and local semantic embeddings.</div>
      <hr style="border:0;border-top:1px solid #edf0f5;margin:14px 0">
      <div style="font-weight:700;color:#26334b">03 &nbsp; Retrieve</div>
      <div class="subtle">Find the most relevant passages for each question.</div>
      <hr style="border:0;border-top:1px solid #edf0f5;margin:14px 0">
      <div style="font-weight:700;color:#26334b">04 &nbsp; Explain</div>
      <div class="subtle">The hosted language model drafts an answer using retrieved evidence and source IDs.</div>
    </div>
    """, unsafe_allow_html=True)
    st.write("")
    st.markdown("<div class='panel'>", unsafe_allow_html=True)
    st.markdown("**Try the sample question**")
    st.code("How many days of annual leave are provided?", language="text")
    st.caption("Sample document: `data/sample_documents/employee_handbook_sample.txt`")
    st.markdown("</div>", unsafe_allow_html=True)
    st.info("Grounding is not a mathematical guarantee. Always inspect the cited source passages, especially for compliance or policy decisions.")

st.markdown("""
<div style="text-align:center;color:#8a96a8;font-size:12px;padding:26px 0 8px">
  DOCUMIND · ENTERPRISE DOCUMENT INTELLIGENCE · PORTFOLIO EDITION
</div>
""", unsafe_allow_html=True)
