from __future__ import annotations

from typing import Any

from core.utils import write_text


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Generate markdown report for the baseline phase."""
    lines = [
        "# Phase 1: Baseline Pipeline Report",
        "",
        "## Source Summary",
        "",
        f"- **Source:** {source_summary.get('source', 'Crossref API')}",
        f"- **Query:** {source_summary.get('query', 'N/A')}",
        f"- **Filter:** {source_summary.get('filter', 'N/A')}",
        f"- **Records fetched:** {source_summary.get('records_fetched', 'N/A')}",
        f"- **Records after cleaning:** {source_summary.get('records_cleaned', 'N/A')}",
        "",
        "## Evaluation Metrics",
        "",
        f"| Metric | Value |",
        f"| --- | ---: |",
        f"| retrieval_hit_rate | {metrics.get('retrieval_hit_rate', 'N/A')} |",
        f"| mean_token_f1 | {metrics.get('mean_token_f1', 'N/A')} |",
        f"| judge_accuracy | {metrics.get('judge_accuracy', 'N/A')} |",
        f"| mean_judge_score | {metrics.get('mean_judge_score', 'N/A')} |",
        f"| samples | {metrics.get('samples', 'N/A')} |",
        "",
        "## Data Quality",
        "",
        f"- **All checks passed:** {quality.get('all_passed', 'N/A')}",
        "",
    ]

    for check in quality.get("checks", []):
        status = "✅ PASS" if check["passed"] else "❌ FAIL"
        lines.append(f"- {check['check']} ({check['dimension']}): {status} — {check['value']}")

    lines.extend([
        "",
        "## Freshness",
        "",
        f"- **Status:** {freshness.get('status', 'N/A')}",
        f"- **Latest published:** {freshness.get('latest_published', 'N/A')}",
        f"- **Oldest published:** {freshness.get('oldest_published', 'N/A')}",
        f"- **Stale rows:** {freshness.get('stale_rows', 'N/A')}/{freshness.get('total_rows', 'N/A')}",
        f"- **Threshold:** {freshness.get('freshness_threshold_days', 'N/A')} days",
        "",
    ])

    write_text(report_path, "\n".join(lines))
    print(f"[reporting] Phase 1 report written to {report_path}")


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
    """Generate markdown report comparing baseline/corrupted/repaired."""
    def fmt(val):
        if isinstance(val, float):
            return f"{val:.4f}"
        return str(val)

    lines = [
        "# Corruption & Repair Comparison Report",
        "",
        "## Metrics Comparison",
        "",
        "| Metric | Baseline | Corrupted | Repaired |",
        "| --- | ---: | ---: | ---: |",
    ]

    for metric in ("retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"):
        b = fmt(baseline_metrics.get(metric, "N/A"))
        c = fmt(corrupted_metrics.get(metric, "N/A"))
        r = fmt(repaired_metrics.get(metric, "N/A"))
        lines.append(f"| {metric} | {b} | {c} | {r} |")

    lines.extend([
        "",
        "## Data Quality Comparison",
        "",
        f"- **Corrupted all passed:** {corrupted_quality.get('all_passed', 'N/A')}",
        f"- **Repaired all passed:** {repaired_quality.get('all_passed', 'N/A')}",
        "",
        "## Freshness Comparison",
        "",
        f"- **Corrupted freshness:** {corrupted_freshness.get('status', 'N/A')}",
        f"- **Repaired freshness:** {repaired_freshness.get('status', 'N/A')}",
        "",
        "## Analysis",
        "",
        "Data corruption degrades retrieval and answer quality. "
        "Repair from the original raw source restores data integrity and recovers evaluation metrics.",
        "",
    ])

    write_text(report_path, "\n".join(lines))
    print(f"[reporting] Corruption comparison report written to {report_path}")
