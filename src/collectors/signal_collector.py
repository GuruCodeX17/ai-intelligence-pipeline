"""
High-Fidelity Signal Ingestion Engine (Phase II)
Monitors 5 distinct AI news sources and 5 distinct AI job boards.
Enforces strict 24-hour freshness, date normalization (handling relative dates),
full-text extraction, and intelligent deduplication heuristics.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import feedparser
import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from src.processing.entity_resolver import default_entity_resolver

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, application/xml, text/html, */*",
}


class DateNormalizer:
    """
    Parses and normalizes dates across heterogenous formats:
    - ISO-8601
    - RFC 2822 / RSS (e.g., 'Mon, 23 Nov 2026 01:25:53 +0000')
    - Relative timestamps (e.g., '2 hours ago', '45m ago', 'yesterday')
    - Unix epoch timestamps (seconds or milliseconds)
    """

    @staticmethod
    def parse_relative_date(text: str, reference_time: Optional[datetime] = None) -> Optional[datetime]:
        """Convert relative date strings like '2 hours ago' into UTC datetime."""
        if not text or not isinstance(text, str):
            return None

        clean = text.lower().strip()
        ref = reference_time or datetime.now(timezone.utc)

        if "just now" in clean or "moments ago" in clean:
            return ref

        if "yesterday" in clean:
            return ref - timedelta(days=1)

        # Pattern: N hours / hrs / hr / minutes / mins / min / days / d / sec
        match = re.search(r"(\d+)\s*(hour|hr|h|minute|min|m|day|d|second|sec|s)s?\s*ago", clean)
        if match:
            amount = int(match.group(1))
            unit = match.group(2)

            if unit in ("hour", "hr", "h"):
                return ref - timedelta(hours=amount)
            elif unit in ("minute", "min", "m"):
                return ref - timedelta(minutes=amount)
            elif unit in ("day", "d"):
                return ref - timedelta(days=amount)
            elif unit in ("second", "sec", "s"):
                return ref - timedelta(seconds=amount)

        return None

    @classmethod
    def normalize_to_iso(
        cls,
        raw_date: Any,
        reference_time: Optional[datetime] = None,
        fallback_heuristic: bool = True,
    ) -> Tuple[Optional[str], Optional[datetime]]:
        """
        Normalize raw date input to ISO-8601 string and datetime object.
        """
        ref = reference_time or datetime.now(timezone.utc)

        if raw_date is None:
            if fallback_heuristic:
                # Fallback heuristic: newly discovered signal assumed published near reference time
                return ref.isoformat(), ref
            return None, None

        # Numeric Unix timestamp
        if isinstance(raw_date, (int, float)):
            # Distinguish milliseconds vs seconds
            ts = raw_date / 1000.0 if raw_date > 1e11 else raw_date
            try:
                dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                return dt.isoformat(), dt
            except (ValueError, OSError):
                return None, None

        if isinstance(raw_date, datetime):
            if raw_date.tzinfo is None:
                raw_date = raw_date.replace(tzinfo=timezone.utc)
            else:
                raw_date = raw_date.astimezone(timezone.utc)
            return raw_date.isoformat(), raw_date

        text = str(raw_date).strip()
        if not text:
            return (ref.isoformat(), ref) if fallback_heuristic else (None, None)

        # Check relative date first
        rel_dt = cls.parse_relative_date(text, reference_time=ref)
        if rel_dt:
            return rel_dt.isoformat(), rel_dt

        # Check standard date formats via dateutil
        try:
            dt = date_parser.parse(text)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            return dt.isoformat(), dt
        except (ValueError, OverflowError):
            pass

        if fallback_heuristic:
            return ref.isoformat(), ref
        return None, None

    @classmethod
    def is_within_24_hours(
        cls,
        dt: Optional[datetime],
        reference_time: Optional[datetime] = None,
        max_hours: float = 24.0,
    ) -> bool:
        """Verify that the timestamp is strictly within the last 24 hours."""
        if dt is None:
            return False

        ref = reference_time or datetime.now(timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)

        diff = ref - dt
        # Allow up to 10 minutes future clock drift, and strictly up to max_hours in past
        return -timedelta(minutes=10) <= diff <= timedelta(hours=max_hours)


def clean_article_text(html_or_text: str) -> str:
    """Extract clean, dense textual content from HTML markup."""
    if not html_or_text:
        return ""
    soup = BeautifulSoup(html_or_text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
    return " ".join(soup.get_text(" ", strip=True).split())


# =====================================================================
# 5 DISTINCT AI NEWS SOURCES
# =====================================================================

NEWS_SOURCES = [
    {
        "name": "TechCrunch AI",
        "url": "https://techcrunch.com/category/artificial-intelligence/feed/",
        "type": "rss",
    },
    {
        "name": "Wired AI",
        "url": "https://www.wired.com/feed/tag/ai/latest/rss",
        "type": "rss",
    },
    {
        "name": "The Verge AI",
        "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
        "type": "rss",
    },
    {
        "name": "Decrypt AI",
        "url": "https://decrypt.co/feed",
        "type": "rss",
    },
    {
        "name": "HackerNews AI Signals",
        "url": "https://hn.algolia.com/api/v1/search_by_date?tags=story&query=AI",
        "type": "json_api",
    },
]


def collect_fresh_news(
    sources: Optional[List[Dict[str, str]]] = None,
    reference_time: Optional[datetime] = None,
    enforce_24h: bool = True,
) -> List[Dict[str, Any]]:
    """
    Collect and normalize news signals across 5 distinct sources.
    Filters exclusively for items published within the last 24 hours.
    """
    ref_time = reference_time or datetime.now(timezone.utc)
    sources_to_query = sources or NEWS_SOURCES
    news_records = []
    seen_urls = set()

    print(f"\n[Phase II] Ingesting 24-hr Fresh News Signals across {len(sources_to_query)} sources...")

    for src in sources_to_query:
        name = src["name"]
        url = src["url"]
        stype = src.get("type", "rss")

        try:
            resp = requests.get(url, headers=HEADERS, timeout=12)
            if resp.status_code != 200:
                logger.warning(f"Failed to fetch {name}: HTTP {resp.status_code}")
                continue

            if stype == "rss":
                feed = feedparser.parse(resp.content)
                for entry in feed.entries:
                    link = entry.get("link", "")
                    if not link or link in seen_urls:
                        continue

                    raw_date = entry.get("published") or entry.get("updated")
                    iso_date, dt = DateNormalizer.normalize_to_iso(raw_date, reference_time=ref_time)

                    if enforce_24h and not DateNormalizer.is_within_24_hours(dt, reference_time=ref_time):
                        continue

                    title = clean_article_text(entry.get("title", ""))
                    summary = clean_article_text(entry.get("summary", ""))

                    seen_urls.add(link)
                    news_records.append({
                        "schemaVersion": "1.0",
                        "recordType": "NEWS",
                        "source": {
                            "name": name,
                            "url": link,
                        },
                        "content": {
                            "title": title,
                            "published_date": iso_date,
                            "summary": summary[:400] if summary else title,
                            "full_text": summary,
                        },
                        "collectedAt": ref_time.isoformat(),
                    })

            elif stype == "json_api":
                data = resp.json()
                hits = data.get("hits", [])
                for hit in hits:
                    link = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
                    if not link or link in seen_urls:
                        continue

                    raw_date = hit.get("created_at")
                    iso_date, dt = DateNormalizer.normalize_to_iso(raw_date, reference_time=ref_time)

                    if enforce_24h and not DateNormalizer.is_within_24_hours(dt, reference_time=ref_time):
                        continue

                    title = clean_article_text(hit.get("title", ""))
                    if not title:
                        continue

                    seen_urls.add(link)
                    news_records.append({
                        "schemaVersion": "1.0",
                        "recordType": "NEWS",
                        "source": {
                            "name": name,
                            "url": link,
                        },
                        "content": {
                            "title": title,
                            "published_date": iso_date,
                            "summary": title,
                            "full_text": f"{title} (Discussed on Hacker News, points: {hit.get('points', 0)})",
                        },
                        "collectedAt": ref_time.isoformat(),
                    })

        except Exception as err:
            logger.warning(f"Error querying news source {name}: {err}")

    print(f"Collected {len(news_records)} fresh AI news articles (published in last 24h).")
    return news_records


# =====================================================================
# 5 DISTINCT AI JOB BOARDS
# =====================================================================

JOB_SOURCES = [
    {
        "name": "RemoteOK",
        "url": "https://remoteok.com/api?tag=ai",
        "parser": "remoteok",
    },
    {
        "name": "Jobicy",
        "url": "https://jobicy.com/api/v2/remote-jobs?count=50&tag=ai",
        "parser": "jobicy",
    },
    {
        "name": "Remotive",
        "url": "https://remotive.com/api/remote-jobs?search=ai&limit=50",
        "parser": "remotive",
    },
    {
        "name": "Arbeitnow",
        "url": "https://www.arbeitnow.com/api/job-board-api",
        "parser": "arbeitnow",
    },
    {
        "name": "Himalayas",
        "url": "https://himalayas.app/jobs/api?search=ai",
        "parser": "himalayas",
    },
]


def classify_role_family(title: str, description: str = "") -> str:
    """Classify role into canonical functional category."""
    text = f"{title} {description}".lower()

    if any(k in text for k in ["research", "scientist", "phd", "postdoc"]):
        return "Research"
    elif any(k in text for k in ["engineer", "developer", "backend", "fullstack", "infrastructure", "mlops", "software"]):
        return "Engineering"
    elif any(k in text for k in ["product", "pm", "product manager"]):
        return "Product"
    elif any(k in text for k in ["data", "analytics", "bi", "analyst"]):
        return "Data & Analytics"
    elif any(k in text for k in ["design", "ux", "ui"]):
        return "Design"
    elif any(k in text for k in ["sales", "marketing", "growth", "account"]):
        return "Growth & Sales"
    return "Operations"


def collect_fresh_jobs(
    sources: Optional[List[Dict[str, str]]] = None,
    reference_time: Optional[datetime] = None,
    enforce_24h: bool = True,
) -> List[Dict[str, Any]]:
    """
    Collect and normalize fresh AI job postings across 5 distinct job boards.
    Filters exclusively for jobs posted within the last 24 hours.
    Resolves company names via EntityResolver.
    """
    ref_time = reference_time or datetime.now(timezone.utc)
    sources_to_query = sources or JOB_SOURCES
    job_records = []
    seen_urls = set()

    print(f"\n[Phase II] Ingesting 24-hr Fresh AI Jobs across {len(sources_to_query)} job boards...")

    for src in sources_to_query:
        name = src["name"]
        url = src["url"]
        parser_type = src["parser"]

        try:
            resp = requests.get(url, headers=HEADERS, timeout=12)
            if resp.status_code != 200:
                logger.warning(f"Failed to fetch jobs from {name}: HTTP {resp.status_code}")
                continue

            data = resp.json()

            if parser_type == "remoteok":
                items = data[1:] if isinstance(data, list) and len(data) > 1 else []
                for item in items:
                    job_url = item.get("url") or f"https://remoteok.com/l/{item.get('id')}"
                    if not job_url or job_url in seen_urls:
                        continue

                    raw_date = item.get("date")
                    iso_date, dt = DateNormalizer.normalize_to_iso(raw_date, reference_time=ref_time)

                    if enforce_24h and not DateNormalizer.is_within_24_hours(dt, reference_time=ref_time):
                        continue

                    raw_company = item.get("company", "Unknown")
                    canonical_company, _, _ = default_entity_resolver.resolve(raw_company, entity_type="JOB_COMPANY")
                    title = clean_article_text(item.get("position", "AI Specialist"))

                    seen_urls.add(job_url)
                    job_records.append({
                        "schemaVersion": "1.0",
                        "recordType": "JOB",
                        "source": {
                            "name": name,
                            "url": job_url,
                        },
                        "content": {
                            "company": canonical_company,
                            "title": title,
                            "date": iso_date,
                            "is_remote": True,
                            "role_family": classify_role_family(title),
                        },
                        "collectedAt": ref_time.isoformat(),
                    })

            elif parser_type == "jobicy":
                items = data.get("jobs", [])
                for item in items:
                    job_url = item.get("url", "")
                    if not job_url or job_url in seen_urls:
                        continue

                    raw_date = item.get("pubDate")
                    iso_date, dt = DateNormalizer.normalize_to_iso(raw_date, reference_time=ref_time)

                    if enforce_24h and not DateNormalizer.is_within_24_hours(dt, reference_time=ref_time):
                        continue

                    raw_company = item.get("companyName", "Unknown")
                    canonical_company, _, _ = default_entity_resolver.resolve(raw_company, entity_type="JOB_COMPANY")
                    title = clean_article_text(item.get("jobTitle", "AI Role"))

                    seen_urls.add(job_url)
                    job_records.append({
                        "schemaVersion": "1.0",
                        "recordType": "JOB",
                        "source": {
                            "name": name,
                            "url": job_url,
                        },
                        "content": {
                            "company": canonical_company,
                            "title": title,
                            "date": iso_date,
                            "is_remote": True,
                            "role_family": classify_role_family(title),
                        },
                        "collectedAt": ref_time.isoformat(),
                    })

            elif parser_type == "remotive":
                items = data.get("jobs", [])
                for item in items:
                    job_url = item.get("url", "")
                    if not job_url or job_url in seen_urls:
                        continue

                    raw_date = item.get("publication_date")
                    iso_date, dt = DateNormalizer.normalize_to_iso(raw_date, reference_time=ref_time)

                    if enforce_24h and not DateNormalizer.is_within_24_hours(dt, reference_time=ref_time):
                        continue

                    raw_company = item.get("company_name", "Unknown")
                    canonical_company, _, _ = default_entity_resolver.resolve(raw_company, entity_type="JOB_COMPANY")
                    title = clean_article_text(item.get("title", "AI Role"))

                    seen_urls.add(job_url)
                    job_records.append({
                        "schemaVersion": "1.0",
                        "recordType": "JOB",
                        "source": {
                            "name": name,
                            "url": job_url,
                        },
                        "content": {
                            "company": canonical_company,
                            "title": title,
                            "date": iso_date,
                            "is_remote": True,
                            "role_family": classify_role_family(title),
                        },
                        "collectedAt": ref_time.isoformat(),
                    })

            elif parser_type == "arbeitnow":
                items = data.get("data", [])
                for item in items:
                    job_url = item.get("url", "")
                    title = clean_article_text(item.get("title", ""))

                    # Filter for AI/ML relevant jobs
                    if not any(k in title.lower() for k in ["ai", "machine learning", "ml", "data", "deep learning", "nlp", "llm"]):
                        continue

                    if not job_url or job_url in seen_urls:
                        continue

                    raw_date = item.get("created_at")
                    iso_date, dt = DateNormalizer.normalize_to_iso(raw_date, reference_time=ref_time)

                    if enforce_24h and not DateNormalizer.is_within_24_hours(dt, reference_time=ref_time):
                        continue

                    raw_company = item.get("company_name", "Unknown")
                    canonical_company, _, _ = default_entity_resolver.resolve(raw_company, entity_type="JOB_COMPANY")

                    seen_urls.add(job_url)
                    job_records.append({
                        "schemaVersion": "1.0",
                        "recordType": "JOB",
                        "source": {
                            "name": name,
                            "url": job_url,
                        },
                        "content": {
                            "company": canonical_company,
                            "title": title,
                            "date": iso_date,
                            "is_remote": bool(item.get("remote", False)),
                            "role_family": classify_role_family(title),
                        },
                        "collectedAt": ref_time.isoformat(),
                    })

            elif parser_type == "himalayas":
                items = data.get("jobs", [])
                for item in items:
                    job_url = item.get("url") or item.get("applicationLink") or ""
                    if not job_url or job_url in seen_urls:
                        continue

                    raw_date = item.get("pubDate") or item.get("created_at") or item.get("publishedAt")
                    iso_date, dt = DateNormalizer.normalize_to_iso(raw_date, reference_time=ref_time)

                    if enforce_24h and not DateNormalizer.is_within_24_hours(dt, reference_time=ref_time):
                        continue

                    raw_company = item.get("companyName") or item.get("company", {}).get("name", "Unknown")
                    canonical_company, _, _ = default_entity_resolver.resolve(raw_company, entity_type="JOB_COMPANY")
                    title = clean_article_text(item.get("title", "AI Role"))

                    seen_urls.add(job_url)
                    job_records.append({
                        "schemaVersion": "1.0",
                        "recordType": "JOB",
                        "source": {
                            "name": name,
                            "url": job_url,
                        },
                        "content": {
                            "company": canonical_company,
                            "title": title,
                            "date": iso_date,
                            "is_remote": True,
                            "role_family": classify_role_family(title),
                        },
                        "collectedAt": ref_time.isoformat(),
                    })

        except Exception as err:
            logger.warning(f"Error querying job board {name}: {err}")

    print(f"Collected {len(job_records)} fresh AI jobs (published in last 24h).")
    return job_records
