from datetime import date

from pydantic import BaseModel, Field

from app.core.embed import embed_query
from app.core.similarity import cosine_similarity
from app.semantic_search.extraction.schema import Injury
from app.semantic_search.store import NoteRecord

# Results scoring below this are not returned. Chosen by the threshold experiment
# (python -m app.embedding.threshold): keeps all 12 injury questions, blocks 23 of 28 off-topic.
MIN_SCORE = 0.54


class SearchFilters(BaseModel):
    body_part: str | None = None
    min_severity: int | None = Field(default=None, ge=1, le=10)
    date_from: date | None = None
    date_to: date | None = None


class SearchResult(BaseModel):
    id: str
    text: str
    fields: Injury
    score: float


def matches(record: NoteRecord, filters: SearchFilters) -> bool:
    """True if the note's extracted fields pass every filter that is set."""
    fields = record.fields
    if filters.body_part is not None:
        if fields.body_part is None or filters.body_part.lower() not in fields.body_part.lower():
            return False
    if filters.min_severity is not None:
        if fields.severity is None or fields.severity < filters.min_severity:
            return False
    if filters.date_from is not None or filters.date_to is not None:
        note_date = parse_date(fields.date)
        if note_date is None:
            return False
        if filters.date_from is not None and note_date < filters.date_from:
            return False
        if filters.date_to is not None and note_date > filters.date_to:
            return False
    return True


def parse_date(text: str | None) -> date | None:
    """The note's date as a real date, or None if it's missing or not YYYY-MM-DD."""
    if text is None:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def search(
    query: str,
    records: list[NoteRecord],
    embed_model: str,
    filters: SearchFilters | None = None,
    top_k: int = 5,
    min_score: float = MIN_SCORE,
) -> list[SearchResult]:
    """Hybrid search: filter by the extracted fields, then rank by meaning (cosine)."""
    if top_k < 0:
        raise ValueError(f"top_k must be 0 or more, got {top_k}")
    filters = filters or SearchFilters()

    # 1. Filter: only notes made with this model that pass the field filters.
    candidates = [record for record in records if record.embed_model == embed_model and matches(record, filters)]
    if not candidates:
        return []

    # 2. Embed the question (with the search_query prefix). Not saved.
    query_vector = embed_query(query, embed_model)

    # 3. Score every candidate and drop the ones below the threshold.
    results = [
        SearchResult(id=record.id, text=record.text, fields=record.fields, score=cosine_similarity(query_vector, record.vector))
        for record in candidates
    ]
    results = [result for result in results if result.score >= min_score]

    # 4. Sort best first, 5. keep the top k.
    results.sort(key=lambda result: result.score, reverse=True)
    return results[:top_k]
