from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import write_json


def _check_row_count(df: pd.DataFrame) -> dict[str, Any]:
    total_rows = len(df)
    passed = total_rows > 0
    return {
        "name": "row_count",
        "dimension": "completeness",
        "passed": passed,
        "details": {"total_rows": total_rows},
    }


def _check_paper_id(df: pd.DataFrame) -> dict[str, Any]:
    if "paper_id" not in df.columns:
        return {
            "name": "paper_id_not_null_unique",
            "dimension": "uniqueness",
            "passed": False,
            "details": {"error": "Column 'paper_id' not found in dataframe."},
        }
    null_count = int(df["paper_id"].isna().sum())
    duplicate_count = int(df["paper_id"].duplicated().sum())
    passed = null_count == 0 and duplicate_count == 0
    return {
        "name": "paper_id_not_null_unique",
        "dimension": "uniqueness",
        "passed": passed,
        "details": {"null_count": null_count, "duplicate_count": duplicate_count},
    }


def _check_title(df: pd.DataFrame) -> dict[str, Any]:
    if "title" not in df.columns:
        return {
            "name": "title_not_null",
            "dimension": "completeness",
            "passed": False,
            "details": {"error": "Column 'title' not found in dataframe."},
        }
    null_count = int(df["title"].isna().sum())
    blank_count = int((df["title"].astype(str).str.strip() == "").sum())
    passed = null_count == 0 and blank_count == 0
    return {
        "name": "title_not_null",
        "dimension": "completeness",
        "passed": passed,
        "details": {"null_count": null_count, "blank_count": blank_count},
    }


def _check_summary_length(df: pd.DataFrame, min_chars: int = 40) -> dict[str, Any]:
    if "summary" not in df.columns:
        return {
            "name": "summary_min_length",
            "dimension": "validity",
            "passed": False,
            "details": {"error": "Column 'summary' not found in dataframe."},
        }
    lengths = df["summary"].fillna("").astype(str).str.len()
    too_short_count = int((lengths < min_chars).sum())
    passed = too_short_count == 0
    return {
        "name": "summary_min_length",
        "dimension": "validity",
        "passed": passed,
        "details": {"min_chars": min_chars, "too_short_count": too_short_count},
    }


def _check_freshness(df: pd.DataFrame, settings: Settings) -> dict[str, Any]:
    if "age_days" not in df.columns:
        return {
            "name": "freshness_age_days",
            "dimension": "timeliness",
            "passed": False,
            "details": {"error": "Column 'age_days' not found in dataframe."},
        }
    threshold = settings.freshness_threshold_days
    stale_count = int((df["age_days"] > threshold).sum())
    passed = stale_count == 0
    return {
        "name": "freshness_age_days",
        "dimension": "timeliness",
        "passed": passed,
        "details": {"threshold_days": threshold, "stale_count": stale_count},
    }


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Chay bo data quality checks tren cleaned dataframe va ghi report vao data/quality/."""
    checks = [
        _check_row_count(df),
        _check_paper_id(df),
        _check_title(df),
        _check_summary_length(df),
        _check_freshness(df, settings),
    ]

    passed_count = sum(1 for c in checks if c["passed"])
    total_count = len(checks)

    report = {
        "report_name": report_name,
        "generated_at": datetime.now(UTC).isoformat(),
        "total_rows": len(df),
        "checks": checks,
        "passed_checks": passed_count,
        "total_checks": total_count,
        "success_rate": passed_count / total_count if total_count else 0.0,
        "all_passed": passed_count == total_count,
    }

    output_path = settings.paths.quality_dir / f"{report_name}.json"
    write_json(output_path, report)  # write_json already calls ensure_parent internally

    return report


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Tong hop freshness report: latest/oldest published date va so dong stale."""
    total_rows = len(df)

    if total_rows == 0 or "published" not in df.columns:
        payload = {
            "generated_at": datetime.now(UTC).isoformat(),
            "latest_published": None,
            "oldest_published": None,
            "stale_rows": 0,
            "total_rows": total_rows,
            "is_fresh": False,
        }
        write_json(report_path, payload)
        return payload

    published = pd.to_datetime(df["published"], errors="coerce", utc=True)
    valid_published = published.dropna()

    latest_published = valid_published.max() if not valid_published.empty else None
    oldest_published = valid_published.min() if not valid_published.empty else None

    threshold = settings.freshness_threshold_days
    if "age_days" in df.columns:
        stale_rows = int((df["age_days"] > threshold).sum())
    else:
        now = datetime.now(UTC)
        age_days = (now - published).dt.days
        stale_rows = int((age_days > threshold).sum())

    is_fresh = False
    if latest_published is not None:
        latest_age_days = (datetime.now(UTC) - latest_published.to_pydatetime()).days
        is_fresh = latest_age_days <= threshold

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "latest_published": latest_published.isoformat() if latest_published is not None else None,
        "oldest_published": oldest_published.isoformat() if oldest_published is not None else None,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "freshness_threshold_days": threshold,
        "is_fresh": is_fresh,
    }

    write_json(report_path, payload)

    return payload