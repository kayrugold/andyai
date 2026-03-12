import hashlib
import math
from typing import List, Optional
from llm_gemini import GeminiClient

class Embedder:
    """
    Lightweight embedder that works offline.
    If Gemini is available later, you can swap to a real embedding model.
    For now: stable hashing -> vector (good enough for similarity + recall).
    """
    def __init__(self, gemini: Optional[GeminiClient] = None, dim: int = 96) -> None:
        self.gemini = gemini
        self.dim = dim

    def embed(self, text: str) -> List[float]:
        text = (text or "").strip().lower()
        if not text:
            return [0.0] * self.dim

        # hash into buckets
        v = [0.0] * self.dim
        for token in text.split():
            h = hashlib.sha256(token.encode("utf-8")).digest()
            for i in range(0, len(h), 2):
                idx = (h[i] << 8 | h[i + 1]) % self.dim
                v[idx] += 1.0

        # normalize
        mag = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / mag for x in v]