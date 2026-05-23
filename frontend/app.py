import os
import json
import uuid
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Legal Aid",
    page_icon="⚖️",
    layout="wide",
)

# ── Session state ────────────────────────────────────────────
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "result" not in st.session_state:
    st.session_state.result = None

# ── Helpers ──────────────────────────────────────────────────
RISK_COLORS = {
    "low":      "🟢",
    "medium":   "🟡",
    "high":     "🔴",
    "critical": "🚨",
}

FLAG_COLORS = {
    "ILLEGAL":    "🔴",
    "UNFAIR":     "🟠",
    "SUSPICIOUS": "🟡",
    "MISSING":    "🔵",
}


def _parse(val):
    if isinstance(val, str):
        try:
            return json.loads(val)
        except Exception:
            return val
    return val


def render_explanation(explanation: dict, lang: str):
    data = _parse(explanation.get(lang)) or _parse(explanation.get("en")) or {}
    if not data:
        st.info("No explanation available.")
        return

    st.subheader("📄 What is this document?")
    st.write(data.get("what_is_this", ""))

    st.subheader("📬 Why did you receive it?")
    st.write(data.get("why_you_received_it", ""))

    st.subheader("💡 What it means for you")
    for point in data.get("what_it_means_for_you", []):
        st.markdown(f"- {point}")

    st.subheader("⚖️ Your rights")
    st.write(data.get("your_rights", ""))

    st.subheader("📋 Overall summary")
    st.info(data.get("overall_summary", ""))


def render_action_items(action_items: list):
    if not action_items:
        st.info("No action items.")
        return

    for i, item in enumerate(action_items):
        urgency = item.get("urgency", "no_rush")
        color = {
            "immediate":     "🔴",
            "within_week":   "🟠",
            "within_month":  "🟡",
            "no_rush":       "🟢",
        }.get(urgency, "⚪")

        with st.expander(f"{color} {item.get('action', f'Action {i+1}')}"):
            if item.get("deadline"):
                st.markdown(f"**Deadline:** {item['deadline']}")
            st.markdown(f"**Urgency:** {urgency.replace('_', ' ').title()}")
            if item.get("consequence_if_ignored"):
                st.markdown(f"**If ignored:** {item['consequence_if_ignored']}")


def render_flags(flagged_clauses: list):
    if not flagged_clauses:
        st.success("No red flags found in this document.")
        return

    for flag in flagged_clauses:
        flag_type = flag.get("flag_type", "UNKNOWN")
        severity  = flag.get("severity", "low")
        icon      = FLAG_COLORS.get(flag_type, "⚪")

        with st.expander(f"{icon} {flag_type} — {severity.upper()}"):
            st.markdown(f"**Reason:** {flag.get('reason', '')}")
            if flag.get("legal_basis"):
                st.markdown(f"**Legal basis:** {flag['legal_basis']}")
            if flag.get("recommended_action"):
                st.markdown(f"**What to do:** {flag['recommended_action']}")


def render_clauses(key_clauses: list):
    if not key_clauses:
        st.info("No clauses extracted.")
        return

    for clause in key_clauses:
        with st.expander(f"📌 {clause.get('clause_type', 'Clause').replace('_', ' ').title()}"):
            st.markdown(f"**Text:** {clause.get('text', '')}")
            st.markdown(f"**Meaning:** {clause.get('plain_meaning', '')}")


def render_rag_sources(rag_sources: list, web_used: bool):
    if not rag_sources:
        return
    st.caption(f"{'🌐 Web search used · ' if web_used else ''}📚 {len(rag_sources)} legal references consulted")
    with st.expander("View sources"):
        for src in rag_sources:
            title = src.get("title", "Legal reference")
            url   = src.get("url", "")
            source = src.get("source", "vector")
            icon  = "🌐" if source == "web" else "📚"
            if url:
                st.markdown(f"{icon} [{title}]({url})")
            else:
                st.markdown(f"{icon} {title}")


# ── Main UI ──────────────────────────────────────────────────
st.title("⚖️ Legal Aid")
st.caption("Upload any legal document — rental agreement, notice, govt letter — and understand it instantly.")

with st.sidebar:
    st.header("Settings")
    language = st.radio(
        "Language",
        options=["en", "ta"],
        format_func=lambda x: "English" if x == "en" else "தமிழ்",
        index=0,
    )
    st.divider()
    st.caption(f"Session: `{st.session_state.session_id[:8]}...`")
    if st.button("New session"):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.result = None
        st.rerun()

# ── Upload ───────────────────────────────────────────────────
uploaded = st.file_uploader(
    "Upload document",
    type=["pdf", "jpg", "jpeg", "png", "txt"],
    help="Supported: PDF, images (JPG/PNG), text files. Max 10MB.",
)

if uploaded:
    col1, col2 = st.columns([3, 1])
    with col1:
        st.caption(f"📎 {uploaded.name} · {round(uploaded.size / 1024, 1)} KB")
    with col2:
        analyze_btn = st.button("Analyze document", type="primary", use_container_width=True)

    if analyze_btn:
        with st.spinner("Analyzing document... this may take 20-40 seconds"):
            try:
                response = requests.post(
                    f"{API_URL}/analyze",
                    files={"file": (uploaded.name, uploaded.getvalue(), uploaded.type)},
                    data={
                        "language_preference": language,
                        "session_id":          st.session_state.session_id,
                    },
                    timeout=120,
                )
                if response.status_code == 200:
                    st.session_state.result = response.json()
                else:
                    st.error(f"Error {response.status_code}: {response.text}")
            except requests.exceptions.Timeout:
                st.error("Request timed out. Please try again.")
            except Exception as e:
                st.error(f"Failed to connect to API: {str(e)}")

# ── Results ──────────────────────────────────────────────────
if st.session_state.result:
    r = st.session_state.result

    # Header
    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        doc_type = (r.get("document_type") or "unknown").replace("_", " ").title()
        st.metric("Document type", doc_type)
    with col2:
        risk = r.get("risk_level", "low")
        st.metric("Risk level", f"{RISK_COLORS.get(risk, '')} {risk.upper()}")
    with col3:
        st.metric("Flags found", len(r.get("flagged_clauses", [])))

    st.divider()

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📖 Explanation",
        "✅ Action items",
        "🚩 Red flags",
        "📋 Clauses",
    ])

    with tab1:
        render_explanation(r.get("explanation", {}), language)

    with tab2:
        action_items = r.get("action_items", [])
        if not action_items:
            expl = _parse(r.get("explanation", {}).get(language) or r.get("explanation", {}).get("en"))
            if isinstance(expl, dict):
                action_items = expl.get("action_items", [])
        render_action_items(action_items)

    with tab3:
        render_flags(r.get("flagged_clauses", []))

    with tab4:
        render_clauses(r.get("key_clauses", []))

    render_rag_sources(r.get("rag_sources", []), r.get("web_search_used", False))

    if r.get("errors"):
        with st.expander("⚠️ Processing warnings"):
            for err in r["errors"]:
                st.caption(err)