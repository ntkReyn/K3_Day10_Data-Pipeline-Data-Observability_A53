from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Build a deterministic factual test set from actual clean records."""
    required = {"paper_id", "title", "summary", "authors_joined", "categories_joined", "published"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Clean dataframe is missing test-set columns: {sorted(missing)}")
    if len(df) < 4:
        raise ValueError("At least four clean documents are required to create the evaluation set.")
    question_types = ["summary", "authors", "date", "categories"]
    selected = df.head(min(8, len(df))).reset_index(drop=True)
    samples: list[dict[str, Any]] = []
    for index, row in selected.iterrows():
        question_type = question_types[index % len(question_types)]
        title = str(row["title"])
        if question_type == "authors":
            question, answer = f"Who authored '{title}'?", str(row["authors_joined"])
        elif question_type == "date":
            question, answer = f"When was '{title}' published?", str(row["published"])
        elif question_type == "categories":
            question, answer = f"What categories does '{title}' have?", str(row["categories_joined"])
        else:
            question, answer = f"What is the main topic of '{title}'?", first_sentence(str(row["summary"]))
        samples.append(
            {
                "id": f"eval-{index + 1:02d}",
                "question_type": question_type,
                "question": question,
                "ground_truth": answer,
                "ground_truth_doc_ids": [str(row["paper_id"])],
            }
        )
    write_json(output_path, samples)
    return samples
