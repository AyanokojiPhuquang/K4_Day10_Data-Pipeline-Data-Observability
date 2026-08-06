from __future__ import annotations

import re
from datetime import datetime

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord

_MIN_SUMMARY_CHARS = 20
_MARKUP_TAG_RE = re.compile(r"<[^>]+>")


def _strip_markup(value: str) -> str:
    return normalize_whitespace(_MARKUP_TAG_RE.sub(" ", value or ""))

_CLEAN_COLUMNS = [
    "paper_id",
    "title",
    "summary",
    "authors",
    "authors_joined",
    "categories",
    "categories_joined",
    "primary_category",
    "published",
    "updated",
    "abs_url",
    "pdf_url",
    "comment",
    "summary_chars",
    "age_days",
    "text_for_embedding",
]


def build_text_for_embedding(title: str, authors_joined: str, categories_joined: str, published: str, summary: str) -> str:
    """Compose the text block that gets embedded for retrieval."""
    lines = [
        f"Title: {title}",
        f"Authors: {authors_joined or 'Unknown'}",
        f"Categories: {categories_joined or 'Unknown'}",
        f"Published: {published or 'Unknown'}",
        "",
        summary,
    ]
    return "\n".join(lines).strip()


def _parse_published_date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw `PaperRecord`s into a dataframe ready for embedding."""
    rows: list[dict] = []

    for record in records:
        paper_id = normalize_whitespace(record.paper_id)
        title = _strip_markup(record.title)
        summary = _strip_markup(record.summary)
        if not paper_id or not title or len(summary) < _MIN_SUMMARY_CHARS:
            continue

        published_date = _parse_published_date(record.published)
        if published_date is None:
            continue

        authors = [normalize_whitespace(author) for author in record.authors if normalize_whitespace(author)]
        categories = [normalize_whitespace(category) for category in record.categories if normalize_whitespace(category)]
        authors_joined = compact_join(authors)
        categories_joined = compact_join(categories)
        published_iso = published_date.date().isoformat()

        rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "authors_joined": authors_joined,
                "categories": categories,
                "categories_joined": categories_joined,
                "primary_category": normalize_whitespace(record.primary_category),
                "published": published_iso,
                "updated": normalize_whitespace(record.updated) or published_iso,
                "abs_url": record.abs_url,
                "pdf_url": record.pdf_url,
                "comment": record.comment,
                "summary_chars": len(summary),
                "age_days": (run_date.date() - published_date.date()).days,
            }
        )

    df = pd.DataFrame(rows, columns=_CLEAN_COLUMNS[:-1])
    if df.empty:
        return pd.DataFrame(columns=_CLEAN_COLUMNS)

    df = df.drop_duplicates(subset="paper_id", keep="first")
    df["text_for_embedding"] = df.apply(
        lambda row: build_text_for_embedding(
            row["title"], row["authors_joined"], row["categories_joined"], row["published"], row["summary"]
        ),
        axis=1,
    )
    df = df.sort_values("published", ascending=False).reset_index(drop=True)
    return df
