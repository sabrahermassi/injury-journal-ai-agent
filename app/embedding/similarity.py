import math


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """How similar two vectors are in direction: 1 same, 0 unrelated, -1 opposite."""
    if len(a) != len(b):
        raise ValueError(f"Vectors have different lengths: {len(a)} and {len(b)}")

    dot = sum(x * y for x, y in zip(a, b))
    length_a = math.sqrt(sum(x * x for x in a))
    length_b = math.sqrt(sum(y * y for y in b))

    if length_a == 0 or length_b == 0:
        raise ValueError("Cannot compare a zero vector: it has no direction")

    return dot / (length_a * length_b)
