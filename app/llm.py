from ollama import Client

from app.env import require_env


def chat(messages: list[dict[str, str]], model: str | None = None) -> str:
    client = Client(host=require_env("OLLAMA_URL"))
    response = client.chat(
        model=model or require_env("LLM_MODEL"),
        messages=messages,
        format="json",
        options={"temperature": 0},
    )
    return response.message.content or ""