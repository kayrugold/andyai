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

def top_k(db: List[Dict[str, Any]], query_emb: List[float], k: int = 5) -> List[Tuple[float, Dict[str, Any]]]:
    scored = []
    for e in db:
        s = cosine(query_emb, e.get("embedding", []))
        scored.append((s, e))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:k]