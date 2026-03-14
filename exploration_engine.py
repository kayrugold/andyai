import random

from dream_engine import auto_dream
from art_engine import write_invented_art
from linguistic_sieve import load_vocab, normalize_vocab
from sentence_memory import load_sentence_memory


def _exploration_readiness(state):
    st = state.get("internal_state", {}) or {}

    stability = float(st.get("emotion_stability", 1.0) or 1.0)
    frustration = float(st.get("emotion_frustration", 0.0) or 0.0)
    curiosity = float(st.get("emotion_curiosity", 0.0) or 0.0)
    pressure = float(st.get("reflex_fault_pressure", 0.0) or 0.0)
    recovery_mode = bool(st.get("recovery_mode", False))

    ready = (
        not recovery_mode
        and pressure <= 1.8
        and frustration <= 0.45
        and stability >= 0.70
        and curiosity >= 0.10
    )

    return {
        "ready": ready,
        "stability": stability,
        "frustration": frustration,
        "curiosity": curiosity,
        "pressure": pressure,
        "recovery_mode": recovery_mode,
    }


def exploration_advice(state):
    info = _exploration_readiness(state)

    stability = info["stability"]
    frustration = info["frustration"]
    curiosity = info["curiosity"]
    pressure = info["pressure"]
    recovery_mode = info["recovery_mode"]

    method = "none"
    reason = "Exploration not advised."

    if recovery_mode:
        method = "none"
        reason = "Recovery mode is active."
    elif pressure > 1.8:
        method = "none"
        reason = "Fault pressure is still too high."
    elif frustration > 0.45:
        method = "none"
        reason = "Frustration is too elevated for exploration."
    elif curiosity >= 0.60 and stability >= 0.70:
        method = "invent_art"
        reason = "Curiosity and stability support creative exploration."
    elif curiosity >= 0.25 and stability >= 0.70:
        method = random.choice(["dream", "language_practice"])
        reason = "Moderate curiosity supports dream or language exploration."
    elif curiosity >= 0.10 and stability >= 0.80:
        method = random.choice(["reflective_scan", "language_practice"])
        reason = "Low but active curiosity supports gentle scanning or language practice."

    lines = [
        "EXPLORATION ADVICE",
        "",
        f"Suggested Method: {method}",
        f"Reason: {reason}",
        "",
        "Readiness:",
        f"  ready={info['ready']}",
        f"  stability={round(stability, 3)}",
        f"  frustration={round(frustration, 3)}",
        f"  curiosity={round(curiosity, 3)}",
        f"  fault_pressure={round(pressure, 3)}",
        f"  recovery_mode={recovery_mode}",
    ]

    return "\n".join(lines), method


def _apply_exploration_effects(state, method):
    st = state.get("internal_state", {}) or {}

    stability = float(st.get("emotion_stability", 1.0) or 1.0)
    frustration = float(st.get("emotion_frustration", 0.0) or 0.0)
    curiosity = float(st.get("emotion_curiosity", 0.0) or 0.0)
    confidence = float(st.get("emotion_confidence", 0.5) or 0.5)

    before = dict(
        stability=stability,
        frustration=frustration,
        curiosity=curiosity,
        confidence=confidence,
    )

    if method == "invent_art":
        curiosity -= 0.08
        confidence += 0.03
        stability += 0.01
    elif method == "dream":
        curiosity -= 0.05
        stability += 0.02
    elif method == "reflective_scan":
        curiosity -= 0.03
        confidence += 0.01
    elif method == "language_practice":
        curiosity -= 0.04
        confidence += 0.02

    stability = max(0.0, min(1.0, stability))
    frustration = max(0.0, min(1.0, frustration))
    curiosity = max(0.0, min(1.0, curiosity))
    confidence = max(0.0, min(1.0, confidence))

    st["emotion_stability"] = stability
    st["emotion_frustration"] = frustration
    st["emotion_curiosity"] = curiosity
    st["emotion_confidence"] = confidence

    after = dict(
        stability=stability,
        frustration=frustration,
        curiosity=curiosity,
        confidence=confidence,
    )

    return before, after


def _language_practice_text():
    vocab = normalize_vocab(load_vocab())
    if not vocab:
        return "EXPLORATION ACT\n\nLanguage practice skipped (no vocabulary yet)."

    candidates = [w for w, e in vocab.items() if len((e.get("roles", {}) or {})) >= 1]
    if not candidates:
        return "EXPLORATION ACT\n\nLanguage practice skipped (no usable vocabulary entries)."

    word = random.choice(candidates)
    entry = vocab[word]
    roles = entry.get("roles", {}) or {}
    examples = list(entry.get("examples", []) or [])

    lines = [
        "EXPLORATION ACT",
        "",
        "Method: language_practice",
        "",
        f"Word: {word}",
        f"Roles: {', '.join(sorted(roles.keys())) if roles else '(none)'}",
    ]

    if examples:
        lines.append(f"Example: {examples[0]}")

    return "\n".join(lines)


def exploration_act(state):
    _text, method = exploration_advice(state)

    lines = [
        "EXPLORATION ACT",
        "",
        f"Method: {method}",
    ]

    if method == "invent_art":
        result = write_invented_art(state)
        lines.extend([
            "Action: inventive art exploration",
            f"Mode: {result['mode']}",
            f"Path: {result['path']}",
            f"Score: {result['score']}",
        ])

    elif method == "dream":
        lines.append(auto_dream(state))

    elif method == "reflective_scan":
        vocab = normalize_vocab(load_vocab())
        memories = load_sentence_memory()
        lines.extend([
            "Action: reflective scan",
            f"Vocabulary Size: {len(vocab)}",
            f"Sentence Memories: {len(memories)}",
        ])

    elif method == "language_practice":
        lines = [_language_practice_text()]

    else:
        lines.append("Action: no exploration performed.")

    before, after = _apply_exploration_effects(state, method)

    lines.extend([
        "",
        "State Transition:",
        "",
        "Before:",
        f"  stability={round(before['stability'], 3)}",
        f"  frustration={round(before['frustration'], 3)}",
        f"  curiosity={round(before['curiosity'], 3)}",
        f"  confidence={round(before['confidence'], 3)}",
        "",
        "After:",
        f"  stability={round(after['stability'], 3)}",
        f"  frustration={round(after['frustration'], 3)}",
        f"  curiosity={round(after['curiosity'], 3)}",
        f"  confidence={round(after['confidence'], 3)}",
    ])

    return "\n".join(lines)
