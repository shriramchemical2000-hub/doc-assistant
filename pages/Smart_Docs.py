from __future__ import annotations

import os
import streamlit as st

from config import get_settings
from src.doc_assistant.ingestion.loader import load_uploaded_file
from src.doc_assistant.rag.smart_docs import SmartDocsService

st.set_page_config(
    page_title="DocuMind | Smart Docs",
    page_icon="◈",
    layout="wide",
)

# Read secrets only on the server; never expose the API key in the UI.
try:
    for key in ("GEMINI_API_KEY", "GEMINI_MODEL"):
        if st.secrets.get(key) is not None:
            os.environ[key] = str(st.secrets[key])
except Exception:
    pass

settings = get_settings()

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
html, body, [class*="css"] { font-family:'DM Sans',sans-serif; }
.stApp {
  background:
    radial-gradient(ellipse at 80% 12%,rgba(167,190,112,.19),transparent 34%),
    radial-gradient(ellipse at 25% 40%,rgba(49,125,101,.22),transparent 42%),
    linear-gradient(135deg,#061411 0%,#0b211c 48%,#101d18 100%);
}
.block-container { max-width:1250px; padding-top:1.5rem; padding-bottom:3rem; }
[data-testid="stHeader"] { background:transparent; }
[data-testid="stSidebar"] {
  background:linear-gradient(180deg,rgba(9,30,25,.98),rgba(11,35,29,.96));
  border-right:1px solid rgba(205,235,220,.13);
}
[data-testid="stSidebar"] * { color:#e5f2e9; }
.hero {
  padding:28px 30px; border-radius:22px; margin-bottom:22px;
  background:linear-gradient(115deg,rgba(19,54,45,.94),rgba(41,83,68,.82) 58%,rgba(119,126,76,.62));
  border:1px solid rgba(221,245,225,.2);
  box-shadow:0 18px 55px rgba(0,0,0,.22);
}
.kicker { text-transform:uppercase; letter-spacing:2px; font-size:10px; font-weight:700; color:#b9dfc7; }
.hero h1 { font-family:'Manrope',sans-serif; font-size:36px; margin:6px 0; color:#f4fff7; }
.hero p { color:#d3e7d9; margin:0; font-size:14px; }
.stMarkdown, .stMarkdown p, .stMarkdown li, label { color:#e5f1e8; }
.stCaption, [data-testid="stCaptionContainer"] { color:#a9bdaf !important; }
.stButton>button {
  border-radius:11px; font-weight:700; min-height:44px;
  border:1px solid rgba(190,231,202,.2);
  background:rgba(164,218,183,.1); color:#effff3;
}
.stButton>button[kind="primary"] {
  background:linear-gradient(110deg,#4a9d78,#72c69a); color:#092017; border:0;
}
div[data-testid="stTextArea"] textarea {
  border-radius:12px; background:rgba(6,22,18,.72); color:#f0fff4;
}
div[data-testid="stFileUploader"] section {
  border-radius:14px; background:rgba(255,255,255,.045);
  border:1px dashed rgba(177,220,194,.4);
}
div[data-testid="stExpander"] {
  background:rgba(17,43,36,.75); border:1px solid rgba(205,235,220,.13); border-radius:12px;
}
footer {visibility:hidden;} #MainMenu {visibility:hidden;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <div class="kicker">DocuMind · Document intelligence workspace</div>
  <h1>Smart Docs</h1>
  <p>Turn lengthy documents into structured knowledge. Summarise large files, draft process SOPs, or translate existing procedures into plain language.</p>
</div>
""", unsafe_allow_html=True)

st.markdown("### Choose a workflow")
task = st.radio(
    "Smart Docs workflow",
    [
        "Summarise document",
        "Create an SOP",
        "Explain an existing SOP",
    ],
    horizontal=True,
    label_visibility="collapsed",
    key="smart_docs_task",
)

descriptions = {
    "Summarise document": "Create an executive summary, section-by-section breakdown, and key takeaways from a lengthy document.",
    "Create an SOP": "Draft a structured SOP with purpose, scope, responsibilities, inputs, ordered steps, decision points, records, and escalation paths.",
    "Explain an existing SOP": "Rewrite a procedure in plain language, explaining the sequence, roles, checks, and important cautions.",
}
st.info(descriptions[task])

st.markdown("### 1 · Upload your source document")
smart_file = st.file_uploader(
    "Choose a PDF, Word document, or text file",
    type=["pdf", "docx", "txt"],
    accept_multiple_files=False,
    key="smart_docs_upload",
    help="Maximum file size: 20 MB. Long documents are processed in sections.",
)

st.markdown("### 2 · Add optional guidance")
smart_context = st.text_area(
    "What should DocuMind focus on?",
    placeholder="Example: Focus on operating limits, maintenance responsibilities, safety checks and escalation criteria.",
    height=90,
    key="smart_docs_context",
)

if st.button("Generate document output  →", type="primary", use_container_width=True, disabled=not smart_file):
    if not settings.gemini_api_key:
        st.error("Gemini is not configured. Add GEMINI_API_KEY in the app's server-side Streamlit Secrets.")
    else:
        try:
            pages = load_uploaded_file(smart_file.name, smart_file.getvalue())
            full_text = "\n\n".join(
                f"[Page {page.page}]\n{page.text}" for page in pages if page.text.strip()
            )
            if not full_text.strip():
                st.error("No readable text was found. Scanned/image-only PDFs are not supported yet.")
            else:
                with st.spinner("Processing your document in sections and preparing the result…"):
                    service = SmartDocsService(settings)
                    result = service.run(
                        full_text,
                        task=task,
                        instructions=smart_context.strip(),
                    )
                st.session_state["smart_docs_result"] = {
                    "filename": smart_file.name,
                    "task": task,
                    "text": result,
                }
        except Exception as exc:
            st.error(f"Smart Docs could not complete the request: {str(exc)[:600]}")

if st.session_state.get("smart_docs_result"):
    result = st.session_state["smart_docs_result"]
    st.markdown("---")
    st.markdown("### Generated output")
    st.caption(f"{result['task']} · Source: {result['filename']}")
    st.markdown(result["text"])
    st.download_button(
        "Download result as Markdown",
        data=result["text"],
        file_name="documind_smart_docs_result.md",
        mime="text/markdown",
        use_container_width=True,
    )
