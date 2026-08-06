# Corruption and Repair Comparison Report

The same evaluation set was used for baseline, corrupted, and repaired indexes.

## Evaluation comparison

| Metric | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| `retrieval_hit_rate` | 1.0 | 0.25 | 1.0 |
| `mean_token_f1` | 1.0 | 0.4083333333333333 | 1.0 |
| `judge_accuracy` | 1.0 | 0.375 | 1.0 |
| `mean_judge_score` | 5 | 2.625 | 5 |

## Ragas comparison

| Metric | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| `context_precision` | 0.749999999925 | 0.1249999999875 | 0.749999999925 |
| `context_recall` | 0.75 | 0.125 | 0.75 |
| `faithfulness` | 0.75 | 0.2619047619047619 | 0.75 |

## Data-quality comparison

| State | Quality status | Freshness status | Stale rows |
| --- | --- | --- | ---: |
| Baseline | See phase 1 report | N/A | N/A |
| Corrupted | FAIL | False | 1 |
| Repaired | PASS | True | 0 |

## Interpretation

The corruption log identifies records deliberately dropped, blanked, noised, truncated, aged, and duplicated. Repair rebuilds the dataset from the parsed raw snapshot, then rebuilds the index and evaluates it on the unchanged test set. Compare the numbers above with the JSON artifacts before drawing conclusions.
