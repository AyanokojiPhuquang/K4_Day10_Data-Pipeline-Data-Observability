from __future__ import annotations

from pathlib import Path
import pandas as pd

from core.utils import write_json


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: Path | str) -> pd.DataFrame:
    """Simulate basic and advanced data corruption scenarios on the clean dataframe and save a corruption log."""
    if df.empty:
        write_json(Path(output_log_path), {"status": "empty_input"})
        return df.copy()

    corrupted = df.copy()
    # Ensure string/text columns have str/object dtype to avoid Pandas float64 coercion errors
    text_cols = ["paper_id", "title", "summary", "authors_joined", "categories_joined", "primary_category", "published", "abs_url", "pdf_url", "comment"]
    for col in text_cols:
        if col in corrupted.columns:
            corrupted[col] = corrupted[col].fillna("").astype(str)

    log_actions: list[str] = []

    # 1. Drop a few latest records (e.g., last 2 rows)
    num_drop = min(2, len(corrupted) - 1)
    if num_drop > 0:
        dropped_ids = corrupted.tail(num_drop)["paper_id"].tolist()
        corrupted = corrupted.iloc[:-num_drop].copy()
        log_actions.append(f"Dropped {num_drop} latest records: {dropped_ids}")

    corrupted = corrupted.reset_index(drop=True)

    # 2. Blank summary in row 0
    if len(corrupted) > 0:
        paper_id = corrupted.at[0, "paper_id"]
        corrupted.at[0, "summary"] = ""
        corrupted.at[0, "summary_chars"] = 0
        log_actions.append(f"Blanked summary for paper_id: {paper_id}")

    # 3. Inject random noise into summary in row 1
    if len(corrupted) > 1:
        paper_id = corrupted.at[1, "paper_id"]
        corrupted.at[1, "summary"] = "NOISE " * 20 + " [CORRUPTED TEXT]"
        corrupted.at[1, "summary_chars"] = len(corrupted.at[1, "summary"])
        log_actions.append(f"Injected noise into summary for paper_id: {paper_id}")

    # 4. Truncate title in row 2
    if len(corrupted) > 2:
        paper_id = corrupted.at[2, "paper_id"]
        corrupted.at[2, "title"] = corrupted.at[2, "title"][:10] + "..."
        log_actions.append(f"Truncated title for paper_id: {paper_id}")

    # 5. Make published date stale in row 3
    if len(corrupted) > 3:
        paper_id = corrupted.at[3, "paper_id"]
        corrupted.at[3, "published"] = "2010-01-01"
        corrupted.at[3, "age_days"] = 5000
        log_actions.append(f"Set publication date to stale (2010-01-01) for paper_id: {paper_id}")

    # 6. Add duplicate row (duplicate row 0)
    if len(corrupted) > 0:
        dup_row = corrupted.iloc[[0]].copy()
        corrupted = pd.concat([corrupted, dup_row], ignore_index=True)
        log_actions.append(f"Added duplicate row for paper_id: {dup_row.iloc[0]['paper_id']}")

    # ==================== ADVANCED CORRUPTION SCENARIOS ====================

    # 7. Author Entity Swap (Swap authors between row 0 and row 4 if available)
    if len(corrupted) > 4:
        id_0 = corrupted.at[0, "paper_id"]
        id_4 = corrupted.at[4, "paper_id"]
        authors_0 = corrupted.at[0, "authors_joined"]
        authors_4 = corrupted.at[4, "authors_joined"]

        corrupted.at[0, "authors_joined"] = authors_4
        corrupted.at[4, "authors_joined"] = authors_0
        log_actions.append(f"Swapped authors between paper_id {id_0} and {id_4} (Factuality corruption)")

    # 8. UTF-8 Mojibake / Encoding Noise Injection in row 4
    if len(corrupted) > 4:
        paper_id = corrupted.at[4, "paper_id"]
        corrupted.at[4, "summary"] = corrupted.at[4, "summary"] + " â€œMojibake Encoding NoiseÃ©â€™"
        log_actions.append(f"Injected UTF-8 Mojibake encoding noise into summary for paper_id: {paper_id}")

    # 9. Category Misclassification in row 5 if available
    if len(corrupted) > 5:
        paper_id = corrupted.at[5, "paper_id"]
        corrupted.at[5, "categories_joined"] = "Agriculture, Veterinary Sciences, Soil Science"
        corrupted.at[5, "primary_category"] = "Agriculture"
        log_actions.append(f"Misclassified domain category to Agriculture for paper_id: {paper_id}")

    # 10. Malformed URL artifact in row 5
    if len(corrupted) > 5:
        paper_id = corrupted.at[5, "paper_id"]
        corrupted.at[5, "abs_url"] = "https://invalid_broken_url_schema"
        log_actions.append(f"Set malformed abs_url for paper_id: {paper_id}")

    # Rebuild text_for_embedding
    corrupted["text_for_embedding"] = (
        "Title: " + corrupted["title"].astype(str) + "\n" +
        "Authors: " + corrupted["authors_joined"].astype(str) + "\n" +
        "Categories: " + corrupted["categories_joined"].astype(str) + "\n" +
        "Published: " + corrupted["published"].astype(str) + "\n" +
        "Summary: " + corrupted["summary"].astype(str)
    )

    log_payload = {
        "status": "success",
        "total_corrupted_rows": len(corrupted),
        "actions_taken": log_actions,
    }

    write_json(Path(output_log_path), log_payload)
    return corrupted
