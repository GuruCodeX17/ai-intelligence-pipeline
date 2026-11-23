
import json
from pathlib import Path

import requests

STARTUP_API_URL = "https://yc-oss.github.io/api/tags/ai.json"

HEADERS = {
    "User-Agent": "AIIntelligencePipeline/1.0",
}


def collect_startups(max_results=1000):
    """Collect up to 1,000 unique AI-tagged YC startups."""

    print("Connecting to Y Combinator AI startup dataset...")

    try:
        response = requests.get(
            STARTUP_API_URL,
            headers=HEADERS,
            timeout=(10, 60),
        )
        response.raise_for_status()
        data = response.json()

    except requests.exceptions.RequestException as error:
        print(f"Startup dataset request failed: {error}")
        return []

    except ValueError:
        print("Invalid JSON received from startup dataset.")
        return []

    if not isinstance(data, list):
        print("Unexpected startup dataset format.")
        return []

    startups = []
    seen = set()

    for item in data:
        if not isinstance(item, dict):
            continue

        tags = item.get("tags") or []

        if not any(str(tag).strip().lower() == "ai" for tag in tags):
            continue

        name = item.get("name") or item.get("startup_name") or ""
        startup_url = (
            item.get("url")
            or item.get("startup_url")
            or ""
        )

        if not name.strip():
            continue

        unique_key = startup_url.lower() or name.strip().lower()

        if unique_key in seen:
            continue

        seen.add(unique_key)

        raw_name = name.strip()
        from src.processing.entity_resolver import default_entity_resolver
        canonical_name, _, _ = default_entity_resolver.resolve(raw_name, entity_type="STARTUP")

        team_size = item.get("team_size")
        employee_count = int(team_size) if team_size is not None and str(team_size).isdigit() else None

        from datetime import datetime, timezone
        now_iso = datetime.now(timezone.utc).isoformat()

        startup = {
            "schemaVersion": "1.0",
            "recordType": "STARTUP",
            "source": "Y Combinator",
            "source_details": {
                "name": "Y Combinator",
                "url": startup_url or f"https://www.ycombinator.com/companies/{raw_name.lower().replace(' ', '-')}",
            },
            "content": {
                "entityName": canonical_name,
                "data": {
                    "employeeCount": employee_count,
                    "industry": item.get("industry", ""),
                    "subindustry": item.get("subindustry", ""),
                    "location": item.get("all_locations") or item.get("location") or "",
                    "batch": item.get("batch", ""),
                    "website": item.get("website", ""),
                    "one_liner": item.get("one_liner", ""),
                },
            },
            "collectedAt": now_iso,
            # Backwards compatibility fields
            "startup_name": raw_name,
            "canonical_name": canonical_name,
            "description": (
                item.get("long_description")
                or item.get("description")
                or item.get("one_liner")
                or ""
            ),
            "one_liner": item.get("one_liner", ""),
            "website": item.get("website", ""),
            "startup_url": startup_url or f"https://www.ycombinator.com/companies/{raw_name.lower().replace(' ', '-')}",
            "industry": item.get("industry", ""),
            "subindustry": item.get("subindustry", ""),
            "tags": tags,
            "location": (
                item.get("all_locations")
                or item.get("location")
                or ""
            ),
            "team_size": employee_count,
            "batch": item.get("batch", ""),
            "status": item.get("status", ""),
            "is_hiring": item.get(
                "isHiring",
                item.get("is_hiring", False)
            ),
            "launched_at": item.get("launched_at"),
            "source_type": "Community-maintained YC API mirror",
        }

        startups.append(startup)

        if max_results is not None and len(startups) >= max_results:
            break

    print(f"Collected {len(startups)} unique AI startups.")

    if len(startups) < 1000:
        print("Warning: fewer than 1,000 records were collected.")

    return startups


def save_startups(startups):
    """Save startup records as JSON."""

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

    print(f"Saved {len(startups)} startups.")
    print(f"Output file: {output_file}")


if __name__ == "__main__":
    results = collect_startups(max_results=1000)

    if results:
        save_startups(results)
        print("\nStartup collection completed!")
        print("Total startups:", len(results))
    else:
        print("\nNo AI startups collected.")
