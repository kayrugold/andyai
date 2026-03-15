from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, List, Any

from subsystems.os.concept_clusters import load_clusters, top_cluster_terms, cluster_reinforcement_text
from subsystems.os.dream_engine import latest_dream
from subsystems.os.identity_notes import latest_identity_note_text

THEME_FILE = "theme_memory.json"

PROMOTION_SCORE_THRESHOLD = 2.5
PROMOTION_COUNT_THRESHOLD = 0.5


def _now_ts() -> int:
    return int(time.time())


def load_themes() -> List[Dict[str, Any]]:
    p = Path(THEME_FILE)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []


def save_themes(items: List[Dict[str, Any]]) -> None:
    Path(THEME_FILE).write_text(
        json.dumps(items, indent=2),
        encoding="utf-8",
    )


def _theme_key(terms: List[str]) -> str:
    return "|".join(sorted(str(x).strip().lower() for x in terms if str(x).strip()))


def _extract_theme_sources(terms: List[str]) -> List[str]:
    sources = ["cluster"]

    dream = latest_dream()
    if dream:
        blob = " ".join(str(x) for x in (dream.get("fragments", []) or []))
        blob += " " + str(dream.get("identity_note", "") or "")
        low = blob.lower()
        if all(term.lower() in low for term in terms[: min(3, len(terms))]):
            sources.append("dream")

    ident = latest_identity_note_text().lower()
    if ident and any(term.lower() in ident for term in terms):
        sources.append("identity")

    return sorted(set(sources))


def build_theme_memory() -> List[Dict[str, Any]]:
    clusters = load_clusters()
    current = load_themes()

    by_key: Dict[str, Dict[str, Any]] = {
        _theme_key(item.get("theme", [])): item for item in current
    }

    for cluster in clusters:
        terms = list(cluster.get("terms", []))
        if not terms:
            continue

        score = float(cluster.get("score", 0.0) or 0.0)
        count = float(cluster.get("count", 0.0) or 0.0)

        if score < PROMOTION_SCORE_THRESHOLD and count < PROMOTION_COUNT_THRESHOLD:
            continue

        theme_terms = terms[:4]
        key = _theme_key(theme_terms)
        sources = _extract_theme_sources(theme_terms)

        existing = by_key.get(key)
        if existing:
            existing["strength"] = round(max(float(existing.get("strength", 0.0)), score), 3)
            existing["count_weight"] = round(max(float(existing.get("count_weight", 0.0)), count), 3)
            existing_sources = set(existing.get("sources", []))
            existing["sources"] = sorted(existing_sources.union(sources))
            existing["last_seen"] = _now_ts()
            existing["reinforcements"] = int(existing.get("reinforcements", 0))
        else:
            by_key[key] = {
                "theme": theme_terms,
                "strength": round(score, 3),
                "count_weight": round(count, 3),
                "sources": sources,
                "status": "adaptive",
                "reinforcements": 0,
                "created_at": _now_ts(),
                "last_seen": _now_ts(),
            }

    items = list(by_key.values())
    items.sort(key=lambda x: (-float(x.get("strength", 0.0)), -float(x.get("count_weight", 0.0)), x.get("theme", [])))
    save_themes(items)
    return items


def themes_text(limit: int = 20) -> str:
    items = load_themes()

    lines = ["THEME MEMORY", ""]
    if not items:
        lines.append("No promoted themes yet.")
        return "\n".join(lines)

    for i, item in enumerate(items[:limit], start=1):
        theme = ", ".join(item.get("theme", []))
        strength = item.get("strength", 0)
        status = item.get("status", "adaptive")
        sources = ",".join(item.get("sources", []))
        reinf = item.get("reinforcements", 0)
        lines.append(
            f"{i:02d}. strength={strength} | status={status} | reinf={reinf} | sources={sources} | {theme}"
        )

    return "\n".join(lines)


def top_theme() -> Dict[str, Any] | None:
    items = load_themes()
    return items[0] if items else None


def theme_summary_text() -> str:
    item = top_theme()
    if not item:
        return "\n".join([
            "THEME SUMMARY",
            "",
            "No promoted themes yet.",
        ])

    lines = [
        "THEME SUMMARY",
        "",
        f"Top Theme: {', '.join(item.get('theme', []))}",
        f"Strength: {item.get('strength', 0)}",
        f"Count Weight: {item.get('count_weight', 0)}",
        f"Status: {item.get('status', 'adaptive')}",
        f"Sources: {', '.join(item.get('sources', []))}",
        f"Reinforcements: {item.get('reinforcements', 0)}",
    ]
    return "\n".join(lines)


def theme_bridge_text() -> str:
    item = top_theme()
    if not item:
        return "\n".join([
            "THEME BRIDGE",
            "",
            "No theme bridge available yet.",
        ])

    theme = list(item.get("theme", []))[:4]
    return "\n".join([
        "THEME BRIDGE",
        "",
        "draw " + " ".join(theme),
    ])


def theme_reinforcement_text() -> str:
    item = top_theme()
    if item:
        return " ".join(list(item.get("theme", []))[:4])

    return cluster_reinforcement_text()


def reinforce_top_theme() -> str:
    items = load_themes()
    if not items:
        return ""

    items[0]["reinforcements"] = int(items[0].get("reinforcements", 0)) + 1
    items[0]["last_seen"] = _now_ts()

    reinf = int(items[0]["reinforcements"])
    if reinf >= 6:
        items[0]["status"] = "stable"
    elif reinf >= 2:
        items[0]["status"] = "adaptive"
    else:
        items[0]["status"] = "experimental"

    save_themes(items)
    return " ".join(list(items[0].get("theme", []))[:4])
