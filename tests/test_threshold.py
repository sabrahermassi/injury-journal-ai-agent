from app.embedding.threshold import suggest_threshold, tradeoff


def test_threshold_is_halfway_between_good_and_bad() -> None:
    assert suggest_threshold([0.7, 0.8], [0.3, 0.5]) == 0.6


def test_overlapping_scores_give_no_threshold() -> None:
    assert suggest_threshold([0.4, 0.8], [0.3, 0.5]) is None


def test_tradeoff_counts_kept_and_blocked() -> None:
    # Good 0.55 is lost at 0.6; bad 0.4 and 0.52 are blocked, 0.65 is not.
    assert tradeoff([0.55, 0.7, 0.8], [0.4, 0.52, 0.65], 0.6) == (2, 2)
