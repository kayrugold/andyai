from dream_engine import auto_dream, latest_dream_bridge
from art_engine import write_invented_art, evolve_art
from linguistic_sieve import load_vocab, normalize_vocab
from sentence_memory import load_sentence_memory


def exploration_advice(state):
    st = state.get("internal_state", {}) or {}

    stability = float(st.get("emotion_stability", 1.0) or 1.0)
    frustration = float(st.get("emotion_frustration", 0.0) or 0.0)
    curiosity = float(st.get("emotion_curiosity", 0.0) or 0.0)
    pressure = float(st.get("reflex_fault_pressure", 0.0) or 0.0)
    recovery_mode = bool(st.get("recovery_mode", False))

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
    elif curiosity >= 0.45 and stability >= 0.70:
        method = "dream"
        reason = "Moderate curiosity supports dream-based exploration."
    elif stability >= 0.80:
        method = "reflective_scan"
        reason = "Stable state supports gentle reflective scanning."

    lines = [
        "EXPLORATION ADVICE",
        "",
        f"Suggested Method: {method}",
        f"Reason: {reason}",
        "",
        "Signals:",
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
