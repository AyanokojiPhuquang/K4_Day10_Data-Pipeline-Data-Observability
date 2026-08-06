# Corruption & Repair Comparison Report

Generated at: 2026-08-06T10:58:05.425443+00:00

## 1. Metrics Comparison

| Metric | Baseline | Corrupted | Repaired | Change (Corrupted) | Recovery (Repaired) |
| --- | --- | --- | --- | --- | --- |
| `retrieval_hit_rate` | 1.0000 | 0.9167 | 1.0000 | -0.0833 | +0.0000 |
| `mean_token_f1` | 1.0000 | 0.8653 | 1.0000 | -0.1347 | +0.0000 |
| `judge_accuracy` | 1.0000 | 0.8611 | 1.0000 | -0.1389 | +0.0000 |
| `mean_judge_score` | 5 | 4.4444 | 5 | -0.5556 | +0.0000 |

## 2. Data Quality Comparison

| Stage | Passed Checks | Total Checks | All Passed |
| --- | --- | --- | --- |
| Corrupted | 2 | 5 | No |
| Repaired | 5 | 5 | Yes |

## 3. Freshness Comparison

| Stage | Stale Rows | Total Rows | Is Fresh |
| --- | --- | --- | --- |
| Corrupted | 1 | 23 | Yes |
| Repaired | 0 | 24 | Yes |

## 4. Interpretation

- Corruption impact: compare the "Change (Corrupted)" column above against the baseline. A negative
  value on `retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`, or `mean_judge_score` indicates the
  injected data corruption degraded agent quality.
- Repair effectiveness: compare the "Recovery (Repaired)" column against the baseline. Values close to
  `0.0000` indicate the repaired dataset recovered agent quality back to baseline levels.
