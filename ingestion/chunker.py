import re


def chunk_text(
    text: str,
    chunk_size: int = 800,
    overlap: int = 100,
) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []

    # Try section-aware splitting first
    section_patterns = [
        r"(?=\n?(?:Section|SECTION|Chapter|CHAPTER|Part|PART)\s+\d+)",
        r"(?=\n?\d+\.\s+[A-Z])",
        r"(?=\n?[A-Z][A-Z\s]{10,}\.?\n)",
    ]

    chunks = []
    for pattern in section_patterns:
        sections = re.split(pattern, text)
        sections = [s.strip() for s in sections if len(s.strip()) > 100]
        if len(sections) > 3:
            for section in sections:
                if len(section) <= chunk_size:
                    chunks.append(section)
                else:
                    chunks.extend(_sliding_window(section, chunk_size, overlap))
            return chunks

    # Fallback to sliding window
    return _sliding_window(text, chunk_size, overlap)


def _sliding_window(text: str, size: int, overlap: int) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start += size - overlap
    return chunks