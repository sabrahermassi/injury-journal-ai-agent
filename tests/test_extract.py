import pytest
from pydantic import ValidationError

from app.extract import extract
from app.schema import Injury

VALID = '{"injury": "twisted ankle", "body_part": "ankle", "severity": 7, "cause": "football", "date": null}'


def test_schema_accepts_valid_json() -> None:
    injury = Injury.model_validate_json(VALID)
    assert injury.severity == 7


def test_schema_rejects_severity_above_10() -> None:
    with pytest.raises(ValidationError):
        Injury.model_validate_json(VALID.replace('"severity": 7', '"severity": 11'))


def test_schema_rejects_empty_text() -> None:
    with pytest.raises(ValidationError):
        Injury.model_validate_json(VALID.replace('"ankle"', '"  "'))


def test_extract_retries_once_with_the_error(monkeypatch: pytest.MonkeyPatch) -> None:
    replies = iter(['{"injury": "twisted ankle"}', VALID])
    calls: list[list[dict[str, str]]] = []

    def fake_chat(messages: list[dict[str, str]], model: str | None = None) -> str:
        calls.append(list(messages))
        return next(replies)

    monkeypatch.setattr("app.extract.chat", fake_chat)

    result = extract("Twisted my ankle playing football, pain 7")

    assert result.body_part == "ankle"
    assert len(calls) == 2
    assert calls[1][-1]["content"].startswith("Invalid:")