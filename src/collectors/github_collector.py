
import json
from pathlib import Path

import requests


GITHUB_API_URL = "https://api.github.com/search/repositories"

HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "AIIntelligencePipeline/1.0",
}


def collect_repositories(max_results=5):
    """Collect AI and machine learning repositories from GitHub."""

    params = {
        "q": "machine learning in:name,description,readme",
        "sort": "updated",
        "order": "desc",
        "per_page": max_results,
        "page": 1,
    }

    print("Connecting to GitHub API...")

    try:
        response = requests.get(
            GITHUB_API_URL,
            params=params,
            headers=HEADERS,
            timeout=(10, 30),
        )

        if response.status_code in (403, 429):
            print("GitHub API rate limit or access restriction reached.")
            print("Rate limit remaining:",
                  response.headers.get("X-RateLimit-Remaining", "unknown"))
            return []

        response.raise_for_status()

    except requests.exceptions.Timeout:
        print("GitHub API connection timed out.")
        return []

    except requests.exceptions.RequestException as error:
        print(f"GitHub API request failed: {error}")
        return []

    data = response.json()
    repositories = []

    for item in data.get("items", []):
        repository = {
            "repository_name": item.get("full_name", ""),
            "description": item.get("description") or "",
            "repository_url": item.get("html_url", ""),
            "stars": item.get("stargazers_count", 0),
            "forks": item.get("forks_count", 0),
            "language": item.get("language"),
            "created_at": item.get("created_at", ""),
            "updated_at": item.get("updated_at", ""),
            "topics": item.get("topics", []),
            "license": (
                item.get("license", {}).get("name")
                if item.get("license")
                else None
            ),
            "source": "GitHub",
        }

        repositories.append(repository)

    return repositories


def save_repositories(repositories):
    """Save GitHub repository metadata as JSON."""

    project_root = Path(__file__).resolve().parents[2]

    output_dir = project_root / "data" / "raw"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "github_repositories.json"

    with output_file.open("w", encoding="utf-8") as file:
        json.dump(
            repositories,
            file,
            indent=4,
            ensure_ascii=False,
        )

    print(f"\nSaved {len(repositories)} repositories.")
    print(f"Output file: {output_file}")


if __name__ == "__main__":

    results = collect_repositories(max_results=5)

    if results:
        save_repositories(results)

        print("\nGitHub collection completed!")
        print(f"Total repositories: {len(results)}")

        print("\nFirst repository:")
        print("Name:", results[0]["repository_name"])
        print("Stars:", results[0]["stars"])
        print("Language:", results[0]["language"])
        print("URL:", results[0]["repository_url"])

    else:
        print("\nNo repositories collected.")
