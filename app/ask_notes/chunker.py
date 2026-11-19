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


def sentence_spans(text: str, max_chars: int) -> list[tuple[int, int]]:
    """(start, end) of each sentence, without surrounding spaces. Sentences longer than max_chars are cut."""
    spans = []
    for match in SENTENCE.finditer(text):
        start, end = match.start(), match.end()
        while start < end and text[start].isspace():
            start += 1
        while end > start and text[end - 1].isspace():
            end -= 1
        while end - start > max_chars:
            spans.append((start, start + max_chars))
            start += max_chars
        if start < end:
            spans.append((start, end))
    return spans


def chunk_note(note_id: int, text: str, max_chars: int = 600, overlap: int = 1) -> list[Chunk]:
    """Group whole sentences into chunks of at most max_chars. Each chunk repeats the last `overlap` sentences of the one before."""
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
    return chunks
