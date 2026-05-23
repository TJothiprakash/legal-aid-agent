import os
import json
import re
from google import genai
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def _fallback_queries(text: str) -> list[str]:
    compact = " ".join(text.split())
    if not compact:
        return ["Indian legal rights document"]

    queries = [compact[:200]]
    lowered = compact.lower()
    if "vacate" in lowered or "evict" in lowered or "tenant" in lowered:
        queries.insert(0, "tenant eviction notice legal procedure India")
    elif "agreement" in lowered or "landlord" in lowered or "rent" in lowered:
        queries.insert(0, "rental agreement tenant rights India")
    else:
        queries.insert(0, "Indian legal rights and obligations document")

    return list(dict.fromkeys(q for q in queries if q))


def build_rag_query(raw_text: str) -> list[str]:
    head = raw_text[:500].strip()
    tail = raw_text[-200:].strip()
    combined = f"{head} {tail}"

    prompt = f"""Extract 2-3 short search queries to find relevant Indian legal information for this document.
Focus on: document type, legal rights involved, applicable laws.
Respond ONLY with a JSON array of strings. Example: ["TN rent control act tenant rights", "eviction notice legal procedure India"]

Document excerpt:
{combined}"""

    try:
        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
            contents=prompt,
        )
        text = re.sub(r"```json|```", "", response.text).strip()
        queries = json.loads(text)
        if isinstance(queries, list):
            valid_queries = [q.strip() for q in queries if isinstance(q, str) and q.strip()]
            return valid_queries or _fallback_queries(combined)
        return [text] if text else _fallback_queries(combined)
    except Exception:
        return _fallback_queries(combined)
