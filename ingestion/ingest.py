import io
import os
import sys
import fitz
import requests
import yaml
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent))

from ingestion.chunker import chunk_text
from ingestion.embedder import embed_chunks
from ingestion.loader import load_chunks
from db.repositories.legal_corpus import count_chunks


HEADERS = {"User-Agent": "Mozilla/5.0 LegalAidBot/1.0"}


def _fetch_pdf_text(url: str) -> str:
    print(f"  Fetching: {url}")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        doc = fitz.open(stream=io.BytesIO(resp.content), filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        return text.strip()
    except Exception as e:
        print(f"  Failed to fetch PDF: {e}")
        return ""


def _fetch_html_text(url: str) -> str:
    print(f"  Fetching: {url}")
    try:
        from bs4 import BeautifulSoup
        resp = requests.get(url, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        return soup.get_text(separator=" ", strip=True)[:50000]
    except Exception as e:
        print(f"  Failed to fetch HTML: {e}")
        return ""


def ingest_source(source: dict) -> int:
    name         = source["name"]
    url          = source.get("url", "")
    doc_type     = source.get("doc_type", "statute")
    jurisdiction = source.get("jurisdiction", "central")
    language     = source.get("language", "en")

    print(f"\n[{name}]")

    if url.endswith(".pdf"):
        text = _fetch_pdf_text(url)
    else:
        text = _fetch_html_text(url)

    if not text:
        print(f"  No text extracted — skipping")
        return 0

    print(f"  Extracted {len(text)} chars")

    chunks = chunk_text(text)
    print(f"  Created {len(chunks)} chunks")

    embeddings = embed_chunks(chunks)
    print(f"  Embedded {len(embeddings)} chunks")

    loaded = load_chunks(
        title=name,
        chunks=chunks,
        embeddings=embeddings,
        source_url=url,
        doc_type=doc_type,
        jurisdiction=jurisdiction,
        language=language,
    )
    print(f"  Loaded {loaded} chunks into pgvector")
    return loaded


def run_ingestion():
    sources_path = Path(__file__).parent / "sources.yaml"
    with open(sources_path, "r") as f:
        config = yaml.safe_load(f)

    sources = config.get("sources", [])
    print(f"Starting ingestion — {len(sources)} sources")
    print(f"Current corpus size: {count_chunks()} chunks\n")

    total = 0
    for source in sources:
        try:
            total += ingest_source(source)
        except Exception as e:
            print(f"  Error ingesting {source.get('name')}: {e}")

    print(f"\nIngestion complete — {total} chunks loaded")
    print(f"Total corpus size: {count_chunks()} chunks")


if __name__ == "__main__":
    run_ingestion()