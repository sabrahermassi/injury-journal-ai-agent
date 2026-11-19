from ollama import Client

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
