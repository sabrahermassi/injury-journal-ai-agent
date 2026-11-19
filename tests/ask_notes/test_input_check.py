import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import app
from app.ask_notes.answer import ask
from app.ask_notes.input_check import OUT_OF_SCOPE, URGENT, check_question
from app.ask_notes.stream import ask_stream


def model_says(monkeypatch: pytest.MonkeyPatch, reply: str) -> list[str]:
    """The input check's model gives this reply. Returns the questions it was asked."""
    asked: list[str] = []

    def fake_chat(messages: list[dict[str, str]]) -> str:
        asked.append(messages[-1]["content"])
        return reply

    monkeypatch.setattr("app.ask_notes.input_check.chat", fake_chat)
    return asked


def no_search(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail the test if anything tries to search the notes."""
    monkeypatch.setattr("app.ask_notes.answer.retrieve", lambda *args: pytest.fail("search should not run"))


@pytest.mark.parametrize("question", ["I have chest pain", "I CAN'T BREATHE", "it won't stop bleeding"])
def test_urgent_words_are_caught_without_the_model(monkeypatch: pytest.MonkeyPatch, question: str) -> None:
    asked = model_says(monkeypatch, '{"scope": "in_scope"}')
    assert check_question(question) == "urgent"
    assert asked == []


@pytest.mark.parametrize("scope", ["in_scope", "out_of_scope", "urgent"])
def test_the_model_sorts_the_rest(monkeypatch: pytest.MonkeyPatch, scope: str) -> None:
    model_says(monkeypatch, json.dumps({"scope": scope}))
    assert check_question("What is the capital of France?") == scope


@pytest.mark.parametrize("reply", ["not json", '{"scope": "maybe"}'])
def test_a_bad_model_reply_counts_as_in_scope(monkeypatch: pytest.MonkeyPatch, reply: str) -> None:
    model_says(monkeypatch, reply)
    assert check_question("How is my knee?") == "in_scope"


def test_out_of_scope_question_is_never_searched(monkeypatch: pytest.MonkeyPatch) -> None:
    model_says(monkeypatch, '{"scope": "out_of_scope"}')
    no_search(monkeypatch)
    result = ask("What is the capital of France?", "nomic-embed-text")
    assert (result.scope, result.refused, result.answer) == ("out_of_scope", True, OUT_OF_SCOPE)


def test_urgent_question_gets_the_emergency_message_in_the_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    no_search(monkeypatch)
    events = list(ask_stream("I have chest pain right now", "nomic-embed-text"))
    assert events[-1]["result"]["scope"] == "urgent"
    assert events[-1]["result"]["answer"] == URGENT


def test_ask_endpoint_returns_the_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    model_says(monkeypatch, '{"scope": "out_of_scope"}')
    no_search(monkeypatch)
    monkeypatch.setenv("EMBED_MODEL", "nomic-embed-text")
    body = TestClient(app).post("/ask", json={"question": "Tell me a joke."}).json()
    assert body["scope"] == "out_of_scope" and body["refused"] is True


def test_test_set_has_every_scope() -> None:
    cases = json.loads(Path("eval/ask_notes/input_check.json").read_text(encoding="utf-8"))
    assert {c["scope"] for c in cases} == {"in_scope", "out_of_scope", "urgent"}
    assert all(c["question"].strip() for c in cases)
