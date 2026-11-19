from ollama import Client

from app.core import model_call
from app.core.env import require_env

# Some embedding models want a prefix that says what the text is for:
# (prefix for documents, prefix for search queries)
PREFIXES: dict[str, tuple[str, str]] = {
    "nomic-embed-text": ("search_document: ", "search_query: "),
    "mxbai-embed-large": ("", "Represent this sentence for searching relevant passages: "),
}


def _prefixes(model: str) -> tuple[str, str]:
    return PREFIXES.get(model.split(":")[0], ("", ""))


def _embed(texts: list[str], model: str) -> list[list[float]]:
    client = Client(host=require_env("OLLAMA_URL"), timeout=model_call.TIMEOUT_SECONDS)
    response = model_call.call_model(lambda: client.embed(model=model, input=texts), "embedding")
    return [list(vector) for vector in response.embeddings]


# for notes, when saving
def embed_documents(texts: list[str], model: str) -> list[list[float]]:
    prefix = _prefixes(model)[0]
    return _embed([prefix + text for text in texts], model)


# for a search question, in milestone 5
def embed_query(text: str, model: str) -> list[float]:
    prefix = _prefixes(model)[1]
    return _embed([prefix + text], model)[0]
