from __future__ import annotations


def rerank_memory_hits(query: str, hits):
    q = str(query or "").strip().lower()
    terms = [t for t in q.split() if t.strip()]
    ranked = []

    for score, entry in hits:
        try:
            base = float(score)
        except Exception:
            base = 0.0

        bonus = 0.0
        text = str(entry.get("text", "") or "")
        low = text.lower()
        tags = entry.get("tags", []) or []

        if "fact" in tags:
            bonus += 0.35
        if "user_fact" in tags:
            bonus += 0.25
        if "protected" in tags:
            bonus += 0.20
        if "reasoning_trace" in tags:
            bonus += 0.05

        exact_hits = 0
        for term in terms:
            if term in low:
                exact_hits += 1

        bonus += min(exact_hits * 0.12, 0.36)

        if q and q in low:
            bonus += 0.20

        if "chat" in tags and "reasoning_trace" not in tags:
            bonus -= 0.04

        ranked.append((round(base + bonus, 3), entry))

    ranked.sort(key=lambda x: x[0], reverse=True)
    return ranked


def memory_result_bonus(entry, query: str) -> float:
    q = str(query or "").strip().lower()
    text = str(entry.get("text", "") or "")
    low = text.lower()
    tags = entry.get("tags", []) or []

    bonus = 0.0

    if "fact" in tags:
        bonus += 0.35
    if "user_fact" in tags:
        bonus += 0.25
    if "protected" in tags:
        bonus += 0.20

    terms = [t for t in q.split() if t.strip()]
    exact_hits = 0
    for term in terms:
        if term in low:
            exact_hits += 1

    bonus += min(exact_hits * 0.12, 0.36)

    if q and q in low:
        bonus += 0.20

    return round(bonus, 3)


def sort_memory_hits(hits, query: str):
    rescored = []
    for score, entry in hits:
        try:
            base = float(score)
        except Exception:
            base = 0.0
        bonus = memory_result_bonus(entry, query)
        rescored.append((round(base + bonus, 3), entry))
    rescored.sort(key=lambda x: x[0], reverse=True)
    return rescored


def classify_learning_novelty(new_text, recent_entries):
    new_text = str(new_text or "").lower().strip()

    if not new_text:
        return "duplicate"

    for old in recent_entries:
        old = str(old or "").lower().strip()

        if new_text == old:
            return "duplicate"

        if new_text in old or old in new_text:
            return "near_duplicate"

        overlap = len(set(new_text.split()) & set(old.split()))
        if overlap >= 6:
            return "near_duplicate"

    return "novel"
