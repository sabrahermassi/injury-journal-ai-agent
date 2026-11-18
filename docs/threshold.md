# Score threshold

|                  |                                                                           |
| ---------------- | ------------------------------------------------------------------------- |
| **Value**        | `MIN_SCORE = 0.53` in `app/search.py`, chosen by experiment               |
| **What it does** | Notes scoring below it are not returned                                   |
| **Why**          | Without it, search always returns 5 notes, even for "best pizza in Paris" |

## The problem

Cosine search always ranks **every** note, so there is always a "top 5", even when nothing fits. An off-topic question gets 5 injury notes with low scores, and they look like real results.

## The fix

```mermaid
flowchart LR
    Q["Search"]
    F["Filter fields"]
    C["Cosine score"]
    M["Min score 0.53"]
    T["Top 5 notes"]

    Q --> F
    F --> C
    C --> M
    M --> T
```

- **Min score 0.53**: results below 0.53 are dropped before sorting.
- If nothing is left, search returns an empty list: "no matching notes".

## The experiment

`app/embedding/threshold.py` measures two groups of scores against the 10 test notes:

- **Good:** for each of the 12 injury questions (`eval/queries.json`), the score of the right note. These should be high.
- **Bad:** for each of the 8 off-topic questions (`eval/off_topic.json`), the best score any note gets. These should be low.

The threshold goes halfway between the lowest good score and the highest bad score.

```bash
uv run --env-file .env python -m app.embedding.threshold
```

## Results (nomic-embed-text)

| Group                   | Lowest | Highest |
| ----------------------- | ------ | ------- |
| Injury questions (12)   | 0.55   | 0.76    |
| Off-topic questions (8) | 0.40   | 0.52    |

- Lowest injury score: 0.55, "my head hurts".
- Highest off-topic score: 0.52, "weather forecast for tomorrow".
- **Threshold: 0.53**, halfway between them.

## Rules

1. **A threshold belongs to one model.** Each model has its own score range. Change the model, rerun the experiment.
2. **Scores are not percentages.** 0.53 doesn't mean "53% relevant". It only works relative to other scores from the same model.
3. **The gap is small (0.03).** Rerun with real notes. If good and bad scores overlap, no threshold is perfect: you choose between missing some good notes (higher) and showing some bad ones (lower).

## In our code

- `search(..., min_score=MIN_SCORE)` in `app/search.py`.
- `POST /search` accepts `min_score`, so you can try other values on the `/docs` page.

| Test                                        | Checks                                 |
| ------------------------------------------- | -------------------------------------- |
| `test_min_score_drops_weak_matches`         | notes below the threshold are dropped  |
| `test_only_weak_matches_returns_nothing`    | nothing above the threshold gives `[]` |
| `test_threshold_is_halfway...`              | the suggested value is halfway         |
| `test_overlapping_scores_give_no_threshold` | overlap gives no suggestion            |
