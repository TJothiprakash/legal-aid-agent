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

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "analyze.yaml"


def _load_prompt() -> dict:
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _format_rag_context(rag_context: list[dict]) -> str:
    if not rag_context:
        return "No legal context available."
    lines = []
    for i, chunk in enumerate(rag_context[:6]):
        title = chunk.get("title", "Legal reference")
        text  = chunk.get("chunk_text", "")[:300]
        lines.append(f"[{i+1}] {title}: {text}")
    return "\n".join(lines)


def analyze_node(state: AgentState) -> AgentState:
    start = time.time()
    errors = list(state.get("errors", []))

    try:
        prompt_cfg = _load_prompt()

        human = prompt_cfg["human_template"].format(
            document_type    = state["document_type"],
            document_subtype = state["document_subtype"],
            raw_text         = state["raw_text"][:4000],
            rag_context      = _format_rag_context(state.get("rag_context", [])),
        )

        model = genai.GenerativeModel(
            model_name=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
            system_instruction=prompt_cfg["system"],
        )
        response = model.generate_content(human)
        raw = re.sub(r"```json|```", "", response.text).strip()
        result = json.loads(raw)

        key_clauses     = result.get("key_clauses", [])
        obligations     = result.get("obligations", [])
        parties         = result.get("parties", [])
        important_dates = result.get("important_dates", [])

    except Exception as e:
        errors.append(f"analyze_node error: {str(e)}")
        key_clauses     = []
        obligations     = []
        parties         = []
        important_dates = []

    timings = dict(state.get("node_timings", {}))
    timings["analyze"] = round(time.time() - start, 3)

    return {
        **state,
        "key_clauses":     key_clauses,
        "obligations":     obligations,
        "parties":         parties,
        "important_dates": important_dates,
        "errors":          errors,
        "node_timings":    timings,
    }