
from src.collectors.github_collector import collect_repositories


def test_collect_repositories(monkeypatch):

    class FakeResponse:
        status_code = 200
        headers = {}

        def raise_for_status(self):
            pass

        def json(self):
            return {
                "items": [
                    {
                        "full_name": "testuser/ai-project",
                        "description": "Machine learning project",
                        "html_url": "https://github.com/testuser/ai-project",
                        "stargazers_count": 10,
                        "forks_count": 2,
                        "language": "Python",
                        "created_at": "2026-01-01T00:00:00Z",
                        "updated_at": "2026-02-01T00:00:00Z",
                        "topics": ["machine-learning"],
                        "license": {"name": "MIT"},
                    }
                ]
            }

    def fake_get(*args, **kwargs):
        return FakeResponse()

    monkeypatch.setattr(
        "src.collectors.github_collector.requests.get",
        fake_get
    )

    results = collect_repositories(max_results=1)

    assert len(results) == 1
    assert results[0]["repository_name"] == "testuser/ai-project"
    assert results[0]["stars"] == 10
    assert results[0]["language"] == "Python"
    assert results[0]["source"] == "GitHub"


def test_github_rate_limit(monkeypatch):

    class FakeResponse:
        status_code = 403
        headers = {"X-RateLimit-Remaining": "0"}

    def fake_get(*args, **kwargs):
        return FakeResponse()

    monkeypatch.setattr(
        "src.collectors.github_collector.requests.get",
        fake_get
    )

    results = collect_repositories()

    assert results == []
