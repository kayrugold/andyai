from pathlib import Path
import json
import time

from sentence_memory import load_sentence_memory

DREAM_LOG_FILE = "dream_log.json"
DREAM_DIR = Path("dreams")
DREAM_DIR.mkdir(exist_ok=True)


def load_dream_log():
    p = Path(DREAM_LOG_FILE)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []


def save_dream_log(items):
    Path(DREAM_LOG_FILE).write_text(
        json.dumps(items, indent=2),
        encoding="utf-8"
    )


def _next_dream_file():
    existing = sorted(DREAM_DIR.glob("dream_*.json"))
    n = len(existing) + 1
    return DREAM_DIR / f"dream_{n:04d}.json"


def _write_dream_file(entry):
    f = _next_dream_file()
    f.write_text(json.dumps(entry, indent=2), encoding="utf-8")
    return str(f)


def dream_allowed(state):
    st = state.get("internal_state", {}) or {}

    stability = float(st.get("emotion_stability", 1.0) or 1.0)
    frustration = float(st.get("emotion_frustration", 0.0) or 0.0)
    pressure = float(st.get("reflex_fault_pressure", 0.0) or 0.0)
    recovery_mode = bool(st.get("recovery_mode", False))

    if recovery_mode:
        return False, "Recovery mode active; dream generation deferred."

    if pressure > 2.5:
        return False, "Fault pressure too high for dreaming."

    if stability < 0.55:
        return False, "Stability too low for dreaming."

    if frustration > 0.75:
        return False, "Frustration too high for dreaming."

    return True, "Dreaming allowed."


def infer_dream_purpose(state):
    st = state.get("internal_state", {}) or {}

    frustration = float(st.get("emotion_frustration", 0.0) or 0.0)
    curiosity = float(st.get("emotion_curiosity", 0.0) or 0.0)
    stability = float(st.get("emotion_stability", 1.0) or 1.0)

    if frustration > 0.45:
        return "language_consolidation"

    if curiosity > 0.55:
        return "creative_recombination"

    if stability > 0.85:
        return "identity_reflection"

    return "memory_replay"


def _build_reflection(purpose):
    return {
        "language_consolidation": "Recent phrases suggest unresolved language patterns worth replaying gently.",
        "creative_recombination": "Recent fragments suggest possible recombination into novel language or art prompts.",
        "identity_reflection": "Recent memories are calm enough to support reflective self-consolidation.",
        "memory_replay": "Recent fragments are being replayed for low-pressure stabilization.",
    }.get(purpose, "Recent fragments are being replayed for consolidation.")


def _weighted_terms_from_fragments(fragments):
    tracked = ("wolf", "moon", "night", "river", "tree", "mountain", "light")
    scores = {}

    for i, frag in enumerate(fragments):
        text = str(frag).lower()
        weight = i + 1
        for term in tracked:
            if term in text:
                scores[term] = scores.get(term, 0) + weight

    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    return ranked


def _build_bridge_from_fragments(fragments):
    ranked = _weighted_terms_from_fragments(fragments)
    if not ranked:
        return ""

    terms = [term for term, _score in ranked[:4]]
    return "draw " + " ".join(terms)


def _build_identity_note(purpose, fragments):
    ranked = _weighted_terms_from_fragments(fragments)
    themes = [term for term, _score in ranked[:4]]

    if purpose == "identity_reflection" and themes:
        return f"Recent memories suggest calm recurring imagery around: {', '.join(themes)}."
    if purpose == "creative_recombination" and themes:
        return f"Imagination appears active around these symbols: {', '.join(themes)}."
    if purpose == "language_consolidation":
        return "Recent language fragments may benefit from repeated contextual rehearsal."
    return "Recent memories appear stable enough for gentle reflective replay."


