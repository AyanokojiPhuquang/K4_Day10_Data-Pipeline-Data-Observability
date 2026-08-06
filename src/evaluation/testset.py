from __future__ import annotations

from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json

_MIN_DOCUMENTS = 3
_QUESTION_TYPES = ("summary", "authors", "date", "categories")


def _build_question(question_type: str, title: str) -> str:
    if question_type == "summary":
        return f"What is the paper '{title}' about?"
    if question_type == "authors":
        return f"Who authored the paper '{title}'?"
    if question_type == "date":
        return f"When was the paper '{title}' published?"
    if question_type == "categories":
        return f"What categories does the paper '{title}' belong to?"
    raise ValueError(f"Unsupported question_type: {question_type}")


def _ground_truth(question_type: str, row: pd.Series) -> str:
    if question_type == "summary":
        return first_sentence(row["summary"])
    if question_type == "authors":
        return row["authors_joined"]
    if question_type == "date":
        return row["published"]
    if question_type == "categories":
        return row["categories_joined"]
    raise ValueError(f"Unsupported question_type: {question_type}")


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Build a question/ground-truth evaluation set from the cleaned dataframe."""
    if len(df) < _MIN_DOCUMENTS:
        raise ValueError(f"Need at least {_MIN_DOCUMENTS} clean documents to build a test set, got {len(df)}.")

    samples: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        for question_type in _QUESTION_TYPES:
            ground_truth = _ground_truth(question_type, row)
            if not ground_truth:
                continue
            samples.append(
                {
                    "id": f"q_{len(samples) + 1:03d}",
                    "question_type": question_type,
                    "question": _build_question(question_type, row["title"]),
                    "ground_truth": ground_truth,
                    "ground_truth_doc_ids": [row["paper_id"]],
                }
            )

    write_json(output_path, samples)
    return samples
