"""
AUTOSAR HLD Document Analysis Assistant — Streamlit frontend.
'Engineering Blueprint' themed UI. Talks to the FastAPI backend only
through frontend/api_client.py — never touches the vector store or
DB directly, so frontend and backend stay cleanly separated.
"""
import sys
from pathlib import Path

# Make the project root importable so "backend.config" resolves regardless
# of the working directory Streamlit was launched from.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from frontend import api_client
from frontend.theme import BLUEPRINT_CSS

st.set_page_config(
    page_title="AUTOSAR HLD Analysis Assistant",
    page_icon="📐",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(BLUEPRINT_CSS, unsafe_allow_html=True)

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "selected_doc_ids" not in st.session_state:
    st.session_state.selected_doc_ids = []


def confidence_badge(confidence: str) -> str:
    css_class = {
        "High": "bp-badge-high",
        "Medium": "bp-badge-medium",
        "Low": "bp-badge-low",
        "Error": "bp-badge-error",
        "No evidence found": "bp-badge-noevidence",
    }.get(confidence, "bp-badge-medium")
    return f'<span class="bp-badge {css_class}">CONFIDENCE: {confidence.upper()}</span>'


def render_banner():
    st.markdown(
        """
        <div class="bp-banner">
            <div class="bp-icon">📐</div>
            <div>
                <h1 style="margin:0;border:none;padding:0;">AUTOSAR HLD DOCUMENT ANALYSIS ASSISTANT</h1>
                <div class="bp-sub">RAG-grounded architecture Q&amp;A · component &amp; interface extraction · revision comparison</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar():
    with st.sidebar:
        st.markdown("### 🩻 SYSTEM STATUS")
        ok, health = api_client.health()
        if ok:
            st.success("Backend online")
            st.caption(f"Documents indexed: **{health['documents_indexed']}**")
            st.caption(f"Vector chunks stored: **{health['chunks_in_vector_store']}**")
            st.caption(f"LLM provider: **{health['llm_provider']}** ({health.get('llm_model', '?')})")
            st.caption(f"OCR available: **{'yes' if health['ocr_available'] else 'no'}**")
        else:
            st.error(f"Backend unreachable: {health}")
            st.info("Start it with:  `uvicorn backend.main:app --reload`")

        st.markdown('<hr class="bp-divider">', unsafe_allow_html=True)
        st.markdown("### 📤 UPLOAD HLD DOCUMENT(S)")
        uploaded_files = st.file_uploader(
            "Drag & drop PDF files here",
            type=["pdf"],
            accept_multiple_files=True,
            label_visibility="collapsed",
        )
        if uploaded_files:
            for f in uploaded_files:
                key = f"uploaded_{f.name}_{f.size}"
                if st.session_state.get(key):
                    continue
                with st.spinner(f"Ingesting '{f.name}' — extracting, chunking, embedding..."):
                    success, result = api_client.upload_pdf(f.name, f.getvalue())
                if success:
                    st.session_state[key] = True
                    st.success(
                        f"✅ {f.name} — {result['pages']} pages, {result['chunks']} chunks"
                        + (f", {result['ocr_pages']} OCR page(s)" if result["ocr_pages"] else "")
                    )
                else:
                    st.error(f"❌ {f.name}: {result}")

        st.markdown('<hr class="bp-divider">', unsafe_allow_html=True)
        st.markdown("### 🗂️ DOCUMENT LIBRARY")
        ok, docs = api_client.list_documents()
        if not ok:
            st.warning("Could not load document list.")
            docs = []
        if not docs:
            st.caption("No documents uploaded yet.")
        selected = []
        for d in docs:
            col1, col2 = st.columns([5, 1])
            with col1:
                checked = st.checkbox(
                    f"{d['filename']}", key=f"chk_{d['doc_id']}", value=True
                )
                st.markdown(
                    f'<div class="bp-doc-chip">Pages: {d["pages"]} · Chunks: {d["chunks"]}'
                    f'{" · OCR: " + str(d["ocr_pages"]) if d["ocr_pages"] else ""}</div>',
                    unsafe_allow_html=True,
                )
            with col2:
                if st.button("🗑️", key=f"del_{d['doc_id']}"):
                    api_client.delete_document(d["doc_id"])
                    st.rerun()
            if checked:
                selected.append(d)
        st.session_state.selected_doc_ids = [d["doc_id"] for d in selected]
        st.session_state.selected_docs_meta = selected
        return docs


def tab_ask():
    st.markdown("#### 💬 Ask a question about the selected document(s)")
    docs = st.session_state.get("selected_docs_meta", [])
    if not docs:
        st.info("Upload and select at least one document from the sidebar to begin.")
        return

    if "question_input" not in st.session_state:
        st.session_state.question_input = ""

    example_cols = st.columns(3)
    examples = [
        "What components are described in this document?",
        "List the interfaces and their ports.",
        "Summarize the main functional flow.",
    ]
    for col, ex in zip(example_cols, examples):
        with col:
            if st.button(ex, key=f"ex_{ex}"):
                st.session_state.question_input = ex

    # IMPORTANT: this widget is bound to session_state via `key` only, with
    # no `value=` argument. Passing a changing `value` here (e.g. tied to
    # which button was clicked) makes Streamlit treat it as a new widget
    # identity on every rerun and silently reset it to "" — which is what
    # wiped out the question text right when the Ask button was clicked.
    question = st.text_input(
        "Your question",
        key="question_input",
        placeholder="e.g. What is the dependency between ComFacade and NetworkManager?",
        label_visibility="collapsed",
    )
    ask_clicked = st.button("🔎 Ask", type="primary")

    if ask_clicked and question.strip():
        with st.spinner("Retrieving evidence and generating a grounded answer..."):
            ok, result = api_client.ask(question.strip(), st.session_state.selected_doc_ids)
        if ok:
            st.session_state.chat_history.insert(0, {"question": question.strip(), **result})
        else:
            st.error(f"Failed to get an answer: {result}")

    for entry in st.session_state.chat_history:
        st.markdown(f"**❓ {entry['question']}**")
        st.markdown(confidence_badge(entry["confidence"]), unsafe_allow_html=True)
        # Rendered as markdown (not raw HTML) so tables/bold from the LLM display
        # properly and stray "<" characters in answers cannot break the layout.
        with st.container(border=True):
            st.markdown(entry["answer"])
        if entry.get("error"):
            st.warning(f"Note: {entry['error']}")
        if entry["citations"]:
            with st.expander(f"📎 View {len(entry['citations'])} source citation(s)"):
                for i, c in enumerate(entry["citations"], start=1):
                    st.markdown(
                        f'<div class="bp-card"><span class="bp-card-title">'
                        f'Source {i} — {c["filename"]} (page {c["page"]}, section: {c["section"]})</span>'
                        f'{c["excerpt"]}</div>',
                        unsafe_allow_html=True,
                    )
        st.markdown('<hr class="bp-divider">', unsafe_allow_html=True)


def tab_extraction():
    st.markdown("#### 🧩 Component / Interface / Signal Extraction")
    docs = st.session_state.get("selected_docs_meta", [])
    if not docs:
        st.info("Select at least one document from the sidebar.")
        return

    use_llm = st.checkbox(
        "AI-assisted (also asks the LLM; finds entities in any naming style, slower)",
        key="extract_use_llm",
    )
    if st.button("⚙️ Run extraction", type="primary"):
        with st.spinner("Scanning document content for architecture entities..."):
            ok, rows = api_client.extract_entities(st.session_state.selected_doc_ids, use_llm)
        if not ok:
            st.error(f"Extraction failed: {rows}")
            return
        if not rows:
            st.info("No recognizable AUTOSAR entities were found using the current heuristics.")
            return

        import pandas as pd
        df = pd.DataFrame(rows)
        for entity_type in df["type"].unique():
            st.markdown(f"**{entity_type}s**")
            st.dataframe(
                df[df["type"] == entity_type][["name", "filename", "page", "section"]],
                use_container_width=True,
                hide_index=True,
            )


def tab_compare():
    st.markdown("#### 🔍 Revision Comparison")
    docs = st.session_state.get("selected_docs_meta", [])
    ok, all_docs = api_client.list_documents()
    if not ok or len(all_docs) < 2:
        st.info("Upload at least two documents to compare revisions.")
        return

    options = {f"{d['filename']} ({d['doc_id']})": d for d in all_docs}
    col1, col2 = st.columns(2)
    with col1:
        choice_a = st.selectbox("Document A", list(options.keys()), key="cmp_a")
    with col2:
        choice_b = st.selectbox("Document B", list(options.keys()), index=min(1, len(options) - 1), key="cmp_b")

    if st.button("🆚 Compare documents", type="primary"):
        doc_a, doc_b = options[choice_a], options[choice_b]
        if doc_a["doc_id"] == doc_b["doc_id"]:
            st.warning("Please choose two different documents.")
            return
        with st.spinner("Comparing sections and flagging inconsistencies..."):
            ok, findings = api_client.compare_documents(
                doc_a["doc_id"], doc_a["filename"], doc_b["doc_id"], doc_b["filename"]
            )
        if not ok:
            st.error(f"Comparison failed: {findings}")
            return
        if not findings:
            st.success("No structural differences detected between these documents.")
            return

        status_class = {
            "Modified": "bp-status-modified",
            "Only in A": "bp-status-onlyina",
            "Only in B": "bp-status-onlyinb",
            "Entity added": "bp-status-added",
            "Entity removed": "bp-status-removed",
        }
        for f in findings:
            cls = status_class.get(f["status"], "")
            st.markdown(
                f'<div class="bp-card"><span class="bp-card-title">'
                f'<span class="{cls}">[{f["status"]}]</span> {f["section"]}</span>{f["detail"]}</div>',
                unsafe_allow_html=True,
            )


def tab_history():
    st.markdown("#### 📜 Q&A History & Export")
    ok, history = api_client.get_history()
    if not ok:
        st.error(f"Could not load history: {history}")
        return
    if not history:
        st.info("No questions have been asked yet.")
        return

    import pandas as pd
    import time as time_mod

    flat = [
        {
            "Asked At": time_mod.strftime("%Y-%m-%d %H:%M:%S", time_mod.localtime(h["asked_at"])),
            "Question": h["question"],
            "Confidence": h["confidence"],
            "Citations": len(h["citations"]),
        }
        for h in history
    ]
    st.dataframe(pd.DataFrame(flat), use_container_width=True, hide_index=True)

    col1, col2 = st.columns(2)
    with col1:
        st.link_button("⬇️ Download as JSON", api_client.export_url("json"))
    with col2:
        st.link_button("⬇️ Download as CSV", api_client.export_url("csv"))


def main():
    render_banner()
    render_sidebar()

    tabs = st.tabs(["💬 Ask", "🧩 Extraction", "🔍 Compare", "📜 History & Export"])
    with tabs[0]:
        tab_ask()
    with tabs[1]:
        tab_extraction()
    with tabs[2]:
        tab_compare()
    with tabs[3]:
        tab_history()


if __name__ == "__main__":
    main()
