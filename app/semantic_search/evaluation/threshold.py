from pathlib import Path

from pydantic import TypeAdapter

from app.semantic_search.evaluation.embedding_benchmark import EvalQuery, LabelledNote
from app.core.embed import embed_documents, embed_query
from app.core.similarity import cosine_similarity
from app.core.env import require_env


def suggest_threshold(good_scores: list[float], bad_scores: list[float]) -> float | None:
    """Halfway between the lowest good score and the highest bad score. None if they overlap."""
    lowest_good = min(good_scores)
    highest_bad = max(bad_scores)
    if lowest_good <= highest_bad:
        return None
    return round((lowest_good + highest_bad) / 2, 2)


def tradeoff(good_scores: list[float], bad_scores: list[float], threshold: float) -> tuple[int, int]:
    """At this threshold: how many injury questions still find their note, how many off-topic ones are blocked."""
    kept = sum(1 for score in good_scores if score >= threshold)
    blocked = sum(1 for score in bad_scores if score < threshold)
    return kept, blocked


def main() -> None:
    model = require_env("EMBED_MODEL")
    notes = TypeAdapter(list[LabelledNote]).validate_json(Path("eval/semantic_search/notes.json").read_text(encoding="utf-8"))
    queries = TypeAdapter(list[EvalQuery]).validate_json(Path("eval/semantic_search/queries.json").read_text(encoding="utf-8"))
    off_topic = TypeAdapter(list[str]).validate_json(Path("eval/semantic_search/off_topic.json").read_text(encoding="utf-8"))

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

    # What each threshold would cost: good notes lost vs off-topic questions blocked.
    print("Threshold | injury questions kept | off-topic blocked")
    for step in range(50, 71, 2):
        candidate = step / 100
        kept, blocked = tradeoff(good_scores, bad_scores, candidate)
        print(f"  {candidate:.2f}    | {kept}/{len(good_scores)}                 | {blocked}/{len(bad_scores)}")


if __name__ == "__main__":
    main()
