import json
import os
import uuid
from collections.abc import Generator, Iterator
from datetime import date
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api import app
from app.ask_notes.answer import MIN_SCORE, NOT_FOUND, REFUSAL
from app.ask_notes.retrieve import RetrievedChunk
from app.ask_notes.setup_db import setup_db
from app.ask_notes.stream import answer_so_far, ask_stream
from app.core.db import connect
from app.core.model_call import ModelUnavailableError

NOTE = "Saw Dr. Lambert about the ankle. She said no X-ray was needed because I could take four steps."
CHUNKS = [
    RetrievedChunk(
        chunk_id=7, note_id=70, position=0, start=100, end=100 + len(NOTE), text=NOTE,
        score=0.9, body_part="ankle", severity=6, note_date=date(2026, 4, 6),
    )
]
GOOD = json.dumps(
    {"found": True, "quotes": [{"chunkId": 1, "text": "She said no X-ray was needed"}], "answer": 'No "X-ray" was needed.'}
)
INVENTED = json.dumps({"found": True, "quotes": [{"chunkId": 1, "text": "She ordered an MRI"}], "answer": "An MRI."})


def in_pieces(text: str, size: int = 3) -> Iterator[str]:
    """A reply cut into small pieces, like a model streaming it."""
    return (text[i : i + size] for i in range(0, len(text), size))


