from __future__ import annotations

from typing import List, Tuple

ENVIRONMENT_WORDS = {
    "moon",
    "river",
    "night",
    "light",
    "misty",
    "sky",
    "stars",
    "fog",
}

ENTITY_WORDS = {
    "wolf",
    "dog",
    "person",
    "truck",
    "bird",
}

ATMOSPHERE_WORDS = {
    "quiet",
    "misty",
    "soft",
    "glowing",
    "dark",
    "calm",
}

def score_scene(scene: str) -> float:

    words = scene.lower().split()

    score = 0.0

    # length bonus
    score += len(scene) * 0.01

    # environment richness
    for w in words:
        if w in ENVIRONMENT_WORDS:
            score += 0.4

    # atmospheric tone
    for w in words:
        if w in ATMOSPHERE_WORDS:
            score += 0.35

    # entity anchor
    for w in words:
        if w in ENTITY_WORDS:
            score += 0.6

    # composition bonus
    if "under" in words or "beneath" in words:
        score += 0.25

    if "reflecting" in words:
        score += 0.35

    return score


def choose_most_aesthetic(variations: List[str]) -> Tuple[str, float]:

    best_scene = ""
    best_score = -1.0

    for v in variations:
        s = score_scene(v)

        if s > best_score:
            best_score = s
            best_scene = v

    return best_scene, best_score
