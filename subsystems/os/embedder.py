import hashlib
import math
from typing import List, Optional

from plugins.mentors.gemini import GeminiClient


class Embedder:
    """
    Lightweight embedder that works offline.
    If Gemini is available later, this can be swapped to a real embedding model.
    """

    def __init__(self, gemini: Optional[GeminiClient] = None, dim: int = 96) -> None:
        self.gemini = gemini
        self.dim = dim

    def embed(self, text: str) -> List[float]:
        text = (text or "").strip().lower()
        if not text:
            return [0.0] * self.dim

        vector = [0.0] * self.dim
        for token in text.split():
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for i in range(0, len(digest), 2):
                idx = (digest[i] << 8 | digest[i + 1]) % self.dim
                vector[idx] += 1.0

        magnitude = math.sqrt(sum(x * x for x in vector)) or 1.0
        return [x / magnitude for x in vector]
