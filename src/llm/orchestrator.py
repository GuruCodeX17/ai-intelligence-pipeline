"""
Multi-Tier LLM Extraction Engine & Orchestrator
Features:
1. Multi-tier fallback chain: Gemini Flash -> Groq Llama 3 -> DeepSeek -> Deterministic Fallback.
2. Intelligent chunking & token budgeting preventing HTTP 413 (Payload Too Large).
3. Resilient Rate Limit (HTTP 429) handling with exponential backoff and jitter.
4. Schema-enforced canonical JSON extraction.
"""

from __future__ import annotations

import json
import logging
import os
import random
import re
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Type
from bs4 import BeautifulSoup
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)


class RateLimitError(Exception):
    """Raised when an LLM provider returns HTTP 429 Too Many Requests."""
    pass


class PayloadTooLargeError(Exception):
    """Raised when payload exceeds context window / HTTP 413."""
    pass


class IntelligentChunker:
    """
    Semantic chunker and text preprocessor.
    Truncates and filters raw HTML/text to avoid 413 Payload Too Large
    while preserving high-density semantic information.
    """

    def __init__(self, max_characters: int = 12000):
        self.max_characters = max_characters

    def clean_html(self, raw_html: str) -> str:
        """Strip boilerplate HTML elements (scripts, styles, navs, footers)."""
        if not raw_html:
            return ""

        soup = BeautifulSoup(raw_html, "html.parser")

        # Strip non-informative DOM nodes
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg", "iframe", "form"]):
            tag.decompose()

        # Extract text with hierarchical linebreaks
        text = soup.get_text(separator="\n", strip=True)

        # Collapse excess empty lines
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def chunk_payload(self, content: str, preserve_header_chars: int = 3000) -> str:
        """
        Intelligently truncate content exceeding context budgets.
        Keeps the initial dense header context (titles, metadata, lead paragraphs)
        and tail context (author, summary, conclusion), discarding middle fluff.
        """
        if not content:
            return ""

        if len(content) <= self.max_characters:
            return content

        # Split into head and tail preserving semantic density
        head = content[:preserve_header_chars]
        remaining_budget = self.max_characters - preserve_header_chars - 100
        tail = content[-remaining_budget:]

        return f"{head}\n\n[... TRUNCATED MIDDLE CONTENT TO PREVENT 413 OVERFLOW ...]\n\n{tail}"


class BaseLLMProvider(ABC):
    """Abstract Base Class for LLM Providers in the fallback chain."""

    name: str
    tier: int
    model_name: str

    @abstractmethod
    def complete(self, prompt: str, system_prompt: str) -> str:
        """Execute chat completion and return raw text response."""
        pass


class GeminiFlashProvider(BaseLLMProvider):
    """Tier 1: Google Gemini Flash provider."""

    name = "Gemini Flash"
    tier = 1
    model_name = "gemini-1.5-flash"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")

    def complete(self, prompt: str, system_prompt: str) -> str:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not configured.")

        import requests

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
        payload = {
            "contents": [
                {"role": "user", "parts": [{"text": f"{system_prompt}\n\n{prompt}"}]}
            ],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 2048},
        }

        resp = requests.post(url, json=payload, timeout=20)
        if resp.status_code == 429:
            raise RateLimitError("Gemini Flash rate limit reached (HTTP 429).")
        if resp.status_code == 413:
            raise PayloadTooLargeError("Gemini Flash payload too large (HTTP 413).")
        resp.raise_for_status()

        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            raise RuntimeError("Gemini returned empty candidates.")
        return candidates[0]["content"]["parts"][0]["text"]


class GroqLlama3Provider(BaseLLMProvider):
    """Tier 2: Groq Llama 3 (Ultra-fast fallback)."""

    name = "Groq Llama 3"
    tier = 2
    model_name = "llama-3.3-70b-versatile"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")

    def complete(self, prompt: str, system_prompt: str) -> str:
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not configured.")

        import requests

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=20)
        if resp.status_code == 429:
            raise RateLimitError("Groq rate limit reached (HTTP 429).")
        if resp.status_code == 413:
            raise PayloadTooLargeError("Groq payload too large (HTTP 413).")
        resp.raise_for_status()

        data = resp.json()
        return data["choices"][0]["message"]["content"]


class DeepSeekProvider(BaseLLMProvider):
    """Tier 3: DeepSeek provider."""

    name = "DeepSeek"
    tier = 3
    model_name = "deepseek-chat"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")

    def complete(self, prompt: str, system_prompt: str) -> str:
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY not configured.")

        import requests

        url = "https://api.deepseek.com/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=25)
        if resp.status_code == 429:
            raise RateLimitError("DeepSeek rate limit reached (HTTP 429).")
        if resp.status_code == 413:
            raise PayloadTooLargeError("DeepSeek payload too large (HTTP 413).")
        resp.raise_for_status()

        data = resp.json()
        return data["choices"][0]["message"]["content"]


