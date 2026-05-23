import os
import json
import re
from google import genai
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def build_rag_query(raw_text: str) -> list[str]:
    head = raw_text[:500].strip()
    tail = raw_text[-200:].strip()
    combined = f"{head} {tail}"

    prompt = f"""Extract 2-3 short search queries to find relevant Indian legal information for this document.
Focus on: document type, legal rights involved, applicable laws.
Respond ONLY with a JSON array of strings. Example: ["TN rent control act tenant rights", "eviction notice legal procedure India"]

Document excerpt:
{combined}"""

    response = client.models.generate_content(
        model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
        contents=prompt,
    )
    text = re.sub(r"```json|```", "", response.text).strip()
    try:
        queries = json.loads(text)
        return queries if isinstance(queries, list) else [text]
    except Exception:
        return [combined[:200]]