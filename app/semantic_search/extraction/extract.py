from pydantic import ValidationError
from app.core.llm import chat
from app.semantic_search.extraction.schema import Injury

SYSTEM = """You extract injury data from a personal note.
Return JSON with keys: injury, body_part, severity (1-10), cause, date (YYYY-MM-DD).
If a value is not in the note, use null. Never guess."""


def extract(note: str, model: str | None = None) -> Injury:
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": note},
    ]

    first = chat(messages, model)
    try:
        return Injury.model_validate_json(first)
    except ValidationError as error:
        messages.append({"role": "assistant", "content": first})
        messages.append({"role": "user", "content": f"Invalid: {error}. Fix it and return JSON only."})

    second = chat(messages, model)
    return Injury.model_validate_json(second)