class DeterministicRuleExtractor(BaseLLMProvider):
    """
    Tier 4: Resilient Offline / Rule-Based Extractor.
    Guarantees zero downtime, schema compliance, and offline evaluation
    without requiring third-party API credits.
    """

    name = "Deterministic Extractor"
    tier = 4
    model_name = "rule-engine-v1"

    def complete(self, prompt: str, system_prompt: str) -> str:
        """Extract structured JSON fields from text using pattern heuristics."""
        lines = [line.strip() for line in prompt.split("\n") if line.strip()]

        result = {
            "title": lines[0] if lines else "Untitled Extraction",
            "summary": " ".join(lines[1:5]) if len(lines) > 1 else "",
            "entities": [re.sub(r"[^\w\s]", "", word) for word in prompt.split()[:5] if len(word) > 3],
            "extracted_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        return json.dumps(result)


class LLMOrchestrator:
    """
    Coordinates multi-tier LLM fallback, chunking, and exponential backoff retry.
    """

    def __init__(
        self,
        providers: Optional[List[BaseLLMProvider]] = None,
        max_retries_per_tier: int = 3,
        base_backoff_seconds: float = 1.0,
        jitter_seconds: float = 0.5,
        max_characters: int = 12000,
    ):
        self.chunker = IntelligentChunker(max_characters=max_characters)
        self.max_retries = max_retries_per_tier
        self.base_backoff = base_backoff_seconds
        self.jitter = jitter_seconds

        # Configure tier chain
        if providers is not None:
            self.providers = providers
        else:
            self.providers = [
                GeminiFlashProvider(),
                GroqLlama3Provider(),
                DeepSeekProvider(),
                DeterministicRuleExtractor(),
            ]

    def _execute_with_backoff(
        self,
        provider: BaseLLMProvider,
        prompt: str,
        system_prompt: str,
    ) -> str:
        """
        Execute call on a provider with exponential backoff and jitter on 429 rate limits.
        """
        for attempt in range(self.max_retries):
            try:
                return provider.complete(prompt, system_prompt)
            except RateLimitError as rate_err:
                if attempt == self.max_retries - 1:
                    logger.warning(
                        f"[{provider.name}] Exhausted {self.max_retries} retries on 429: {rate_err}"
                    )
                    raise

                sleep_time = (self.base_backoff * (2 ** attempt)) + random.uniform(0, self.jitter)
                logger.info(
                    f"[{provider.name}] HTTP 429 encountered. Backing off for {sleep_time:.2f}s (attempt {attempt + 1}/{self.max_retries})"
                )
                time.sleep(sleep_time)

            except PayloadTooLargeError:
                # 413 should not be retried with the same payload; fail immediately to let caller chunk harder or fall back
                raise

        raise RuntimeError(f"[{provider.name}] Failed after retries.")

    def extract_structured(
        self,
        raw_text_or_html: str,
        target_schema: Optional[Type[BaseModel]] = None,
        system_instructions: Optional[str] = None,
    ) -> Tuple[Dict[str, Any], str]:
        """
        Extract structured data using the multi-tier fallback chain.

        Returns:
            Tuple[parsed_json_dict, provider_name_used]
        """
        # Step 1: Pre-process and chunk to avoid 413
        cleaned_text = self.chunker.clean_html(raw_text_or_html)
        chunked_text = self.chunker.chunk_payload(cleaned_text)

        system_prompt = system_instructions or (
            "You are an AI data extraction engine. Extract the required entities "
            "from the input text and respond ONLY with valid JSON."
        )

        # Step 2: Iterate across fallback chain
        last_exception = None

        for provider in self.providers:
            try:
                raw_response = self._execute_with_backoff(
                    provider,
                    chunked_text,
                    system_prompt,
                )

                # Extract JSON block
                clean_json_str = self._clean_json_markdown(raw_response)
                parsed_data = json.loads(clean_json_str)

                # Validate against Pydantic schema if provided
                if target_schema is not None:
                    if isinstance(parsed_data, list):
                        validated = [target_schema(**item).model_dump() for item in parsed_data]
                        return {"items": validated}, provider.name
                    else:
                        validated = target_schema(**parsed_data).model_dump()
                        return validated, provider.name

                return parsed_data, provider.name

            except (RateLimitError, PayloadTooLargeError, ValueError, RuntimeError, json.JSONDecodeError, ValidationError) as err:
                logger.warning(f"Tier {provider.tier} ({provider.name}) failed: {err}. Falling back...")
                last_exception = err
                continue

        raise RuntimeError(f"All providers in the fallback chain failed. Last error: {last_exception}")

    @staticmethod
    def _clean_json_markdown(response_text: str) -> str:
        """Strip markdown fences (```json ... ```) from model output."""
        text = response_text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()


# Default orchestrator singleton
default_orchestrator = LLMOrchestrator()
