"""
Tests for Multi-Tier LLM Extraction Engine & Fallback Chain.
"""

from unittest.mock import MagicMock
import pytest
from src.llm.orchestrator import (
    BaseLLMProvider,
    DeterministicRuleExtractor,
    IntelligentChunker,
    LLMOrchestrator,
    RateLimitError,
    PayloadTooLargeError,
)


class MockFlakyProvider(BaseLLMProvider):
    name = "Mock Flaky"
    tier = 1
    model_name = "flaky-v1"

    def __init__(self, fail_times=2):
        self.fail_times = fail_times
        self.call_count = 0

    def complete(self, prompt: str, system_prompt: str) -> str:
        self.call_count += 1
        if self.call_count <= self.fail_times:
            raise RateLimitError("Rate limit exceeded")
        return '{"result": "success_after_retry"}'


class MockFailingProvider(BaseLLMProvider):
    name = "Mock Failing"
    tier = 1
    model_name = "failing-v1"

    def complete(self, prompt: str, system_prompt: str) -> str:
        raise RateLimitError("Permanently 429")


class MockBackupProvider(BaseLLMProvider):
    name = "Mock Backup"
    tier = 2
    model_name = "backup-v1"

    def complete(self, prompt: str, system_prompt: str) -> str:
        return '{"result": "backup_success"}'


def test_chunker_strips_html_boilerplate():
    chunker = IntelligentChunker(max_characters=1000)
    html = """
    <html>
        <head><script>alert('noise')</script><style>.ad{color:red}</style></head>
        <body>
            <nav><a href='/'>Home</a></nav>
            <h1>OpenAI Announces GPT-5</h1>
            <p>OpenAI has released their next frontier model.</p>
            <footer>Copyright 2026</footer>
        </body>
    </html>
    """
    cleaned = chunker.clean_html(html)
    assert "alert('noise')" not in cleaned
    assert ".ad{color:red}" not in cleaned
    assert "Home" not in cleaned
    assert "Copyright 2026" not in cleaned
    assert "OpenAI Announces GPT-5" in cleaned
    assert "OpenAI has released their next frontier model." in cleaned


def test_chunker_truncates_large_payload_to_prevent_413():
    chunker = IntelligentChunker(max_characters=500)
    long_text = "Headline: Important AI Launch\n" + ("x" * 2000) + "\nConclusion: Successful test."
    chunked = chunker.chunk_payload(long_text, preserve_header_chars=100)
    assert len(chunked) <= 600
    assert "TRUNCATED MIDDLE CONTENT TO PREVENT 413 OVERFLOW" in chunked
    assert "Headline: Important AI Launch" in chunked


def test_fallback_chain_on_tier_failure():
    tier1 = MockFailingProvider()
    tier2 = MockBackupProvider()

    orchestrator = LLMOrchestrator(
        providers=[tier1, tier2],
        max_retries_per_tier=1,
        base_backoff_seconds=0.01,
        jitter_seconds=0.01,
    )

    data, provider_used = orchestrator.extract_structured("Test prompt input")
    assert provider_used == "Mock Backup"
    assert data == {"result": "backup_success"}


def test_rate_limit_retry_with_backoff():
    flaky = MockFlakyProvider(fail_times=2)
    orchestrator = LLMOrchestrator(
        providers=[flaky],
        max_retries_per_tier=3,
        base_backoff_seconds=0.01,
        jitter_seconds=0.01,
    )

    data, provider_used = orchestrator.extract_structured("Test input")
    assert flaky.call_count == 3
    assert provider_used == "Mock Flaky"
    assert data == {"result": "success_after_retry"}


def test_deterministic_rule_fallback_succeeds_offline():
    deterministic = DeterministicRuleExtractor()
    orchestrator = LLMOrchestrator(providers=[deterministic])

    input_text = "Anthropic announces Claude 4\nAnthropic has made breakthrough progress."
    data, provider_used = orchestrator.extract_structured(input_text)
    assert provider_used == "Deterministic Extractor"
    assert data["title"] == "Anthropic announces Claude 4"
    assert "Anthropic" in data["summary"]
