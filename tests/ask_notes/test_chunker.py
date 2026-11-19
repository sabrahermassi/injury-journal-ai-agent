import json
from pathlib import Path

import pytest

from app.ask_notes.chunker import Chunk, chunk_note

NOTES = json.loads(Path("eval/ask_notes/notes.json").read_text(encoding="utf-8"))


def check_offsets(text: str, chunks: list[Chunk]) -> None:
    """Every chunk's text is exactly the note's text between its offsets."""
    for chunk in chunks:
        assert chunk.text == text[chunk.start : chunk.end]


def test_empty_note_gives_no_chunks() -> None:
    assert chunk_note(1, "") == []
    assert chunk_note(1, "   \n\n  ") == []


def test_short_note_is_one_chunk() -> None:
    chunks = chunk_note(7, "Knee hurts after running.")
    assert chunks == [Chunk(7, 0, 0, 25, "Knee hurts after running.")]


def test_chunks_keep_note_id_and_positions_in_order() -> None:
    chunks = chunk_note(3, NOTES[0]["text"], max_chars=200)
    assert len(chunks) > 1
    assert [c.note_id for c in chunks] == [3] * len(chunks)
    assert [c.position for c in chunks] == list(range(len(chunks)))


@pytest.mark.parametrize("note", NOTES, ids=[n["id"] for n in NOTES])
def test_test_notes_offsets_size_and_coverage(note: dict[str, str]) -> None:
    text = note["text"]
    chunks = chunk_note(1, text, max_chars=300)
    check_offsets(text, chunks)
    assert all(len(c.text) <= 300 for c in chunks)
    # No text is lost: every non-space character is inside some chunk.
    covered: set[int] = set()
    for c in chunks:
        covered.update(range(c.start, c.end))
    assert all(i in covered for i, ch in enumerate(text) if not ch.isspace())


def test_neighbour_chunks_overlap() -> None:
    chunks = chunk_note(1, NOTES[0]["text"], max_chars=200, overlap=1)
    assert len(chunks) > 1
    for before, after in zip(chunks, chunks[1:]):
        assert after.start < before.end


def test_no_overlap_when_overlap_is_zero() -> None:
    chunks = chunk_note(1, NOTES[0]["text"], max_chars=200, overlap=0)
    for before, after in zip(chunks, chunks[1:]):
        assert after.start >= before.end


def test_one_huge_paragraph_without_punctuation_is_cut() -> None:
    text = "pain " * 500  # 2500 characters, no full stop
    chunks = chunk_note(1, text, max_chars=300)
    assert len(chunks) > 1
    assert all(len(c.text) <= 300 for c in chunks)
    check_offsets(text, chunks)


def test_empty_lines_are_not_inside_chunk_edges() -> None:
    text = "\n\nFirst sentence.\n\n\n\nSecond sentence.\n\n"
    chunks = chunk_note(1, text)
    check_offsets(text, chunks)
    for c in chunks:
        assert c.text == c.text.strip()
    assert "First sentence." in chunks[0].text
    assert "Second sentence." in chunks[-1].text


def test_bad_settings_are_rejected() -> None:
    with pytest.raises(ValueError):
        chunk_note(1, "text", max_chars=0)
    with pytest.raises(ValueError):
        chunk_note(1, "text", overlap=-1)
