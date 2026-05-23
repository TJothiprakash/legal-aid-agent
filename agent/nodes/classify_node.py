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

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "classify.yaml"


def _load_prompt() -> dict:
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def classify_node(state: AgentState) -> AgentState:
    start = time.time()
    errors = list(state.get("errors", []))

    try:
        prompt_cfg = _load_prompt()
        text_sample = state["raw_text"][:2000]

        human = prompt_cfg["human_template"].format(text=text_sample)

        model = genai.GenerativeModel(
            model_name=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
            system_instruction=prompt_cfg["system"],
        )
        response = model.generate_content(human)
        raw = re.sub(r"```json|```", "", response.text).strip()
        result = json.loads(raw)

        document_type    = result.get("document_type", "unknown")
        document_subtype = result.get("document_subtype", "")
        confidence       = float(result.get("confidence", 0.0))

        if confidence < 0.6:
            document_type = "unknown"

    except Exception as e:
        errors.append(f"classify_node error: {str(e)}")
        document_type    = "unknown"
        document_subtype = ""
        confidence       = 0.0

    timings = dict(state.get("node_timings", {}))
    timings["classify"] = round(time.time() - start, 3)

    return {
        **state,
        "document_type":    document_type,
        "document_subtype": document_subtype,
        "confidence":       confidence,
        "errors":           errors,
        "node_timings":     timings,
    }