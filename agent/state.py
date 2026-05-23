from typing import TypedDict, Optional


class AgentState(TypedDict):
    # ── inputs ──────────────────────────────────────────
    document_id:        str
    session_id:         str
    raw_text:           str
    file_name:          str
    file_type:          str
    language_preference: str        # "en" | "ta"
    detected_language:  str         # auto-detected from document

    # ── classification ──────────────────────────────────
    document_type:      str         # rental | notice | order | contract | govt_letter | unknown
    document_subtype:   str         # eviction_notice | police_notice | tax_demand | etc.
    confidence:         float

    # ── analysis ────────────────────────────────────────
    key_clauses:        list[dict]
    obligations:        list[dict]
    parties:            list[dict]
    important_dates:    list[dict]

    # ── flags ────────────────────────────────────────────
    flagged_clauses:    list[dict]
    risk_level:         str         # low | medium | high | critical

    # ── rag context ──────────────────────────────────────
    rag_context:        list[dict]  # pre-populated before agent starts
    web_search_used:    bool

    # ── outputs ──────────────────────────────────────────
    explanation_en:     str
    explanation_ta:     Optional[str]
    action_items:       list[dict]

    # ── meta ─────────────────────────────────────────────
    errors:             list[str]
    node_timings:       dict[str, float]
    langfuse_trace_id:  str


def initial_state(
    document_id: str,
    session_id: str,
    file_name: str,
    file_type: str,
    language_preference: str = "en",
) -> AgentState:
    return AgentState(
        document_id=document_id,
        session_id=session_id,
        raw_text="",
        file_name=file_name,
        file_type=file_type,
        language_preference=language_preference,
        detected_language="en",
        document_type="",
        document_subtype="",
        confidence=0.0,
        key_clauses=[],
        obligations=[],
        parties=[],
        important_dates=[],
        flagged_clauses=[],
        risk_level="low",
        rag_context=[],
        web_search_used=False,
        explanation_en="",
        explanation_ta=None,
        action_items=[],
        errors=[],
        node_timings={},
        langfuse_trace_id="",
    )