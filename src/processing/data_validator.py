
import json
from pathlib import Path
from urllib.parse import urlparse


# Project directories
PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


# Dataset validation configuration
DATASETS = {
    "research_papers": {
        "file": "research_papers.json",
        "required": [
            "title",
            "summary",
            "published",
            "authors",
            "paper_url",
        ],
        "optional": [],
        "unique": "arxiv_id",
        "urls": ["paper_url"],
        "text": ["title", "summary"],
    },

    "github_repositories": {
        "file": "github_repositories.json",
        "required": [
            "repository_name",
            "repository_url",
            "stars",
            "forks",
        ],
        "optional": ["description"],
        "unique": "repository_name",
        "urls": ["repository_url"],
        "text": ["repository_name", "description"],
    },

    "ai_products": {
        "file": "ai_products.json",
        "required": [
            "product_name",
            "description",
            "product_url",
            "published_at",
        ],
        "optional": [],
        "unique": "product_url",
        "urls": ["product_url"],
        "text": ["product_name", "description"],
    },

    "ai_startups": {
        "file": "ai_startups.json",
        "required": [
            "startup_name",
            "description",
            "website",
            "startup_url",
            "tags",
        ],
        "optional": [],
        "unique": "startup_url",
        "urls": ["website", "startup_url"],
        "text": ["startup_name", "description"],
    },
}


def is_empty(value):
    """Check whether a field has a missing or empty value."""

    if value is None:
        return True

    if isinstance(value, str):
        return not value.strip()

    if isinstance(value, (list, dict)):
        return len(value) == 0

    return False


def is_valid_url(value):
    """Check whether a value is a valid HTTP or HTTPS URL."""

    if not isinstance(value, str):
        return False

    try:
        parsed = urlparse(value.strip())

        return (
            parsed.scheme in ("http", "https")
            and bool(parsed.netloc)
            and "." in parsed.netloc
        )

    except ValueError:
        return False


def validate_dataset(
    records,
    dataset_name,
    required_fields,
    unique_field,
    url_fields,
    text_fields,
    optional_fields=None,
):
    """Validate records and return a structured quality report."""

    optional_fields = optional_fields or []

    issues = []
    seen_values = set()

    if not isinstance(records, list):
        return {
            "dataset": dataset_name,
            "total_records": 0,
            "valid_records": 0,
            "invalid_records": 0,
            "warning_count": 0,
            "issues": [
                {
                    "record": None,
                    "field": "dataset",
                    "severity": "error",
                    "message": "Dataset must contain a JSON list.",
                }
            ],
        }

    valid_records = 0
    invalid_records = 0

    for index, record in enumerate(records, start=1):

        record_has_error = False

        def add_issue(field, severity, message):
            nonlocal record_has_error

            issues.append({
                "record": index,
                "field": field,
                "severity": severity,
                "message": message,
            })

            if severity == "error":
                record_has_error = True

        # Check record type
        if not isinstance(record, dict):

            add_issue(
                "record",
                "error",
                "Record must be a JSON object.",
            )

            invalid_records += 1
            continue

        # 1. Required-field validation
        for field in required_fields:

            if field not in record or is_empty(record[field]):

                add_issue(
                    field,
                    "error",
                    "Required field is missing or empty.",
                )

        # 2. Optional-field validation
        for field in optional_fields:

            if is_empty(record.get(field)):

                add_issue(
                    field,
                    "warning",
                    "Optional field is empty.",
                )

        # 3. Duplicate detection
        unique_value = record.get(unique_field)

        if not is_empty(unique_value):

            normalized_value = str(unique_value).strip().casefold()

            if normalized_value in seen_values:

                add_issue(
                    unique_field,
                    "error",
                    "Duplicate record detected.",
                )

            else:
                seen_values.add(normalized_value)

        # 4. URL validation
        for field in url_fields:

            value = record.get(field)

            if not is_empty(value) and not is_valid_url(value):

                add_issue(
                    field,
                    "error",
                    "Invalid HTTP or HTTPS URL.",
                )

        # 5. Text encoding validation
        encoding_markers = (
            "Ã",
            "â",
            "Î",
            "�",
        )

        for field in text_fields:

            value = record.get(field)

            if isinstance(value, str):

                if any(marker in value for marker in encoding_markers):

                    add_issue(
                        field,
                        "warning",
                        "Possible text encoding corruption detected.",
                    )

        # Record-level status
        if record_has_error:
            invalid_records += 1

        else:
            valid_records += 1

    # Count warnings
    warning_count = sum(
        1
        for issue in issues
        if issue["severity"] == "warning"
    )

    return {
        "dataset": dataset_name,
        "total_records": len(records),
        "valid_records": valid_records,
        "invalid_records": invalid_records,
        "warning_count": warning_count,
        "issues": issues,
    }


def run_validation():
    """Validate all configured datasets and save the report."""

    print("\n" + "=" * 55)
    print("          DATA VALIDATION AND QUALITY CHECK")
    print("=" * 55)

    report = {}

    for dataset_name, config in DATASETS.items():

        file_path = RAW_DIR / config["file"]

        try:

            with open(
                file_path,
                "r",
                encoding="utf-8",
            ) as file:

                records = json.load(file)

            result = validate_dataset(
                records=records,
                dataset_name=dataset_name,
                required_fields=config["required"],
                unique_field=config["unique"],
                url_fields=config["urls"],
                text_fields=config["text"],
                optional_fields=config.get("optional", []),
            )

        except (OSError, json.JSONDecodeError) as error:

            result = {
                "dataset": dataset_name,
                "total_records": 0,
                "valid_records": 0,
                "invalid_records": 0,
                "warning_count": 0,
                "load_error": str(error),
                "issues": [],
            }

        report[dataset_name] = result

        print(f"\nDataset: {dataset_name}")
        print(f"Total records : {result['total_records']}")
        print(f"Valid records : {result['valid_records']}")
        print(f"Invalid       : {result['invalid_records']}")
        print(f"Warnings      : {result['warning_count']}")

        if "load_error" in result:
            print(f"Load error    : {result['load_error']}")

    # Save validation report
    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    report_path = (
        PROCESSED_DIR / "data_validation_report.json"
    )

    with open(
        report_path,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            report,
            file,
            indent=4,
            ensure_ascii=False,
        )

    print("\n" + "=" * 55)
    print("VALIDATION COMPLETED")
    print("=" * 55)

    print("\nValidation report saved:")
    print(report_path)

    return report


if __name__ == "__main__":
    run_validation()
