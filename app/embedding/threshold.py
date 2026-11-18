from pathlib import Path

from pydantic import TypeAdapter

from app.embedding.benchmark import EvalQuery, LabelledNote
from app.embedding.embed import embed_documents, embed_query
from app.embedding.similarity import cosine_similarity
from app.env import require_env


def suggest_threshold(good_scores: list[float], bad_scores: list[float]) -> float | None:
    """Halfway between the lowest good score and the highest bad score. None if they overlap."""
    lowest_good = min(good_scores)
    highest_bad = max(bad_scores)
    if lowest_good <= highest_bad:
        return None
    return round((lowest_good + highest_bad) / 2, 2)


def main() -> None:
    model = require_env("EMBED_MODEL")
    notes = TypeAdapter(list[LabelledNote]).validate_json(Path("eval/notes.json").read_text(encoding="utf-8"))
    queries = TypeAdapter(list[EvalQuery]).validate_json(Path("eval/queries.json").read_text(encoding="utf-8"))
    off_topic = TypeAdapter(list[str]).validate_json(Path("eval/off_topic.json").read_text(encoding="utf-8"))

    note_vectors = embed_documents([note.note for note in notes], model)

    # Good: the score of the right note for each injury question.
    print("Injury questions (score of the right note):")
    good_scores = []
    for query in queries:
        query_vector = embed_query(query.query, model)
        score = max(cosine_similarity(query_vector, note_vectors[i]) for i in query.relevant)
        good_scores.append(score)
        print(f"  {score:.2f}  {query.query}")

    # Bad: the best score any note gets for an off-topic question. It should be low.
    print("Off-topic questions (best score of any note):")
    bad_scores = []
    for text in off_topic:
        query_vector = embed_query(text, model)
        score = max(cosine_similarity(query_vector, vector) for vector in note_vectors)
        bad_scores.append(score)
        print(f"  {score:.2f}  {text}")

    print(f"Lowest injury score: {min(good_scores):.2f}")
    print(f"Highest off-topic score: {max(bad_scores):.2f}")
    threshold = suggest_threshold(good_scores, bad_scores)
    if threshold is None:
        print("The scores overlap: no threshold separates them cleanly.")
    else:
        print(f"Suggested threshold: {threshold}")


if __name__ == "__main__":
    main()
