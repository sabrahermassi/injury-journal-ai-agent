"""Answer a question from the notes, with quotes that plain code checks word for word."""

import logging

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.ask_notes.retrieve import RetrievedChunk, retrieve
from app.core.llm import chat
from app.semantic_search.search import SearchFilters

logger = logging.getLogger(__name__)

REFUSAL = "I couldn't find a reliable answer in your notes."

SYSTEM = """You answer questions about the user's own injury notes.
Use ONLY the numbered note passages you are given. Never use outside knowledge.
Return JSON: {"quotes": [{"chunkId": 1, "text": "..."}], "answer": "..."}
- quotes: FIRST, copy the exact sentences that answer the question, word for word, with the passage number as chunkId.
- answer: THEN answer in one full sentence that says the same thing as the quotes. Never just "yes" or "no".
If a quote says something did NOT happen, the answer must say it did not happen.
Every quote must appear exactly in its passage. Give at least one quote."""


class Quote(BaseModel):
    """One quote the model says it used. chunkId is the passage number in the prompt (1, 2, 3...)."""

    model_config = ConfigDict(populate_by_name=True)

    chunk_id: int = Field(alias="chunkId")
    text: str = Field(min_length=5)


class ModelAnswer(BaseModel):
    """The shape the model must return. Pydantic rejects anything else."""

    answer: str = Field(min_length=1)
    quotes: list[Quote] = Field(min_length=1)


class Citation(BaseModel):
    """A checked quote, with where it comes from, so the UI can show and highlight it."""

    note_id: int
    chunk_id: int
    start: int  # the chunk's place in the note
    end: int
    quote: str


class AskResult(BaseModel):
    answer: str
    citations: list[Citation]
    refused: bool  # True when no checked answer could be given


def normalize(text: str) -> str:
    """Collapse runs of spaces and line breaks into one space, so line breaks don't break a match."""
    return " ".join(text.split())


# Core function: the check that makes answers trustworthy. Plain code, no AI.
def find_bad_quotes(quotes: list[Quote], chunks: list[RetrievedChunk]) -> list[Quote]:
    """Quotes that are NOT word for word in the passage they point to (or point to no passage)."""
    bad = []
    for quote in quotes:
        text = normalize(quote.text)
        if len(text) < 5:
            bad.append(quote)  # empty or almost empty after removing spaces: quotes nothing
        elif not 1 <= quote.chunk_id <= len(chunks):
            bad.append(quote)  # points to a passage that doesn't exist
        elif text not in normalize(chunks[quote.chunk_id - 1].text):
            bad.append(quote)  # the words are not in that passage
    return bad


def build_messages(question: str, chunks: list[RetrievedChunk]) -> list[dict[str, str]]:
    """The system rules, then the numbered passages and the question last."""
    passages = "\n\n".join(f"[{number}] {chunk.text}" for number, chunk in enumerate(chunks, start=1))
    return [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": f"Passages:\n\n{passages}\n\nQuestion: {question}"},
    ]


def ask(
    question: str,
    embed_model: str,
    filters: SearchFilters | None = None,
    top_k: int = 5,
    user_id: str = "demo",
) -> AskResult:
    """Retrieve passages, ask the model, check every quote. Retry once, then refuse."""
    chunks = retrieve(question, embed_model, filters, top_k, user_id)
    if not chunks:
        return AskResult(answer=REFUSAL, citations=[], refused=True)

    messages = build_messages(question, chunks)
    for attempt in (1, 2):
        raw = chat(messages)
        try:
            result = ModelAnswer.model_validate_json(raw)
        except ValidationError as error:
            problem = f"Your reply was not valid JSON in the required shape: {error.errors()[0]['msg']}."
        else:
            bad = find_bad_quotes(result.quotes, chunks)
            if not bad:
                citations = [
                    Citation(
                        note_id=chunks[q.chunk_id - 1].note_id,
                        chunk_id=chunks[q.chunk_id - 1].chunk_id,
                        start=chunks[q.chunk_id - 1].start,
                        end=chunks[q.chunk_id - 1].end,
                        quote=q.text,
                    )
                    for q in result.quotes
                ]
                return AskResult(answer=result.answer, citations=citations, refused=False)
            problem = "These quotes are not word for word in their passage: " + "; ".join(
                f'[{q.chunk_id}] "{q.text}"' for q in bad
            )
        logger.warning("answer attempt %s rejected", attempt)  # never log the question or note text
        messages = messages + [
            {"role": "assistant", "content": raw},
            {"role": "user", "content": f"{problem} Fix it: copy quotes exactly from the passages. Return JSON only."},
        ]
    return AskResult(answer=REFUSAL, citations=[], refused=True)
