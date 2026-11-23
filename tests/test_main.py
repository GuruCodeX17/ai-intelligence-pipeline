
import main


def test_pipeline_success(monkeypatch):

    saved = {
        "papers": False,
        "repositories": False,
        "quality": False,
        "products": False,
        "startups": False,
        "validation": False,
    }

    monkeypatch.setattr(
        main,
        "collect_papers",
        lambda max_results: [{"title": "Test AI paper"}],
    )

    monkeypatch.setattr(
        main,
        "save_papers",
        lambda papers: saved.update(papers=True),
    )

    monkeypatch.setattr(
        main,
        "collect_repositories",
        lambda max_results: [
            {"repository_name": "test/ai-project"}
        ],
    )

    monkeypatch.setattr(
        main,
        "save_repositories",
        lambda repositories: saved.update(repositories=True),
    )

    monkeypatch.setattr(
        main,
        "process_github_data",
        lambda: saved.update(quality=True),
    )

    monkeypatch.setattr(
        main,
        "collect_products",
        lambda max_results: [{"product_name": "Test AI Product"}],
    )

    monkeypatch.setattr(
        main,
        "save_products",
        lambda products: saved.update(products=True),
    )

    monkeypatch.setattr(
        main,
        "collect_startups",
        lambda max_results: [{"startup_name": "Test AI Startup"}],
    )

    monkeypatch.setattr(
        main,
        "save_startups",
        lambda startups: saved.update(startups=True),
    )

    monkeypatch.setattr(
        main,
        "run_validation",
        lambda: saved.update(validation=True) or {},
    )

    main.run_pipeline()

    assert saved["papers"] is True
    assert saved["repositories"] is True
    assert saved["quality"] is True
    assert saved["products"] is True
    assert saved["startups"] is True
    assert saved["validation"] is True


def test_quality_skipped_when_no_github_data(monkeypatch):

    saved = {
        "quality": False,
        "validation": False,
    }

    monkeypatch.setattr(
        main,
        "collect_papers",
        lambda max_results: [],
    )

    monkeypatch.setattr(
        main,
        "collect_repositories",
        lambda max_results: [],
    )

    monkeypatch.setattr(
        main,
        "process_github_data",
        lambda: saved.update(quality=True),
    )

    monkeypatch.setattr(
        main,
        "collect_products",
        lambda max_results: [],
    )

    monkeypatch.setattr(
        main,
        "collect_startups",
        lambda max_results: [],
    )

    monkeypatch.setattr(
        main,
        "run_validation",
        lambda: saved.update(validation=True) or {},
    )

    main.run_pipeline()

    assert saved["quality"] is False
    assert saved["validation"] is True


def test_pipeline_continues_when_validation_fails(monkeypatch):

    monkeypatch.setattr(
        main,
        "collect_papers",
        lambda max_results: [],
    )

    monkeypatch.setattr(
        main,
        "collect_repositories",
        lambda max_results: [],
    )

    monkeypatch.setattr(
        main,
        "collect_products",
        lambda max_results: [],
    )

    monkeypatch.setattr(
        main,
        "collect_startups",
        lambda max_results: [],
    )

    monkeypatch.setattr(
        main,
        "run_validation",
        lambda: (_ for _ in ()).throw(
            RuntimeError("Validation test error")
        ),
    )

    # The pipeline should handle the error without crashing.
    main.run_pipeline()
