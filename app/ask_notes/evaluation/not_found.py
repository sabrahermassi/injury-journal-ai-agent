"""Do questions the notes can't answer get refused, while answerable ones still get answered?

Needs Postgres with the 20 test notes saved, and Ollama.
Run: uv run --env-file .env python -m app.ask_notes.evaluation.not_found
"""

import json
from pathlib import Path

from app.ask_notes import answer
from app.ask_notes.answer import ask
from app.ask_notes.retrieve import retrieve
from app.core.env import require_env


def best_score(question: str, model: str) -> float:
    """Score of the closest chunk: high = the notes talk about this, low = they don't."""
    chunks = retrieve(question, model, top_k=1)
    return chunks[0].score if chunks else 0.0


def main() -> None:
    model = require_env("EMBED_MODEL")
    answerable = [q["question"] for q in json.loads(Path("eval/ask_notes/questions.json").read_text(encoding="utf-8"))]
    unanswerable = json.loads(Path("eval/ask_notes/unanswerable.json").read_text(encoding="utf-8"))

    # 1. Best chunk score per question. A good threshold sits between the two groups.
    print("Best chunk score (answerable should be high, unanswerable low):")
    for group, questions in (("answerable", answerable), ("unanswerable", unanswerable)):
        scores = sorted(best_score(q, model) for q in questions)
        print(f"  {group:<13} lowest {scores[0]:.2f}  highest {scores[-1]:.2f}  all {[round(s, 2) for s in scores]}")

    # 2. The full flow with the current threshold and instruction.
    print(f"\nWith MIN_SCORE = {answer.MIN_SCORE}:")
    refused = [q for q in unanswerable if ask(q, model).refused]
    print(f"  unanswerable refused: {len(refused)}/{len(unanswerable)}")
    for q in unanswerable:
        if q not in refused:
            print(f"    ANSWERED (wrong): {q}")
    answered = [q for q in answerable if not ask(q, model).refused]
    print(f"  answerable answered:  {len(answered)}/{len(answerable)}")
    for q in answerable:
        if q not in answered:
            print(f"    refused: {q}")


if __name__ == "__main__":
    main()
