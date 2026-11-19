import json
from pathlib import Path

from app.ask_notes.answer import AskResult, Citation
from app.ask_notes.evaluation.answers import grade

NOTE = "Saw Dr. Lambert about the ankle. She said no X-ray was needed because I could take four steps."
OTHER = "Cut my finger chopping onions."


def result(note_id: int, quote: str, refused: bool = False) -> AskResult:
    citation = Citation(note_id=note_id, chunk_id=1, start=0, end=1, quote=quote)
    return AskResult(answer="x", citations=[] if refused else [citation], refused=refused)


def test_right_note_and_passage_is_correct() -> None:
    texts = {1: NOTE}
    assert grade(result(1, "She said no X-ray was needed because I could take four steps."), texts, NOTE, "said no X-ray was needed") == "correct"


def test_wrong_note_is_wrong() -> None:
    assert grade(result(2, "Cut my finger"), {2: OTHER}, NOTE, "said no X-ray was needed") == "wrong"


def test_right_note_but_other_passage_is_wrong() -> None:
    assert grade(result(1, "Saw Dr. Lambert about the ankle."), {1: NOTE}, NOTE, "said no X-ray was needed") == "wrong"


def test_refusal_is_counted_as_refused() -> None:
    assert grade(result(1, "", refused=True), {}, NOTE, "said no X-ray was needed") == "refused"


def test_every_expected_passage_is_really_in_its_note() -> None:
    notes = {n["id"]: " ".join(n["text"].split()) for n in json.loads(Path("eval/ask_notes/notes.json").read_text(encoding="utf-8"))}
    cases = json.loads(Path("eval/ask_notes/answers.json").read_text(encoding="utf-8"))
    assert len(cases) == 20
    assert all(case["passage"] in notes[case["note"]] for case in cases)
