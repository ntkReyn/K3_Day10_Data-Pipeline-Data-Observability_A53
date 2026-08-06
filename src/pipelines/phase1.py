from __future__ import annotations

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex
from retrieval.qa import answer_question


def main() -> None:
    """Run the clean-data baseline from source snapshot through evidence report."""
    settings = load_settings()
    if settings.paths.raw_records_json.exists() and not settings.refresh_source:
        records = load_raw_records(settings.paths.raw_records_json)
        source_mode = "cached raw snapshot"
    else:
        records = fetch_source_records(settings)
        source_mode = "Crossref REST API"
    if not records:
        raise RuntimeError("No valid Crossref records were available after parsing.")

    clean_df = build_clean_dataframe(records, run_date=now_utc())
    if clean_df.empty:
        raise RuntimeError("Cleaning removed every source record; cannot build a baseline.")
    write_csv(clean_df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, clean_df.to_dict(orient="records"))

    index = LocalEmbeddingIndex.build(clean_df, settings=settings, embeddings_output_path=settings.paths.embeddings_json)
    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        build_test_set(clean_df, settings.paths.eval_testset)
    evaluation = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    quality = run_data_quality_checks(clean_df, settings=settings, report_name="baseline_quality")
    freshness = build_freshness_report(clean_df, settings=settings, report_path=settings.paths.freshness_report)
    test_set = read_json(settings.paths.eval_testset)
    demo = [answer_question(item["question"], settings=settings, index=index).__dict__ for item in test_set[:3]]
    write_json(settings.paths.demo_answers, demo)
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary={
            "source": settings.source_api,
            "mode": source_mode,
            "query": settings.source_query,
            "filter": settings.source_filter,
            "raw_records": len(records),
            "clean_records": len(clean_df),
        },
        metrics=evaluation.summary,
        quality=quality,
        freshness=freshness,
    )
    print(f"Baseline completed with {len(clean_df)} clean records. Metrics: {settings.paths.baseline_metrics}")
