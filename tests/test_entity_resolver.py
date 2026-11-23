"""
Tests for Deterministic Entity Resolution Engine
"""

from src.processing.entity_resolver import EntityResolver, default_entity_resolver


def test_openai_canonicalization():
    resolver = EntityResolver()
    assert resolver.resolve("OpenAI")[0] == "OpenAI"
    assert resolver.resolve("OpenAI, Inc.")[0] == "OpenAI"
    assert resolver.resolve("Open AI")[0] == "OpenAI"
    assert resolver.resolve("OpenAI LLC")[0] == "OpenAI"


def test_anthropic_canonicalization():
    resolver = EntityResolver()
    assert resolver.resolve("Anthropic")[0] == "Anthropic"
    assert resolver.resolve("Anthropic, PBC")[0] == "Anthropic"
    assert resolver.resolve("Anthropic PBC")[0] == "Anthropic"
    assert resolver.resolve("Anthropic Inc")[0] == "Anthropic"


def test_cursor_alias_canonicalization():
    resolver = EntityResolver()
    assert resolver.resolve("Anysphere")[0] == "Cursor"
    assert resolver.resolve("Anysphere, Inc.")[0] == "Cursor"
    assert resolver.resolve("Cursor AI")[0] == "Cursor"


def test_fuzzy_match():
    resolver = EntityResolver()
    # Typo / slight variation
    canonical, method, conf = resolver.resolve("Midjourney Inc")
    assert canonical == "Midjourney"
    assert conf >= 0.85


def test_mapping_log_recording():
    resolver = EntityResolver()
    resolver.resolve("OpenAI, Inc.", entity_type="STARTUP")
    resolver.resolve("RunwayML", entity_type="PRODUCT_MAKER")

    log = resolver.get_mapping_log()
    assert len(log) == 2
    assert log[0]["raw_name"] == "OpenAI, Inc."
    assert log[0]["canonical_name"] == "OpenAI"
    assert log[0]["is_seed_match"] is True
    assert log[0]["matched_seed_id"] == "ai-001"
    assert log[1]["raw_name"] == "RunwayML"
    assert log[1]["canonical_name"] == "Runway"


def test_empty_string_handling():
    resolver = EntityResolver()
    canonical, method, conf = resolver.resolve("")
    assert canonical == ""
    assert method == "EMPTY"
    assert conf == 0.0
