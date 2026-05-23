from db.client import get_supabase


def upsert_chunk(
    title: str,
    chunk_text: str,
    chunk_index: int,
    embedding: list[float],
    source_url: str = "",
    doc_type: str = "statute",
    jurisdiction: str = "central",
    language: str = "en",
    metadata: dict = {},
) -> None:
    get_supabase().table("legal_documents").upsert({
        "title":        title,
        "chunk_text":   chunk_text,
        "chunk_index":  chunk_index,
        "embedding":    embedding,
        "source_url":   source_url,
        "doc_type":     doc_type,
        "jurisdiction": jurisdiction,
        "language":     language,
        "metadata":     metadata,
    }).execute()


def search_similar(embedding: list[float], k: int = 10) -> list[dict]:
    result = get_supabase().rpc("match_legal_documents", {
        "query_embedding": embedding,
        "match_count": k,
    }).execute()
    return result.data or []


def count_chunks() -> int:
    result = get_supabase().table("legal_documents").select("id", count="exact").execute()
    return result.count or 0