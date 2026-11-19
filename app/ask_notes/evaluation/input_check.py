"""How well does the input check sort questions? Needs Ollama only.

Run: uv run --env-file .env python -m app.ask_notes.evaluation.input_check
"""

import json
from pathlib import Path

from app.ask_notes.input_check import URGENT_WORDS, check_question


def main() -> None:
    cases = json.loads(Path("eval/ask_notes/input_check.json").read_text(encoding="utf-8"))
    for scope in ("in_scope", "out_of_scope", "urgent"):
        group = [c["question"] for c in cases if c["scope"] == scope]
        wrong = [(q, got) for q in group if (got := check_question(q)) != scope]
        print(f"{scope:<13} {len(group) - len(wrong)}/{len(group)} right")
        for question, got in wrong:
            print(f"    got {got}: {question}")
    urgent = [c["question"] for c in cases if c["scope"] == "urgent"]
    by_words = sum(1 for q in urgent if URGENT_WORDS.search(q))
    print(f"\nurgent caught by the word list alone (no model): {by_words}/{len(urgent)}")


if __name__ == "__main__":
    main()
