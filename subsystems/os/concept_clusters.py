from pathlib import Path
import json
from collections import defaultdict
from itertools import combinations
from typing import Dict, List, Tuple

from subsystems.linguistic.sentence_memory import load_sentence_memory
from subsystems.os.dream_engine import latest_dream
from subsystems.os.identity_notes import latest_identity_note_text

CLUSTER_FILE = "concept_clusters.json"

TRACKED_TERMS = (
    "wolf",
    "moon",
    "night",
    "river",
    "tree",
    "mountain",
    "light",
    "dog",
    "run",
    "runs",
    "running",
    "black",
    "sun",
    "storm",
    "weather",
    "road",
    "truck",
)

NORMALIZE_MAP = {
    "runs": "run",
    "running": "run",
}

PAIR_BONUS = 0.35
RECENCY_STEP = 0.12
MAX_CLUSTER_TERMS = 5

DREAM_BONUS = 0.55
IDENTITY_BONUS = 0.40
FOUR_TERM_SCENE_BONUS = 0.30

SCENIC_TERMS = {"wolf", "moon", "river", "night", "tree", "mountain", "light", "sun"}
ANCHOR_TERMS = {"wolf", "dog", "truck", "storm", "weather"}
ENVIRONMENT_TERMS = {"moon", "river", "night", "tree", "mountain", "light", "sun", "road"}

LAST_PAIR_COUNTER: Dict[Tuple[str, str], float] = {}


def load_clusters() -> List[Dict]:
    p = Path(CLUSTER_FILE)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []


def save_clusters(items: List[Dict]) -> None:
    Path(CLUSTER_FILE).write_text(
        json.dumps(items, indent=2),
        encoding="utf-8",
    )


def _normalize_term(term: str) -> str:
    t = str(term).lower().strip()
    return NORMALIZE_MAP.get(t, t)


def _extract_terms(text: str) -> List[str]:
    low = str(text).lower()
    found = []

    for term in TRACKED_TERMS:
        if term in low:
            found.append(_normalize_term(term))

    return sorted(set(found))


def _weighted_recent_memories() -> List[Tuple[Dict, float]]:
    memories = load_sentence_memory()
    total = len(memories)
    out: List[Tuple[Dict, float]] = []

    for i, item in enumerate(memories):
        recency_weight = 1.0 + ((i / max(1, total)) * RECENCY_STEP)
        out.append((item, recency_weight))

    return out


def _dream_terms_and_bonus() -> Tuple[List[str], float]:
    item = latest_dream()
    if not item:
        return [], 0.0

    fragments = item.get("fragments", []) or []
    identity_note = item.get("identity_note", "") or ""
    text = " ".join(str(x) for x in fragments) + " " + str(identity_note)
    terms = _extract_terms(text)
    if not terms:
        return [], 0.0

    return terms, DREAM_BONUS


def _identity_terms_and_bonus() -> Tuple[List[str], float]:
    text = latest_identity_note_text()
    if not text:
        return [], 0.0

    terms = _extract_terms(text)
    if not terms:
        return [], 0.0

    return terms, IDENTITY_BONUS


def build_clusters_from_sentence_memory() -> List[Dict]:
    global LAST_PAIR_COUNTER

    weighted_memories = _weighted_recent_memories()

    combo_counter: Dict[Tuple[str, ...], float] = defaultdict(float)
    pair_counter: Dict[Tuple[str, str], float] = defaultdict(float)
    term_counter: Dict[str, float] = defaultdict(float)

    for item, recency_weight in weighted_memories:
        text = str(item.get("text", "")).strip()
        if not text:
            continue

        terms = _extract_terms(text)
        if not terms:
            continue

        for term in terms:
            term_counter[term] += recency_weight

        for i in range(len(terms)):
            for j in range(i + 1, len(terms)):
                pair = tuple(sorted((terms[i], terms[j])))
                pair_counter[pair] += recency_weight

        if len(terms) >= 2:
            combo = tuple(terms[:MAX_CLUSTER_TERMS])
            combo_counter[combo] += recency_weight

    dream_terms, dream_bonus = _dream_terms_and_bonus()
    if len(dream_terms) >= 2:
        combo = tuple(dream_terms[:MAX_CLUSTER_TERMS])
        combo_counter[combo] += dream_bonus

        for term in dream_terms:
            term_counter[term] += dream_bonus

        for i in range(len(dream_terms)):
            for j in range(i + 1, len(dream_terms)):
                pair = tuple(sorted((dream_terms[i], dream_terms[j])))
                pair_counter[pair] += dream_bonus

    identity_terms, identity_bonus = _identity_terms_and_bonus()
    if len(identity_terms) >= 2:
        combo = tuple(identity_terms[:MAX_CLUSTER_TERMS])
        combo_counter[combo] += identity_bonus

        for term in identity_terms:
            term_counter[term] += identity_bonus

        for i in range(len(identity_terms)):
            for j in range(i + 1, len(identity_terms)):
                pair = tuple(sorted((identity_terms[i], identity_terms[j])))
                pair_counter[pair] += identity_bonus

    LAST_PAIR_COUNTER = dict(pair_counter)

    clusters: List[Dict] = []

    for combo, combo_weight in sorted(combo_counter.items(), key=lambda kv: kv[1], reverse=True):
        pair_strength = 0.0
        combo_list = list(combo)

        for i in range(len(combo_list)):
            for j in range(i + 1, len(combo_list)):
                pair = tuple(sorted((combo_list[i], combo_list[j])))
                pair_strength += pair_counter.get(pair, 0.0)

        term_strength = sum(term_counter.get(term, 0.0) for term in combo_list)

        scenic_count = sum(1 for t in combo_list if t in SCENIC_TERMS)
        scene_bonus = FOUR_TERM_SCENE_BONUS if scenic_count >= 4 else 0.0

        score = combo_weight + (pair_strength * PAIR_BONUS) + (term_strength * 0.05) + scene_bonus

        clusters.append({
            "terms": combo_list,
            "count": round(combo_weight, 3),
            "pair_strength": round(pair_strength, 3),
            "term_strength": round(term_strength, 3),
            "scene_bonus": round(scene_bonus, 3),
            "score": round(score, 3),
        })

    clusters.sort(key=lambda x: (-x["score"], -x["count"], x["terms"]))
    save_clusters(clusters)
    return clusters


