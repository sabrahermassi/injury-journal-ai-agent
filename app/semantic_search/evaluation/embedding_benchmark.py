import time
from pathlib import Path

from pydantic import BaseModel, TypeAdapter

from app.core.embed import embed_documents, embed_query
from app.core.similarity import cosine_similarity
from app.semantic_search.extraction.schema import Injury

MODELS = ["nomic-embed-text", "mxbai-embed-large", "all-minilm"]
TEXT_OPTIONS = ["raw", "fields", "both"]
TOP_K = 3


class LabelledNote(BaseModel):
    note: str
    expected: Injury


class EvalQuery(BaseModel):
    query: str
    relevant: list[int]  # positions of the right notes in eval/semantic_search/notes.json


def fields_text(fields: Injury) -> str:
    """Turn the fields into one line of text, skipping empty ones."""
    values = fields.model_dump()
    return "; ".join(f"{name.replace('_', ' ')}: {value}" for name, value in values.items() if value is not None)


def text_to_embed(note: LabelledNote, option: str) -> str:
    """The text that gets embedded for one note, depending on the option."""
    if option == "raw":
        return note.note
    if option == "fields":
        return fields_text(note.expected)
    return f"{note.note}\n{fields_text(note.expected)}"


def rank(query_vector: list[float], note_vectors: list[list[float]]) -> list[int]:
    """Note positions sorted from most to least similar to the query."""
    scores = [cosine_similarity(query_vector, vector) for vector in note_vectors]
    return sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)


def main() -> None:
    notes = TypeAdapter(list[LabelledNote]).validate_json(Path("eval/semantic_search/notes.json").read_text(encoding="utf-8"))
    queries = TypeAdapter(list[EvalQuery]).validate_json(Path("eval/semantic_search/queries.json").read_text(encoding="utf-8"))

    for model in MODELS:
        query_vectors = [embed_query(query.query, model) for query in queries]

        for option in TEXT_OPTIONS:
            start_time = time.perf_counter()
            note_vectors = embed_documents([text_to_embed(note, option) for note in notes], model)
            seconds = time.perf_counter() - start_time

            top1 = 0
            top3 = 0
            for query, query_vector in zip(queries, query_vectors, strict=True):
                ranking = rank(query_vector, note_vectors)
                if ranking[0] in query.relevant:
                    top1 += 1
                if any(position in query.relevant for position in ranking[:TOP_K]):
                    top3 += 1

            total = len(queries)
            print(f"{model} | {option} | top-1 {top1}/{total} | top-3 {top3}/{total} | {seconds:.2f}s")


if __name__ == "__main__":
    main()
