from __future__ import annotations

import pandas as pd

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Measure corruption impact, repair from raw source, and compare all states."""
    settings = load_settings()
    required = [settings.paths.clean_json, settings.paths.raw_records_json, settings.paths.baseline_metrics, settings.paths.eval_testset]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise RuntimeError("Run the baseline pipeline first; missing artifacts: " + ", ".join(missing))
    baseline_metrics = read_json(settings.paths.baseline_metrics)
    baseline_df = pd.DataFrame(read_json(settings.paths.clean_json))

    corrupted_df = corrupt_clean_dataframe(baseline_df, settings.paths.corruption_log)
    write_csv(corrupted_df, settings.paths.corrupted_clean_csv)
    write_json(settings.paths.corrupted_clean_json, corrupted_df.to_dict(orient="records"))
    corrupted_index = LocalEmbeddingIndex.build(corrupted_df, settings=settings, embeddings_output_path=settings.paths.corrupted_embeddings_json)
    corrupted_evaluation = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    corrupted_quality = run_data_quality_checks(corrupted_df, settings=settings, report_name="corrupted_quality")
    corrupted_freshness = build_freshness_report(
        corrupted_df, settings=settings, report_path=settings.paths.quality_dir / "freshness_corrupted.json"
    )

    raw_records = load_raw_records(settings.paths.raw_records_json)
    repaired_df = build_clean_dataframe(raw_records, run_date=now_utc())
    write_csv(repaired_df, settings.paths.repaired_clean_csv)
    write_json(settings.paths.repaired_clean_json, repaired_df.to_dict(orient="records"))
    repaired_index = LocalEmbeddingIndex.build(repaired_df, settings=settings, embeddings_output_path=settings.paths.repaired_embeddings_json)
    repaired_evaluation = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    repaired_quality = run_data_quality_checks(repaired_df, settings=settings, report_name="repaired_quality")
    repaired_freshness = build_freshness_report(
        repaired_df, settings=settings, report_path=settings.paths.quality_dir / "freshness_repaired.json"
    )
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_evaluation.summary,
        repaired_metrics=repaired_evaluation.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )
    print(f"Corruption/repair flow completed. Comparison: {settings.paths.comparison_report}")
