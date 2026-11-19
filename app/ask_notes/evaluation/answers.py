"""The project's number: how many of 20 questions get a correct answer with verified quotes.

Needs Postgres with the 20 test notes saved, and Ollama.
Run: uv run --env-file .env python -m app.ask_notes.evaluation.answers
"""

import json
from pathlib import Path

from app.ask_notes.answer import AskResult, ask, normalize
from app.ask_notes.ingest import get_note
from app.core.env import require_env


def grade(result: AskResult, note_texts: dict[int, str], expected_note: str, passage: str) -> str:
    """correct: answered, citing the expected note, with a quote that covers the expected passage.

    note_texts: the text of each cited note, by its database id.
    """
    if result.refused:
        return "refused"
    for citation in result.citations:
        right_note = normalize(note_texts.get(citation.note_id, "")) == normalize(expected_note)
        quote, wanted = normalize(citation.quote), normalize(passage)
        if right_note and (wanted in quote or quote in wanted):
            return "correct"
    return "wrong"


def main() -> None:
    model = require_env("EMBED_MODEL")
    notes = {n["id"]: n["text"] for n in json.loads(Path("eval/ask_notes/notes.json").read_text(encoding="utf-8"))}
    cases = json.loads(Path("eval/ask_notes/answers.json").read_text(encoding="utf-8"))

    counts = {"correct": 0, "wrong": 0, "refused": 0}
    for case in cases:
        result = ask(case["question"], model)
        note_texts = {}
        for citation in result.citations:
            note = get_note(citation.note_id)
            if note is not None:
                note_texts[citation.note_id] = note.text
        outcome = grade(result, note_texts, notes[case["note"]], case["passage"])
        counts[outcome] += 1
        if outcome != "correct":
            quotes = [c.quote for c in result.citations]
            print(f"  {outcome:<8} {case['question']}\n           -> {result.answer[:90]} | quotes: {quotes}")

    total = len(cases)
    print(f"\nCorrect with verified quotes: {counts['correct']}/{total}")
    print(f"Wrong: {counts['wrong']}/{total}   Refused: {counts['refused']}/{total}")


if __name__ == "__main__":
    main()
