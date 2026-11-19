import socket
import threading
import time
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
import pytest
from fastapi.testclient import TestClient
from ollama import ResponseError

from app.api import app
from app.core import model_call
from app.core.embed import embed_documents
from app.core.llm import chat
from app.core.model_call import ModelUnavailableError, call_model


@pytest.fixture(autouse=True)
def no_pause(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Record the retry pause instead of really sleeping, so tests stay fast."""
    pauses: list[float] = []
    monkeypatch.setattr(model_call, "pause", pauses.append)
    return pauses


class FakeCall:
    """A model call that fails with the given errors first, then answers 'ok'."""

    def __init__(self, *errors: Exception) -> None:
        self.errors = list(errors)
        self.count = 0

    def __call__(self) -> str:
        self.count += 1
        if self.errors:
            raise self.errors.pop(0)
        return "ok"


def test_works_first_time_without_retry(no_pause: list[float]) -> None:
    call = FakeCall()
    assert call_model(call, "language") == "ok"
    assert call.count == 1 and no_pause == []


def test_one_timeout_then_success_retries_after_a_pause(no_pause: list[float]) -> None:
    call = FakeCall(httpx.ReadTimeout("slow"))
    assert call_model(call, "language") == "ok"
    assert call.count == 2 and no_pause == [model_call.RETRY_PAUSE_SECONDS]


def test_down_twice_gives_a_clear_error() -> None:
    call = FakeCall(ConnectionError("down"), ConnectionError("down"))
    with pytest.raises(ModelUnavailableError, match="embedding model is not responding"):
        call_model(call, "embedding")
    assert call.count == 2


def test_our_own_mistake_is_not_retried() -> None:
    call = FakeCall(ResponseError("model not found", 404))
    with pytest.raises(ResponseError):
        call_model(call, "language")
    assert call.count == 1


class SlowHandler(BaseHTTPRequestHandler):
    """A fake Ollama that takes 2 seconds to answer anything."""

    hits = 0

    def do_POST(self) -> None:
        SlowHandler.hits += 1
        time.sleep(2)
        self.send_response(200)
        self.end_headers()

    def log_message(self, *args: object) -> None:
        pass


@pytest.fixture
def slow_ollama(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), SlowHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setenv("OLLAMA_URL", f"http://127.0.0.1:{server.server_port}")
    monkeypatch.setenv("LLM_MODEL", "qwen2.5:3b")
    monkeypatch.setattr(model_call, "TIMEOUT_SECONDS", 0.3)
    SlowHandler.hits = 0
    yield
    server.shutdown()


def test_slow_model_times_out_instead_of_hanging(slow_ollama: None) -> None:
    started = time.monotonic()
    with pytest.raises(ModelUnavailableError, match="language model"):
        chat([{"role": "user", "content": "hi"}])
    assert time.monotonic() - started < 1.5  # two 0.3 s timeouts, not two 2 s waits
    assert SlowHandler.hits == 2  # the first try and the one retry


def test_crashed_model_gives_a_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    with socket.socket() as s:  # find a port where nothing is listening
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    monkeypatch.setenv("OLLAMA_URL", f"http://127.0.0.1:{port}")
    with pytest.raises(ModelUnavailableError, match="embedding model"):
        embed_documents(["knee pain"], "nomic-embed-text")


def test_endpoint_answers_503_when_the_model_is_down(monkeypatch: pytest.MonkeyPatch) -> None:
    def model_down(note: str) -> None:
        raise ModelUnavailableError("The language model is not responding. Is Ollama running?")

    monkeypatch.setattr("app.semantic_search.router.extract", model_down)
    response = TestClient(app).post("/extract", json={"note": "knee pain"})
    assert response.status_code == 503
    assert response.json() == {"detail": "The language model is not responding. Is Ollama running?"}
