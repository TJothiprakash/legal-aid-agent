import os
import time
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END

from agent.state import AgentState, initial_state
from agent.nodes import (
    ingest_node,
    classify_node,
    analyze_node,
    flag_node,
    explain_node,
)
from agent.rag import (
    build_rag_query,
    retrieve,
    embed_text,
    grade_chunks,
    reciprocal_rank_fusion,
    web_search,
)
from db.repositories.documents import (
    create_document,
    complete_document,
    fail_document,
)

load_dotenv()


def _run_rag_prestep(state: AgentState) -> AgentState:
    raw_text = state.get("raw_text", "")
    if not raw_text:
        return state

    try:
        queries = build_rag_query(raw_text)
    except Exception:
        queries = [raw_text[:300]]

    # Track A — pgvector
    try:
        vector_results = retrieve(queries, k=10)
    except Exception:
        vector_results = []

    # Grade vector results
    try:
        graded = grade_chunks(vector_results, raw_text)
    except Exception:
        graded = vector_results

    web_results = []
    web_used = False

    # Track B — web search (fallback only, if < 3 good chunks)
    if len(graded) < 3:
        try:
            web_results = web_search(queries, max_results=5)
            web_used = True
        except Exception:
            web_results = []

    # Merge via RRF
    final_context = reciprocal_rank_fusion(graded, web_results)

    return {
        **state,
        "rag_context":    final_context,
        "web_search_used": web_used,
    }


def _should_continue_after_classify(state: AgentState) -> str:
    if state.get("document_type") == "unknown":
        return "unknown_handler"
    return "analyze"


def _unknown_handler_node(state: AgentState) -> AgentState:
    explanation = json.dumps({
        "what_is_this": "We could not determine the type of this document with confidence.",
        "why_you_received_it": "Please ensure the document is clear and legible.",
        "what_it_means_for_you": ["Upload a clearer version of the document."],
        "your_rights": "You have the right to seek legal advice.",
        "action_items": [],
        "red_flags": [],
        "overall_summary": "Document type could not be classified. Please try again with a clearer document or provide more context.",
    })
    return {
        **state,
        "explanation_en": explanation,
        "risk_level": "low",
    }


def build_graph() -> StateGraph:
    import json

    graph = StateGraph(AgentState)

    graph.add_node("ingest",          ingest_node)
    graph.add_node("classify",        classify_node)
    graph.add_node("analyze",         analyze_node)
    graph.add_node("flag",            flag_node)
    graph.add_node("explain",         explain_node)
    graph.add_node("unknown_handler", _unknown_handler_node)

    graph.set_entry_point("ingest")

    graph.add_edge("ingest", "classify")

    graph.add_conditional_edges(
        "classify",
        _should_continue_after_classify,
        {
            "analyze":         "analyze",
            "unknown_handler": "unknown_handler",
        }
    )

    graph.add_edge("analyze",         "flag")
    graph.add_edge("flag",            "explain")
    graph.add_edge("explain",         END)
    graph.add_edge("unknown_handler", END)

    return graph.compile()


def run_pipeline(
    file_bytes:          bytes,
    file_name:           str,
    file_type:           str,
    session_id:          str,
    language_preference: str = "en",
) -> dict:
    import json

    doc_id = create_document(session_id, file_name, file_type)

    state = initial_state(
        document_id=doc_id,
        session_id=session_id,
        file_name=file_name,
        file_type=file_type,
        language_preference=language_preference,
    )
    state["_file_bytes"] = file_bytes

    # RAG pre-step — ingest text first, then retrieve
    try:
        state = ingest_node(state)
        state = _run_rag_prestep(state)
    except Exception as e:
        fail_document(doc_id, str(e))
        raise

    # Remove raw bytes before passing to graph
    state.pop("_file_bytes", None)

    graph = build_graph()

    try:
        # Skip ingest in graph since we already ran it
        # Feed state directly from classify onward
        final_state = state

        # Run classify → analyze → flag → explain manually
        # (graph entry is ingest but raw_text is already populated)
        final_state = classify_node(final_state)

        if final_state.get("document_type") == "unknown":
            import json as _json
            final_state["explanation_en"] = _json.dumps({
                "what_is_this": "Could not classify this document.",
                "why_you_received_it": "Please upload a clearer document.",
                "what_it_means_for_you": [],
                "your_rights": "",
                "action_items": [],
                "red_flags": [],
                "overall_summary": "Document type unclear. Please try again.",
            })
            final_state["risk_level"] = "low"
        else:
            final_state = analyze_node(final_state)
            final_state = flag_node(final_state)
            final_state = explain_node(final_state)

        complete_document(doc_id, final_state)
        return _build_response(doc_id, final_state)

    except Exception as e:
        fail_document(doc_id, str(e))
        raise


def _build_response(doc_id: str, state: AgentState) -> dict:
    import json

    def _parse(val):
        if isinstance(val, str):
            try:
                return json.loads(val)
            except Exception:
                return val
        return val

    return {
        "analysis_id":      doc_id,
        "document_type":    state.get("document_type"),
        "document_subtype": state.get("document_subtype"),
        "risk_level":       state.get("risk_level"),
        "confidence":       state.get("confidence"),
        "explanation":      {
            "en": _parse(state.get("explanation_en")),
            "ta": _parse(state.get("explanation_ta")),
        },
        "key_clauses":      state.get("key_clauses", []),
        "flagged_clauses":  state.get("flagged_clauses", []),
        "action_items":     state.get("action_items", []),
        "parties":          state.get("parties", []),
        "important_dates":  state.get("important_dates", []),
        "rag_sources":      [
            {
                "title":  c.get("title", ""),
                "source": c.get("source", "vector"),
                "url":    c.get("source_url") or c.get("url", ""),
            }
            for c in state.get("rag_context", [])
        ],
        "web_search_used":  state.get("web_search_used", False),
        "node_timings":     state.get("node_timings", {}),
        "errors":           state.get("errors", []),
        "detected_language": state.get("detected_language", "en"),
    }