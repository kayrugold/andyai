from __future__ import annotations

import random
from typing import List

from subsystems.os.theme_memory import top_theme
from subsystems.os.aesthetic_engine import choose_most_aesthetic
from subsystems.os.taste_memory import taste_bias_score, reinforce_taste_from_scene


def generate_scene_variations(max_variations: int = 5) -> List[str]:
    theme = top_theme()

    if not theme:
        return []

    terms = list(theme.get("theme", []))
    if not terms:
        return []

    variations: List[str] = []

    if len(terms) >= 4:
        a, b, c, d = terms[:4]

        variations.append(f"{b} reflecting on {d} at {c}")
        variations.append(f"{d} under the {b} light")
        variations.append(f"misty {d} beneath the {b}")
        variations.append(f"{b} illuminating the {d}")
        variations.append(f"quiet {d} under the {b}")

        if a not in {b, c, d}:
            variations.append(f"{a} beside the {d} under the {b}")
            variations.append(f"{a} watching the {b} over the {d}")

    elif len(terms) == 3:
        a, b, c = terms
        variations.append(f"{a} beneath the {b}")
        variations.append(f"{b} over the {c}")
        variations.append(f"{c} beneath the {b}")
        variations.append(f"{a} near the {c}")
        variations.append(f"{b} lighting the {c}")

    elif len(terms) == 2:
        a, b = terms
        variations.append(f"{a} and {b}")
        variations.append(f"{a} near {b}")
        variations.append(f"{b} surrounding {a}")

    else:
        variations.append(" ".join(terms))

    # remove duplicates while preserving order
    deduped: List[str] = []
    seen = set()
    for v in variations:
        key = v.strip().lower()
        if key and key not in seen:
            seen.add(key)
            deduped.append(v)

    random.shuffle(deduped)
    return deduped[:max_variations]


def choose_best_scene(variations: List[str]) -> str:
    if not variations:
        return ""

    best = ""
    best_score = -1e18

    for v in variations:
        base_scene, base_score = choose_most_aesthetic([v])
        total_score = float(base_score) + float(taste_bias_score(v))

        if total_score > best_score:
            best_score = total_score
            best = v

    return best


def imagination_bridge() -> str:
    variations = generate_scene_variations()

    if not variations:
        return "\n".join([
            "IMAGINATION ENGINE",
            "",
            "No scene variations available.",
        ])

    best, score = choose_most_aesthetic(variations)
    reinforce_taste_from_scene(best, score)

    lines = [
        "IMAGINATION ENGINE",
        "",
        "Scene Variations:",
        "",
    ]

    for v in variations:
        lines.append(f"- {v}")

    lines.extend([
        f"Aesthetic Score: {round(score,3)}",
        "",
        "Chosen Scene:",
        best,
        "",
        "Art Prompt:",
        f"draw {best}",
    ])

    return "\n".join(lines)


def imagination_prompt() -> str:
    variations = generate_scene_variations()

    if not variations:
        return ""

    return choose_best_scene(variations)
