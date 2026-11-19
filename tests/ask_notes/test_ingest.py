import os
import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api import app
from app.ask_notes.ingest import ingest_note
from app.ask_notes.setup_db import setup_db
from app.core.db import connect
from app.semantic_search.extraction.schema import Injury

# These tests need a real Postgres (docker compose up -d). Without DATABASE_URL they are skipped.
pytestmark = pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="needs DATABASE_URL (docker compose up -d)")

FIELDS = Injury(injury="sprain", body_part="ankle", severity=6, cause="curb", date="2026-04-02")
MODEL = "nomic-embed-text"


@pytest.fixture
def calls(monkeypatch: pytest.MonkeyPatch) -> Iterator[dict[str, int]]:
    """Fake models that count their calls, and a unique user whose rows are deleted after the test."""
    counts = {"extract": 0, "embed": 0}

    def fake_extract(text: str) -> Injury:
        counts["extract"] += 1
        return FIELDS

    def fake_embed(texts: list[str], model: str) -> list[list[float]]:
        counts["embed"] += 1
        return [[1.0] + [0.0] * 767 for _ in texts]

    monkeypatch.setattr("app.ask_notes.ingest.extract", fake_extract)
    monkeypatch.setattr("app.ask_notes.ingest.embed_documents", fake_embed)
    monkeypatch.setenv("EMBED_MODEL", MODEL)
    setup_db()
    yield counts
    with connect() as conn:
        conn.execute("DELETE FROM notes WHERE user_id LIKE 'test-%' OR text LIKE '%test-run-%'")


def long_note() -> str:
    return f"test-run-{uuid.uuid4()}. " + "I rolled my left ankle on the curb. It swelled up a lot. " * 30


def chunk_count(note_id: int) -> int:
    with connect() as conn:
        row = conn.execute("SELECT count(*) FROM chunks WHERE note_id = %s", (note_id,)).fetchone()
    assert row is not None
    return int(row[0])


def test_saves_note_fields_and_chunks(calls: dict[str, int]) -> None:
    result = ingest_note(long_note(), MODEL, user_id=f"test-{uuid.uuid4()}")
    assert result.created and result.chunks > 1
    assert chunk_count(result.note_id) == result.chunks
    with connect() as conn:
        row = conn.execute("SELECT body_part, severity, note_date::text FROM notes WHERE id = %s", (result.note_id,)).fetchone()
    assert row == ("ankle", 6, "2026-04-02")


def test_saving_twice_does_not_duplicate(calls: dict[str, int]) -> None:
    text, user = long_note(), f"test-{uuid.uuid4()}"
    first = ingest_note(text, MODEL, user_id=user)
    second = ingest_note(text, MODEL, user_id=user)
    assert second.note_id == first.note_id
    assert not second.created
    assert chunk_count(first.note_id) == first.chunks
    assert calls == {"extract": 1, "embed": 1}  # the second save made no model calls


def test_bad_date_from_the_model_is_saved_as_empty(calls: dict[str, int], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.ask_notes.ingest.extract", lambda text: FIELDS.model_copy(update={"date": "last spring"}))
    result = ingest_note(long_note(), MODEL, user_id=f"test-{uuid.uuid4()}")
    with connect() as conn:
        row = conn.execute("SELECT note_date FROM notes WHERE id = %s", (result.note_id,)).fetchone()
    assert row == (None,)


def test_post_notes_endpoint(calls: dict[str, int]) -> None:
    client = TestClient(app)
    text = long_note()
    first = client.post("/notes", json={"text": text})
    again = client.post("/notes", json={"text": text})
    assert first.status_code == 200 and first.json()["created"] is True
    assert again.json() == {**first.json(), "created": False}


@pytest.mark.parametrize("body", [{"text": ""}, {"text": "   \n  "}, {"text": "x" * 20_001}, {}])
def test_post_notes_rejects_bad_input(body: dict[str, str]) -> None:
    assert TestClient(app).post("/notes", json=body).status_code == 422
