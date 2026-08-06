from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from core.utils import write_text


def _fmt(value: Any, digits: int = 4) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (int, float)):
        return f"{value:.{digits}f}" if isinstance(value, float) else str(value)
    return str(value)


def _metrics_table(metrics: dict[str, Any]) -> str:
    rows = [
        ("retrieval_hit_rate", metrics.get("retrieval_hit_rate")),
        ("mean_token_f1", metrics.get("mean_token_f1")),
        ("judge_accuracy", metrics.get("judge_accuracy")),
        ("mean_judge_score", metrics.get("mean_judge_score")),
        ("samples", metrics.get("samples")),
    ]
    lines = ["| Metric | Value |", "| --- | --- |"]
    for name, value in rows:
        lines.append(f"| `{name}` | {_fmt(value)} |")

    ragas = metrics.get("ragas")
    if isinstance(ragas, dict) and ragas and "skipped" not in ragas and "error" not in ragas:
        for name, value in ragas.items():
            lines.append(f"| `ragas.{name}` | {_fmt(value)} |")
    elif isinstance(ragas, dict) and ("skipped" in ragas or "error" in ragas):
        note = ragas.get("skipped") or ragas.get("error")
        lines.append(f"| `ragas` | Not available ({note}) |")

    return "\n".join(lines)


def _quality_table(quality: dict[str, Any]) -> str:
    checks = quality.get("checks", [])
    lines = ["| Check | Dimension | Passed | Details |", "| --- | --- | --- | --- |"]
    for check in checks:
        details = ", ".join(f"{k}={v}" for k, v in check.get("details", {}).items())
        lines.append(
            f"| `{check.get('name')}` | {check.get('dimension')} | "
            f"{'Pass' if check.get('passed') else 'Fail'} | {details} |"
        )
    summary_line = (
        f"\n**Summary:** {quality.get('passed_checks')}/{quality.get('total_checks')} checks passed "
        f"({_fmt(quality.get('success_rate'), digits=2)} success rate). "
        f"All passed: {_fmt(quality.get('all_passed'))}."
    )
    return "\n".join(lines) + "\n" + summary_line


def _freshness_table(freshness: dict[str, Any]) -> str:
    lines = ["| Field | Value |", "| --- | --- |"]
    for key in (
        "latest_published",
        "oldest_published",
        "stale_rows",
        "total_rows",
        "freshness_threshold_days",
        "is_fresh",
    ):
        lines.append(f"| `{key}` | {_fmt(freshness.get(key))} |")
    return "\n".join(lines)


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Viet markdown report cho baseline phase: source, metrics, quality, freshness."""
    source_lines = "\n".join(f"- **{key}**: {value}" for key, value in source_summary.items())

    content = f"""# Phase 1 Report (Baseline)

Generated at: {datetime.now(UTC).isoformat()}

## 1. Source Summary

{source_lines}

## 2. Evaluation Metrics

{_metrics_table(metrics)}

## 3. Data Quality

{_quality_table(quality)}

## 4. Freshness

{_freshness_table(freshness)}
"""

    write_text(report_path, content)


def _delta(baseline: float | None, other: float | None) -> str:
    if baseline is None or other is None:
        return "N/A"
    return f"{other - baseline:+.4f}"


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
    """Viet markdown report so sanh baseline / corrupted / repaired."""
    metric_keys = ["retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"]

    comparison_lines = [
        "| Metric | Baseline | Corrupted | Repaired | Change (Corrupted) | Recovery (Repaired) |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for key in metric_keys:
        b = baseline_metrics.get(key)
        c = corrupted_metrics.get(key)
        r = repaired_metrics.get(key)
        comparison_lines.append(
            f"| `{key}` | {_fmt(b)} | {_fmt(c)} | {_fmt(r)} | {_delta(b, c)} | {_delta(b, r)} |"
        )
    comparison_table = "\n".join(comparison_lines)

    quality_lines = [
        "| Stage | Passed Checks | Total Checks | All Passed |",
        "| --- | --- | --- | --- |",
        f"| Corrupted | {corrupted_quality.get('passed_checks')} | "
        f"{corrupted_quality.get('total_checks')} | {_fmt(corrupted_quality.get('all_passed'))} |",
        f"| Repaired | {repaired_quality.get('passed_checks')} | "
        f"{repaired_quality.get('total_checks')} | {_fmt(repaired_quality.get('all_passed'))} |",
    ]
    quality_table = "\n".join(quality_lines)

    freshness_lines = [
        "| Stage | Stale Rows | Total Rows | Is Fresh |",
        "| --- | --- | --- | --- |",
        f"| Corrupted | {corrupted_freshness.get('stale_rows')} | "
        f"{corrupted_freshness.get('total_rows')} | {_fmt(corrupted_freshness.get('is_fresh'))} |",
        f"| Repaired | {repaired_freshness.get('stale_rows')} | "
        f"{repaired_freshness.get('total_rows')} | {_fmt(repaired_freshness.get('is_fresh'))} |",
    ]
    freshness_table = "\n".join(freshness_lines)

    content = f"""# Corruption & Repair Comparison Report

Generated at: {datetime.now(UTC).isoformat()}

## 1. Metrics Comparison

{comparison_table}

## 2. Data Quality Comparison

{quality_table}

## 3. Freshness Comparison

{freshness_table}

## 4. Interpretation

- Corruption impact: compare the "Change (Corrupted)" column above against the baseline. A negative
  value on `retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`, or `mean_judge_score` indicates the
  injected data corruption degraded agent quality.
- Repair effectiveness: compare the "Recovery (Repaired)" column against the baseline. Values close to
  `0.0000` indicate the repaired dataset recovered agent quality back to baseline levels.
"""

    write_text(report_path, content)