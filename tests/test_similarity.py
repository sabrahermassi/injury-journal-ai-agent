import pytest

from app.embedding.similarity import cosine_similarity


def test_identical_vectors_score_1() -> None:
    assert cosine_similarity([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == pytest.approx(1.0)


def test_orthogonal_vectors_score_0() -> None:
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_opposite_vectors_score_minus_1() -> None:
    assert cosine_similarity([1.0, 2.0], [-1.0, -2.0]) == pytest.approx(-1.0)


def test_scaling_does_not_change_the_score() -> None:
    assert cosine_similarity([1.0, 2.0], [10.0, 20.0]) == pytest.approx(1.0)


def test_different_lengths_raise() -> None:
    with pytest.raises(ValueError):
        cosine_similarity([1.0, 2.0], [1.0, 2.0, 3.0])


def test_zero_vector_raises() -> None:
    with pytest.raises(ValueError):
        cosine_similarity([0.0, 0.0], [1.0, 2.0])
