import json
import time
from pathlib import Path
from typing import Any

from app.extract import extract

MODELS = ["llama3.2", "qwen2.5:3b", "qwen2.5:7b"]
FIELDS = ["injury", "body_part", "severity", "cause", "date"]


def is_match(actual: object, expected: object) -> bool:
    if isinstance(actual, str) and isinstance(expected, str):
        actual_text = actual.strip().lower()
        expected_text = expected.strip().lower()
        if not actual_text or not expected_text:
            return False
        return actual_text in expected_text or expected_text in actual_text
    return actual == expected


def main() -> None:
    test_cases: list[dict[str, Any]] = json.loads(Path("eval/notes.json").read_text())

    for model in MODELS:
        correct_fields = 0
        failed_notes = 0
        total_seconds = 0.0

        for test_case in test_cases:
            start_time = time.perf_counter()
            try:
                result = extract(test_case["note"], model).model_dump()
                for field in FIELDS:
                    if is_match(result[field], test_case["expected"][field]):
                        correct_fields += 1
            except Exception:
                failed_notes += 1
            total_seconds += time.perf_counter() - start_time

        total_fields = len(test_cases) * len(FIELDS)
        percent_correct = round(correct_fields / total_fields * 100)
        seconds_per_note = total_seconds / len(test_cases)
        print(f"{model} | {percent_correct}% correct | {failed_notes} failed | {seconds_per_note:.1f}s per note")


if __name__ == "__main__":
    main()