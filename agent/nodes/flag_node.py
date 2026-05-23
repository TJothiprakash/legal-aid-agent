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

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "flag.yaml"


def _load_prompt() -> dict:
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def flag_node(state: AgentState) -> AgentState:
    start = time.time()
    errors = list(state.get("errors", []))

    try:
        prompt_cfg = _load_prompt()

        human = prompt_cfg["human_template"].format(
            document_type = state["document_type"],
            key_clauses   = json.dumps(state.get("key_clauses", []), indent=2),
            obligations   = json.dumps(state.get("obligations", []), indent=2),
            rag_context   = json.dumps(
                [{"title": c.get("title"), "text": c.get("chunk_text", "")[:200]}
                 for c in state.get("rag_context", [])[:5]],
                indent=2
            ),
        )

        model = genai.GenerativeModel(
            model_name=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
            system_instruction=prompt_cfg["system"],
        )
        response = model.generate_content(human)
        raw = re.sub(r"```json|```", "", response.text).strip()
        result = json.loads(raw)

        flagged_clauses = result.get("flagged_clauses", [])
        risk_level      = result.get("risk_level", "low")

    except Exception as e:
        errors.append(f"flag_node error: {str(e)}")
        flagged_clauses = []
        risk_level      = "low"

    timings = dict(state.get("node_timings", {}))
    timings["flag"] = round(time.time() - start, 3)

    return {
        **state,
        "flagged_clauses": flagged_clauses,
        "risk_level":      risk_level,
        "errors":          errors,
        "node_timings":    timings,
    }