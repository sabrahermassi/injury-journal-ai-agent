"""Does chunking beat embedding whole notes, and which chunk size works best?

Run once with real models: uv run --env-file .env python -m app.ask_notes.evaluation.chunking_experiment
"""

import json
from pathlib import Path

from pydantic import BaseModel, TypeAdapter

from app.ask_notes.chunker import chunk_note
from app.core.embed import embed_documents, embed_query
from app.core.env import require_env
from app.core.similarity import cosine_similarity

# Each setting: (max_chars, overlap), or None for "embed the whole note, no chunking".
SETTINGS: dict[str, tuple[int, int] | None] = {
    "whole note": None,
    "small 300, overlap 1": (300, 1),
    "medium 600, overlap 1": (600, 1),
    "medium 600, overlap 0": (600, 0),
    "large 1000, overlap 1": (1000, 1),
}


class EvalNote(BaseModel):
    id: str
    text: str


class EvalQuestion(BaseModel):
    question: str
    relevant: list[str]  # ids of the notes that answer it


def pieces(notes: list[EvalNote], setting: tuple[int, int] | None) -> list[tuple[str, str]]:
    """(note id, text) for every piece that gets embedded: whole notes, or their chunks."""
    if setting is None:
        return [(note.id, note.text) for note in notes]
    max_chars, overlap = setting
    return [(note.id, chunk.text) for note in notes for chunk in chunk_note(0, note.text, max_chars, overlap)]


def rank_notes(question_vector: list[float], piece_ids: list[str], piece_vectors: list[list[float]]) -> list[str]:
    """Note ids from best to worst. A note's score is the score of its best piece."""
    best: dict[str, float] = {}
    for note_id, vector in zip(piece_ids, piece_vectors, strict=True):
        score = cosine_similarity(question_vector, vector)
        best[note_id] = max(score, best.get(note_id, -1.0))
    return sorted(best, key=lambda note_id: best[note_id], reverse=True)


def hits(ranking: list[str], relevant: list[str], k: int) -> bool:
    """True if a right note is in the first k results."""
    return any(note_id in relevant for note_id in ranking[:k])


def main() -> None:
    model = require_env("EMBED_MODEL")
    notes = TypeAdapter(list[EvalNote]).validate_json(Path("eval/ask_notes/notes.json").read_text(encoding="utf-8"))
    questions = TypeAdapter(list[EvalQuestion]).validate_json(
        Path("eval/ask_notes/questions.json").read_text(encoding="utf-8")
    )
    question_vectors = [embed_query(q.question, model) for q in questions]
    total = len(questions)

    print(f"{'Setting':<24} {'Pieces':>6} {'Top-1':>7} {'Top-3':>7}")
    for name, setting in SETTINGS.items():
        piece_list = pieces(notes, setting)
        piece_vectors = embed_documents([text for _, text in piece_list], model)
        piece_ids = [note_id for note_id, _ in piece_list]
        top1 = top3 = 0
        misses = []
        for q, vector in zip(questions, question_vectors, strict=True):
            ranking = rank_notes(vector, piece_ids, piece_vectors)
            top1 += hits(ranking, q.relevant, 1)
            top3 += hits(ranking, q.relevant, 3)
            if not hits(ranking, q.relevant, 1):
                misses.append(q.question)
        print(f"{name:<24} {len(piece_list):>6} {top1:>4}/{total} {top3:>4}/{total}")
        for question in misses:
            print(f"    missed top-1: {json.dumps(question)}")


if __name__ == "__main__":
    main()
