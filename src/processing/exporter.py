"""
Submission Data Exporter
Exports pipeline datasets across 6 canonical sheets / CSV files:
1. Startups (Min. 1,000 rows)
2. Products (Min. 1,000 rows)
3. Research Papers (Min. 1,000 rows, including GitHub stars)
4. Jobs (All 24-hr fresh jobs found)
5. News (All 24-hr fresh news found)
6. Entity Mapping Log (Raw vs Canonical names)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd


import re
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXPORTS_DIR = PROJECT_ROOT / "exports"


def ensure_export_dir() -> Path:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return EXPORTS_DIR


def sanitize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Sanitize all dataframe values to strip illegal Excel XML control characters."""
    def _clean_val(v):
        if isinstance(v, str):
            return re.sub(ILLEGAL_CHARACTERS_RE, "", v)
        return v
    return df.map(_clean_val)


def format_startups(startups: List[Dict[str, Any]]) -> pd.DataFrame:
    """Format startup records according to the canonical Startup Entity schema."""
    rows = []
    for item in startups:
        source_obj = item.get("source_details") or (
            item["source"] if isinstance(item.get("source"), dict) else {"name": str(item.get("source", "Y Combinator")), "url": item.get("startup_url", "")}
        )
        content_obj = item.get("content", {})
        data_obj = content_obj.get("data", {})

        entity_name = content_obj.get("entityName") or item.get("canonical_name") or item.get("startup_name", "")
        emp_count = data_obj.get("employeeCount") or item.get("team_size")

        rows.append({
            "schemaVersion": item.get("schemaVersion", "1.0"),
            "recordType": "STARTUP",
            "source.name": source_obj.get("name", "Y Combinator"),
            "source.url": source_obj.get("url", item.get("startup_url", "")),
            "content.entityName": entity_name,
            "content.data.employeeCount": emp_count if emp_count is not None else "",
            "collectedAt": item.get("collectedAt", ""),
            "industry": item.get("industry") or data_obj.get("industry", ""),
            "location": item.get("location") or data_obj.get("location", ""),
            "website": item.get("website") or data_obj.get("website", ""),
            "one_liner": item.get("one_liner") or data_obj.get("one_liner", ""),
        })

    return pd.DataFrame(rows)


def format_products(products: List[Dict[str, Any]]) -> pd.DataFrame:
    """Format product records according to the canonical Product Entity schema."""
    rows = []
    for item in products:
        source_obj = item.get("source_details") or (
            item["source"] if isinstance(item.get("source"), dict) else {"name": "Product Hunt", "url": item.get("product_url", "")}
        )
        content_obj = item.get("content", {})

        rows.append({
            "schemaVersion": item.get("schemaVersion", "1.0"),
            "recordType": "PRODUCT",
            "source.name": source_obj.get("name", "Product Hunt"),
            "source.url": source_obj.get("url", item.get("product_url", "")),
            "content.productName": content_obj.get("productName") or item.get("product_name", ""),
            "content.startupName": content_obj.get("startupName") or item.get("canonical_startup", ""),
            "content.pricingModel": content_obj.get("pricingModel", "FREEMIUM"),
            "content.description": content_obj.get("description") or item.get("description", ""),
            "collectedAt": item.get("collectedAt", ""),
        })

    return pd.DataFrame(rows)


def format_research_papers(papers: List[Dict[str, Any]]) -> pd.DataFrame:
    """Format research paper records according to the canonical Research Paper Entity schema."""
    rows = []
    for item in papers:
        content_obj = item.get("content", {})
        authors = content_obj.get("authors") or item.get("authors", [])
        if isinstance(authors, list):
            authors_str = ", ".join(authors)
        else:
            authors_str = str(authors)

        rows.append({
            "schemaVersion": item.get("schemaVersion", "1.0"),
            "recordType": "RESEARCH_PAPER",
            "content.title": content_obj.get("title") or item.get("title", ""),
            "content.authors": authors_str,
            "content.paper_url": content_obj.get("paper_url") or item.get("paper_url", ""),
            "content.github_url": content_obj.get("github_url") or item.get("github_url", ""),
            "content.github_stars": content_obj.get("github_stars", item.get("github_stars", 0)),
            "content.published_date": content_obj.get("published_date") or item.get("published", ""),
        })

    return pd.DataFrame(rows)


def format_jobs(jobs: List[Dict[str, Any]]) -> pd.DataFrame:
    """Format job records according to the canonical Job Entity schema."""
    rows = []
    for item in jobs:
        source_obj = item.get("source", {})
        content_obj = item.get("content", {})

        rows.append({
            "schemaVersion": item.get("schemaVersion", "1.0"),
            "recordType": "JOB",
            "source.name": source_obj.get("name", ""),
            "source.url": source_obj.get("url", ""),
            "content.company": content_obj.get("company", ""),
            "content.title": content_obj.get("title", ""),
            "content.date": content_obj.get("date", ""),
            "content.is_remote": content_obj.get("is_remote", True),
            "content.role_family": content_obj.get("role_family", "Engineering"),
            "collectedAt": item.get("collectedAt", ""),
        })

    return pd.DataFrame(rows)


