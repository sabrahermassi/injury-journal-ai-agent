import json
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.api import app
from app.ask_notes.answer import REFUSAL, Quote, ask, build_messages, find_bad_quotes
from app.ask_notes.retrieve import RetrievedChunk


def chunk(chunk_id: int, text: str) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id, note_id=chunk_id * 10, position=0, start=0, end=len(text), text=text,
        score=0.9, body_part="ankle", severity=6, note_date=date(2026, 4, 6),
    )


CHUNKS = [
    chunk(7, "Saw Dr. Lambert about the ankle. She said no X-ray was needed because I could take four steps."),
    chunk(8, "The swelling is less today, and pain while walking is about a 4."),
]


def quote(number: int, text: str) -> Quote:
    return Quote.model_validate({"chunkId": number, "text": text})


def reply(answer: str, *quotes: tuple[int, str]) -> str:
    return json.dumps({"answer": answer, "quotes": [{"chunkId": n, "text": t} for n, t in quotes]})


Prompts = list[list[dict[str, str]]]  # every message list sent to the fake model

GOOD = reply("No, she said no X-ray was needed.", (1, "She said no X-ray was needed"))
INVENTED = reply("She ordered an MRI.", (1, "She ordered an MRI for the ankle"))


@pytest.fixture
def model(monkeypatch: pytest.MonkeyPatch) -> Prompts:
    """Fake retrieve (always CHUNKS); each test sets the fake model's replies. Records every prompt."""
    prompts: Prompts = []
    monkeypatch.setattr("app.ask_notes.answer.retrieve", lambda q, m, f, k, u: CHUNKS)
    monkeypatch.setenv("EMBED_MODEL", "nomic-embed-text")
    return prompts


def fake_replies(monkeypatch: pytest.MonkeyPatch, prompts: Prompts, *replies: str) -> None:
    queue = list(replies)

    def fake_chat(messages: list[dict[str, str]], model: str | None = None) -> str:
        prompts.append(messages)
        return queue.pop(0)

    monkeypatch.setattr("app.ask_notes.answer.chat", fake_chat)


# --- the quote check (core function) ---


def test_exact_quote_is_good() -> None:
    assert find_bad_quotes([quote(1, "She said no X-ray was needed")], CHUNKS) == []


def test_changed_word_is_caught() -> None:
    bad = quote(1, "She said no MRI was needed")
    assert find_bad_quotes([bad], CHUNKS) == [bad]


def test_quote_from_the_wrong_passage_is_caught() -> None:
    bad = quote(2, "She said no X-ray was needed")
    assert find_bad_quotes([bad], CHUNKS) == [bad]


def test_passage_number_that_does_not_exist_is_caught() -> None:
    quotes = [quote(0, "She said no X-ray"), quote(3, "She said no X-ray")]
    assert find_bad_quotes(quotes, CHUNKS) == quotes


def test_extra_spaces_and_line_breaks_still_match() -> None:
    assert find_bad_quotes([quote(1, "She said  no\nX-ray was needed")], CHUNKS) == []


# --- the prompt ---


def test_prompt_numbers_the_passages_and_puts_the_question_last() -> None:
    messages = build_messages("Did I need an X-ray?", CHUNKS)
    user = messages[1]["content"]
    assert "[1] Saw Dr. Lambert" in user and "[2] The swelling" in user
    assert user.endswith("Question: Did I need an X-ray?")


# --- the whole flow ---


def test_good_answer_is_returned_with_its_citation(model: Prompts, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_replies(monkeypatch, model, GOOD)
    result = ask("Did I need an X-ray?", "nomic-embed-text")
    assert not result.refused
    assert result.answer == "No, she said no X-ray was needed."
    assert [(c.note_id, c.chunk_id, c.quote) for c in result.citations] == [(70, 7, "She said no X-ray was needed")]
    assert len(model) == 1


def test_invented_quote_is_retried_once_then_accepted(model: Prompts, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_replies(monkeypatch, model, INVENTED, GOOD)
    result = ask("Did I need an X-ray?", "nomic-embed-text")
    assert not result.refused and len(model) == 2
    assert "not word for word" in model[1][-1]["content"]  # the retry tells the model what was wrong


def test_invented_quote_twice_is_refused(model: Prompts, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_replies(monkeypatch, model, INVENTED, INVENTED)
    result = ask("Did I need an X-ray?", "nomic-embed-text")
    assert result.refused and result.answer == REFUSAL and result.citations == []
    assert len(model) == 2


def test_broken_json_is_retried(model: Prompts, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_replies(monkeypatch, model, "not json", GOOD)
    assert not ask("Did I need an X-ray?", "nomic-embed-text").refused


def test_answer_without_quotes_is_rejected(model: Prompts, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_replies(monkeypatch, model, reply("No X-ray."), reply("No X-ray."))
    assert ask("Did I need an X-ray?", "nomic-embed-text").refused


def test_no_passages_means_refusal_without_calling_the_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.ask_notes.answer.retrieve", lambda q, m, f, k, u: [])
    monkeypatch.setattr("app.ask_notes.answer.chat", lambda messages: pytest.fail("model should not be called"))
    assert ask("Did I need an X-ray?", "nomic-embed-text").refused


def test_ask_endpoint(model: Prompts, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_replies(monkeypatch, model, GOOD)
    client = TestClient(app)
    response = client.post("/ask", json={"question": "Did I need an X-ray?"})
    assert response.status_code == 200
    assert response.json()["refused"] is False
    assert client.post("/ask", json={"question": "x\x00"}).status_code == 422
