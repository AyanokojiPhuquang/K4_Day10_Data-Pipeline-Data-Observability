from __future__ import annotations

from datetime import datetime

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records into a DataFrame ready for embedding.

    Steps:
    1. Normalize title, summary, authors, categories.
    2. Parse published/updated date.
    3. Compute age_days.
    4. Create helper columns: authors_joined, categories_joined, summary_chars, text_for_embedding.
    5. Drop duplicates and filter bad rows.
    6. Sort by published date descending and return.
    """
    rows = []
    for record in records:
        title = normalize_whitespace(record.title)
        summary = normalize_whitespace(record.summary)
        authors = [normalize_whitespace(a) for a in record.authors if a.strip()]
        categories = [normalize_whitespace(c) for c in record.categories if c.strip()]
        primary_category = normalize_whitespace(record.primary_category)
        published = record.published.strip()
        updated = record.updated.strip()

        # Skip records without title
        if not title:
            continue

        # Parse published date and compute age_days
        try:
            pub_date = datetime.strptime(published, "%Y-%m-%d") if published else None
        except ValueError:
            pub_date = None

        # Make run_date naive for comparison if needed
        if pub_date:
            run_date_naive = run_date.replace(tzinfo=None) if run_date.tzinfo else run_date
            age_days = (run_date_naive - pub_date).days
        else:
            age_days = None

        authors_joined = compact_join(authors)
        categories_joined = compact_join(categories)
        summary_chars = len(summary)

        # Build text_for_embedding: combine title, summary, authors, categories
        text_parts = [f"Title: {title}"]
        if summary:
            text_parts.append(f"Abstract: {summary}")
        if authors_joined:
            text_parts.append(f"Authors: {authors_joined}")
        if categories_joined:
            text_parts.append(f"Categories: {categories_joined}")
        text_for_embedding = "\n".join(text_parts)

        rows.append(
            {
                "paper_id": record.paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": primary_category,
                "published": published,
                "updated": updated,
                "abs_url": record.abs_url,
                "pdf_url": record.pdf_url,
                "comment": record.comment,
                "age_days": age_days,
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": summary_chars,
                "text_for_embedding": text_for_embedding,
            }
        )

    df = pd.DataFrame(rows)

    if df.empty:
        return df

    # Drop duplicates by paper_id
    df = df.drop_duplicates(subset=["paper_id"], keep="first")

    # Filter rows with no summary (empty abstract)
    df = df[df["summary_chars"] > 0].copy()

    # Sort by published date descending
    df = df.sort_values("published", ascending=False).reset_index(drop=True)

    print(f"[cleaning] Cleaned {len(df)} records from {len(records)} raw records.")
    return df
