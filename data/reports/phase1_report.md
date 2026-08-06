# Phase 1 — Baseline Report

## Source summary

| Field | Value |
| --- | --- |
| Source | Crossref REST API |
| Query | agentic retrieval augmented generation large language model |
| Filter | from-pub-date:2026-02-07,has-abstract:true |
| Raw records | 24 |
| Clean records | 24 |

## Evaluation metrics

| Metric | Value |
| --- | ---: |
| `samples` | 8 |
| `retrieval_hit_rate` | 1.0 |
| `mean_token_f1` | 1.0 |
| `judge_accuracy` | 1.0 |
| `mean_judge_score` | 5 |

## Data quality

Overall status: **PASS**

| Check | Status | Observed | Expected |
| --- | --- | ---: | --- |
| row_count | PASS | 24 | > 0 |
| paper_id_not_null | PASS | 0 | 0 |
| paper_id_unique | PASS | 0 | 0 |
| title_not_blank | PASS | 0 | 0 |
| summary_min_length | PASS | 0 | 0 |
| embedding_text_not_blank | PASS | 0 | 0 |
| age_days_valid | PASS | 0 | 0 |
| freshness_threshold | PASS | 0 | 0 |

## Ragas

| Metric | Value |
| --- | ---: |
| `context_precision` | 0.749999999925 |
| `context_recall` | 0.75 |
| `faithfulness` | 0.75 |

## Freshness

| Signal | Value |
| --- | --- |
| Latest published | 2026-08-01 |
| Oldest published | 2026-02-12 |
| Stale rows | 0 |
| Threshold days | 180 |
| Is fresh | True |