def _build_dream_entry(state, source="manual"):
    purpose = infer_dream_purpose(state)
    memories = load_sentence_memory()
    recent = memories[-5:]

    if not recent:
        return None

    fragments = [str(x.get("text", "")).strip() for x in recent if str(x.get("text", "")).strip()]
    if not fragments:
        return None

    reflection = _build_reflection(purpose)
    suggested_bridge = _build_bridge_from_fragments(fragments)
    identity_note = _build_identity_note(purpose, fragments)

    entry = {
        "id": int(time.time() * 1000),
        "ts": int(time.time()),
        "source": source,
        "purpose": purpose,
        "fragments": fragments,
        "reflection": reflection,
        "suggested_bridge": suggested_bridge,
        "identity_note": identity_note,
    }
    return entry


def _format_dream_entry(title, entry):
    lines = [
        title,
        "",
        f"Purpose: {entry.get('purpose', '')}",
        f"Source: {entry.get('source', '')}",
    ]

    dream_file = entry.get("dream_file", "")
    if dream_file:
        lines.append(f"File: {dream_file}")

    lines.extend([
        "",
        "Fragments:",
    ])

    for frag in entry.get("fragments", []) or []:
        lines.append(f"- {frag}")

    lines.extend([
        "",
        "Reflection:",
        entry.get("reflection", ""),
        "",
        "Identity Note:",
        entry.get("identity_note", ""),
    ])

    bridge = entry.get("suggested_bridge", "")
    if bridge:
        lines.extend([
            "",
            "Suggested Bridge:",
            bridge,
        ])

    return "\n".join(lines)


def make_dream(state):
    allowed, reason = dream_allowed(state)

    if not allowed:
        return "\n".join([
            "DREAM MAKE",
            "",
            f"Blocked: {reason}",
        ])

    entry = _build_dream_entry(state, source="manual")
    if not entry:
        return "\n".join([
            "DREAM MAKE",
            "",
            "No sentence memories available.",
        ])

    dream_file = _write_dream_file(entry)
    entry["dream_file"] = dream_file

    items = load_dream_log()
    items.append(entry)
    items = items[-100:]
    save_dream_log(items)

    return _format_dream_entry("DREAM LOG", entry)


def auto_dream(state):
    allowed, reason = dream_allowed(state)

    if not allowed:
        return "\n".join([
            "DREAM AUTO",
            "",
            f"Blocked: {reason}",
        ])

    entry = _build_dream_entry(state, source="auto")
    if not entry:
        return "\n".join([
            "DREAM AUTO",
            "",
            "No sentence memories available.",
        ])

    dream_file = _write_dream_file(entry)
    entry["dream_file"] = dream_file

    items = load_dream_log()
    items.append(entry)
    items = items[-100:]
    save_dream_log(items)

    return _format_dream_entry("DREAM AUTO", entry)


def dreams_text(limit=20):
    items = load_dream_log()[-limit:]

    lines = ["DREAM LOGS", ""]
    if not items:
        lines.append("No dreams logged yet.")
        return "\n".join(lines)

    for i, item in enumerate(items, start=1):
        purpose = item.get("purpose", "")
        source = item.get("source", "")
        frag_count = len(item.get("fragments", []) or [])
        dream_file = Path(item.get("dream_file", "")).name if item.get("dream_file") else ""
        if dream_file:
            lines.append(f"{i:02d}. source={source} | purpose={purpose} | fragments={frag_count} | file={dream_file}")
        else:
            lines.append(f"{i:02d}. source={source} | purpose={purpose} | fragments={frag_count} | id={item.get('id')}")

    return "\n".join(lines)


def latest_dream():
    items = load_dream_log()
    if not items:
        return None
    return items[-1]


def latest_dream_text():
    item = latest_dream()
    if not item:
        return "\n".join([
            "DREAM LATEST",
            "",
            "No dreams logged yet.",
        ])

    return _format_dream_entry("DREAM LATEST", item)


def latest_dream_bridge():
    item = latest_dream()
    if not item:
        return ""
    return str(item.get("suggested_bridge", "")).strip()


def latest_identity_note():
    item = latest_dream()
    if not item:
        return ""
    return str(item.get("identity_note", "")).strip()
