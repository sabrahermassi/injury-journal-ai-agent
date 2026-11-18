from pathlib import Path

import pytest

from app.extraction.schema import Injury
from app.index import index_notes
from app.store import NoteRecord, load, note_id, save

FIELDS = Injury(injury="knee pain", body_part="knee", severity=5, cause="running", date=None)


@pytest.fixture
def fakes(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    """Replace the real models with fakes, and record what was embedded."""
    embedded: list[list[str]] = []

    def fake_embed(texts: list[str], model: str) -> list[list[float]]:
        embedded.append(texts)
        return [[1.0, 0.0] for _ in texts]

    monkeypatch.setattr("app.index.embed_documents", fake_embed)
    monkeypatch.setattr("app.index.extract", lambda text: FIELDS)
    return embedded


def test_indexes_new_notes(fakes: list[list[str]]) -> None:
    records = index_notes(["knee pain 5/10", "sore neck"], [], "nomic-embed-text")
    assert len(records) == 2
    assert records[0].id == note_id("knee pain 5/10")
    assert records[0].fields.body_part == "knee"


def test_skips_notes_already_embedded(fakes: list[list[str]]) -> None:
    first = index_notes(["knee pain 5/10"], [], "nomic-embed-text")
    second = index_notes(["knee pain 5/10", "sore neck"], first, "nomic-embed-text")
    assert len(second) == 2
    assert fakes[-1] == ["sore neck"]  # only the new note was embedded


def test_reembeds_everything_when_model_changes(fakes: list[list[str]]) -> None:
    first = index_notes(["knee pain 5/10"], [], "nomic-embed-text")
    second = index_notes(["knee pain 5/10"], first, "all-minilm")
    assert [record.embed_model for record in second] == ["all-minilm"]


def test_save_and_load_round_trip(tmp_path: Path) -> None:
    record = NoteRecord(id="abc", text="knee pain", fields=FIELDS, vector=[0.1, 0.2], embed_model="nomic-embed-text")
    path = tmp_path / "notes.json"
    save([record], path)
    assert load(path) == [record]
    assert not (tmp_path / "notes.json.tmp").exists()


def test_duplicate_notes_with_different_spaces_are_saved_once(fakes: list[list[str]]) -> None:
    records = index_notes(["knee pain", " knee pain "], [], "nomic-embed-text")
    assert len(records) == 1


def test_model_change_reuses_saved_fields_without_extracting(
    fakes: list[list[str]], monkeypatch: pytest.MonkeyPatch
) -> None:
    first = index_notes(["knee pain 5/10"], [], "nomic-embed-text")

    def must_not_extract(text: str) -> Injury:
        raise AssertionError("extract must not run for notes that are already saved")

    monkeypatch.setattr("app.index.extract", must_not_extract)
    second = index_notes(["knee pain 5/10"], first, "all-minilm")

    assert len(second) == 1
    assert second[0].embed_model == "all-minilm"
    assert second[0].fields == first[0].fields
