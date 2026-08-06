# Phase 1 Report (Baseline)

Generated at: 2026-08-06T10:57:43.789645+00:00

## 1. Source Summary

- **source**: Crossref REST API
- **query**: agentic retrieval augmented generation large language model
- **filter**: from-pub-date:2026-02-07,has-abstract:true
- **records_fetched**: 24
- **records_cleaned**: 24

## 2. Evaluation Metrics

| Metric | Value |
| --- | --- |
| `retrieval_hit_rate` | 1.0000 |
| `mean_token_f1` | 1.0000 |
| `judge_accuracy` | 1.0000 |
| `mean_judge_score` | 5 |
| `samples` | 72 |
| `ragas` | Not available (Set RUN_RAGAS=1 to enable the slower Ragas pass.) |

## 3. Data Quality

| Check | Dimension | Passed | Details |
| --- | --- | --- | --- |
| `row_count` | completeness | Pass | total_rows=24 |
| `paper_id_not_null_unique` | uniqueness | Pass | null_count=0, duplicate_count=0 |
| `title_not_null` | completeness | Pass | null_count=0, blank_count=0 |
| `summary_min_length` | validity | Pass | min_chars=40, too_short_count=0 |
| `freshness_age_days` | timeliness | Pass | threshold_days=180, stale_count=0 |

**Summary:** 5/5 checks passed (1.00 success rate). All passed: Yes.

## 4. Freshness

| Field | Value |
| --- | --- |
| `latest_published` | 2026-08-01T00:00:00+00:00 |
| `oldest_published` | 2026-02-13T00:00:00+00:00 |
| `stale_rows` | 0 |
| `total_rows` | 24 |
| `freshness_threshold_days` | 180 |
| `is_fresh` | Yes |
