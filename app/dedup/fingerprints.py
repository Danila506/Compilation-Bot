import hashlib
import re


def content_hash(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def tiny_simhash(text: str) -> int:
    tokens = re.findall(r"[a-zA-Z0-9_]+", text.lower())
    if not tokens:
        return 0

    vector = [0] * 32
    for token in tokens:
        h = int(hashlib.md5(token.encode("utf-8")).hexdigest()[:8], 16)
        for i in range(32):
            bit = 1 if (h >> i) & 1 else -1
            vector[i] += bit

    result = 0
    for i, value in enumerate(vector):
        if value > 0:
            result |= 1 << i
    return result

