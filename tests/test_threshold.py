from app.embedding.threshold import suggest_threshold


def test_threshold_is_halfway_between_good_and_bad() -> None:
    assert suggest_threshold([0.7, 0.8], [0.3, 0.5]) == 0.6


def test_overlapping_scores_give_no_threshold() -> None:
    assert suggest_threshold([0.4, 0.8], [0.3, 0.5]) is None