def _candidate_bridge_score(terms: List[str], pair_counter: Dict[Tuple[str, str], float]) -> float:
    score = 0.0

    anchor_count = sum(1 for t in terms if t in ANCHOR_TERMS)
    environment_count = sum(1 for t in terms if t in ENVIRONMENT_TERMS)
    scenic_count = sum(1 for t in terms if t in SCENIC_TERMS)

    score += anchor_count * 1.4
    score += environment_count * 0.9
    score += scenic_count * 0.5

    for a, b in combinations(sorted(terms), 2):
        score += pair_counter.get((a, b), 0.0) * 0.35

    if anchor_count >= 1 and environment_count >= 2:
        score += 1.0

    if "wolf" in terms:
        score += 0.8

    return round(score, 6)


def _select_best_bridge_terms(cluster_terms: List[str]) -> List[str]:
    if len(cluster_terms) <= 4:
        return cluster_terms

    best_terms = cluster_terms[:4]
    best_score = -1e18

    for combo in combinations(cluster_terms, 4):
        combo_list = list(combo)
        score = _candidate_bridge_score(combo_list, LAST_PAIR_COUNTER)

        if score > best_score:
            best_score = score
            best_terms = combo_list

    ordering_priority = {
        "wolf": 0,
        "dog": 0,
        "truck": 0,
        "storm": 0,
        "weather": 0,
        "moon": 1,
        "sun": 1,
        "night": 2,
        "river": 3,
        "tree": 4,
        "mountain": 4,
        "light": 5,
        "road": 6,
    }

    best_terms = sorted(best_terms, key=lambda t: (ordering_priority.get(t, 99), t))
    return best_terms


def clusters_text(limit: int = 20) -> str:
    clusters = load_clusters()

    lines = ["CONCEPT CLUSTERS", ""]
    if not clusters:
        lines.append("No concept clusters yet.")
        return "\n".join(lines)

    for i, item in enumerate(clusters[:limit], start=1):
        terms = ", ".join(item.get("terms", []))
        count = item.get("count", 0)
        score = item.get("score", 0)
        pair_strength = item.get("pair_strength", 0)
        scene_bonus = item.get("scene_bonus", 0)
        lines.append(
            f"{i:02d}. score={score} | count={count} | pair={pair_strength} | scene={scene_bonus} | {terms}"
        )

    return "\n".join(lines)


def latest_cluster_bridge() -> str:
    clusters = load_clusters()
    if not clusters:
        return ""

    top = clusters[0]
    terms = list(top.get("terms", []))
    if not terms:
        return ""

    bridge_terms = _select_best_bridge_terms(terms)
    if not bridge_terms:
        return ""

    return "draw " + " ".join(bridge_terms)


def top_cluster_terms(limit: int = 4) -> List[str]:
    clusters = load_clusters()
    if not clusters:
        return []

    terms = list(clusters[0].get("terms", []))
    if not terms:
        return []

    return _select_best_bridge_terms(terms)[:limit]


def cluster_reinforcement_text() -> str:
    terms = top_cluster_terms(limit=4)
    if not terms:
        return ""

    return " ".join(terms)


def cluster_summary_text() -> str:
    clusters = load_clusters()
    if not clusters:
        return "\n".join([
            "CLUSTER SUMMARY",
            "",
            "No concept clusters yet.",
        ])

    top = clusters[0]
    terms = ", ".join(top.get("terms", []))
    count = top.get("count", 0)
    score = top.get("score", 0)
    pair_strength = top.get("pair_strength", 0)
    scene_bonus = top.get("scene_bonus", 0)
    bridge = latest_cluster_bridge()
    reinforce = cluster_reinforcement_text()

    lines = [
        "CLUSTER SUMMARY",
        "",
        f"Top Cluster: {terms}",
        f"Count Weight: {count}",
        f"Pair Strength: {pair_strength}",
        f"Scene Bonus: {scene_bonus}",
        f"Score: {score}",
    ]

    if bridge:
        lines.extend([
            "",
            "Cluster Bridge:",
            bridge,
        ])

    if reinforce:
        lines.extend([
            "",
            "Reinforcement Text:",
            reinforce,
        ])

    return "\n".join(lines)


def cluster_bridge_text() -> str:
    bridge = latest_cluster_bridge()
    if not bridge:
        return "\n".join([
            "CLUSTER BRIDGE",
            "",
            "No cluster bridge available yet.",
        ])

    return "\n".join([
        "CLUSTER BRIDGE",
        "",
        bridge,
    ])
