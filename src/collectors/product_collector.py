
import json
from pathlib import Path
from bs4 import BeautifulSoup
import feedparser
import requests


PRODUCT_HUNT_FEED_URL = (
    "https://www.producthunt.com/feed"
    "?category=artificial-intelligence"
)

HEADERS = {
    "User-Agent": "AIIntelligencePipeline/1.0",
}
def clean_description(html):
    """Extract the product tagline from HTML content."""

    soup = BeautifulSoup(html, "html.parser")

    paragraphs = soup.find_all("p")

    if paragraphs:
        return paragraphs[0].get_text(" ", strip=True)

    return soup.get_text(" ", strip=True)

def collect_products(max_results=5):
    """Collect AI product information from Product Hunt RSS."""

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

    except requests.exceptions.Timeout:
        print("Product Hunt connection timed out.")
        return []

    except requests.exceptions.RequestException as error:
        print(f"Product Hunt request failed: {error}")
        return []

    feed = feedparser.parse(response.content)

    if feed.bozo and not feed.entries:
        print("Unable to parse Product Hunt RSS feed.")
        return []

    products = []

    for item in feed.entries[:max_results]:
        product = {
            "product_name": item.get("title", ""),
            "description": clean_description(item.get("summary", "")),
            "product_url": item.get("link", ""),
            "published_at": item.get("published", ""),
            "updated_at": item.get("updated", ""),
            "category": "Artificial Intelligence",
            "source": "Product Hunt",
        }

        products.append(product)

    print(f"Collected {len(products)} AI products.")

    return products


def save_products(products):
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

    results = collect_products(max_results=5)

    if results:
        save_products(results)

        print("\nProduct collection completed!")
        print(f"Total products: {len(results)}")

        print("\nFirst product:")
        print("Name:", results[0]["product_name"])
        print("Description:", results[0]["description"])
        print("URL:", results[0]["product_url"])

    else:
        print("\nNo products collected.")
