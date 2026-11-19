from collections.abc import Generator, Iterator

from ollama import ChatResponse, Client

from app.core import model_call
from app.core.env import require_env


def chat(messages: list[dict[str, str]], model: str | None = None) -> str:
    client = Client(host=require_env("OLLAMA_URL"), timeout=model_call.TIMEOUT_SECONDS)
    response = model_call.call_model(
        lambda: client.chat(
            model=model or require_env("LLM_MODEL"),
            messages=messages,
            format="json",
            options={"temperature": 0},
        ),
        "language",
    )
    return response.message.content or ""


def chat_stream(messages: list[dict[str, str]], model: str | None = None) -> Generator[str, None, None]:
    """Like chat, but yields the reply piece by piece as the model writes it.

    Connecting (up to the first piece) gets the timeout and one retry. If the caller stops reading,
    closing this generator closes the HTTP stream, so Ollama stops generating.
    """
    client = Client(host=require_env("OLLAMA_URL"), timeout=model_call.TIMEOUT_SECONDS)

    def start() -> tuple[ChatResponse | None, Iterator[ChatResponse]]:
        stream = client.chat(
            model=model or require_env("LLM_MODEL"),
            messages=messages,
            format="json",
            options={"temperature": 0},
            stream=True,
        )
        return next(stream, None), stream  # next() makes the connection now, inside the retry

    first, stream = model_call.call_model(start, "language")
    try:
        if first is not None:
            yield first.message.content or ""
        for part in stream:
            yield part.message.content or ""
    finally:
        close = getattr(stream, "close", None)
        if close is not None:
            close()  # closes the HTTP stream: Ollama stops generating
