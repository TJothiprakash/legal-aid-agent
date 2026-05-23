import os
from google import genai
from dotenv import load_dotenv
from db.repositories.legal_corpus import search_similar

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
DIMS = 768


def embed_text(text: str) -> list[float]:
    result = client.models.embed_content(
        model="gemini-embedding-001",
        contents=text,
    )
    return result.embeddings[0].values[:DIMS]


def retrieve(queries: list[str], k: int = 10) -> list[dict]:
    seen_ids = set()
    all_results = []

    for query in queries:
        embedding = embed_text(query)
        results = search_similar(embedding, k=k)
        for r in results:
            if r["id"] not in seen_ids:
                seen_ids.add(r["id"])
                all_results.append(r)

    all_results.sort(key=lambda x: x.get("similarity", 0), reverse=True)
    return all_results[:k]