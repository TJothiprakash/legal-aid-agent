import pytest
from agent.state import initial_state
from agent.nodes.ingest_node import ingest_node
from agent.nodes.classify_node import classify_node


def make_state(**kwargs):
    s = initial_state(
        document_id="test-id",
        session_id="test-session",
        file_name="test.txt",
        file_type="txt",
    )
    s.update(kwargs)
    return s


def test_ingest_plain_text():
    state = make_state()
    state["_file_bytes"] = b"This is a rental agreement between landlord and tenant."
    state["file_type"] = "txt"
    result = ingest_node(state)
    assert result["raw_text"] != ""
    assert result["detected_language"] in ("en", "ta")
    assert "ingest" in result["node_timings"]


def test_ingest_empty_file():
    state = make_state()
    state["_file_bytes"] = b""
    state["file_type"] = "txt"
    result = ingest_node(state)
    assert result["raw_text"] == ""


def test_classify_known_document():
    state = make_state(
        raw_text="""NOTICE TO VACATE
        You are hereby required to vacate the premises within 30 days.
        Failure to comply will result in legal action."""
    )
    result = classify_node(state)
    assert result["document_type"] != ""
    assert 0.0 <= result["confidence"] <= 1.0
    assert "classify" in result["node_timings"]


def test_classify_unknown_document():
    state = make_state(raw_text="random gibberish xyz abc 123")
    result = classify_node(state)
    assert result["document_type"] in (
        "unknown", "rental_agreement", "eviction_notice",
        "police_notice", "court_order", "tax_demand",
        "employment_contract", "govt_letter", "consumer_complaint",
        "fir",
    )