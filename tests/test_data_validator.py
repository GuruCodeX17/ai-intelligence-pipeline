
from src.processing.data_validator import (
    is_empty,
    is_valid_url,
    validate_dataset,
)


def sample_record():
    return {
        "name": "Test AI Project",
        "description": "A sample AI project",
        "url": "https://example.com/project",
        "stars": 10,
    }


def validate(records):
    return validate_dataset(
        records=records,
        dataset_name="test_dataset",
        required_fields=["name", "url", "stars"],
        unique_field="url",
        url_fields=["url"],
        text_fields=["name", "description"],
        optional_fields=["description"],
    )


def test_is_empty():
    assert is_empty(None) is True
    assert is_empty("") is True
    assert is_empty("   ") is True
    assert is_empty([]) is True
    assert is_empty({}) is True
    assert is_empty("Hello") is False
    assert is_empty(0) is False


def test_is_valid_url():
    assert is_valid_url("https://example.com") is True
    assert is_valid_url("http://example.com/page") is True
    assert is_valid_url("invalid-url") is False
    assert is_valid_url("ftp://example.com") is False
    assert is_valid_url("") is False


def test_valid_record():
    result = validate([sample_record()])

    assert result["total_records"] == 1
    assert result["valid_records"] == 1
    assert result["invalid_records"] == 0
    assert result["warning_count"] == 0


def test_missing_required_field():
    record = sample_record()
    record["name"] = ""

    result = validate([record])

    assert result["invalid_records"] == 1
    assert result["valid_records"] == 0
    assert result["issues"][0]["field"] == "name"
    assert result["issues"][0]["severity"] == "error"


def test_empty_optional_field_generates_warning():
    record = sample_record()
    record["description"] = ""

    result = validate([record])

    assert result["valid_records"] == 1
    assert result["invalid_records"] == 0
    assert result["warning_count"] == 1
    assert result["issues"][0]["field"] == "description"
    assert result["issues"][0]["severity"] == "warning"


def test_duplicate_records():
    record1 = sample_record()
    record2 = sample_record()

    result = validate([record1, record2])

    assert result["total_records"] == 2
    assert result["valid_records"] == 1
    assert result["invalid_records"] == 1

    duplicate_issues = [
        issue for issue in result["issues"]
        if issue["message"] == "Duplicate record detected."
    ]

    assert len(duplicate_issues) == 1


def test_invalid_url():
    record = sample_record()
    record["url"] = "not-a-valid-url"

    result = validate([record])

    assert result["invalid_records"] == 1

    assert any(
        issue["field"] == "url"
        and issue["severity"] == "error"
        for issue in result["issues"]
    )


def test_encoding_warning():
    record = sample_record()
    record["description"] = "This text contains Ã corrupted characters"

    result = validate([record])

    assert result["valid_records"] == 1
    assert result["invalid_records"] == 0
    assert result["warning_count"] == 1

    assert any(
        issue["field"] == "description"
        and issue["severity"] == "warning"
        for issue in result["issues"]
    )


def test_non_list_dataset():
    result = validate_dataset(
        records={"name": "Invalid dataset"},
        dataset_name="test_dataset",
        required_fields=["name"],
        unique_field="name",
        url_fields=[],
        text_fields=["name"],
    )

    assert result["total_records"] == 0
    assert result["invalid_records"] == 0
    assert result["issues"][0]["severity"] == "error"


def test_non_dictionary_record():
    result = validate([None])

    assert result["total_records"] == 1
    assert result["valid_records"] == 0
    assert result["invalid_records"] == 1
    assert result["issues"][0]["field"] == "record"
