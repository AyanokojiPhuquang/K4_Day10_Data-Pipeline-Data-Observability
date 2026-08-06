# Phase 1: Baseline Pipeline Report

## Source Summary

- **Source:** Crossref REST API
- **Query:** agentic retrieval augmented generation large language model
- **Filter:** from-pub-date:2026-02-07,has-abstract:true
- **Records fetched:** 24
- **Records after cleaning:** 24

## Evaluation Metrics

| Metric | Value |
| --- | ---: |
| retrieval_hit_rate | 1.0 |
| mean_token_f1 | 1.0 |
| judge_accuracy | 1.0 |
| mean_judge_score | 5 |
| samples | 72 |

## Data Quality

- **All checks passed:** True

- row_count (completeness): ✅ PASS — 24
- paper_id_unique_not_null (uniqueness): ✅ PASS — nulls=0, unique=24/24
- title_not_null (completeness): ✅ PASS — invalid=0
- summary_not_empty (completeness): ✅ PASS — 100.00% (24/24)
- freshness (timeliness): ✅ PASS — 100.00% fresh (24/24)

## Freshness

- **Status:** FRESH
- **Latest published:** 2026-08-01
- **Oldest published:** 2026-02-13
- **Stale rows:** 0/24
- **Threshold:** 180 days
