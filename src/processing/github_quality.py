
import json
import re
from pathlib import Path


AI_ML_KEYWORDS = [
    "machine learning",
    "deep learning",
    "artificial intelligence",
    "natural language processing",
    "computer vision",
    "neural network",
    "large language model",
    "generative ai",
    "tensorflow",
    "pytorch",
    "scikit-learn",
    "classification",
    "prediction",
    "nlp",
    "transformer",
    "llm",
    "rag",
    "retrieval augmented generation",
    "agentic ai",
    "langchain",
    "langgraph",
    "hugging face",
    "diffusion model",
]

PROFILE_KEYWORDS = [
    "github profile",
    "profile readme",
]


def normalize_text(value):
    """Normalize text for consistent keyword matching."""

    if not isinstance(value, str):
        return ""

    value = value.lower()
    value = re.sub(r"[-_]+", " ", value)
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def classify_repository(repository):
    """Classify a GitHub repository based on available metadata."""

    name = normalize_text(
        repository.get("repository_name", "")
    )

    description = normalize_text(
        repository.get("description", "")
    )

    raw_topics = repository.get("topics", [])

    if not isinstance(raw_topics, list):
        raw_topics = []

    topics = " ".join(
        normalize_text(topic)
        for topic in raw_topics
        if isinstance(topic, str)
    )

    searchable_text = f"{name} {description} {topics}"

    # Exclude obvious personal profile repositories.
    if any(
        keyword in searchable_text
        for keyword in PROFILE_KEYWORDS
    ):
        return "not_relevant"

    # Check AI/ML-related keywords.
    has_ai_keyword = any(
        keyword in searchable_text
        for keyword in AI_ML_KEYWORDS
    )

    if has_ai_keyword:
        if description or topics:
            return "relevant"

        return "needs_review"

    # Missing metadata requires manual review.
    if not description and not topics:
        return "needs_review"

    return "not_relevant"


def process_github_data():
    """Classify repositories and save processed results."""

    project_root = Path(__file__).resolve().parents[2]

    input_file = (
        project_root / "data" / "raw"
        / "github_repositories.json"
    )

    output_dir = project_root / "data" / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)

    with input_file.open("r", encoding="utf-8") as file:
        repositories = json.load(file)

    processed = []

    for repository in repositories:
        status = classify_repository(repository)

        record = repository.copy()
        record["relevance_status"] = status

        processed.append(record)

    output_file = (
        output_dir / "github_quality_results.json"
    )

    with output_file.open("w", encoding="utf-8") as file:
        json.dump(
            processed,
            file,
            indent=4,
            ensure_ascii=False,
        )

    print(f"Total repositories: {len(processed)}")
    print(
        "Relevant:",
        sum(r["relevance_status"] == "relevant"
            for r in processed),
    )
    print(
        "Needs review:",
        sum(r["relevance_status"] == "needs_review"
            for r in processed),
    )
    print(
        "Not relevant:",
        sum(r["relevance_status"] == "not_relevant"
            for r in processed),
    )

    print(f"\nProcessed data saved to: {output_file}")


if __name__ == "__main__":
    process_github_data()
