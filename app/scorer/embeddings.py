from __future__ import annotations

import hashlib
import math
import re


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9_+-]{2,}", text.lower())


def _vectorize(text: str, dim: int = 256) -> list[float]:
    vec = [0.0] * dim
    tokens = _tokenize(text)
    if not tokens:
        return vec

    for token in tokens:
        digest = hashlib.md5(token.encode("utf-8")).hexdigest()
        idx = int(digest[:8], 16) % dim
        sign = 1.0 if (int(digest[8:10], 16) % 2 == 0) else -1.0
        vec[idx] += sign

    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


def cosine_similarity(a_text: str, b_text: str, dim: int = 256) -> float:
    a = _vectorize(a_text, dim=dim)
    b = _vectorize(b_text, dim=dim)
    dot = sum(x * y for x, y in zip(a, b))
    return max(-1.0, min(1.0, dot))

