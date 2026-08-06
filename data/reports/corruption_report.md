# Corruption & Repair Comparison Report

## Metrics Comparison

| Metric | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| retrieval_hit_rate | 1.0000 | 0.8750 | 1.0000 |
| mean_token_f1 | 1.0000 | 0.6975 | 1.0000 |
| judge_accuracy | 1.0000 | 0.6806 | 1.0000 |
| mean_judge_score | 5 | 3.7222 | 5 |

## Data Quality Comparison

- **Corrupted all passed:** False
- **Repaired all passed:** True

## Freshness Comparison

- **Corrupted freshness:** FRESH
- **Repaired freshness:** FRESH

## Analysis

Data corruption degrades retrieval and answer quality. Repair from the original raw source restores data integrity and recovers evaluation metrics.
