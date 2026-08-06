from __future__ import annotations

from dataclasses import dataclass
import re

from core.config import Settings
from core.utils import first_sentence
from retrieval.index import LocalEmbeddingIndex, SearchResult


@dataclass(frozen=True)
class AnswerResult:
    question: str
    answer: str
    retrieved_doc_ids: list[str]
    retrieved_contexts: list[str]
    retrieved_titles: list[str]


def _extract_answer(question: str, top_result: SearchResult) -> str:
    lowered = question.lower()
    metadata = top_result.metadata

    # 1. Asking which paper an author wrote
    if any(p in lowered for p in ["bài báo nào", "which paper", "what paper", "tác giả của"]):
        return f"'{metadata['title']}' (DOI: {metadata['paper_id']})"

    # 2. Asking for authors list
    if any(p in lowered for p in ["who authored", "list the authors", "ai là tác giả", "tác giả là ai", "authors"]):
        return metadata["authors_joined"]

    # 3. Asking for publication date
    if any(p in lowered for p in ["when was", "publication date", "published on", "ngày xuất bản", "xuất bản khi nào"]):
        return metadata["published"]

    # 4. Asking for categories
    if any(p in lowered for p in ["what categories", "danh mục nào", "thuộc thể loại"]):
        return metadata["categories_joined"]

    # 5. Default: Summary first sentence or title fallback if summary is empty
    summary = metadata.get("summary", "").strip()
    if summary:
        return first_sentence(summary)
    return metadata["title"]


def _lookup_by_author(question: str, index: LocalEmbeddingIndex) -> SearchResult | None:
    """Look up an exact author name matching any document's authors_joined metadata."""
    lowered_q = question.lower()
    for doc in index.documents:
        authors_joined = str(doc.get("metadata", {}).get("authors_joined", "")).lower()
        if not authors_joined or authors_joined == "unknown":
            continue
        for author in authors_joined.split(","):
            author_name = author.strip()
            if len(author_name) > 3 and author_name in lowered_q:
                return SearchResult(
                    paper_id=doc["paper_id"],
                    title=doc["title"],
                    score=1.0,
                    content=doc["content"],
                    metadata=doc["metadata"],
                )
    return None


def answer_question(question: str, settings: Settings, index: LocalEmbeddingIndex, top_k: int | None = None) -> AnswerResult:
    # 1. Check title match in quotes
    title_match = re.search(r"'([^']+)'", question)
    exact = index.lookup(title_match.group(1)) if title_match else None

    # 2. Check author match in question
    author_exact = _lookup_by_author(question, index) if not exact else None

    retrieved = index.search(question, top_k=top_k)

    if exact:
        exact_result = SearchResult(
            paper_id=exact["paper_id"],
            title=exact["title"],
            score=1.0,
            content=exact["content"],
            metadata=exact["metadata"],
        )
        deduped = [exact_result] + [item for item in retrieved if item.paper_id != exact_result.paper_id]
        retrieved = deduped[: (top_k or settings.top_k)]
    elif author_exact:
        deduped = [author_exact] + [item for item in retrieved if item.paper_id != author_exact.paper_id]
        retrieved = deduped[: (top_k or settings.top_k)]

    score_threshold = 0.20
    is_exact_match = bool(exact or author_exact)

    if not retrieved or (retrieved[0].score < score_threshold and not is_exact_match):
        answer = "I don't know from the indexed corpus. No sufficiently relevant paper was found in the indexed dataset."
    else:
        answer = _extract_answer(question, retrieved[0])

    return AnswerResult(
        question=question,
        answer=answer,
        retrieved_doc_ids=[item.paper_id for item in retrieved],
        retrieved_contexts=[item.content for item in retrieved],
        retrieved_titles=[item.title for item in retrieved],
    )
