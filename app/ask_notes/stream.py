"""Stream an answer: progress, the answer text as the model writes it, then the checked result."""

import json
import re
from contextlib import closing
from collections.abc import Generator
from typing import Any

from pydantic import ValidationError

from app.ask_notes.answer import (
    NOT_FOUND,
    REFUSAL,
    AskResult,
    ModelAnswer,
    build_messages,
    find_bad_quotes,
    make_citations,
    strong_chunks,
)
from app.core.llm import chat_stream
from app.semantic_search.search import SearchFilters

Event = dict[str, Any]

ANSWER_START = re.compile(r'"answer"\s*:\s*"')


def answer_so_far(raw: str) -> str:
    """The text of the "answer" field in a JSON reply that is still being written.

    '{"found": true, "quotes": [...], "answer": "The doctor sa' -> 'The doctor sa'
    """
    match = ANSWER_START.search(raw)
    if match is None:
        return ""
    value = []
    i = match.end()
    while i < len(raw):
        char = raw[i]
        if char == '"':
            break  # end of the answer string
        if char == "\\":
            escape = raw[i : i + 6] if raw[i + 1 : i + 2] == "u" else raw[i : i + 2]
            if len(escape) < (6 if raw[i + 1 : i + 2] == "u" else 2):
                break  # the escape is cut off: wait for the next piece
            value.append(json.loads(f'"{escape}"'))
            i += len(escape)
            continue
        value.append(char)
        i += 1
    return "".join(value)


def ask_stream(
    question: str,
    embed_model: str,
    filters: SearchFilters | None = None,
    top_k: int = 5,
    user_id: str = "demo",
) -> Generator[Event, None, None]:
    """The same steps as ask(), as events the page can show while they happen.

    status: what is happening now. answer: new answer text to add (not checked yet).
    reset: throw away the answer shown so far (its quotes failed, trying again).
    done: the final, checked result (an answer with citations, or a refusal).
    """
    yield {"type": "status", "text": "Searching your notes"}
    chunks = strong_chunks(question, embed_model, filters, top_k, user_id)
    if not chunks:
        yield {"type": "done", "result": AskResult(answer=NOT_FOUND, citations=[], refused=True).model_dump()}
        return

    messages = build_messages(question, chunks)
    for attempt in (1, 2):
        yield {"type": "status", "text": "Writing the answer" if attempt == 1 else "Checking failed, trying again"}
        raw = ""
        shown = ""
        # closing(): if the user leaves mid-answer, the model stream is closed, which stops Ollama.
        with closing(chat_stream(messages)) as pieces:
            for piece in pieces:
                raw += piece
                text = answer_so_far(raw)
                if len(text) > len(shown):
                    yield {"type": "answer", "text": text[len(shown) :]}
                    shown = text
        yield {"type": "status", "text": "Checking the quotes"}
        try:
            result = ModelAnswer.model_validate_json(raw)
        except ValidationError:
            problem = "Your reply was not valid JSON in the required shape."
        else:
            if not result.found:
                yield {"type": "reset"}
                yield {"type": "done", "result": AskResult(answer=NOT_FOUND, citations=[], refused=True).model_dump()}
                return
            bad = find_bad_quotes(result.quotes, chunks)
            if not bad:
                final = AskResult(answer=result.answer, citations=make_citations(result.quotes, chunks), refused=False)
                yield {"type": "done", "result": final.model_dump()}
                return
            problem = "These quotes are not word for word in their passage: " + "; ".join(
                f'[{q.chunk_id}] "{q.text}"' for q in bad
            )
        yield {"type": "reset"}
        messages = messages + [
            {"role": "assistant", "content": raw},
            {"role": "user", "content": f"{problem} Fix it: copy quotes exactly from the passages. Return JSON only."},
        ]
    yield {"type": "done", "result": AskResult(answer=REFUSAL, citations=[], refused=True).model_dump()}
