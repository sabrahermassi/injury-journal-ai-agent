from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import app
from app.semantic_search.extraction.schema import Injury

FIELDS = Injury(injury="knee pain", body_part="knee", severity=5, cause="running", date=None)

client = TestClient(app)


@pytest.fixture(autouse=True)
def fakes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """No real models, and a temporary store instead of data/semantic_search/notes.json."""
    monkeypatch.setenv("EMBED_MODEL", "nomic-embed-text")
    monkeypatch.chdir(tmp_path)  # the store path is relative: data/semantic_search/notes.json lands in tmp_path
    monkeypatch.setattr("app.semantic_search.index.embed_documents", lambda texts, model: [[1.0, 0.0] for _ in texts])
    monkeypatch.setattr("app.semantic_search.index.extract", lambda text: FIELDS)
    monkeypatch.setattr("app.semantic_search.router.extract", lambda text: FIELDS)
    monkeypatch.setattr("app.semantic_search.search.embed_query", lambda text, model: [1.0, 0.0])


def test_extract_returns_fields() -> None:
    response = client.post("/extract", json={"note": "knee pain 5/10 after running"})
    assert response.status_code == 200
    assert response.json()["body_part"] == "knee"


def test_extract_rejects_empty_note() -> None:
    assert client.post("/extract", json={"note": ""}).status_code == 422


def test_index_then_search() -> None:
    response = client.post("/index", json={"notes": ["knee pain 5/10", "sore neck"]})
    assert response.json() == {"total": 2, "added": 2, "rebuilt": 0}

    response = client.post("/search", json={"query": "knee", "filters": {"body_part": "knee"}, "top_k": 1})
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_body_parts_lists_each_part_once() -> None:
    client.post("/index", json={"notes": ["knee pain 5/10", "sore knee again"]})
    assert client.get("/body-parts").json() == ["knee"]