@pytest.fixture
def replies(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Fake retrieve (always CHUNKS) and a fake streaming model; each test fills in its replies."""
    queue: list[str] = []
    monkeypatch.setattr("app.ask_notes.answer.retrieve", lambda q, m, f, k, u: CHUNKS)
    monkeypatch.setattr("app.ask_notes.stream.chat_stream", lambda messages: in_pieces(queue.pop(0)))
    monkeypatch.setenv("EMBED_MODEL", "nomic-embed-text")
    return queue


def events_of(question: str = "Did I need an X-ray?") -> list[dict[str, Any]]:
    return list(ask_stream(question, "nomic-embed-text"))


def shown_answer(events: list[dict[str, Any]]) -> str:
    """What the page would show: answer pieces added up, emptied by each reset."""
    text = ""
    for event in events:
        if event["type"] == "answer":
            text += event["text"]
        elif event["type"] == "reset":
            text = ""
    return text


# --- reading the answer out of half-written JSON ---


def test_no_answer_field_yet() -> None:
    assert answer_so_far('{"found": true, "quotes": [') == ""


def test_answer_cut_in_the_middle() -> None:
    assert answer_so_far('{"quotes": [], "answer": "The doctor sa') == "The doctor sa"


def test_finished_answer_stops_at_its_closing_quote() -> None:
    assert answer_so_far('{"answer": "No X-ray.", "found": true}') == "No X-ray."


def test_escapes_are_decoded_and_a_cut_off_escape_waits() -> None:
    assert answer_so_far('{"answer": "a \\"b\\" \\u00e9') == 'a "b" é'
    assert answer_so_far('{"answer": "a \\') == "a "
    assert answer_so_far('{"answer": "a \\u00') == "a "


# --- the event stream ---


def test_good_answer_streams_then_ends_with_the_checked_result(replies: list[str]) -> None:
    replies.append(GOOD)
    events = events_of()
    assert events[0] == {"type": "status", "text": "Checking the question"}
    assert events[1] == {"type": "status", "text": "Searching your notes"}
    assert shown_answer(events) == 'No "X-ray" was needed.'
    done = events[-1]
    assert done["type"] == "done" and done["result"]["refused"] is False
    citation = done["result"]["citations"][0]
    assert NOTE[citation["start"] - 100 : citation["end"] - 100] == "She said no X-ray was needed"  # exact quote offsets


def test_bad_quote_resets_the_answer_and_retries(replies: list[str]) -> None:
    replies.extend([INVENTED, GOOD])
    events = events_of()
    assert {"type": "reset"} in events
    assert shown_answer(events) == 'No "X-ray" was needed.'
    assert events[-1]["result"]["refused"] is False


def test_bad_quote_twice_ends_in_refusal(replies: list[str]) -> None:
    replies.extend([INVENTED, INVENTED])
    events = events_of()
    assert shown_answer(events) == ""
    assert events[-1]["result"] == {"answer": REFUSAL, "citations": [], "refused": True, "scope": "in_scope"}


def test_weak_chunks_end_in_not_found_without_the_model(monkeypatch: pytest.MonkeyPatch) -> None:
    weak = [CHUNKS[0].model_copy(update={"score": MIN_SCORE - 0.01})]
    monkeypatch.setattr("app.ask_notes.answer.retrieve", lambda q, m, f, k, u: weak)
    monkeypatch.setattr("app.ask_notes.stream.chat_stream", lambda messages: pytest.fail("model should not be called"))
    assert events_of()[-1]["result"]["answer"] == NOT_FOUND


def test_model_saying_not_found(replies: list[str]) -> None:
    replies.append(json.dumps({"found": False, "answer": "", "quotes": []}))
    assert events_of()[-1]["result"]["answer"] == NOT_FOUND


def test_stopping_early_closes_the_model_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    closed = []

    def model_stream(messages: list[dict[str, str]]) -> Generator[str, None, None]:
        try:
            yield from in_pieces(GOOD)
        finally:
            closed.append(True)  # what stops Ollama in the real chat_stream

    monkeypatch.setattr("app.ask_notes.answer.retrieve", lambda q, m, f, k, u: CHUNKS)
    monkeypatch.setattr("app.ask_notes.stream.chat_stream", model_stream)
    events = ask_stream("Did I need an X-ray?", "nomic-embed-text")
    for event in events:
        if event["type"] == "answer":
            break  # the user leaves after the first words
    events.close()
    assert closed == [True]


# --- the HTTP endpoint ---


def sse_events(text: str) -> list[dict[str, Any]]:
    return [json.loads(line[len("data: ") :]) for line in text.splitlines() if line.startswith("data: ")]


def test_stream_endpoint_sends_server_sent_events(replies: list[str]) -> None:
    replies.append(GOOD)
    response = TestClient(app).post("/ask/stream", json={"question": "Did I need an X-ray?"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = sse_events(response.text)
    assert events[-1]["type"] == "done" and shown_answer(events) == 'No "X-ray" was needed.'


def test_model_down_sends_an_error_event(monkeypatch: pytest.MonkeyPatch) -> None:
    def down(messages: list[dict[str, str]]) -> Iterator[str]:
        raise ModelUnavailableError("The language model is not responding. Is Ollama running?")

    monkeypatch.setattr("app.ask_notes.answer.retrieve", lambda q, m, f, k, u: CHUNKS)
    monkeypatch.setattr("app.ask_notes.stream.chat_stream", down)
    monkeypatch.setenv("EMBED_MODEL", "nomic-embed-text")
    events = sse_events(TestClient(app).post("/ask/stream", json={"question": "knee"}).text)
    assert events[-1] == {"type": "error", "message": "The language model is not responding. Is Ollama running?"}


# --- one full note, for the citation view (needs Postgres) ---


@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="needs DATABASE_URL (docker compose up -d)")
def test_get_note_returns_the_users_note_only() -> None:
    setup_db()
    with connect() as conn:
        mine = conn.execute(
            "INSERT INTO notes (content_hash, text) VALUES (%s, 'test-run note') RETURNING id", (str(uuid.uuid4()),)
        ).fetchone()
        theirs = conn.execute(
            "INSERT INTO notes (user_id, content_hash, text) VALUES ('test-other', %s, 'x') RETURNING id",
            (str(uuid.uuid4()),),
        ).fetchone()
    assert mine is not None and theirs is not None
    try:
        client = TestClient(app)
        response = client.get(f"/notes/{mine[0]}")
        assert response.status_code == 200 and response.json()["text"] == "test-run note"
        assert client.get(f"/notes/{theirs[0]}").status_code == 404
    finally:
        with connect() as conn:
            conn.execute("DELETE FROM notes WHERE id IN (%s, %s)", (mine[0], theirs[0]))
