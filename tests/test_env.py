import pytest

from app.env import require_env


def test_returns_value_when_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_VAR", "hello")
    assert require_env("TEST_VAR") == "hello"


def test_raises_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MISSING_VAR", raising=False)
    with pytest.raises(RuntimeError, match="Missing environment variable: MISSING_VAR"):
        require_env("MISSING_VAR")