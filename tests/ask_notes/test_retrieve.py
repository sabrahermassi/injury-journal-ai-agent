import os
import uuid
from collections.abc import Iterator
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.api import app
from app.ask_notes.retrieve import like_pattern, retrieve
from app.ask_notes.setup_db import setup_db
from app.core.db import connect
from app.semantic_search.search import SearchFilters

# These tests need a real Postgres (docker compose up -d). Without DATABASE_URL they are skipped.
pytestmark = pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="needs DATABASE_URL (docker compose up -d)")

MODEL = "nomic-embed-text"


def vector(x: float, y: float) -> list[float]:
    """A 768-number vector pointing in direction (x, y): close directions = close meaning."""
    return [x, y] + [0.0] * 766


# Each test note: (chunk text, its vector, body part, severity, date)
NOTES = [
    ("knee pain after running", vector(1.0, 0.0), "right knee", 4, date(2026, 3, 3)),
    ("knee swollen after the hike", vector(0.9, 0.1), "knee", 3, date(2026, 7, 5)),
    ("lower back hurts when bending", vector(0.5, 0.5), "lower back", 5, date(2026, 3, 9)),
    ("cut finger chopping onions", vector(0.0, 1.0), "finger", 3, date(2026, 3, 14)),
    ("ankle sprain, no date", vector(0.8, 0.2), "left ankle", 8, None),
]


@pytest.fixture
def user(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    """A unique user with the test notes saved, and the question embedding faked to point at 'knee'."""
    monkeypatch.setattr("app.ask_notes.retrieve.embed_query", lambda text, model: vector(1.0, 0.0))
    monkeypatch.setenv("EMBED_MODEL", MODEL)
    setup_db()
    user_id = f"test-{uuid.uuid4()}"
    with connect() as conn:
        for text, vec, body_part, severity, note_date in NOTES:
            row = conn.execute(
                "INSERT INTO notes (user_id, content_hash, text, body_part, severity, note_date)"
                " VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
                (user_id, str(uuid.uuid4()), text, body_part, severity, note_date),
            ).fetchone()
            assert row is not None
            conn.execute(
                "INSERT INTO chunks (note_id, position, start_offset, end_offset, text, embedding, embed_model)"
                " VALUES (%s, 0, 0, %s, %s, %s::vector, %s)",
                (row[0], len(text), text, str(vec), MODEL),
            )
    yield user_id
    with connect() as conn:
        conn.execute("DELETE FROM notes WHERE user_id = %s", (user_id,))


def texts(user_id: str, filters: SearchFilters | None = None, top_k: int = 5) -> list[str]:
    return [chunk.text for chunk in retrieve("knee", MODEL, filters, top_k, user_id=user_id)]


def test_closest_chunks_come_first(user: str) -> None:
    chunks = retrieve("knee", MODEL, top_k=3, user_id=user)
    assert [c.text for c in chunks] == ["knee pain after running", "knee swollen after the hike", "ankle sprain, no date"]
    assert chunks[0].score == pytest.approx(1.0)
    assert chunks[0].score >= chunks[1].score >= chunks[2].score


def test_top_k_limits_the_results(user: str) -> None:
    assert len(texts(user, top_k=2)) == 2
    assert len(texts(user, top_k=20)) == 5


def test_body_part_filter_ignores_case_and_matches_part_of_the_name(user: str) -> None:
    assert texts(user, SearchFilters(body_part="KNEE")) == ["knee pain after running", "knee swollen after the hike"]


def test_severity_filter(user: str) -> None:
    assert texts(user, SearchFilters(min_severity=5)) == ["ankle sprain, no date", "lower back hurts when bending"]


def test_date_filter_drops_notes_without_a_date(user: str) -> None:
    filters = SearchFilters(date_from=date(2026, 3, 1), date_to=date(2026, 3, 31))
    assert texts(user, filters) == ["knee pain after running", "lower back hurts when bending", "cut finger chopping onions"]


def test_other_users_chunks_are_never_returned(user: str) -> None:
    assert texts(f"test-{uuid.uuid4()}") == []


def test_other_embed_model_is_ignored(user: str) -> None:
    assert retrieve("knee", "another-model", user_id=user) == []


def test_percent_sign_in_a_filter_is_not_a_wildcard(user: str) -> None:
    assert like_pattern("50%_x") == "%50\\%\\_x%"
    assert texts(user, SearchFilters(body_part="%")) == []


def test_top_k_must_be_positive() -> None:
    with pytest.raises(ValueError):
        retrieve("knee", MODEL, top_k=0)


def test_retrieve_endpoint(user: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.ask_notes.router.retrieve", lambda q, m, f, k: retrieve(q, m, f, k, user_id=user))
    client = TestClient(app)
    response = client.post("/retrieve", json={"question": "knee", "filters": {"body_part": "knee"}, "top_k": 1})
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1 and body[0]["text"] == "knee pain after running" and body[0]["note_date"] == "2026-03-03"
    assert client.post("/retrieve", json={"question": "knee", "top_k": 0}).status_code == 422
    assert client.post("/retrieve", json={"question": "  "}).status_code == 422
