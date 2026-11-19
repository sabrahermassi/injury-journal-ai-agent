"""Save a note: extract its fields, chunk it, embed the chunks and store everything in Postgres."""

import hashlib
import logging
from datetime import date

from pydantic import BaseModel, ValidationError

from app.ask_notes.chunker import chunk_note
from app.core.db import connect
from app.core.embed import embed_documents
from app.semantic_search.extraction.extract import extract
from app.semantic_search.extraction.schema import Injury

logger = logging.getLogger(__name__)


class IngestResult(BaseModel):
    note_id: int
    chunks: int
    created: bool  # False when the same note was already saved with all its chunks


def content_hash(text: str) -> str:
    """Fingerprint of the note's text: the same text always gives the same hash."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_date(value: str | None) -> date | None:
    """The model's date as a real date, or None if it is missing or not YYYY-MM-DD."""
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None


def ingest_note(text: str, embed_model: str, user_id: str = "demo") -> IngestResult:
    """Save one note and its chunks. Saving the same text again changes nothing (upsert)."""
    note_hash = content_hash(text)

    # 1. Already saved with its chunks? Then skip the slow model calls entirely.
    with connect() as conn:
        row = conn.execute(
            "SELECT n.id, count(c.id) FROM notes n LEFT JOIN chunks c ON c.note_id = n.id AND c.embed_model = %s"
            " WHERE n.user_id = %s AND n.content_hash = %s GROUP BY n.id",
            (embed_model, user_id, note_hash),
        ).fetchone()
    if row is not None and row[1] > 0:
        return IngestResult(note_id=row[0], chunks=row[1], created=False)

    # 2. The slow part, outside any transaction: extract fields, chunk, embed.
    try:
        fields = extract(text)
    except ValidationError:
        fields = Injury(injury=None, body_part=None, severity=None, cause=None, date=None)
        logger.warning("extraction failed, note saved without fields (hash %s)", note_hash[:12])
    chunks = chunk_note(0, text)  # note id is set below, once Postgres gives one
    vectors = embed_documents([chunk.text for chunk in chunks], embed_model)

    # 3. One transaction: the note and all its chunks are saved together, or nothing is.
    with connect() as conn:
        note_row = conn.execute(
            "INSERT INTO notes (user_id, content_hash, text, injury, body_part, severity, cause, note_date)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
            " ON CONFLICT (user_id, content_hash) DO UPDATE SET content_hash = EXCLUDED.content_hash"
            " RETURNING id",
            (user_id, note_hash, text, fields.injury, fields.body_part, fields.severity, fields.cause,
             parse_date(fields.date)),
        ).fetchone()
        assert note_row is not None
        note_id = int(note_row[0])
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO chunks (note_id, position, start_offset, end_offset, text, embedding, embed_model)"
                " VALUES (%s, %s, %s, %s, %s, %s::vector, %s)"
                " ON CONFLICT (note_id, position, embed_model) DO NOTHING",
                [
                    (note_id, c.position, c.start, c.end, c.text, str(vector), embed_model)
                    for c, vector in zip(chunks, vectors, strict=True)
                ],
            )
    logger.info("note %s saved with %s chunks", note_id, len(chunks))
    return IngestResult(note_id=note_id, chunks=len(chunks), created=True)


class Note(BaseModel):
    id: int
    text: str
    body_part: str | None
    severity: int | None
    note_date: date | None


def get_note(note_id: int, user_id: str = "demo") -> Note | None:
    """One saved note of this user, for showing a citation in its full note. None if it isn't theirs."""
    with connect() as conn:
        row = conn.execute(
            "SELECT id, text, body_part, severity, note_date FROM notes WHERE id = %s AND user_id = %s",
            (note_id, user_id),
        ).fetchone()
    if row is None:
        return None
    return Note(id=row[0], text=row[1], body_part=row[2], severity=row[3], note_date=row[4])
