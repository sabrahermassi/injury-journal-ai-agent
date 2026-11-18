from datetime import date
import pytest

from app.semantic_search.extraction.schema import Injury
from app.semantic_search.search import SearchFilters, search
from app.semantic_search.store import NoteRecord

MODEL = "nomic-embed-text"


def record(text: str, body_part: str, severity: int | None, vector: list[float], model: str = MODEL) -> NoteRecord:
    fields = Injury(injury=text, body_part=body_part, severity=severity, cause=None, date=None)
    return NoteRecord(id=text, text=text, fields=fields, vector=vector, embed_model=model)


RECORDS = [
    record("knee pain running", "knee", 5, [1.0, 0.0]),
    record("left knee sore", "left knee", 2, [0.9, 0.1]),
    record("cut finger", "finger", 2, [0.0, 1.0]),
]


@pytest.fixture(autouse=True)
def fake_query_vector(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every question gets the vector [1, 0], so no real model is needed."""
    monkeypatch.setattr("app.semantic_search.search.embed_query", lambda query, model: [1.0, 0.0])


def test_ranks_by_meaning() -> None:
    results = search("knee", RECORDS, MODEL, min_score=0.0)
    assert [result.id for result in results] == ["knee pain running", "left knee sore", "cut finger"]
    assert results[0].score == pytest.approx(1.0)


def test_top_k_limits_the_results() -> None:
    assert len(search("knee", RECORDS, MODEL, top_k=2)) == 2


def test_body_part_filter_matches_part_of_the_name() -> None:
    results = search("pain", RECORDS, MODEL, SearchFilters(body_part="knee"))
    assert [result.id for result in results] == ["knee pain running", "left knee sore"]


def test_min_severity_filter() -> None:
    results = search("pain", RECORDS, MODEL, SearchFilters(min_severity=5))
    assert [result.id for result in results] == ["knee pain running"]


def test_no_match_returns_empty_list() -> None:
    assert search("pain", RECORDS, MODEL, SearchFilters(body_part="elbow")) == []


def test_ignores_notes_from_another_model() -> None:
    other = [record("old note", "knee", 5, [1.0, 0.0], model="all-minilm")]
    assert search("knee", other, MODEL) == []


def test_negative_top_k_is_rejected() -> None:
    with pytest.raises(ValueError):
        search("knee", RECORDS, MODEL, top_k=-1)


def test_zero_top_k_returns_empty_list() -> None:
    assert search("knee", RECORDS, MODEL, top_k=0) == []


def test_min_score_drops_weak_matches() -> None:
    # Scores against [1, 0]: knee pain 1.0, left knee about 0.99, cut finger 0.0.
    results = search("knee", RECORDS, MODEL, min_score=0.5)
    assert [result.id for result in results] == ["knee pain running", "left knee sore"]


def test_only_weak_matches_returns_nothing() -> None:
    # The only finger note scores 0.0, below the threshold.
    assert search("knee", RECORDS, MODEL, SearchFilters(body_part="finger"), min_score=0.5) == []


def dated(text: str, note_date: str | None) -> NoteRecord:
    fields = Injury(injury=text, body_part="knee", severity=5, cause=None, date=note_date)
    return NoteRecord(id=text, text=text, fields=fields, vector=[1.0, 0.0], embed_model=MODEL)


DATED = [dated("october", "2026-10-15"), dated("november", "2026-11-02"), dated("no date", None)]


def test_date_range_keeps_notes_inside_it() -> None:
    filters = SearchFilters(date_from=date(2026, 11, 1), date_to=date(2026, 11, 30))
    assert [result.id for result in search("knee", DATED, MODEL, filters)] == ["november"]


def test_date_filter_skips_notes_without_a_date() -> None:
    filters = SearchFilters(date_from=date(2026, 1, 1))
    assert sorted(result.id for result in search("knee", DATED, MODEL, filters)) == ["november", "october"]
