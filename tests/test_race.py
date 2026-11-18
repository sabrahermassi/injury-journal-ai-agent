import threading
import time
from pathlib import Path

import pytest

from app.extraction.schema import Injury
from app.index import index_and_save
from app.store import load

FIELDS = Injury(injury="knee pain", body_part="knee", severity=5, cause="running", date=None)


def test_two_overlapping_saves_keep_both_notes(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Two /index calls at the same time: neither may delete the other's note."""

    def slow_embed(texts: list[str], model: str) -> list[list[float]]:
        time.sleep(0.2)  # long enough for the other call to load the store meanwhile
        return [[1.0, 0.0] for _ in texts]

    monkeypatch.setattr("app.index.embed_documents", slow_embed)
    monkeypatch.setattr("app.index.extract", lambda text: FIELDS)
    path = tmp_path / "notes.json"

    calls = [
        threading.Thread(target=index_and_save, args=(["knee pain"], "nomic-embed-text", path)),
        threading.Thread(target=index_and_save, args=(["sore neck"], "nomic-embed-text", path)),
    ]
    for call in calls:
        call.start()
    for call in calls:
        call.join()

    assert sorted(record.text for record in load(path)) == ["knee pain", "sore neck"]
