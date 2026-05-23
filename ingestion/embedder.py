import os
import time
from google import genai
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
DIMS = 768


def embed_chunks(chunks: list[str], batch_size: int = 5) -> list[list[float]]:
    embeddings = []

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        for chunk in batch:
            try:
                result = client.models.embed_content(
                    model="gemini-embedding-001",
                    contents=chunk,
                )
                full = result.embeddings[0].values
                embeddings.append(full[:DIMS])
            except Exception as e:
                print(f"  Embedding error: {e} — skipping chunk")
                embeddings.append([0.0] * DIMS)

        if i + batch_size < len(chunks):
            time.sleep(1)

    return embeddings