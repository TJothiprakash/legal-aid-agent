from db.repositories.legal_corpus import upsert_chunk


def load_chunks(
    title: str,
    chunks: list[str],
    embeddings: list[list[float]],
    source_url: str = "",
    doc_type: str = "statute",
    jurisdiction: str = "central",
    language: str = "en",
) -> int:
    loaded = 0
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        if not chunk.strip():
            continue
        if all(v == 0.0 for v in embedding):
            continue
        try:
            upsert_chunk(
                title=title,
                chunk_text=chunk,
                chunk_index=i,
                embedding=embedding,
                source_url=source_url,
                doc_type=doc_type,
                jurisdiction=jurisdiction,
                language=language,
                metadata={"chunk_index": i, "total_chunks": len(chunks)},
            )
            loaded += 1
        except Exception as e:
            print(f"  Load error chunk {i}: {e}")
    return loaded