import pytest


@pytest.fixture(autouse=True)
def questions_are_in_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every Ask Notes test: the input check's model says "in scope", so no test calls Ollama.

    Tests of the input check itself replace this with their own fake.
    """
    monkeypatch.setattr("app.ask_notes.input_check.chat", lambda messages: '{"scope": "in_scope"}')
