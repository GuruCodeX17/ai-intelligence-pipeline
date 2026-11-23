
import json

from src.collectors.product_collector import (
    collect_products,
    save_products,
    clean_description,
)


def test_collect_products(monkeypatch):

    class FakeResponse:
        status_code = 200
        content = b"<rss></rss>"

        def raise_for_status(self):
            pass

    class FakeFeed:
        bozo = False
        entries = [
            {
                "title": "AI Assistant",
                "summary": "<p>AI productivity tool</p>",
                "link": "https://example.com/ai",
                "published": "2026-11-23",
                "updated": "2026-11-23",
            }
        ]

    monkeypatch.setattr(
        "src.collectors.product_collector.requests.get",
        lambda *args, **kwargs: FakeResponse(),
    )

    monkeypatch.setattr(
        "src.collectors.product_collector.feedparser.parse",
        lambda content: FakeFeed(),
    )

    results = collect_products(max_results=5)

    assert len(results) == 1
    assert results[0]["product_name"] == "AI Assistant"
    assert results[0]["description"] == "AI productivity tool"
    assert results[0]["source"] == "Product Hunt"


def test_clean_product_description():

    html = "<p>AI-powered research assistant</p>"

    result = clean_description(html)

    assert result == "AI-powered research assistant"


def test_product_max_results(monkeypatch):

    class FakeResponse:
        status_code = 200
        content = b"<rss></rss>"

        def raise_for_status(self):
            pass

    class FakeFeed:
        bozo = False
        entries = [
            {"title": "Product One"},
            {"title": "Product Two"},
            {"title": "Product Three"},
        ]

    monkeypatch.setattr(
        "src.collectors.product_collector.requests.get",
        lambda *args, **kwargs: FakeResponse(),
    )

    monkeypatch.setattr(
        "src.collectors.product_collector.feedparser.parse",
        lambda content: FakeFeed(),
    )

    results = collect_products(max_results=2)

    assert len(results) == 2


def test_product_api_failure(monkeypatch):

    class FakeResponse:
        status_code = 429

    monkeypatch.setattr(
        "src.collectors.product_collector.requests.get",
        lambda *args, **kwargs: FakeResponse(),
    )

    results = collect_products()

    assert results == []


def test_save_products(tmp_path, monkeypatch):

    import src.collectors.product_collector as collector

    monkeypatch.setattr(
        "src.collectors.product_collector.Path.resolve",
        lambda self: tmp_path / "src" / "collectors" / "product_collector.py",
    )

    products = [
        {
            "product_name": "AI Assistant",
            "description": "AI productivity tool",
        }
    ]

    save_products(products)

    output_file = tmp_path / "data" / "raw" / "ai_products.json"

    assert output_file.exists()

    saved_data = json.loads(
        output_file.read_text(encoding="utf-8")
    )

    assert saved_data == products
