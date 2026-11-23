
import json
from pathlib import Path

import requests


STARTUP_API_URL = "https://yc-oss.github.io/api/tags/ai.json"

HEADERS = {
    "User-Agent": "AIIntelligencePipeline/1.0",
}


def collect_startups(max_results=5):
    """Collect AI-tagged startup information from the YC company dataset."""

    print("Connecting to Y Combinator AI startup dataset...")

    try:
        response = requests.get(
            STARTUP_API_URL,
            headers=HEADERS,
            timeout=(10, 30),
        )

        if response.status_code in (403, 429):
            print("Startup dataset access restriction or rate limit reached.")
            return []

        response.raise_for_status()

    except requests.exceptions.Timeout:
        print("Startup dataset connection timed out.")
        return []

    except requests.exceptions.RequestException as error:
        print(f"Startup dataset request failed: {error}")
        return []

    try:
        data = response.json()
    except ValueError:
        print("Invalid JSON received from startup dataset.")
        return []

    if not isinstance(data, list):
        print("Unexpected startup dataset format.")
        return []

    startups = []

    for item in data:
        tags = item.get("tags") or []

        # Keep only companies explicitly tagged as AI.
        if "AI" not in tags:
            continue

        startup = {
            "startup_name": item.get("name", ""),
            "description": (
                item.get("long_description")
                or item.get("one_liner")
                or ""
            ),
            "one_liner": item.get("one_liner", ""),
            "website": item.get("website", ""),
            "startup_url": item.get("url", ""),
            "industry": item.get("industry", ""),
            "subindustry": item.get("subindustry", ""),
            "tags": tags,
            "location": item.get("all_locations", ""),
            "team_size": item.get("team_size"),
            "batch": item.get("batch", ""),
            "status": item.get("status", ""),
            "is_hiring": item.get("isHiring", False),
            "launched_at": item.get("launched_at"),
            "source": "Y Combinator",
            "source_type": "Community-maintained YC API mirror",
        }

        startups.append(startup)

        if len(startups) >= max_results:
            break

    print(f"Collected {len(startups)} AI startups.")

    return startups


def save_startups(startups):
    """Save AI startup information as JSON."""

    project_root = Path(__file__).resolve().parents[2]

    output_dir = project_root / "data" / "raw"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "ai_startups.json"

    with output_file.open("w", encoding="utf-8") as file:
        json.dump(
            startups,
            file,
            indent=4,
            ensure_ascii=False,
        )

    print(f"\nSaved {len(startups)} startups.")
    print(f"Output file: {output_file}")


if __name__ == "__main__":

    results = collect_startups(max_results=5)

    if results:
        save_startups(results)

        print("\nStartup collection completed!")
        print(f"Total startups: {len(results)}")

        print("\nFirst startup:")
        print("Name:", results[0]["startup_name"])
        print("Description:", results[0]["one_liner"])
        print("Website:", results[0]["website"])
        print("Industry:", results[0]["industry"])
        print("Status:", results[0]["status"])

    else:
        print("\nNo AI startups collected.")
