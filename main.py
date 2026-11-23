
from src.collectors.research_collector import (
    collect_papers,
    save_papers,
)

from src.collectors.github_collector import (
    collect_repositories,
    save_repositories,
)

from src.collectors.product_collector import (
    collect_products,
    save_products,
)

from src.collectors.startup_collector import (
    collect_startups,
    save_startups,
)

from src.processing.github_quality import process_github_data
from src.processing.data_validator import run_validation


def run_pipeline():

    print("=" * 55)
    print("       AI INTELLIGENCE DATA PIPELINE")
    print("=" * 55)

    research_count = 0
    github_count = 0
    product_count = 0
    startup_count = 0

    quality_status = "Skipped"
    validation_status = "Skipped"

    # STEP 1: Collect research papers
    print("\n[STEP 1] Research Paper Collection")

    try:
        papers = collect_papers(max_results=5)

        if papers:
            save_papers(papers)
            research_count = len(papers)
        else:
            print("No new research papers collected.")

    except Exception as error:
        print(f"Research collection failed: {error}")

    # STEP 2: Collect GitHub repositories
    print("\n[STEP 2] GitHub Repository Collection")

    try:
        repositories = collect_repositories(max_results=5)

        if repositories:
            save_repositories(repositories)
            github_count = len(repositories)
        else:
            print("No new GitHub repositories collected.")

    except Exception as error:
        print(f"GitHub collection failed: {error}")

    # STEP 3: Process GitHub data
    print("\n[STEP 3] GitHub Data Quality Processing")

    if github_count > 0:
        try:
            process_github_data()
            quality_status = "Completed"

        except Exception as error:
            quality_status = "Failed"
            print(f"Quality processing failed: {error}")

    else:
        print("Skipped because no new GitHub data was collected.")

    # STEP 4: Collect AI products
    print("\n[STEP 4] AI Product Collection")

    try:
        products = collect_products(max_results=5)

        if products:
            save_products(products)
            product_count = len(products)
        else:
            print("No new AI products collected.")

    except Exception as error:
        print(f"Product collection failed: {error}")

    # STEP 5: Collect AI startups
    print("\n[STEP 5] AI Startup Collection")

    try:
        startups = collect_startups(max_results=5)

        if startups:
            save_startups(startups)
            startup_count = len(startups)
        else:
            print("No new AI startups collected.")

    except Exception as error:
        print(f"Startup collection failed: {error}")

    # STEP 6: Data validation
    print("\n[STEP 6] Data Validation and Quality Checks")

    try:
        validation_report = run_validation()

        if validation_report is not None:
            validation_status = "Completed"
        else:
            validation_status = "Failed"

    except Exception as error:
        validation_status = "Failed"
        print(f"Data validation failed: {error}")

    # STEP 7: Final summary
    print("\n" + "=" * 55)
    print("             PIPELINE SUMMARY")
    print("=" * 55)

    print(f"Research papers collected  : {research_count}")
    print(f"GitHub repositories        : {github_count}")
    print(f"GitHub quality processing  : {quality_status}")
    print(f"AI products collected      : {product_count}")
    print(f"AI startups collected      : {startup_count}")
    print(f"Data validation            : {validation_status}")

    print("\nPipeline execution finished.")
    print("=" * 55)


if __name__ == "__main__":
    run_pipeline()
