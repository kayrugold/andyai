from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, List, Any

TASTE_FILE = "taste_memory.json"

PREFERENCE_WORDS = (
    "misty",
    "quiet",
    "moon",
    "river",
    "night",
    "light",
    "beneath",
    "under",
    "reflecting",
    "illuminating",
    "wolf",
    "glowing",
    "calm",
)


def _now_ts() -> int:
    return int(time.time())


def load_taste_memory() -> List[Dict[str, Any]]:
    p = Path(TASTE_FILE)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []


def save_taste_memory(items: List[Dict[str, Any]]) -> None:
    Path(TASTE_FILE).write_text(
        json.dumps(items, indent=2),
        encoding="utf-8",
    )


def _tokenize_scene(scene: str) -> List[str]:
    words = []
    for w in str(scene).lower().replace(",", " ").replace(".", " ").split():
        w = w.strip()
        if w:
            words.append(w)
    return words


def reinforce_taste_from_scene(scene: str, score: float) -> List[Dict[str, Any]]:
    items = load_taste_memory()
    by_word: Dict[str, Dict[str, Any]] = {
        str(item.get("token", "")): item for item in items
    }

    words = _tokenize_scene(scene)
    seen = set()

    for word in words:
        if word not in PREFERENCE_WORDS:
            continue
        if word in seen:
            continue
        seen.add(word)

        existing = by_word.get(word)
        if existing:
            existing["count"] = int(existing.get("count", 0)) + 1
            existing["strength"] = round(float(existing.get("strength", 0.0)) + float(score), 3)
            existing["last_seen"] = _now_ts()
        else:
            by_word[word] = {
                "token": word,
                "count": 1,
                "strength": round(float(score), 3),
                "created_at": _now_ts(),
                "last_seen": _now_ts(),
            }

    out = list(by_word.values())
    out.sort(key=lambda x: (-float(x.get("strength", 0.0)), -int(x.get("count", 0)), x.get("token", "")))
    save_taste_memory(out)
    return out


def taste_bias_score(scene: str) -> float:
    items = load_taste_memory()
    if not items:
        return 0.0

    by_word = {str(item.get("token", "")): item for item in items}
    words = _tokenize_scene(scene)

    score = 0.0
    seen = set()

    for word in words:
        if word in seen:
            continue
        seen.add(word)

        item = by_word.get(word)
        if not item:
            continue

        strength = float(item.get("strength", 0.0) or 0.0)
        count = int(item.get("count", 0) or 0)

        score += min(1.25, 0.08 * count + 0.015 * strength)

    return round(score, 6)


def taste_memory_text(limit: int = 20) -> str:
    items = load_taste_memory()

    lines = ["TASTE MEMORY", ""]
    if not items:
        lines.append("No taste preferences learned yet.")
        return "\n".join(lines)

    for i, item in enumerate(items[:limit], start=1):
        lines.append(
            f"{i:02d}. token={item.get('token')} | count={item.get('count', 0)} | strength={item.get('strength', 0)}"
        )

    return "\n".join(lines)


def taste_summary_text() -> str:
    items = load_taste_memory()
    if not items:
        return "\n".join([
            "TASTE SUMMARY",
            "",
            "No taste preferences learned yet.",
        ])

    top = items[0]
    lines = [
        "TASTE SUMMARY",
        "",
        f"Top Preference: {top.get('token', '')}",
        f"Count: {top.get('count', 0)}",
        f"Strength: {top.get('strength', 0)}",
    ]
    return "\n".join(lines)


def build_taste_memory_from_scene(scene: str, score: float) -> str:
    items = reinforce_taste_from_scene(scene, score)
    return "\n".join([
        "TASTE BUILD",
        "",
        f"Scene: {scene}",
        f"Score: {round(score, 3)}",
        f"Updated Tokens: {len(items)}",
    ])
