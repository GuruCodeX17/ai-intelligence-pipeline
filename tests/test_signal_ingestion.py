"""
Tests for High-Fidelity Signal Ingestion & Date Normalization.
"""

from datetime import datetime, timedelta, timezone
from src.collectors.signal_collector import DateNormalizer, classify_role_family


def test_date_normalizer_relative_dates():
    ref = datetime(2026, 11, 23, 12, 0, 0, tzinfo=timezone.utc)

    # 2 hours ago
    iso, dt = DateNormalizer.normalize_to_iso("2 hours ago", reference_time=ref)
    assert dt == datetime(2026, 11, 23, 10, 0, 0, tzinfo=timezone.utc)
    assert DateNormalizer.is_within_24_hours(dt, reference_time=ref)

    # 45 mins ago
    iso, dt = DateNormalizer.normalize_to_iso("45 minutes ago", reference_time=ref)
    assert dt == datetime(2026, 11, 23, 11, 15, 0, tzinfo=timezone.utc)
    assert DateNormalizer.is_within_24_hours(dt, reference_time=ref)

    # 2 days ago (should fail 24h freshness)
    iso, dt = DateNormalizer.normalize_to_iso("2 days ago", reference_time=ref)
    assert dt == datetime(2026, 11, 21, 12, 0, 0, tzinfo=timezone.utc)
    assert not DateNormalizer.is_within_24_hours(dt, reference_time=ref)


def test_date_normalizer_rfc2822():
    ref = datetime(2026, 11, 23, 12, 0, 0, tzinfo=timezone.utc)
    raw = "Mon, 23 Nov 2026 01:25:53 +0000"
    iso, dt = DateNormalizer.normalize_to_iso(raw, reference_time=ref)
    assert dt is not None
    assert dt.year == 2026
    assert dt.month == 11
    assert dt.day == 23
    assert DateNormalizer.is_within_24_hours(dt, reference_time=ref)


def test_date_normalizer_iso():
    ref = datetime(2026, 11, 23, 12, 0, 0, tzinfo=timezone.utc)
    raw = "2026-11-23T05:30:00Z"
    iso, dt = DateNormalizer.normalize_to_iso(raw, reference_time=ref)
    assert dt is not None
    assert DateNormalizer.is_within_24_hours(dt, reference_time=ref)


def test_date_normalizer_missing_date_heuristic():
    ref = datetime(2026, 11, 23, 12, 0, 0, tzinfo=timezone.utc)
    iso, dt = DateNormalizer.normalize_to_iso(None, reference_time=ref, fallback_heuristic=True)
    assert dt == ref
    assert DateNormalizer.is_within_24_hours(dt, reference_time=ref)


def test_role_family_classification():
    assert classify_role_family("Senior Machine Learning Engineer") == "Engineering"
    assert classify_role_family("AI Research Scientist (PhD)") == "Research"
    assert classify_role_family("Product Manager - GenAI") == "Product"
    assert classify_role_family("Lead Data Analyst") == "Data & Analytics"
