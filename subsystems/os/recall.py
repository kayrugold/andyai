import math
from typing import Any, Dict, List, Tuple


def cosine(a: List[float], b: List[float]) -> float:
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    dot = 0.0
    ma = 0.0
    mb = 0.0
    for i in range(n):
        av = float(a[i])
        bv = float(b[i])
        dot += av * bv
        ma += av * av
        mb += bv * bv
    denom = math.sqrt(ma) * math.sqrt(mb)
    return float(dot / denom) if denom else 0.0


def top_k(
    db: List[Dict[str, Any]],
    query_emb: List[float],
    k: int = 5,
) -> List[Tuple[float, Dict[str, Any]]]:
    scored = []
    for entry in db:
        score = cosine(query_emb, entry.get("embedding", []))
        scored.append((score, entry))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:k]
