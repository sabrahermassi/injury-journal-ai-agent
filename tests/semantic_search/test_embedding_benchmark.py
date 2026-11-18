from app.semantic_search.evaluation.embedding_benchmark import LabelledNote, fields_text, rank, text_to_embed
from app.semantic_search.extraction.schema import Injury

NOTE = LabelledNote(
    note="knee pain after running",
    expected=Injury(injury="knee pain", body_part="knee", severity=None, cause="running", date=None),
)


def test_fields_text_skips_empty_fields() -> None:
    assert fields_text(NOTE.expected) == "injury: knee pain; body part: knee; cause: running"


def test_text_to_embed_options() -> None:
    assert text_to_embed(NOTE, "raw") == "knee pain after running"
    assert text_to_embed(NOTE, "fields") == "injury: knee pain; body part: knee; cause: running"
    assert text_to_embed(NOTE, "both") == "knee pain after running\ninjury: knee pain; body part: knee; cause: running"


def test_rank_puts_the_most_similar_note_first() -> None:
    query = [1.0, 0.0]
    notes = [[0.0, 1.0], [1.0, 0.1], [0.5, 0.5]]
    assert rank(query, notes) == [1, 2, 0]
