"""Find the chunks closest in meaning to a question, with the same field filters as Project 1."""

from datetime import date

from pydantic import BaseModel

from app.core.db import connect
from app.core.embed import embed_query
from app.semantic_search.search import SearchFilters


class RetrievedChunk(BaseModel):
    chunk_id: int
    note_id: int
    position: int
    start: int  # where the chunk sits in the note's text, for highlighting the citation
    end: int
    text: str
    score: float  # cosine similarity: 1 = same meaning, 0 = unrelated
    body_part: str | None
    severity: int | None
    note_date: date | None


def like_pattern(text: str) -> str:
    """'knee' -> '%knee%', with % and _ escaped so they match themselves, not anything."""
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


# Step 1 (eligible) keeps only this user's chunks that pass the filters. MATERIALIZED makes Postgres
# finish that step first, so step 2 ranks every eligible chunk exactly. Without it, Postgres can use the
# HNSW index, which looks at only ~40 nearest chunks and filters afterwards: if those belong to other users
# or fail the filters, you get fewer than top_k results, or none.
SQL = """
WITH eligible AS MATERIALIZED (
    SELECT c.id, c.note_id, c.position, c.start_offset, c.end_offset, c.text, c.embedding,
           n.body_part, n.severity, n.note_date
    FROM chunks c
    JOIN notes n ON n.id = c.note_id
    WHERE n.user_id = %(user_id)s
      AND c.embed_model = %(embed_model)s
      AND (%(body_part)s::text IS NULL OR n.body_part ILIKE %(body_part)s)
      AND (%(min_severity)s::int IS NULL OR n.severity >= %(min_severity)s)
      AND (%(date_from)s::date IS NULL OR n.note_date >= %(date_from)s)
      AND (%(date_to)s::date IS NULL OR n.note_date <= %(date_to)s)
)
SELECT id, note_id, position, start_offset, end_offset, text,
       1 - (embedding <=> %(question)s::vector) AS score,
       body_part, severity, note_date
FROM eligible
ORDER BY embedding <=> %(question)s::vector
LIMIT %(top_k)s
"""


def retrieve(
    question: str,
    embed_model: str,
    filters: SearchFilters | None = None,
    top_k: int = 5,
    user_id: str = "demo",
) -> list[RetrievedChunk]:
    """Question in, the top_k closest chunks out, best first. Filters are applied inside the same SQL query."""
    if top_k < 1:
        raise ValueError(f"top_k must be 1 or more, got {top_k}")
    filters = filters or SearchFilters()
    question_vector = embed_query(question, embed_model)
    params = {
        "question": str(question_vector),
        "user_id": user_id,
        "embed_model": embed_model,
        "body_part": like_pattern(filters.body_part) if filters.body_part else None,
        "min_severity": filters.min_severity,
        "date_from": filters.date_from,
        "date_to": filters.date_to,
        "top_k": top_k,
    }
    with connect() as conn:
        rows = conn.execute(SQL, params).fetchall()
    return [
        RetrievedChunk(
            chunk_id=row[0], note_id=row[1], position=row[2], start=row[3], end=row[4], text=row[5],
            score=float(row[6]), body_part=row[7], severity=row[8], note_date=row[9],
        )
        for row in rows
    ]
