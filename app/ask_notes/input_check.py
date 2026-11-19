"""Sort a question before any search runs: in scope, out of scope, or urgent."""

import logging
import re
from typing import Literal

from pydantic import BaseModel, ValidationError

from app.core.llm import chat

logger = logging.getLogger(__name__)

Scope = Literal["in_scope", "out_of_scope", "urgent"]

OUT_OF_SCOPE = "I can only answer questions about your injury notes."
URGENT = (
    "This sounds like it could be an emergency. Call your local emergency number (112 in Europe, 911 in the US) "
    "or go to the nearest emergency room now. This app can't give medical help."
)

# Plain-code safety net, checked first: these words always mean urgent, whatever the model says.
URGENT_WORDS = re.compile(
    r"chest pain|can'?t breathe|cannot breathe|trouble breathing|short(ness)? of breath|unconscious|passed out"
    r"|won'?t stop bleeding|bleeding (a lot|heavily)|heavy bleeding|overdose|suicid|kill myself|end my life"
    r"|stroke|face is drooping|seizure|severe allergic|throat (is )?(closing|swelling)",
    re.IGNORECASE,
)

SYSTEM = """You sort questions sent to an app that answers questions from the user's own injury notes.
Return JSON: {"scope": "in_scope" | "out_of_scope" | "urgent"}
- urgent: the user describes a possible medical emergency happening now (severe pain, breathing problems,
  heavy bleeding, losing consciousness, thoughts of self-harm).
- in_scope: any question about the user themselves: their injuries, pain, body, health, treatments, doctors,
  accidents or exercise. Questions with "I", "my" or "me" about the body or health are in_scope,
  even if the notes might not contain the answer.
- out_of_scope: only questions clearly unrelated to the user's own body and health
  (general knowledge, coding, news, weather, jokes, other people's matters).
If you are not sure, answer in_scope.

Examples:
"Did I bump my head on something?" -> {"scope": "in_scope"}
"What is my blood type?" -> {"scope": "in_scope"}
"Which injuries came back more than once?" -> {"scope": "in_scope"}
"What is the capital of France?" -> {"scope": "out_of_scope"}
"Write a Python function that sorts a list." -> {"scope": "out_of_scope"}
"I have chest pain right now" -> {"scope": "urgent"}"""


class ScopeReply(BaseModel):
    scope: Scope


def check_question(question: str) -> Scope:
    """Urgent words first (plain code), then the model sorts the rest."""
    if URGENT_WORDS.search(question):
        return "urgent"
    raw = chat([{"role": "system", "content": SYSTEM}, {"role": "user", "content": question}])
    try:
        return ScopeReply.model_validate_json(raw).scope
    except ValidationError:
        # Fail open: the threshold and "not found" still stop an answer that isn't in the notes.
        logger.warning("input check reply was invalid, treating the question as in scope")
        return "in_scope"


def scope_message(scope: Scope) -> str:
    return URGENT if scope == "urgent" else OUT_OF_SCOPE
