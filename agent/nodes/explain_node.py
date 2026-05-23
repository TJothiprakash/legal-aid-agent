import json
import os
import re
import time
import yaml
import google.generativeai as genai
from pathlib import Path
from agent.state import AgentState
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def _load_prompt(filename: str) -> dict:
    with open(PROMPTS_DIR / filename, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _format_rag_context(rag_context: list[dict]) -> str:
    if not rag_context:
        return "No legal context available."
    lines = []
    for i, chunk in enumerate(rag_context[:4]):
        title = chunk.get("title", "Legal reference")
        text  = chunk.get("chunk_text", "")[:200]
        lines.append(f"[{i+1}] {title}: {text}")
    return "\n".join(lines)


def _call_llm(prompt_cfg: dict, variables: dict) -> dict:
    human = prompt_cfg["human_template"].format(**variables)
    model = genai.GenerativeModel(
        model_name=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
        system_instruction=prompt_cfg["system"],
    )
    response = model.generate_content(human)
    raw = re.sub(r"```json|```", "", response.text).strip()
    return json.loads(raw)


def explain_node(state: AgentState) -> AgentState:
    start = time.time()
    errors = list(state.get("errors", []))
    explanation_en = ""
    explanation_ta = None
    action_items   = []

    # ── English explanation ──────────────────────────────
    try:
        prompt_en = _load_prompt("explain_en.yaml")
        result_en = _call_llm(prompt_en, {
            "document_type":    state["document_type"],
            "document_subtype": state["document_subtype"],
            "parties":          json.dumps(state.get("parties", []), indent=2),
            "key_clauses":      json.dumps(state.get("key_clauses", []), indent=2),
            "obligations":      json.dumps(state.get("obligations", []), indent=2),
            "important_dates":  json.dumps(state.get("important_dates", []), indent=2),
            "flagged_clauses":  json.dumps(state.get("flagged_clauses", []), indent=2),
            "risk_level":       state.get("risk_level", "low"),
            "rag_context":      _format_rag_context(state.get("rag_context", [])),
        })
        explanation_en = json.dumps(result_en)
        action_items   = result_en.get("action_items", [])

    except Exception as e:
        errors.append(f"explain_node (en) error: {str(e)}")

    # ── Tamil explanation ────────────────────────────────
    needs_tamil = (
        state.get("language_preference") == "ta"
        or state.get("detected_language") == "ta"
    )

    if needs_tamil and explanation_en:
        try:
            prompt_ta = _load_prompt("explain_ta.yaml")
            result_ta = _call_llm(prompt_ta, {
                "explanation_en": explanation_en,
                "document_type":  state["document_type"],
                "risk_level":     state.get("risk_level", "low"),
            })
            explanation_ta = json.dumps(result_ta)

        except Exception as e:
            errors.append(f"explain_node (ta) error: {str(e)}")

    timings = dict(state.get("node_timings", {}))
    timings["explain"] = round(time.time() - start, 3)

    return {
        **state,
        "explanation_en": explanation_en,
        "explanation_ta": explanation_ta,
        "action_items":   action_items,
        "errors":         errors,
        "node_timings":   timings,
    }