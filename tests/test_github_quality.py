
from src.processing.github_quality import classify_repository


def test_relevant_repository():
    repository = {
        "repository_name": "ai-project",
        "description": "Machine learning project using Python",
        "topics": ["machine-learning"],
    }

    assert classify_repository(repository) == "relevant"


def test_profile_repository():
    repository = {
        "repository_name": "user/profile",
        "description": "My developer profile",
        "topics": ["github-profile", "portfolio"],
    }

    assert classify_repository(repository) == "not_relevant"


def test_missing_metadata():
    repository = {
        "repository_name": "unknown-project",
        "description": "",
        "topics": [],
    }

    assert classify_repository(repository) == "needs_review"


def test_irrelevant_repository():
    repository = {
        "repository_name": "weather-website",
        "description": "A simple weather website",
        "topics": ["html", "css"],
    }

    assert classify_repository(repository) == "not_relevant"

def test_hyphenated_ai_keyword():
    repository = {
        "repository_name": "ml-project",
        "description": "AI research project",
        "topics": ["machine-learning"],
    }

    assert classify_repository(repository) == "relevant"


def test_genai_repository():
    repository = {
        "repository_name": "rag-assistant",
        "description": "Retrieval augmented generation application",
        "topics": ["llm", "rag"],
    }

    assert classify_repository(repository) == "relevant"


def test_agentic_ai_repository():
    repository = {
        "repository_name": "agent-project",
        "description": "Agentic AI application using LangGraph",
        "topics": ["agentic-ai", "langgraph"],
    }

    assert classify_repository(repository) == "relevant"

