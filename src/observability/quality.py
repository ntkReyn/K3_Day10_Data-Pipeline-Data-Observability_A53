from __future__ import annotations

from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import now_utc, write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run compact, serializable quality checks and persist their evidence."""
    required = {"paper_id", "title", "summary", "text_for_embedding", "age_days"}
    missing = sorted(required - set(df.columns))
    row_count = len(df)
    null_paper_ids = int(df["paper_id"].isna().sum()) if "paper_id" in df else row_count
    blank_paper_ids = int(df["paper_id"].fillna("").astype(str).str.strip().eq("").sum()) if "paper_id" in df else row_count
    duplicate_paper_ids = int(df["paper_id"].duplicated().sum()) if "paper_id" in df else row_count
    blank_titles = int(df["title"].fillna("").astype(str).str.strip().eq("").sum()) if "title" in df else row_count
    short_summaries = int(df["summary"].fillna("").astype(str).str.len().lt(30).sum()) if "summary" in df else row_count
    blank_embedding_text = int(df["text_for_embedding"].fillna("").astype(str).str.strip().eq("").sum()) if "text_for_embedding" in df else row_count
    invalid_age = int((pd.to_numeric(df["age_days"], errors="coerce") < 0).sum()) if "age_days" in df else row_count
    stale_rows = int((pd.to_numeric(df["age_days"], errors="coerce") > settings.freshness_threshold_days).sum()) if "age_days" in df else row_count
    checks = [
        {"name": "row_count", "passed": row_count > 0, "observed": row_count, "expected": "> 0"},
        {"name": "paper_id_not_null", "passed": null_paper_ids + blank_paper_ids == 0, "observed": null_paper_ids + blank_paper_ids, "expected": 0},
        {"name": "paper_id_unique", "passed": duplicate_paper_ids == 0, "observed": duplicate_paper_ids, "expected": 0},
        {"name": "title_not_blank", "passed": blank_titles == 0, "observed": blank_titles, "expected": 0},
        {"name": "summary_min_length", "passed": short_summaries == 0, "observed": short_summaries, "expected": 0},
        {"name": "embedding_text_not_blank", "passed": blank_embedding_text == 0, "observed": blank_embedding_text, "expected": 0},
        {"name": "age_days_valid", "passed": invalid_age == 0, "observed": invalid_age, "expected": 0},
        {"name": "freshness_threshold", "passed": stale_rows == 0, "observed": stale_rows, "expected": 0},
    ]
    report = {
        "report_name": report_name,
        "generated_at": now_utc().isoformat(),
        "rows": row_count,
        "missing_columns": missing,
        "checks": checks,
        "passed": not missing and all(check["passed"] for check in checks),
    }
    write_json(settings.paths.quality_dir / f"{report_name}.json", report)
    return report


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Summarize publication-age signals separately from other quality checks."""
    published = pd.to_datetime(df.get("published", pd.Series(dtype="object")), errors="coerce", utc=True)
    ages = pd.to_numeric(df.get("age_days", pd.Series(dtype="float")), errors="coerce")
    total_rows = len(df)
    stale_rows = int((ages > settings.freshness_threshold_days).sum())
    report = {
        "generated_at": now_utc().isoformat(),
        "threshold_days": settings.freshness_threshold_days,
        "latest_published": None if published.dropna().empty else published.max().date().isoformat(),
        "oldest_published": None if published.dropna().empty else published.min().date().isoformat(),
        "stale_rows": stale_rows,
        "invalid_published_rows": int(published.isna().sum()),
        "total_rows": total_rows,
        "is_fresh": total_rows > 0 and stale_rows == 0 and int(published.isna().sum()) == 0,
    }
    write_json(report_path, report)
    return report
