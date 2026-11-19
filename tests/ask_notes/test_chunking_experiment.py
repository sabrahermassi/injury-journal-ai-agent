import json
from pathlib import Path

from app.ask_notes.evaluation.chunking_experiment import EvalNote, hits, pieces, rank_notes

NOTES = [EvalNote(id="a", text="Knee hurts. " * 60), EvalNote(id="b", text="Cut my finger.")]


def test_whole_note_setting_gives_one_piece_per_note() -> None:
    assert pieces(NOTES, None) == [("a", NOTES[0].text), ("b", "Cut my finger.")]


def test_chunk_setting_cuts_long_notes_and_keeps_their_id() -> None:
    result = pieces(NOTES, (100, 1))
    assert len(result) > 2
    assert {note_id for note_id, _ in result} == {"a", "b"}
    assert all(len(text) <= 100 for _, text in result)


def test_a_note_scores_as_its_best_piece() -> None:
    question = [1.0, 0.0]
    piece_ids = ["a", "a", "b"]
    vectors = [[0.0, 1.0], [1.0, 0.0], [0.7, 0.7]]  # note a has one perfect piece and one bad one
    assert rank_notes(question, piece_ids, vectors) == ["a", "b"]


def test_hits_checks_the_first_k_results() -> None:
    assert hits(["x", "y", "z"], ["y"], 1) is False
    assert hits(["x", "y", "z"], ["y"], 3) is True


def test_every_question_points_to_a_real_test_note() -> None:
    note_ids = {n["id"] for n in json.loads(Path("eval/ask_notes/notes.json").read_text(encoding="utf-8"))}
    questions = json.loads(Path("eval/ask_notes/questions.json").read_text(encoding="utf-8"))
    assert len(questions) >= 15
    assert all(set(q["relevant"]) <= note_ids for q in questions)
