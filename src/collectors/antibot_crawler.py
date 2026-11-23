"""
Anti-Bot & Resilient Asynchronous Crawler Engine (Phase V)
Features:
1. High-concurrency async fetching using asyncio + aiohttp.
2. Per-domain token-bucket rate limiting and jitter to avoid WAF velocity triggers.
3. Realistic browser fingerprint emulation (Client Hints, modern Sec-CH headers, User-Agent pool).
4. Cloudflare / Datadome detection, exponential backoff, and jittered retries.
5. Playwright Async stealth engine architecture for JavaScript-rendered & captcha-protected targets.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import aiohttp

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
]


class DomainRateLimiter:
    """Token-bucket per-domain rate limiter to avoid triggering Cloudflare rate rules."""

    def __init__(self, delay_between_requests: float = 1.0):
        self.delay = delay_between_requests
        self.last_request_time: Dict[str, float] = {}
        self.locks: Dict[str, asyncio.Lock] = {}

    def _get_domain(self, url: str) -> str:
        return urlparse(url).netloc.lower()

    async def wait(self, url: str) -> None:
        domain = self._get_domain(url)
        if domain not in self.locks:
            self.locks[domain] = asyncio.Lock()

        async with self.locks[domain]:
            now = time.monotonic()
            last = self.last_request_time.get(domain, 0.0)
            elapsed = now - last
            if elapsed < self.delay:
                jitter = random.uniform(0.1, 0.4)
                await asyncio.sleep((self.delay - elapsed) + jitter)
            self.last_request_time[domain] = time.monotonic()


class AsyncAntiBotCrawler:
    """
    Production-grade asynchronous crawler capable of handling high throughput
    while evading anti-bot detection systems.
    """

    def __init__(
        self,
        max_concurrency: int = 10,
        domain_delay: float = 0.5,
        max_retries: int = 3,
        proxy: Optional[str] = None,
    ):
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.rate_limiter = DomainRateLimiter(delay_between_requests=domain_delay)
        self.max_retries = max_retries
        self.proxy = proxy

    @staticmethod
    def get_stealth_headers() -> Dict[str, str]:
        """Generate realistic browser headers mimicking modern Google Chrome on Windows/macOS."""
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "DNT": "1",
        }

    async def fetch_url(
        self,
        session: aiohttp.ClientSession,
        url: str,
    ) -> Tuple[int, str]:
        """Fetch single URL with stealth headers, rate limiting, and exponential retry."""
        async with self.semaphore:
            await self.rate_limiter.wait(url)

            for attempt in range(self.max_retries):
                headers = self.get_stealth_headers()
                try:
                    async with session.get(
                        url,
                        headers=headers,
                        proxy=self.proxy,
                        timeout=aiohttp.ClientTimeout(total=15),
                    ) as response:
                        status = response.status

                        # Cloudflare / Datadome Challenge Detection
                        if status in (403, 429, 503):
                            text = await response.text()
                            is_cloudflare = any(m in text.lower() for m in ["cloudflare", "turnstile", "cf-browser-verification", "ddos-protection"])
                            if is_cloudflare or status == 429:
                                sleep_time = (1.5 ** attempt) + random.uniform(1.0, 2.0)
                                logger.warning(
                                    f"Anti-bot barrier triggered for {url} (HTTP {status}). Retrying in {sleep_time:.2f}s..."
                                )
                                await asyncio.sleep(sleep_time)
                                continue

                        text = await response.text()
                        return status, text

                except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                    if attempt == self.max_retries - 1:
                        logger.error(f"Failed to fetch {url} after {self.max_retries} attempts: {err}")
                        return 0, ""
                    await asyncio.sleep(1.0 + random.uniform(0.5, 1.5))

            return 0, ""

    async def fetch_many(self, urls: List[str]) -> List[Tuple[str, int, str]]:
        """Concurrent bulk download across a list of URLs."""
        async with aiohttp.ClientSession() as session:
            tasks = [self.fetch_url(session, url) for url in urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            output = []
            for url, res in zip(urls, results):
                if isinstance(res, Exception):
                    output.append((url, 0, ""))
                else:
                    status, body = res
                    output.append((url, status, body))
            return output


class PlaywrightStealthStrategy:
    """
    Architectural blueprint and documentation for bypassing hardened Cloudflare / Datadome
    bot mitigation using Playwright Async with browser stealth evasions.
    """

    STEALTH_SCRIPTS = """
    // Override navigator.webdriver flag
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    // Mock standard plugins array
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
    // Spoof languages
    Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
    // Add chrome runtime object
    window.chrome = { runtime: {} };
    """

    RECOMMENDED_ARGS = [
        "--disable-blink-features=AutomationControlled",
        "--disable-features=IsolateOrigins,site-per-process",
        "--use-fake-ui-for-media-stream",
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--window-size=1920,1080",
    ]

    @classmethod
    def get_architecture_summary(cls) -> Dict[str, Any]:
        return {
            "browser_engine": "Chromium (Headless=new)",
            "evasions": [
                "navigator.webdriver masking",
                "Chrome runtime emulation",
                "WebGL vendor/renderer spoofing (ANGLE Direct3D11)",
                "Canvas fingerprint randomization with noise injections",
                "AudioContext latency jitter",
            ],
            "network_layer": "Rotating Residential / 4G Mobile Proxies with Sticky IP per Session",
            "captcha_solving": "Automated Turnstile / hCaptcha click heuristics with fallback to CapSolver/2Captcha API",
            "concurrency_model": "Worker pool with browser context recycling every 50 requests to prevent memory leaks",
        }
