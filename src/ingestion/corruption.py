from __future__ import annotations

import pandas as pd

from core.utils import write_json


def _embedding_text(row: pd.Series) -> str:
    return "\n".join(
        [
            f"Title: {row['title']}",
            f"Abstract: {row['summary']}",
            f"Authors: {row['authors_joined']}",
            f"Categories: {row['categories_joined']}",
        ]
    )


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Create deterministic, auditable quality failures from a clean dataset."""
    if df.empty:
        raise ValueError("Cannot corrupt an empty clean dataset.")
    corrupted = df.copy().reset_index(drop=True)
    log: dict[str, object] = {"input_rows": len(corrupted), "scenarios": []}

    drop_count = min(max(1, len(corrupted) // 4), 6)
    dropped_ids = corrupted.head(drop_count)["paper_id"].tolist()
    corrupted = corrupted.iloc[drop_count:].copy().reset_index(drop=True)
    log["scenarios"].append({"type": "drop_latest_records", "paper_ids": dropped_ids})

    if not corrupted.empty:
        blank_idx = corrupted.index[: min(2, len(corrupted))].tolist()
        blank_ids = corrupted.loc[blank_idx, "paper_id"].tolist()
        corrupted.loc[blank_idx, "summary"] = ""
        corrupted.loc[blank_idx, "summary_chars"] = 0
        log["scenarios"].append({"type": "blank_summary", "paper_ids": blank_ids})

    if len(corrupted) >= 3:
        noise_idx = corrupted.index[2]
        corrupted.loc[noise_idx, "summary"] = str(corrupted.loc[noise_idx, "summary"]) + " ### NOISE_TOKEN_123 ### " * 8
        corrupted.loc[noise_idx, "summary_chars"] = len(corrupted.loc[noise_idx, "summary"])
        log["scenarios"].append({"type": "inject_summary_noise", "paper_ids": [corrupted.loc[noise_idx, "paper_id"]]})
    if len(corrupted) >= 4:
        title_idx = corrupted.index[3]
        corrupted.loc[title_idx, "title"] = str(corrupted.loc[title_idx, "title"])[:24]
        log["scenarios"].append({"type": "truncate_title", "paper_ids": [corrupted.loc[title_idx, "paper_id"]]})
    if len(corrupted) >= 5:
        stale_idx = corrupted.index[4]
        corrupted.loc[stale_idx, "published"] = "2000-01-01"
        corrupted.loc[stale_idx, "age_days"] = 9999
        log["scenarios"].append({"type": "stale_publication_date", "paper_ids": [corrupted.loc[stale_idx, "paper_id"]]})
    if not corrupted.empty:
        duplicate = corrupted.tail(1).copy()
        corrupted = pd.concat([corrupted, duplicate], ignore_index=True)
        log["scenarios"].append({"type": "duplicate_row", "paper_ids": duplicate["paper_id"].tolist()})

    corrupted["text_for_embedding"] = corrupted.apply(_embedding_text, axis=1)
    log["output_rows"] = len(corrupted)
    write_json(output_log_path, log)
    return corrupted
