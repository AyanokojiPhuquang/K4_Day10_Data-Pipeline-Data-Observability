from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from core.config import Settings
from core.utils import write_json


def _to_native(val):
    """Convert numpy types to native Python types for JSON serialization."""
    if isinstance(val, (np.bool_,)):
        return bool(val)
    if isinstance(val, (np.integer,)):
        return int(val)
    if isinstance(val, (np.floating,)):
        return float(val)
    return val


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run data quality checks on the cleaned dataframe.

    Checks:
    1. Row count >= 1.
    2. paper_id not null and unique.
    3. title not null.
    4. summary length > 0.
    5. Freshness: age_days within threshold.
    """
    checks: list[dict[str, Any]] = []
    all_passed = True

    # Check 1: Row count
    row_count = len(df)
    passed = row_count >= 1
    checks.append({
        "check": "row_count",
        "dimension": "completeness",
        "threshold": ">= 1",
        "value": row_count,
        "passed": passed,
    })
    if not passed:
        all_passed = False

    # Check 2: paper_id not null and unique
    null_ids = df["paper_id"].isna().sum()
    unique_ids = df["paper_id"].nunique()
    total = len(df)
    id_valid = null_ids == 0 and unique_ids == total
    checks.append({
        "check": "paper_id_unique_not_null",
        "dimension": "uniqueness",
        "threshold": "0 nulls, all unique",
        "value": f"nulls={null_ids}, unique={unique_ids}/{total}",
        "passed": id_valid,
    })
    if not id_valid:
        all_passed = False

    # Check 3: title not null
    null_titles = df["title"].isna().sum() + (df["title"] == "").sum()
    title_valid = null_titles == 0
    checks.append({
        "check": "title_not_null",
        "dimension": "completeness",
        "threshold": "0 nulls/empty",
        "value": f"invalid={null_titles}",
        "passed": title_valid,
    })
    if not title_valid:
        all_passed = False

    # Check 4: summary length > 0
    if "summary_chars" in df.columns:
        empty_summaries = (df["summary_chars"] == 0).sum()
    else:
        empty_summaries = (df["summary"].str.len() == 0).sum()
    summary_pct = (total - empty_summaries) / total if total > 0 else 0
    summary_valid = summary_pct >= 0.8  # At least 80% should have summaries
    checks.append({
        "check": "summary_not_empty",
        "dimension": "completeness",
        "threshold": ">= 80% with summary",
        "value": f"{summary_pct:.2%} ({total - empty_summaries}/{total})",
        "passed": summary_valid,
    })
    if not summary_valid:
        all_passed = False

    # Check 5: Freshness
    if "age_days" in df.columns:
        stale_count = (df["age_days"] > settings.freshness_threshold_days).sum()
        fresh_pct = (total - stale_count) / total if total > 0 else 0
        freshness_valid = fresh_pct >= 0.5  # At least 50% fresh
    else:
        stale_count = 0
        fresh_pct = 1.0
        freshness_valid = True
    checks.append({
        "check": "freshness",
        "dimension": "timeliness",
        "threshold": f">= 50% within {settings.freshness_threshold_days} days",
        "value": f"{fresh_pct:.2%} fresh ({total - stale_count}/{total})",
        "passed": freshness_valid,
    })
    if not freshness_valid:
        all_passed = False

    result = {
        "report_name": report_name,
        "timestamp": datetime.utcnow().isoformat(),
        "total_records": int(total),
        "all_passed": bool(all_passed),
        "checks": [
            {k: _to_native(v) for k, v in c.items()}
            for c in checks
        ],
    }

    # Save report
    output_path = settings.paths.quality_dir / f"{report_name}.json"
    write_json(output_path, result)
    print(f"[quality] Quality checks for '{report_name}': {'ALL PASSED' if all_passed else 'SOME FAILED'}")
    return result


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Build freshness report from cleaned dataframe.

    Steps:
    1. Find latest and oldest published date.
    2. Count stale rows.
    3. Build payload with is_fresh status.
    4. Write JSON report.
    """
    total = len(df)

    if "age_days" in df.columns and total > 0:
        valid_dates = df[df["published"].str.len() > 0]
        if len(valid_dates) > 0:
            latest_published = valid_dates["published"].max()
            oldest_published = valid_dates["published"].min()
            stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum())
        else:
            latest_published = "N/A"
            oldest_published = "N/A"
            stale_rows = total
    else:
        latest_published = "N/A"
        oldest_published = "N/A"
        stale_rows = 0

    is_fresh = stale_rows < (total * 0.5) if total > 0 else False

    report = {
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_rows": stale_rows,
        "total_rows": total,
        "freshness_threshold_days": settings.freshness_threshold_days,
        "is_fresh": is_fresh,
        "status": "FRESH" if is_fresh else "STALE",
    }

    write_json(report_path, report)
    print(f"[freshness] Status: {'FRESH' if is_fresh else 'STALE'} "
          f"(stale={stale_rows}/{total}, threshold={settings.freshness_threshold_days}d)")
    return report
