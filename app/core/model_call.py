"""Calls to Ollama that fail fast and clearly: a timeout, one retry after a pause, then a clear error."""

import logging
import time
from collections.abc import Callable
from typing import TypeVar

import httpx
from ollama import ResponseError

logger = logging.getLogger(__name__)

T = TypeVar("T")

TIMEOUT_SECONDS = 60.0  # the longest we wait for one model answer
RETRY_PAUSE_SECONDS = 1.0  # wait before the one retry, so a busy model can recover (backoff)


class ModelUnavailableError(Exception):
    """Ollama is down, unreachable or too slow, even after one retry."""


def pause(seconds: float) -> None:
    """Wait before the retry. Its own function, so tests can replace it and run instantly."""
    time.sleep(seconds)


def is_temporary(error: Exception) -> bool:
    """Worth retrying: the model timed out, can't be reached, or had a server error (5xx).

    Not worth retrying: our own mistakes, like a model name that doesn't exist (404).
    """
    if isinstance(error, (httpx.TimeoutException, httpx.TransportError, ConnectionError)):
        return True
    return isinstance(error, ResponseError) and error.status_code >= 500


def call_model(call: Callable[[], T], what: str) -> T:
    """Run one model call. If it fails for a temporary reason, wait and try once more."""
    try:
        return call()
    except Exception as error:
        if not is_temporary(error):
            raise
        logger.warning("%s call failed (%s), retrying once", what, type(error).__name__)
    pause(RETRY_PAUSE_SECONDS)
    try:
        return call()
    except Exception as error:
        if not is_temporary(error):
            raise
        raise ModelUnavailableError(f"The {what} model is not responding. Is Ollama running?") from error
