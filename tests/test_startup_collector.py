
import requests

from src.collectors.startup_collector import (
    collect_startups,
    save_startups,
)


def test_collect_startups(monkeypatch):

    class FakeResponse:
        status_code = 200
        def raise_for_status(self):
            pass

        def json(self):
            return [
                {
                    "name": "Test AI Startup",
                    "long_description": "An AI-powered software company.",
                    "one_liner": "AI solutions for businesses.",
                    "website": "https://example.com",
                    "url": "https://www.ycombinator.com/companies/test-ai",
                    "industry": "B2B",
                    "subindustry": "B2B -> Software",
                    "tags": ["AI", "Machine Learning"],
                    "all_locations": "San Francisco, USA",
                    "team_size": 10,
                    "batch": "Summer 2025",
                    "status": "Active",
                    "isHiring": True,
                    "launched_at": 1750000000,
                }
            ]

    def fake_get(*args, **kwargs):
        return FakeResponse()

    monkeypatch.setattr(
        "src.collectors.startup_collector.requests.get",
        fake_get,
    )

    results = collect_startups(max_results=1)

    assert len(results) == 1
    assert results[0]["startup_name"] == "Test AI Startup"
    assert results[0]["industry"] == "B2B"
    assert results[0]["source"] == "Y Combinator"


def test_filter_non_ai_startups(monkeypatch):

    class FakeResponse:
        status_code = 200
        def raise_for_status(self):
            pass

        def json(self):
            return [
                {
                    "name": "AI Startup",
                    "tags": ["AI", "Machine Learning"],
                },
                {
                    "name": "Normal Startup",
                    "tags": ["B2B", "SaaS"],
                },
            ]

    def fake_get(*args, **kwargs):
        return FakeResponse()

    monkeypatch.setattr(
        "src.collectors.startup_collector.requests.get",
        fake_get,
    )

    results = collect_startups(max_results=5)

    assert len(results) == 1
    assert results[0]["startup_name"] == "AI Startup"


def test_startup_max_results(monkeypatch):

    class FakeResponse:
        status_code = 200
        def raise_for_status(self):
            pass

        def json(self):
            return [
                {"name": "Startup One", "tags": ["AI"]},
                {"name": "Startup Two", "tags": ["AI"]},
                {"name": "Startup Three", "tags": ["AI"]},
            ]

    def fake_get(*args, **kwargs):
        return FakeResponse()

    monkeypatch.setattr(
        "src.collectors.startup_collector.requests.get",
        fake_get,
    )

    results = collect_startups(max_results=2)

    assert len(results) == 2


def test_startup_api_failure(monkeypatch):

    def fake_get(*args, **kwargs):
        raise requests.exceptions.ConnectionError("Connection failed")

    monkeypatch.setattr(
        "src.collectors.startup_collector.requests.get",
        fake_get,
    )

    results = collect_startups()

    assert results == []


def test_save_startups(tmp_path, monkeypatch):

    import src.collectors.startup_collector as startup_collector

    monkeypatch.setattr(
        startup_collector,
        "__file__",
        str(tmp_path / "src" / "collectors" / "startup_collector.py"),
    )

    startups = [
        {
            "startup_name": "Test AI Startup",
            "description": "An AI company.",
            "source": "Y Combinator",
        }
    ]

    save_startups(startups)

    output_file = tmp_path / "data" / "raw" / "ai_startups.json"

    assert output_file.exists()

    import json

    with output_file.open("r", encoding="utf-8") as file:
        saved_data = json.load(file)

    assert len(saved_data) == 1
    assert saved_data[0]["startup_name"] == "Test AI Startup"
