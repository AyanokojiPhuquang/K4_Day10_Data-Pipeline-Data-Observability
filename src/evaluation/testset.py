from __future__ import annotations

import json
import random
from typing import Any

import pandas as pd

from core.utils import ensure_parent, first_sentence


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Build an evaluation test set from the cleaned dataframe.

    Steps:
    1. Check minimum document count.
    2. Select representative papers.
    3. Generate multiple question types: summary, authors, date, categories.
    4. Each row has: id, question_type, question, ground_truth, ground_truth_doc_ids.
    5. Write JSON to output_path.
    """
    if len(df) < 3:
        raise ValueError(f"Need at least 3 documents to build test set, got {len(df)}.")

    test_items: list[dict[str, Any]] = []
    item_id = 0

    # Use all papers to maximize coverage
    for _, row in df.iterrows():
        paper_id = row["paper_id"]
        title = row["title"]
        summary = row["summary"]
        authors_joined = row["authors_joined"]
        published = row["published"]
        categories_joined = row["categories_joined"]

        # Summary question
        if summary:
            item_id += 1
            test_items.append(
                {
                    "id": f"q_{item_id:03d}",
                    "question_type": "summary",
                    "question": f"What is the main topic of the paper '{title}'?",
                    "ground_truth": first_sentence(summary),
                    "ground_truth_doc_ids": [paper_id],
                }
            )

        # Authors question
        if authors_joined:
            item_id += 1
            test_items.append(
                {
                    "id": f"q_{item_id:03d}",
                    "question_type": "authors",
                    "question": f"Who authored the paper '{title}'?",
                    "ground_truth": authors_joined,
                    "ground_truth_doc_ids": [paper_id],
                }
            )

        # Date question
        if published:
            item_id += 1
            test_items.append(
                {
                    "id": f"q_{item_id:03d}",
                    "question_type": "date",
                    "question": f"When was the paper '{title}' published?",
                    "ground_truth": published,
                    "ground_truth_doc_ids": [paper_id],
                }
            )

        # Categories question
        if categories_joined:
            item_id += 1
            test_items.append(
                {
                    "id": f"q_{item_id:03d}",
                    "question_type": "categories",
                    "question": f"What categories does the paper '{title}' belong to?",
                    "ground_truth": categories_joined,
                    "ground_truth_doc_ids": [paper_id],
                }
            )

    # Shuffle for variety
    random.seed(42)
    random.shuffle(test_items)

    # Save to output path
    ensure_parent(output_path)
    output_path.write_text(
        json.dumps(test_items, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"[testset] Generated {len(test_items)} evaluation questions from {len(df)} papers.")
    return test_items
