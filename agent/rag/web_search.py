import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

WHITELISTED_DOMAINS = [
    "indiankanoon.org",
    "legislative.gov.in",
    "lawmin.gov.in",
    "tngovernment.in",
    "consumeraffairs.nic.in",
    "labour.tn.gov.in",
]


def _is_whitelisted(url: str) -> bool:
    return any(domain in url for domain in WHITELISTED_DOMAINS)


def _fetch_page_text(url: str, max_chars: int = 1500) -> str:
    try:
        resp = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        return text[:max_chars]
    except Exception:
        return ""


def web_search(queries: list[str], max_results: int = 5) -> list[dict]:
    results = []
    seen_urls = set()

    site_filter = " OR ".join(f"site:{d}" for d in WHITELISTED_DOMAINS)

    with DDGS() as ddgs:
        for query in queries:
            restricted = f"{query} ({site_filter})"
            try:
                hits = list(ddgs.text(restricted, max_results=max_results))
            except Exception:
                continue

            for hit in hits:
                url = hit.get("href", "")
                if not url or url in seen_urls:
                    continue
                if not _is_whitelisted(url):
                    continue

                seen_urls.add(url)
                page_text = _fetch_page_text(url)

                results.append({
                    "id":         f"web_{len(results)}",
                    "title":      hit.get("title", ""),
                    "url":        url,
                    "chunk_text": page_text or hit.get("body", "")[:500],
                    "source":     "web",
                    "similarity": 0.75,
                })

    return results