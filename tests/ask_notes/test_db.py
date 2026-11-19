import os
import uuid
from collections.abc import Iterator

import psycopg
import pytest

from app.ask_notes.setup_db import setup_db
from app.core.db import connect

# These tests need a real Postgres (docker compose up -d). Without DATABASE_URL they are skipped.
pytestmark = pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="needs DATABASE_URL (docker compose up -d)")


def vector(*first: float) -> list[float]:
    """A 768-number vector: the given numbers first, then zeros."""
    return list(first) + [0.0] * (768 - len(first))


def unique_hash() -> str:
    """A new hash every run, so rows already in the database can never clash with a test."""
    return f"test-{uuid.uuid4()}"


@pytest.fixture
def conn() -> Iterator[psycopg.Connection]:
    """A connection whose changes are rolled back, so tests never leave data behind."""
    setup_db()
    with connect() as connection:
        yield connection
        connection.rollback()


def add_note(conn: psycopg.Connection, text: str, content_hash: str | None = None) -> int:
    row = conn.execute(
        "INSERT INTO notes (content_hash, text, body_part, severity) VALUES (%s, %s, %s, %s) RETURNING id",
        (content_hash or unique_hash(), text, "knee", 5),
    ).fetchone()
    assert row is not None
    return int(row[0])


def add_chunk(conn: psycopg.Connection, note_id: int, position: int, text: str, embedding: list[float]) -> None:
    conn.execute(
        "INSERT INTO chunks (note_id, position, start_offset, end_offset, text, embedding, embed_model)"
        " VALUES (%s, %s, %s, %s, %s, %s::vector, %s)",
        (note_id, position, 0, len(text), text, str(embedding), "nomic-embed-text"),
    )


def test_closest_chunks_come_first(conn: psycopg.Connection) -> None:
    note_id = add_note(conn, "knee pain after running")
    add_chunk(conn, note_id, 0, "knee pain", vector(1.0, 0.0))
    add_chunk(conn, note_id, 1, "after running", vector(0.7, 0.7))
    add_chunk(conn, note_id, 2, "cut finger", vector(0.0, 1.0))

    # <=> is pgvector's cosine distance: 0 = same direction, so smallest first = most similar first.
    rows = conn.execute(
        "SELECT text FROM chunks WHERE note_id = %s ORDER BY embedding <=> %s::vector LIMIT 2",
        (note_id, str(vector(1.0, 0.0))),
    ).fetchall()
    assert [row[0] for row in rows] == ["knee pain", "after running"]


def test_same_note_cannot_be_saved_twice(conn: psycopg.Connection) -> None:
    content_hash = unique_hash()
    add_note(conn, "sore neck", content_hash)
    with pytest.raises(psycopg.errors.UniqueViolation):
        add_note(conn, "sore neck", content_hash)


def test_two_users_can_save_the_same_note(conn: psycopg.Connection) -> None:
    content_hash = unique_hash()
    for user in ("alice", "bob"):
        conn.execute(
            "INSERT INTO notes (user_id, content_hash, text) VALUES (%s, %s, %s)",
            (user, content_hash, "knee pain"),
        )
    row = conn.execute("SELECT count(*) FROM notes WHERE content_hash = %s", (content_hash,)).fetchone()
    assert row is not None and row[0] == 2


def test_deleting_a_note_deletes_its_chunks(conn: psycopg.Connection) -> None:
    note_id = add_note(conn, "sore shoulder")
    add_chunk(conn, note_id, 0, "sore shoulder", vector(1.0))
    conn.execute("DELETE FROM notes WHERE id = %s", (note_id,))
    row = conn.execute("SELECT count(*) FROM chunks WHERE note_id = %s", (note_id,)).fetchone()
    assert row is not None and row[0] == 0


def test_severity_must_be_between_1_and_10(conn: psycopg.Connection) -> None:
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute("INSERT INTO notes (content_hash, text, severity) VALUES (%s, 'x', 11)", (unique_hash(),))
