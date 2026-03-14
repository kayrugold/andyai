from identity_notes import load_identity_notes
from dream_engine import latest_dream, auto_dream, latest_identity_note, latest_dream_bridge
from linguistic_sieve import extract_scene_concepts, extract_action_concepts
from art_engine import write_scene_art


def _recent_identity_text():
    items = load_identity_notes()
    if not items:
        return ""
    recent = items[-5:]
    return " ".join(str(x.get("note", "")) for x in recent).lower()


def _latest_dream_text_blob():
    item = latest_dream()
    if not item:
        return ""
    parts = []
    parts.extend(item.get("fragments", []) or [])
    parts.append(item.get("reflection", ""))
    parts.append(item.get("identity_note", ""))
    return " ".join(str(x) for x in parts).lower()


def recovery_advice(state):
    st = state.get("internal_state", {}) or {}

    stability = float(st.get("emotion_stability", 1.0))
    frustration = float(st.get("emotion_frustration", 0.0))
    curiosity = float(st.get("emotion_curiosity", 0.0))
    pressure = float(st.get("reflex_fault_pressure", 0.0))
    recovery_mode = bool(st.get("recovery_mode", False))

    ident_blob = _recent_identity_text()
    dream_blob = _latest_dream_text_blob()
    merged = ident_blob + " " + dream_blob

    method = "quiet"
    reason = "Defaulting to low-pressure stabilization."

    if recovery_mode:
        method = "reflect"
        reason = "Recovery mode prefers reflection."
    elif pressure > 2.0:
        method = "quiet"
        reason = "Fault pressure is high."
    elif frustration > 0.55:
        method = "art"
        reason = "Frustration elevated."
    elif stability > 0.80 and any(x in merged for x in ("wolf", "moon", "river", "night")):
        method = "art"
        reason = "Calm imagery detected."
    elif curiosity > 0.55 and stability > 0.65:
        method = "dream"
        reason = "Curiosity suggests dream consolidation."
    elif stability > 0.85:
        method = "reflect"
        reason = "High stability supports reflection."

    text = [
        "RECOVERY ADVICE",
        "",
        f"Suggested Method: {method}",
        f"Reason: {reason}",
        "",
        "Signals:",
        f"  stability={round(stability, 3)}",
        f"  frustration={round(frustration, 3)}",
        f"  curiosity={round(curiosity, 3)}",
        f"  fault_pressure={round(pressure, 3)}",
    ]

    return "\n".join(text), method


def _apply_recovery_effects(state, method):
    st = state.get("internal_state", {}) or {}

    stability = float(st.get("emotion_stability", 1.0))
    frustration = float(st.get("emotion_frustration", 0.0))
    pressure = float(st.get("reflex_fault_pressure", 0.0))
    confidence = float(st.get("emotion_confidence", 0.5))
    curiosity = float(st.get("emotion_curiosity", 0.0))

    before = dict(
        stability=stability,
        frustration=frustration,
        pressure=pressure,
        confidence=confidence,
        curiosity=curiosity,
    )

    if method == "art":
        stability += 0.05
        frustration -= 0.05
        confidence += 0.02
        pressure -= 0.05
        if pressure <= 1.9:
            curiosity += 0.03

    elif method == "dream":
        stability += 0.03
        frustration -= 0.02
        curiosity += 0.02

    elif method == "reflect":
        stability += 0.04
        confidence += 0.04
        if pressure <= 1.8:
            curiosity += 0.02

    elif method == "quiet":
        pressure -= 0.20
        stability += 0.02
        if pressure <= 1.8:
            curiosity += 0.01

    stability = max(0.0, min(1.0, stability))
    frustration = max(0.0, min(1.0, frustration))
    pressure = max(0.0, pressure)
    confidence = max(0.0, min(1.0, confidence))
    curiosity = max(0.0, min(1.0, curiosity))

    st["emotion_stability"] = stability
    st["emotion_frustration"] = frustration
    st["reflex_fault_pressure"] = pressure
    st["emotion_confidence"] = confidence
    st["emotion_curiosity"] = curiosity

    after = dict(
        stability=stability,
        frustration=frustration,
        pressure=pressure,
        confidence=confidence,
        curiosity=curiosity,
    )

    return before, after


def recovery_choose(state):
    _text, method = recovery_advice(state)

    st = state.get("internal_state", {}) or {}
    st["recovery_suggested_method"] = method

    lines = [
        "RECOVERY CHOOSE",
        "",
        f"Chosen Method: {method}",
    ]

    return "\n".join(lines)


def recovery_act(state):
    _text, method = recovery_advice(state)

    lines = [
        "RECOVERY ACT",
        "",
        f"Method: {method}",
    ]

    if method == "art":
        bridge = latest_dream_bridge()
        if bridge.startswith("draw "):
            text = bridge[5:].strip()
            concepts = extract_scene_concepts(text)
            actions = extract_action_concepts(text)

            if concepts:
                result = write_scene_art(state, concepts, actions)
                lines.extend([
                    "Action: art soothing",
                    f"Bridge: {bridge}",
                    f"Path: {result['path']}",
                    f"Score: {result['score']}",
                ])
        else:
            lines.append("Action: art soothing")

    elif method == "dream":
        lines.append(auto_dream(state))

    elif method == "reflect":
        note = latest_identity_note()
        lines.append("Action: reflection")
        if note:
            lines.append(note)

    else:
        lines.append("Action: quiet stabilization")

    before, after = _apply_recovery_effects(state, method)

    lines.extend([
        "",
        "State Transition:",
        "",
        "Before:",
        f"  stability={round(before['stability'], 3)}",
        f"  frustration={round(before['frustration'], 3)}",
        f"  fault_pressure={round(before['pressure'], 3)}",
        f"  confidence={round(before['confidence'], 3)}",
        f"  curiosity={round(before['curiosity'], 3)}",
        "",
        "After:",
        f"  stability={round(after['stability'], 3)}",
        f"  frustration={round(after['frustration'], 3)}",
        f"  fault_pressure={round(after['pressure'], 3)}",
        f"  confidence={round(after['confidence'], 3)}",
        f"  curiosity={round(after['curiosity'], 3)}",
    ])

    return "\n".join(lines)
