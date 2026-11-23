
import json
import re
from pathlib import Path

import feedparser
import requests
from bs4 import BeautifulSoup


ARXIV_API_URL = "https://export.arxiv.org/api/query"
CROSSREF_API_URL = "https://api.crossref.org/works"

HEADERS = {
    "User-Agent": "AIIntelligencePipeline/1.0"
}


def clean_text(value):
    """Remove HTML tags and normalize whitespace."""
    if not value:
        return ""

    text = BeautifulSoup(value, "html.parser").get_text(" ")
    return " ".join(text.split())


def collect_from_arxiv(max_results=5):
    """Collect papers from the official arXiv API."""

    params = {
        "search_query": (
            '(all:"machine learning" OR '
            'all:"artificial intelligence")'
        ),
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }

    print("\nTrying primary source: arXiv...")

    response = requests.get(
        ARXIV_API_URL,
        params=params,
        headers=HEADERS,
        timeout=(10, 30),
    )

    if response.status_code == 429:
        raise RuntimeError("arXiv rate limit reached (HTTP 429).")

    response.raise_for_status()

    feed = feedparser.parse(response.content)

    if feed.bozo and not feed.entries:
        raise RuntimeError("Unable to parse arXiv response.")

    papers = []

    for entry in feed.entries:
        papers.append({
            "title": clean_text(entry.get("title", "")),
            "summary": clean_text(entry.get("summary", "")),
            "authors": [
                author.name
                for author in entry.get("authors", [])
            ],
            "published": entry.get("published", ""),
            "updated": entry.get("updated", ""),
            "paper_url": entry.get("link", ""),
            "arxiv_id": entry.get("id", "").split("/abs/")[-1],
            "doi": "",
            "categories": [
                tag.term for tag in entry.get("tags", [])
            ],
            "source": "arXiv",
        })

    return papers



def collect_from_crossref(max_results=5):
    """Collect relevant AI/ML publications from Crossref."""

    params = {
        "query.title": "machine learning",
        "rows": max_results * 5,
        "filter": (
            "type:journal-article,"
            "from-pub-date:2000-01-01,"
            "until-pub-date:2026-12-31"
        ),
        "select": (
            "DOI,title,author,abstract,published,"
            "published-online,published-print,URL,subject,type"
        ),
    }

    print("\nTrying backup source: Crossref...")

    response = requests.get(
        CROSSREF_API_URL,
        params=params,
        headers=HEADERS,
        timeout=(10, 30),
    )

    response.raise_for_status()

    items = response.json().get("message", {}).get("items", [])

    relevant_phrases = [
        "machine learning",
        "artificial intelligence",
        "deep learning",
        "neural network",
        "natural language processing",
        "computer vision",
        "large language model",
        "generative ai",
    ]

    papers = []
    seen_dois = set()

    for item in items:
        title_list = item.get("title", [])
        title = title_list[0] if title_list else ""

        if not title:
            continue

        normalized_title = title.lower()

        # Reject unrelated publication titles.
        if not any(
            phrase in normalized_title
            for phrase in relevant_phrases
        ):
            continue

        doi = item.get("DOI", "")

        if doi and doi in seen_dois:
            continue

        if doi:
            seen_dois.add(doi)

        # Read publication date without inventing missing dates.
        date_info = (
            item.get("published-online")
            or item.get("published-print")
            or item.get("published")
            or {}
        )

        date_parts = date_info.get("date-parts", [[]])[0]

        published = ""

        if date_parts:
            year = date_parts[0]

            if isinstance(year, int) and 1900 <= year <= 2026:
                published = "-".join(
                    str(part) for part in date_parts
                )

        authors = []

        for author in item.get("author", []):
            name = " ".join(filter(None, [
                author.get("given", ""),
                author.get("family", ""),
            ]))

            if name:
                authors.append(name)

        paper_url = item.get("URL", "")

        if not paper_url and doi:
            paper_url = f"https://doi.org/{doi}"

        papers.append({
            "title": clean_text(title),
            "summary": clean_text(item.get("abstract", "")),
            "authors": authors,
            "published": published,
            "updated": "",
            "paper_url": paper_url,
            "arxiv_id": "",
            "doi": doi,
            "categories": item.get("subject", []),
            "source": "Crossref",
        })

        if len(papers) >= max_results:
            break

    return papers

def collect_papers(max_results=5):
    """Try arXiv first, then Crossref as a backup."""

    try:
        papers = collect_from_arxiv(max_results)

        if papers:
            print(f"Collected {len(papers)} papers from arXiv.")
            return papers

        print("arXiv returned no records.")

    except (requests.RequestException, RuntimeError) as error:
        print(f"Primary source unavailable: {error}")

    try:
        papers = collect_from_crossref(max_results)

        if papers:
            print(f"Collected {len(papers)} records from Crossref.")
            return papers

        print("Crossref returned no records.")

    except (requests.RequestException, ValueError) as error:
        print(f"Backup source unavailable: {error}")

    return []


def save_papers(papers):
    """Save research records in JSON format."""

    project_root = Path(__file__).resolve().parents[2]

    output_dir = project_root / "data" / "raw"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "research_papers.json"

    with output_file.open("w", encoding="utf-8") as file:
        json.dump(
            papers,
            file,
            indent=4,
            ensure_ascii=False,
        )

    print(f"\nSaved {len(papers)} records.")
    print(f"File location: {output_file}")


if __name__ == "__main__":

    results = collect_papers(max_results=5)

    if results:
        save_papers(results)

        print("\nResearch collection completed!")
        print(f"Total records: {len(results)}")

        print("\nFirst record:")
        print("Title:", results[0]["title"])
        print("Source:", results[0]["source"])
        print("URL:", results[0]["paper_url"])

    else:
        print("\nBoth sources failed or returned no records.")
        print("No JSON file was created.")