def format_news(news: List[Dict[str, Any]]) -> pd.DataFrame:
    """Format news records according to the canonical News Entity schema."""
    rows = []
    for item in news:
        source_obj = item.get("source", {})
        content_obj = item.get("content", {})

        rows.append({
            "schemaVersion": item.get("schemaVersion", "1.0"),
            "recordType": "NEWS",
            "source.name": source_obj.get("name", ""),
            "source.url": source_obj.get("url", ""),
            "content.title": content_obj.get("title", ""),
            "content.published_date": content_obj.get("published_date", ""),
            "content.summary": content_obj.get("summary", ""),
            "content.full_text": content_obj.get("full_text", ""),
            "collectedAt": item.get("collectedAt", ""),
        })

    return pd.DataFrame(rows)


def format_mapping_log(log: List[Dict[str, Any]]) -> pd.DataFrame:
    """Format entity mapping log records."""
    if not log:
        return pd.DataFrame(columns=[
            "raw_name", "canonical_name", "entity_type", "resolution_method",
            "confidence_score", "is_seed_match", "matched_seed_id", "resolved_at"
        ])
    return pd.DataFrame(log)


def export_submission_datasets(
    startups: List[Dict[str, Any]],
    products: List[Dict[str, Any]],
    papers: List[Dict[str, Any]],
    jobs: List[Dict[str, Any]],
    news: List[Dict[str, Any]],
    mapping_log: List[Dict[str, Any]],
) -> Dict[str, str]:
    """
    Export all 6 tabs to a single multi-sheet Excel file and individual CSVs.
    Returns dictionary of generated file paths.
    """
    out_dir = ensure_export_dir()
    excel_path = out_dir / "GraphOne_AI_Intelligence_Pipeline_Submission.xlsx"

    df_startups = sanitize_dataframe(format_startups(startups))
    df_products = sanitize_dataframe(format_products(products))
    df_papers = sanitize_dataframe(format_research_papers(papers))
    df_jobs = sanitize_dataframe(format_jobs(jobs))
    df_news = sanitize_dataframe(format_news(news))
    df_mapping = sanitize_dataframe(format_mapping_log(mapping_log))

    print("\n" + "=" * 60)
    print("        EXPORTING PIPELINE SUBMISSION DATASETS")
    print("=" * 60)
    print(f"Tab 1: Startups          : {len(df_startups):>5} rows (Min. 1,000 required)")
    print(f"Tab 2: Products          : {len(df_products):>5} rows (Min. 1,000 required)")
    print(f"Tab 3: Research Papers   : {len(df_papers):>5} rows (Min. 1,000 required)")
    print(f"Tab 4: Jobs (24-hr fresh): {len(df_jobs):>5} rows")
    print(f"Tab 5: News (24-hr fresh): {len(df_news):>5} rows")
    print(f"Tab 6: Entity Mapping Log: {len(df_mapping):>5} rows")

    # Write multi-sheet Excel workbook
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        df_startups.to_excel(writer, sheet_name="Startups", index=False)
        df_products.to_excel(writer, sheet_name="Products", index=False)
        df_papers.to_excel(writer, sheet_name="Research Papers", index=False)
        df_jobs.to_excel(writer, sheet_name="Jobs", index=False)
        df_news.to_excel(writer, sheet_name="News", index=False)
        df_mapping.to_excel(writer, sheet_name="Entity Mapping Log", index=False)

    print(f"\n[OK] Excel workbook generated: {excel_path}")

    # Also export individual CSV files for quick inspection / direct upload
    csv_files = {
        "startups": str(out_dir / "1_startups.csv"),
        "products": str(out_dir / "2_products.csv"),
        "research_papers": str(out_dir / "3_research_papers.csv"),
        "jobs": str(out_dir / "4_jobs.csv"),
        "news": str(out_dir / "5_news.csv"),
        "mapping_log": str(out_dir / "6_entity_mapping_log.csv"),
        "excel": str(excel_path),
    }

    df_startups.to_csv(csv_files["startups"], index=False, encoding="utf-8")
    df_products.to_csv(csv_files["products"], index=False, encoding="utf-8")
    df_papers.to_csv(csv_files["research_papers"], index=False, encoding="utf-8")
    df_jobs.to_csv(csv_files["jobs"], index=False, encoding="utf-8")
    df_news.to_csv(csv_files["news"], index=False, encoding="utf-8")
    df_mapping.to_csv(csv_files["mapping_log"], index=False, encoding="utf-8")

    print("[OK] Individual CSV files generated in exports/ folder.")
    print("=" * 60)

    return csv_files
