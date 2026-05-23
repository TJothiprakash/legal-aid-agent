import pytest
from agent.rag.retriever import embed_text
from agent.rag.grader import reciprocal_rank_fusion
from agent.rag.rewriter import build_rag_query


def test_embed_text_returns_correct_dims():
    embedding = embed_text("tenant rights India rent control")
    assert isinstance(embedding, list)
    assert len(embedding) == 768
    assert all(isinstance(v, float) for v in embedding)


def test_build_rag_query_returns_list():
    queries = build_rag_query(
        "Notice to vacate the premises within 7 days. Landlord: Suresh. Tenant: Rajan."
    )
    assert isinstance(queries, list)
    assert len(queries) >= 1
    assert all(isinstance(q, str) for q in queries)


def test_reciprocal_rank_fusion_merges():
    vector = [
        {"id": "1", "title": "A", "chunk_text": "text a", "similarity": 0.9},
        {"id": "2", "title": "B", "chunk_text": "text b", "similarity": 0.8},
    ]
    web = [
        {"id": "web_0", "url": "http://x.com", "chunk_text": "web text", "similarity": 0.75},
        {"id": "1", "title": "A", "chunk_text": "text a", "similarity": 0.9},
    ]
    result = reciprocal_rank_fusion(vector, web)
    assert isinstance(result, list)
    assert len(result) <= 8


def test_reciprocal_rank_fusion_empty():
    result = reciprocal_rank_fusion([], [])
    assert result == []