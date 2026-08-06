from __future__ import annotations

import json
import random

import pandas as pd

from core.utils import ensure_parent


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Simulate multiple data corruption scenarios.

    Corruptions:
    1. Drop some latest records (simulate data loss).
    2. Blank summary on some rows (simulate missing data).
    3. Inject noise into text (simulate data quality issues).
    4. Truncate title (simulate incomplete ingestion).
    5. Make published date old (simulate stale data).
    6. Add duplicate rows (simulate deduplication failure).
    7. Rebuild text_for_embedding.
    8. Write corruption log.
    """
    random.seed(42)
    corrupted = df.copy()
    log_entries: list[dict] = []
    n = len(corrupted)

    # 1. Drop latest records (top 3 by published date, already sorted desc)
    drop_count = min(3, n // 4)
    if drop_count > 0:
        drop_indices = corrupted.head(drop_count).index.tolist()
        dropped_ids = corrupted.loc[drop_indices, "paper_id"].tolist()
        corrupted = corrupted.drop(drop_indices).reset_index(drop=True)
        log_entries.append({
            "type": "drop_latest",
            "description": f"Dropped {drop_count} most recent records",
            "affected_ids": dropped_ids,
            "count": drop_count,
        })
        n = len(corrupted)

    # 2. Blank summary on some rows
    blank_count = min(4, n // 3)
    if blank_count > 0:
        blank_indices = random.sample(range(n), blank_count)
        blank_ids = corrupted.iloc[blank_indices]["paper_id"].tolist()
        corrupted.loc[corrupted.index[blank_indices], "summary"] = ""
        corrupted.loc[corrupted.index[blank_indices], "summary_chars"] = 0
        log_entries.append({
            "type": "blank_summary",
            "description": f"Blanked summary for {blank_count} records",
            "affected_ids": blank_ids,
            "count": blank_count,
        })

    # 3. Inject noise into summary
    noise_count = min(3, n // 4)
    if noise_count > 0:
        available = [i for i in range(n) if corrupted.iloc[i]["summary"] != ""]
        noise_indices = random.sample(available, min(noise_count, len(available)))
        noise_ids = corrupted.iloc[noise_indices]["paper_id"].tolist()
        for idx in noise_indices:
            original = corrupted.iloc[idx]["summary"]
            corrupted.at[corrupted.index[idx], "summary"] = "CORRUPTED_NOISE " + original[:50] + " GARBAGE_DATA xyz123"
        log_entries.append({
            "type": "noise_injection",
            "description": f"Injected noise into {len(noise_indices)} summaries",
            "affected_ids": noise_ids,
            "count": len(noise_indices),
        })

    # 4. Truncate title
    trunc_count = min(3, n // 4)
    if trunc_count > 0:
        trunc_indices = random.sample(range(n), trunc_count)
        trunc_ids = corrupted.iloc[trunc_indices]["paper_id"].tolist()
        for idx in trunc_indices:
            original = corrupted.iloc[idx]["title"]
            corrupted.at[corrupted.index[idx], "title"] = original[:15] + "..."
        log_entries.append({
            "type": "truncate_title",
            "description": f"Truncated title for {trunc_count} records",
            "affected_ids": trunc_ids,
            "count": trunc_count,
        })

    # 5. Make published date old (stale)
    stale_count = min(4, n // 3)
    if stale_count > 0:
        stale_indices = random.sample(range(n), stale_count)
        stale_ids = corrupted.iloc[stale_indices]["paper_id"].tolist()
        for idx in stale_indices:
            corrupted.at[corrupted.index[idx], "published"] = "2020-01-01"
            corrupted.at[corrupted.index[idx], "age_days"] = 2000
        log_entries.append({
            "type": "stale_date",
            "description": f"Set published date to 2020-01-01 for {stale_count} records",
            "affected_ids": stale_ids,
            "count": stale_count,
        })

    # 6. Add duplicate rows
    dup_count = min(3, n // 4)
    if dup_count > 0:
        dup_indices = random.sample(range(n), dup_count)
        dup_rows = corrupted.iloc[dup_indices]
        dup_ids = dup_rows["paper_id"].tolist()
        corrupted = pd.concat([corrupted, dup_rows], ignore_index=True)
        log_entries.append({
            "type": "duplicates",
            "description": f"Added {dup_count} duplicate rows",
            "affected_ids": dup_ids,
            "count": dup_count,
        })

    # 7. Rebuild text_for_embedding
    def rebuild_text(row):
        parts = [f"Title: {row['title']}"]
        if row["summary"]:
            parts.append(f"Abstract: {row['summary']}")
        if row["authors_joined"]:
            parts.append(f"Authors: {row['authors_joined']}")
        if row["categories_joined"]:
            parts.append(f"Categories: {row['categories_joined']}")
        return "\n".join(parts)

    corrupted["text_for_embedding"] = corrupted.apply(rebuild_text, axis=1)

    # 8. Write corruption log
    log = {
        "total_original": len(df),
        "total_corrupted": len(corrupted),
        "corruptions": log_entries,
    }
    ensure_parent(output_log_path)
    output_log_path.write_text(
        json.dumps(log, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"[corruption] Applied {len(log_entries)} corruption types, "
          f"records: {len(df)} -> {len(corrupted)}")
    return corrupted
