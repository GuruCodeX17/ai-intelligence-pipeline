"""
Tests for Anti-Bot Asynchronous Crawler and Stealth Engine.
"""

import asyncio
import time
import pytest
from src.collectors.antibot_crawler import (
    AsyncAntiBotCrawler,
    DomainRateLimiter,
    PlaywrightStealthStrategy,
)


def test_stealth_headers_generation():
    headers = AsyncAntiBotCrawler.get_stealth_headers()
    assert "User-Agent" in headers
    assert "Sec-Ch-Ua" in headers
    assert headers["Sec-Ch-Ua-Mobile"] == "?0"
    assert headers["Sec-Fetch-Dest"] == "document"


def test_domain_rate_limiter():
    async def _run():
        limiter = DomainRateLimiter(delay_between_requests=0.05)
        url = "https://example.com/page1"

        start = time.monotonic()
        await limiter.wait(url)
        await limiter.wait(url)
        elapsed = time.monotonic() - start

        assert elapsed >= 0.04

    asyncio.run(_run())


def test_playwright_stealth_architecture_summary():
    summary = PlaywrightStealthStrategy.get_architecture_summary()
    assert "evasions" in summary
    assert "network_layer" in summary
    assert len(summary["evasions"]) >= 3
