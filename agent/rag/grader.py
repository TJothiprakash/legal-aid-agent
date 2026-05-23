import json
import re
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


def grade_chunks(chunks: list[dict], raw_text: str) -> list[dict]:
    if not chunks:
        return []

    model = genai.GenerativeModel("gemini-2.0-flash")

    summaries = []
    for i, c in enumerate(chunks):
        summaries.append(f"{i}: {c.get('chunk_text', '')[:200]}")
    chunks_text = "\n".join(summaries)

    prompt = f"""Score each legal text chunk for relevance to the document below.
Score 0.0 to 1.0. Respond ONLY with a JSON array of scores in the same order.
Example: [0.9, 0.3, 0.8]

Document excerpt:
{raw_text[:400]}

Chunks:
{chunks_text}"""

    try:
        response = model.generate_content(prompt)
        text = re.sub(r"```json|```", "", response.text).strip()
        scores = json.loads(text)
        if not isinstance(scores, list):
            scores = [0.5] * len(chunks)
    except Exception:
        scores = [0.5] * len(chunks)

    scored = []
    for chunk, score in zip(chunks, scores):
        if isinstance(score, (int, float)) and score >= 0.7:
            chunk["relevance_score"] = score
            scored.append(chunk)

    return scored


def reciprocal_rank_fusion(
    vector_results: list[dict],
    web_results: list[dict],
    k: int = 60,
) -> list[dict]:
    scores: dict[str, float] = {}
    docs: dict[str, dict] = {}

    for rank, doc in enumerate(vector_results):
        doc_id = doc.get("id") or doc.get("url") or str(rank)
        scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank + 1)
        docs[doc_id] = doc

    for rank, doc in enumerate(web_results):
        doc_id = doc.get("id") or doc.get("url") or f"web_{rank}"
        scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank + 1)
        docs[doc_id] = doc

    ranked_ids = sorted(scores, key=lambda x: scores[x], reverse=True)
    return [docs[i] for i in ranked_ids[:8]]