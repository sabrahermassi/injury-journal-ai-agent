"""Split a long note into small overlapping chunks that remember where they came from."""

import re
from dataclasses import dataclass

# A sentence: text up to and including . ! or ?, or up to a line break, or to the end of the note.
SENTENCE = re.compile(r"[^.!?\n]*(?:[.!?]+|$)", re.MULTILINE)


@dataclass(frozen=True)
class Chunk:
    note_id: int
    position: int  # 0 for the first chunk of the note, then 1, 2, ...
    start: int  # character offset in the note where the chunk starts
    end: int  # offset just after the chunk ends, so note[start:end] == text
    text: str


def trim(text: str, start: int, end: int) -> tuple[int, int]:
    """Move start and end inwards past any spaces or line breaks."""
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def sentence_spans(text: str, max_chars: int) -> list[tuple[int, int]]:
    """(start, end) of each sentence, without surrounding spaces. Sentences longer than max_chars are cut."""
    spans = []
    for match in SENTENCE.finditer(text):
        start, end = trim(text, match.start(), match.end())
        while end - start > max_chars:
            # Cut a piece of max_chars, trim it, and keep it only if something is left.
            piece_start, piece_end = trim(text, start, start + max_chars)
            if piece_start < piece_end:
                spans.append((piece_start, piece_end))
            start, end = trim(text, start + max_chars, end)
        if start < end:
            spans.append((start, end))
    return spans


def chunk_note(note_id: int, text: str, max_chars: int = 600, overlap: int = 1) -> list[Chunk]:
    """Group whole sentences into chunks of at most max_chars.

    Overlap is best effort: each chunk starts `overlap` sentences before the end of the one before,
    but always at least one sentence further on, and only as much overlap as still leaves room
    for the next new sentence. So every chunk adds new text, and some chunks have no overlap.
    """
    if max_chars <= 0 or overlap < 0:
        raise ValueError("max_chars must be positive and overlap not negative")
    spans = sentence_spans(text, max_chars)
    chunks: list[Chunk] = []
    first = 0
    while first < len(spans):
        # Grow the chunk while it still fits in max_chars.
        last = first
        while last + 1 < len(spans) and spans[last + 1][1] - spans[first][0] <= max_chars:
            last += 1
        start, end = spans[first][0], spans[last][1]
        chunks.append(Chunk(note_id, len(chunks), start, end, text[start:end]))
        if last + 1 >= len(spans):
            break
        # Next chunk starts `overlap` sentences back, but always at least 1 sentence forward.
        first = max(last + 1 - overlap, first + 1)
        # Drop overlap sentences until the next chunk can also fit the next new sentence,
        # so every chunk adds new text and is never a copy of part of the one before.
        while first <= last and spans[last + 1][1] - spans[first][0] > max_chars:
            first += 1
    return chunks
