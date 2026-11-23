"""
AI Product Collector (Phase I)
Collects structured AI products from Product Hunt RSS and verified Product Hunt repository.
Canonicalizes startup/maker names and infers pricing models (FREE, FREEMIUM, PAID, ENTERPRISE).
Supports extracting 1,000+ unique AI product records.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup
import feedparser
import requests

from src.processing.entity_resolver import default_entity_resolver

PRODUCT_HUNT_FEED_URL = (
    "https://www.producthunt.com/feed"
    "?category=artificial-intelligence"
)

PRODUCT_HUNT_PARQUET_URL = (
    "https://huggingface.co/datasets/lumalik/Product-Hunt-Data/resolve/refs%2Fconvert%2Fparquet/default/train/0000.parquet"
)

HEADERS = {
    "User-Agent": "AIIntelligencePipeline/1.0",
}


def clean_description(html: str) -> str:
    """Extract clean product tagline/description from HTML content."""
    if not html:
        return ""

    soup = BeautifulSoup(html, "html.parser")
    paragraphs = soup.find_all("p")
    if paragraphs:
        return paragraphs[0].get_text(" ", strip=True)

    return soup.get_text(" ", strip=True)


def infer_pricing_model(text: str) -> str:
    """Infer pricing model from product description or tagline."""
    if not text:
        return "FREEMIUM"

    lower = text.lower()
    if any(k in lower for k in ["open source", "open-source", "100% free", "free to use", "free forever", "no cost"]):
        return "FREE"
    elif any(k in lower for k in ["enterprise", "b2b", "compliance", "teams", "custom plan", "soc2", "white-label"]):
        return "ENTERPRISE"
    elif any(k in lower for k in ["$", "/mo", "/month", "paid", "subscription", "purchase", "billing", "pricing"]):
        return "PAID"
    return "FREEMIUM"


def collect_from_rss(max_results: int = 5) -> List[Dict[str, Any]]:
    """Collect products from Product Hunt RSS feed."""
    print("Connecting to Product Hunt RSS feed...")

    try:
        response = requests.get(
            PRODUCT_HUNT_FEED_URL,
            headers=HEADERS,
            timeout=(10, 30),
        )

        if response.status_code in (403, 429):
            print("Product Hunt access restriction or rate limit reached.")
            return []

        response.raise_for_status()

    except requests.exceptions.RequestException as error:
        print(f"Product Hunt request failed: {error}")
        return []

    feed = feedparser.parse(response.content)

    if feed.bozo and not feed.entries:
        print("Unable to parse Product Hunt RSS feed.")
        return []

    products = []
    now_iso = datetime.now(timezone.utc).isoformat()

    for item in feed.entries[:max_results]:
        raw_title = item.get("title", "")
        raw_desc = clean_description(item.get("summary", ""))
        url = item.get("link", "")
        published = item.get("published", now_iso)
        pricing = infer_pricing_model(raw_desc)

        canonical_startup, _, _ = default_entity_resolver.resolve(raw_title.split()[0] if raw_title else "Unknown", entity_type="PRODUCT_MAKER")

        product = {
            "schemaVersion": "1.0",
            "recordType": "PRODUCT",
            "source": "Product Hunt",
            "source_details": {
                "name": "Product Hunt",
                "url": url,
            },
            "content": {
                "productName": raw_title,
                "description": raw_desc,
                "startupName": canonical_startup,
                "pricingModel": pricing,
            },
            "collectedAt": now_iso,
            # Backwards-compatibility fields
            "product_name": raw_title,
            "description": raw_desc,
            "product_url": url,
            "published_at": published,
            "updated_at": item.get("updated", ""),
            "category": "Artificial Intelligence",
        }
        products.append(product)

    return products


def collect_from_archive(max_results: int = 1000) -> List[Dict[str, Any]]:
    """Collect up to max_results unique AI products from Product Hunt archive."""
    print(f"Connecting to verified Product Hunt dataset for {max_results} AI products...")
    import pandas as pd

    try:
        df = pd.read_parquet(PRODUCT_HUNT_PARQUET_URL)
    except Exception as err:
        print(f"Failed to load Product Hunt parquet dataset: {err}")
        return []

    ai_keywords = (
        "ai|artificial intelligence|machine learning|gpt|neural|bot|smart|"
        "automation|copilot|deep learning|llm|agent|generative"
    )

    ai_mask = (
        df["tagline"].str.contains(ai_keywords, case=False, na=False)
        | df["title"].str.contains(r"\bai\b|bot|gpt|copilot", case=False, na=False)
    )

    filtered_df = df[ai_mask].drop_duplicates(subset=["link"]).head(max_results)

    products = []
    now_iso = datetime.now(timezone.utc).isoformat()

    for _, row in filtered_df.iterrows():
        title = str(row["title"]).strip() if pd.notna(row["title"]) else "Untitled Product"
        tagline = str(row["tagline"]).strip() if pd.notna(row["tagline"]) else ""
        link = str(row["link"]).strip() if pd.notna(row["link"]) else f"https://www.producthunt.com/products/{title.lower().replace(' ', '-')}"
        creator = str(row["creator"]).strip() if pd.notna(row.get("creator")) and str(row.get("creator")).strip() else title

        canonical_startup, _, _ = default_entity_resolver.resolve(creator, entity_type="PRODUCT_MAKER")
        pricing = infer_pricing_model(tagline)

        year = row.get("year", 2026)
        try:
            pub_year = int(year) if pd.notna(year) else 2026
        except (ValueError, TypeError):
            pub_year = 2026
        published_at = f"{pub_year}-01-01T00:00:00Z"

        product = {
            "schemaVersion": "1.0",
            "recordType": "PRODUCT",
            "source": "Product Hunt",
            "source_details": {
                "name": "Product Hunt",
                "url": link,
            },
            "content": {
                "productName": title,
                "description": tagline,
                "startupName": canonical_startup,
                "pricingModel": pricing,
            },
            "collectedAt": now_iso,
            # Backwards-compatibility fields
            "product_name": title,
            "description": tagline,
            "product_url": link,
            "published_at": published_at,
            "updated_at": "",
            "category": "Artificial Intelligence",
        }
        products.append(product)

    print(f"Collected {len(products)} AI products from archive.")
    return products


def collect_products(max_results: int = 5) -> List[Dict[str, Any]]:
    """Collect AI products; queries RSS for small batches (<=50), and bulk archive for 50+ records."""
    if max_results is not None and max_results <= 50:
        return collect_from_rss(max_results=max_results)

    # Bulk collection (e.g. 1,000 records)
    return collect_from_archive(max_results=max_results)


def save_products(products: List[Dict[str, Any]]) -> None:
    """Save AI product metadata as JSON."""
    project_root = Path(__file__).resolve().parents[2]
    output_dir = project_root / "data" / "raw"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "ai_products.json"

    with output_file.open("w", encoding="utf-8") as file:
        json.dump(
            products,
            file,
            indent=4,
            ensure_ascii=False,
        )

    print(f"\nSaved {len(products)} products.")
    print(f"Output file: {output_file}")


if __name__ == "__main__":
    results = collect_products(max_results=1000)
    if results:
        save_products(results)
        print(f"\nCollected and saved {len(results)} AI products!")
    else:
        print("\nNo products collected.")
