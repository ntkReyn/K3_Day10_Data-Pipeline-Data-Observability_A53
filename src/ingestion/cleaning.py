from __future__ import annotations

from datetime import datetime

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Normalize raw papers into the single schema used by retrieval and evaluation."""
    rows: list[dict] = []
    for record in records:
        paper_id = normalize_whitespace(record.paper_id).lower()
        title = normalize_whitespace(record.title)
        summary = normalize_whitespace(record.summary)
        authors = [normalize_whitespace(value) for value in record.authors if normalize_whitespace(value)]
        categories = [normalize_whitespace(value) for value in record.categories if normalize_whitespace(value)]
        published = pd.to_datetime(record.published, errors="coerce", utc=True)
        updated = pd.to_datetime(record.updated, errors="coerce", utc=True)
        if not paper_id or not title or len(summary) < 30 or pd.isna(published):
            continue
        authors_joined = compact_join(authors) or "Unknown authors"
        categories_joined = compact_join(categories) or "Uncategorized"
        age_days = max(0, int((pd.Timestamp(run_date).tz_convert("UTC") - published).total_seconds() // 86400))
        text_for_embedding = "\n".join(
            [f"Title: {title}", f"Abstract: {summary}", f"Authors: {authors_joined}", f"Categories: {categories_joined}"]
        )
        rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": normalize_whitespace(record.primary_category) or (categories[0] if categories else ""),
                "published": published.date().isoformat(),
                "updated": "" if pd.isna(updated) else updated.date().isoformat(),
                "abs_url": normalize_whitespace(record.abs_url),
                "pdf_url": normalize_whitespace(record.pdf_url),
                "comment": normalize_whitespace(record.comment),
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": len(summary),
                "age_days": age_days,
                "text_for_embedding": text_for_embedding,
            }
        )
    columns = [
        "paper_id", "title", "summary", "authors", "categories", "primary_category", "published", "updated", "abs_url", "pdf_url", "comment",
        "authors_joined", "categories_joined", "summary_chars", "age_days", "text_for_embedding",
    ]
    df = pd.DataFrame(rows, columns=columns)
    if df.empty:
        return df
    return df.drop_duplicates(subset=["paper_id"], keep="first").sort_values(["published", "paper_id"], ascending=[False, True]).reset_index(drop=True)
