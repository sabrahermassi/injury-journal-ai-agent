import pytest
from fastapi.testclient import TestClient

from app.api import app
from app.ask_notes.retrieve import RetrievedChunk

client = TestClient(app)


@pytest.fixture
def retrieve_calls(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """A fake retrieve that records each question, so tests can check it was (or wasn't) called."""
    calls: list[str] = []

    def fake_retrieve(question: str, model: str, filters: object, top_k: int) -> list[RetrievedChunk]:
        calls.append(question)
        return []

    monkeypatch.setattr("app.ask_notes.router.retrieve", fake_retrieve)
    monkeypatch.setenv("EMBED_MODEL", "nomic-embed-text")
    return calls


@pytest.mark.parametrize(
    "body",
    [
        {"question": "knee", "filters": {"body_part": "knee\x00"}},
        {"question": "knee\x00pain"},
    ],
)
def test_nul_character_is_rejected_before_retrieval(body: dict[str, object], retrieve_calls: list[str]) -> None:
    assert client.post("/retrieve", json=body).status_code == 422
    assert retrieve_calls == []


@pytest.mark.parametrize("body_part", ["knee", "50%_x"])
def test_normal_text_and_wildcard_characters_are_allowed(body_part: str, retrieve_calls: list[str]) -> None:
    response = client.post("/retrieve", json={"question": "knee", "filters": {"body_part": body_part}})
    assert response.status_code == 200
    assert retrieve_calls == ["knee"]
