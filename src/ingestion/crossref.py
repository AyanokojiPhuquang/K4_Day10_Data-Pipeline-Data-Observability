from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import requests

from core.config import Settings
from core.utils import ensure_parent, normalize_whitespace, read_json, write_json


CROSSREF_API_URL = "https://api.crossref.org/works"


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _extract_date(item: dict) -> str:
    """Extract ISO date string from Crossref date-parts structure."""
    for field in ("published-print", "published-online", "created", "issued"):
        date_obj = item.get(field)
        if date_obj and "date-parts" in date_obj:
            parts = date_obj["date-parts"][0]
            if parts and parts[0]:
                year = parts[0]
                month = parts[1] if len(parts) > 1 and parts[1] else 1
                day = parts[2] if len(parts) > 2 and parts[2] else 1
                return f"{year:04d}-{month:02d}-{day:02d}"
    return ""


def _extract_authors(item: dict) -> list[str]:
    """Extract author names from Crossref author list."""
    authors = []
    for author in item.get("author", []):
        given = author.get("given", "")
        family = author.get("family", "")
        name = f"{given} {family}".strip()
        if name:
            authors.append(name)
    return authors


def _extract_abstract(item: dict) -> str:
    """Extract and clean abstract/summary text."""
    abstract = item.get("abstract", "")
    if abstract:
        # Remove JATS XML tags if present
        import re
        abstract = re.sub(r"<[^>]+>", "", abstract)
        abstract = normalize_whitespace(abstract)
    return abstract


def _extract_categories(item: dict) -> list[str]:
    """Extract subject categories from Crossref item."""
    return item.get("subject", [])


def _extract_urls(item: dict) -> tuple[str, str]:
    """Extract abstract URL and PDF URL from Crossref item."""
    doi = item.get("DOI", "")
    abs_url = f"https://doi.org/{doi}" if doi else item.get("URL", "")

    pdf_url = ""
    for link in item.get("link", []):
        if link.get("content-type") == "application/pdf":
            pdf_url = link.get("URL", "")
            break
    return abs_url, pdf_url


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref API response payload into list of PaperRecord.

    Steps:
    1. Iterate payload["message"]["items"].
    2. Extract DOI, title, abstract, authors, subject, dates, URLs.
    3. Normalize text and skip records without valid title or DOI.
    4. Return list of PaperRecord.
    """
    items = payload.get("message", {}).get("items", [])
    records: list[PaperRecord] = []

    for item in items:
        doi = item.get("DOI", "").strip()
        if not doi:
            continue

        # Title
        title_parts = item.get("title", [])
        title = normalize_whitespace(title_parts[0]) if title_parts else ""
        if not title:
            continue

        # Summary/abstract
        summary = _extract_abstract(item)

        # Authors
        authors = _extract_authors(item)

        # Categories/subjects
        categories = _extract_categories(item)
        primary_category = categories[0] if categories else ""

        # Dates
        published = _extract_date(item)
        # Use deposited or indexed as updated date
        updated = ""
        for field in ("deposited", "indexed"):
            date_obj = item.get(field)
            if date_obj and "date-parts" in date_obj:
                parts = date_obj["date-parts"][0]
                if parts and parts[0]:
                    year = parts[0]
                    month = parts[1] if len(parts) > 1 and parts[1] else 1
                    day = parts[2] if len(parts) > 2 and parts[2] else 1
                    updated = f"{year:04d}-{month:02d}-{day:02d}"
                    break

        # URLs
        abs_url, pdf_url = _extract_urls(item)

        # Comment (subtitle if available)
        subtitle_parts = item.get("subtitle", [])
        comment = normalize_whitespace(subtitle_parts[0]) if subtitle_parts else ""

        records.append(
            PaperRecord(
                paper_id=doi,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=primary_category,
                published=published,
                updated=updated,
                abs_url=abs_url,
                pdf_url=pdf_url,
                comment=comment,
            )
        )

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch records from Crossref API, save raw response, parse into records.

    Steps:
    1. Build query params from settings.
    2. Call API with retry for 429/503 status codes.
    3. Save raw response to settings.paths.raw_api_response.
    4. Parse payload with parse_crossref_payload.
    5. Save records to settings.paths.raw_records_json.
    """
    params: dict[str, Any] = {
        "query": settings.source_query,
        "rows": settings.max_results,
        "filter": settings.source_filter,
        "sort": "relevance",
        "order": "desc",
    }

    # Retry logic for transient errors
    max_retries = 3
    backoff_seconds = 2.0
    response = None

    for attempt in range(max_retries):
        try:
            response = requests.get(
                CROSSREF_API_URL,
                params=params,
                headers={"User-Agent": "DataPipelineLab/1.0 (mailto:student@example.com)"},
                timeout=30,
            )
            if response.status_code == 200:
                break
            if response.status_code in (429, 503):
                wait = backoff_seconds * (2 ** attempt)
                print(f"[crossref] Rate limited ({response.status_code}), retrying in {wait:.1f}s...")
                time.sleep(wait)
                continue
            response.raise_for_status()
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                wait = backoff_seconds * (2 ** attempt)
                print(f"[crossref] Timeout, retrying in {wait:.1f}s...")
                time.sleep(wait)
            else:
                raise

    if response is None or response.status_code != 200:
        raise RuntimeError(f"Failed to fetch from Crossref after {max_retries} attempts.")

    payload = response.json()

    # Save raw API response
    ensure_parent(settings.paths.raw_api_response)
    settings.paths.raw_api_response.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # Parse records
    records = parse_crossref_payload(payload)

    # Save parsed records as JSON
    records_data = [asdict(r) for r in records]
    write_json(settings.paths.raw_records_json, records_data)

    print(f"[crossref] Fetched {len(records)} records from Crossref API.")
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load previously saved raw records from JSON file and map to PaperRecord."""
    data = read_json(path)
    records: list[PaperRecord] = []
    for item in data:
        records.append(
            PaperRecord(
                paper_id=item["paper_id"],
                title=item["title"],
                summary=item["summary"],
                authors=item["authors"],
                categories=item["categories"],
                primary_category=item["primary_category"],
                published=item["published"],
                updated=item["updated"],
                abs_url=item["abs_url"],
                pdf_url=item["pdf_url"],
                comment=item["comment"],
            )
        )
    return records
