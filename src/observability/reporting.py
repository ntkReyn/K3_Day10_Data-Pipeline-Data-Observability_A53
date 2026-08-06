from __future__ import annotations

from typing import Any

from core.utils import write_text


def _metric_rows(metrics: dict[str, Any]) -> str:
    names = ["samples", "retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"]
    return "\n".join(f"| `{name}` | {metrics.get(name, 'N/A')} |" for name in names)


def _check_rows(quality: dict[str, Any]) -> str:
    return "\n".join(
        f"| {item['name']} | {'PASS' if item['passed'] else 'FAIL'} | {item['observed']} | {item['expected']} |"
        for item in quality.get("checks", [])
    )


def _ragas_rows(metrics: dict[str, Any]) -> str:
    ragas = metrics.get("ragas", {})
    summary = ragas.get("summary", {}) if isinstance(ragas, dict) else {}
    if not summary:
        return "| Not run | N/A |"
    return "\n".join(f"| `{name}` | {value} |" for name, value in summary.items())


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write the evidence-backed baseline report."""
    text = f"""# Phase 1 — Baseline Report

## Source summary

| Field | Value |
| --- | --- |
| Source | {source_summary.get('source', 'Crossref')} |
| Query | {source_summary.get('query', '')} |
| Filter | {source_summary.get('filter', '')} |
| Raw records | {source_summary.get('raw_records', 0)} |
| Clean records | {source_summary.get('clean_records', 0)} |

## Evaluation metrics

| Metric | Value |
| --- | ---: |
{_metric_rows(metrics)}

## Data quality

Overall status: **{'PASS' if quality.get('passed') else 'FAIL'}**

| Check | Status | Observed | Expected |
| --- | --- | ---: | --- |
{_check_rows(quality)}

## Ragas

| Metric | Value |
| --- | ---: |
{_ragas_rows(metrics)}

## Freshness

| Signal | Value |
| --- | --- |
| Latest published | {freshness.get('latest_published')} |
| Oldest published | {freshness.get('oldest_published')} |
| Stale rows | {freshness.get('stale_rows')} |
| Threshold days | {freshness.get('threshold_days')} |
| Is fresh | {freshness.get('is_fresh')} |
"""
    write_text(report_path, text)


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Write an explicit baseline/corrupted/repaired comparison."""
    metric_names = ["retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"]
    rows = "\n".join(
        f"| `{name}` | {baseline_metrics.get(name)} | {corrupted_metrics.get(name)} | {repaired_metrics.get(name)} |"
        for name in metric_names
    )
    ragas_names = ["context_precision", "context_recall", "faithfulness"]
    ragas_rows = "\n".join(
        "| `{name}` | {baseline} | {corrupted} | {repaired} |".format(
            name=name,
            baseline=baseline_metrics.get("ragas", {}).get("summary", {}).get(name, "N/A"),
            corrupted=corrupted_metrics.get("ragas", {}).get("summary", {}).get(name, "N/A"),
            repaired=repaired_metrics.get("ragas", {}).get("summary", {}).get(name, "N/A"),
        )
        for name in ragas_names
    )
    text = f"""# Corruption and Repair Comparison Report

The same evaluation set was used for baseline, corrupted, and repaired indexes.

## Evaluation comparison

| Metric | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
{rows}

## Ragas comparison

| Metric | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
{ragas_rows}

## Data-quality comparison

| State | Quality status | Freshness status | Stale rows |
| --- | --- | --- | ---: |
| Baseline | See phase 1 report | N/A | N/A |
| Corrupted | {'PASS' if corrupted_quality.get('passed') else 'FAIL'} | {corrupted_freshness.get('is_fresh')} | {corrupted_freshness.get('stale_rows')} |
| Repaired | {'PASS' if repaired_quality.get('passed') else 'FAIL'} | {repaired_freshness.get('is_fresh')} | {repaired_freshness.get('stale_rows')} |

## Interpretation

The corruption log identifies records deliberately dropped, blanked, noised, truncated, aged, and duplicated. Repair rebuilds the dataset from the parsed raw snapshot, then rebuilds the index and evaluates it on the unchanged test set. Compare the numbers above with the JSON artifacts before drawing conclusions.
"""
    write_text(report_path, text)
