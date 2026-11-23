
from src.collectors.research_collector import (
    clean_text,
    collect_from_crossref,
)


def test_clean_text():
    result = clean_text("<p>Machine   Learning</p>")

    assert result == "Machine Learning"


def test_crossref_filters_irrelevant_records(monkeypatch):

    class MockResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "message": {
                    "items": [
                        {
                            "title": ["Machine Learning Applications"],
                            "DOI": "10.1234/example",
                            "author": [
                                {
                                    "given": "John",
                                    "family": "Smith",
                                }
                            ],
                            "abstract": "<p>AI research paper</p>",
                            "published": {
                                "date-parts": [[2024, 5, 10]]
                            },
                            "URL": "https://doi.org/10.1234/example",
                            "subject": ["Computer Science"],
                        },
                        {
                            "title": ["History of Ancient Literature"],
                            "DOI": "10.1234/irrelevant",
                            "author": [],
                            "published": {
                                "date-parts": [[2020]]
                            },
                        },
                    ]
                }
            }

    def mock_get(*args, **kwargs):
        return MockResponse()

    monkeypatch.setattr(
        "src.collectors.research_collector.requests.get",
        mock_get,
    )

    papers = collect_from_crossref(max_results=5)

    assert len(papers) == 1
    assert papers[0]["title"] == "Machine Learning Applications"
    assert papers[0]["doi"] == "10.1234/example"
    assert papers[0]["source"] == "Crossref"
    assert papers[0]["published"] == "2024-5-10"
