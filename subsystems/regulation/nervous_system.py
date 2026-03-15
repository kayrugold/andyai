from __future__ import annotations

from typing import Any, Callable, Dict


def clamp01(x: float) -> float:
    x = float(x)
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return round(x, 3)


def _sync_flat_emotion_fields(state: Dict[str, Any]) -> Dict[str, float]:
    st = state.get("internal_state", {})
    emo = st.setdefault("emotional_state", {})

    if "confidence" not in emo and "emotion_confidence" in st:
        emo["confidence"] = float(st.get("emotion_confidence", 0.5) or 0.5)
    if "frustration" not in emo and "emotion_frustration" in st:
        emo["frustration"] = float(st.get("emotion_frustration", 0.0) or 0.0)
    if "curiosity" not in emo and "emotion_curiosity" in st:
        emo["curiosity"] = float(st.get("emotion_curiosity", 0.5) or 0.5)
    if "stability" not in emo and "emotion_stability" in st:
        emo["stability"] = float(st.get("emotion_stability", 0.5) or 0.5)

    emo.setdefault("confidence", 0.5)
    emo.setdefault("frustration", 0.0)
    emo.setdefault("curiosity", 0.5)
    emo.setdefault("stability", 0.5)

    st["emotion_confidence"] = clamp01(float(emo.get("confidence", 0.5) or 0.5))
    st["emotion_frustration"] = clamp01(float(emo.get("frustration", 0.0) or 0.0))
    st["emotion_curiosity"] = clamp01(float(emo.get("curiosity", 0.5) or 0.5))
    st["emotion_stability"] = clamp01(float(emo.get("stability", 0.5) or 0.5))
    return emo


def register_reflex_event(
    state: Dict[str, Any],
    kind: str,
    source: str,
    detail: str,
    severity: float = 0.5,
    *,
    now_ts: Callable[[], str],
) -> Dict[str, Any]:
    st = state.get("internal_state", {})
    events = st.setdefault("reflex_events", [])

    evt = {
        "ts": now_ts(),
        "kind": str(kind or "").strip(),
        "source": str(source or "").strip(),
        "detail": str(detail or "").strip(),
        "severity": round(max(0.0, float(severity or 0.0)), 3),
    }
    events.append(evt)
    if len(events) > 64:
        del events[:-64]

    st["last_reflex_kind"] = evt["kind"]
    st["last_reflex_source"] = evt["source"]
    st["last_reflex_detail"] = evt["detail"]
    st["last_reflex_severity"] = evt["severity"]
    st["reflex_total_count"] = int(st.get("reflex_total_count", 0) or 0) + 1
    st["reflex_fault_pressure"] = round(
        float(st.get("reflex_fault_pressure", 0.0) or 0.0) + evt["severity"],
        3,
    )

    counts = st.setdefault("reflex_counts", {})
    counts[evt["kind"]] = int(counts.get(evt["kind"], 0) or 0) + 1
    return evt


def decay_reflex_pressure(state: Dict[str, Any], amount: float = 0.1) -> float:
    st = state.get("internal_state", {})
    cur = float(st.get("reflex_fault_pressure", 0.0) or 0.0)
    cur = max(0.0, cur - float(amount or 0.0))
    st["reflex_fault_pressure"] = round(cur, 3)
    return st["reflex_fault_pressure"]


def ensure_emotional_state(state: Dict[str, Any]) -> Dict[str, float]:
    return _sync_flat_emotion_fields(state)


def update_emotional_state(
    state: Dict[str, Any],
    *,
    now_ts: Callable[[], str],
) -> Dict[str, float]:
    st = state.get("internal_state", {})
    emo = ensure_emotional_state(state)

    diag_delta = float(st.get("last_diag_delta", 0.0) or 0.0)
    pressure = float(st.get("reflex_fault_pressure", 0.0) or 0.0)
    mode = str(st.get("last_strategy_selection_mode", "") or "").strip().lower()

    confidence = float(emo.get("confidence", 0.5) or 0.5)
    frustration = float(emo.get("frustration", 0.0) or 0.0)
    curiosity = float(emo.get("curiosity", 0.5) or 0.5)
    stability = float(emo.get("stability", 0.5) or 0.5)

    if diag_delta > 0:
        confidence += 0.08
        frustration -= 0.05
        stability += 0.06
    elif diag_delta < 0:
        confidence -= 0.07
        frustration += 0.10
        stability -= 0.08
    else:
        stability += 0.01

    if pressure > 0:
        frustration += min(0.12, pressure * 0.05)
        stability -= min(0.08, pressure * 0.03)

    if mode == "explore":
        curiosity += 0.06
    elif mode == "mutant":
        curiosity += 0.03
    elif mode == "exploit":
        curiosity -= 0.02

    emo["confidence"] = clamp01(confidence)
    emo["frustration"] = clamp01(frustration)
    emo["curiosity"] = clamp01(curiosity)
    emo["stability"] = clamp01(stability)
    _sync_flat_emotion_fields(state)

    st["last_emotion_update_ts"] = now_ts()
    return emo


def emotional_state_text(state: Dict[str, Any]) -> str:
    emo = ensure_emotional_state(state)
    lines = [
        "EMOTIONAL STATE",
        "",
        f"Confidence: {emo.get('confidence', 0.0)}",
        f"Frustration: {emo.get('frustration', 0.0)}",
        f"Curiosity: {emo.get('curiosity', 0.0)}",
        f"Stability: {emo.get('stability', 0.0)}",
    ]
    return "\n".join(lines)


def behavior_policy(
    state: Dict[str, Any],
    *,
    ensure_working_memory: Callable[[Dict[str, Any]], Dict[str, Any]],
) -> Dict[str, bool]:
    st = state.get("internal_state", {})
    emo = ensure_emotional_state(state)
    wm = ensure_working_memory(state)

    recovery_mode = bool(st.get("recovery_mode", False))
    pressure = float(st.get("reflex_fault_pressure", 0.0) or 0.0)

    frustration = float(emo.get("frustration", 0.0) or 0.0)
    stability = float(emo.get("stability", 0.5) or 0.5)
    curiosity = float(emo.get("curiosity", 0.5) or 0.5)
    confidence = float(emo.get("confidence", 0.5) or 0.5)

    recent_users = list(wm.get("recent_user_messages", []) or [])
    recent_results = list(wm.get("recent_results", []) or [])
    has_recent_context = bool(recent_users or recent_results)

    cautious = (
        recovery_mode
        or frustration >= 0.60
        or stability <= 0.35
        or pressure >= 2.0
    )

    exploratory = (
        (not cautious)
        and curiosity >= 0.62
        and stability >= 0.42
        and pressure < 1.8
    )

    consolidating = (
        (not exploratory)
        and confidence >= 0.62
        and stability >= 0.45
        and has_recent_context
    )

    allow_mutants = (
        (not recovery_mode)
        and pressure < 1.8
        and frustration < 0.70
        and stability >= 0.38
    )

    prefer_exploit = cautious or consolidating
    prefer_explore = exploratory and not prefer_exploit
    suppress_mutant_temporarily = not allow_mutants

    return {
        "cautious": cautious,
        "exploratory": exploratory,
        "consolidating": consolidating,
        "allow_mutants": allow_mutants,
        "prefer_exploit": prefer_exploit,
        "prefer_explore": prefer_explore,
        "suppress_mutant_temporarily": suppress_mutant_temporarily,
    }


def behavior_policy_text(
    state: Dict[str, Any],
    *,
    ensure_working_memory: Callable[[Dict[str, Any]], Dict[str, Any]],
) -> str:
    policy = behavior_policy(state, ensure_working_memory=ensure_working_memory)
    lines = ["BEHAVIOR POLICY", ""]
    for k in sorted(policy):
        lines.append(f"{k}: {policy[k]}")
    return "\n".join(lines)


def apply_recovery_mode_behavior(state: Dict[str, Any]) -> None:
    st = state.get("internal_state", {})
    emo = ensure_emotional_state(state)

    mode = st.get("recovery_mode_type", "standard")

    pressure = float(st.get("reflex_fault_pressure", 0))
    frustration = float(emo.get("frustration", 0))
    stability = float(emo.get("stability", 0))
    curiosity = float(emo.get("curiosity", 0))
    confidence = float(emo.get("confidence", 0))

    if mode == "standard":
        pressure *= 0.90
        frustration *= 0.92
        stability += 0.04
    elif mode == "reflect":
        confidence += 0.05
        stability += 0.06
        frustration *= 0.90
    elif mode == "art":
        curiosity += 0.07
        frustration *= 0.85
        stability += 0.05

    emo["confidence"] = clamp01(confidence)
    emo["frustration"] = clamp01(frustration)
    emo["curiosity"] = clamp01(curiosity)
    emo["stability"] = clamp01(stability)
    st["reflex_fault_pressure"] = round(max(0, pressure), 3)
    _sync_flat_emotion_fields(state)


def apply_recovery_cycle(
    state: Dict[str, Any],
    *,
    now_ts: Callable[[], str],
    ensure_working_memory: Callable[[Dict[str, Any]], Dict[str, Any]],
) -> Dict[str, Any]:
    st = state.get("internal_state", {})
    emo = ensure_emotional_state(state)
    policy = behavior_policy(state, ensure_working_memory=ensure_working_memory)

    confidence = float(emo.get("confidence", 0.5) or 0.5)
    frustration = float(emo.get("frustration", 0.0) or 0.0)
    curiosity = float(emo.get("curiosity", 0.5) or 0.5)
    stability = float(emo.get("stability", 0.5) or 0.5)
    pressure = float(st.get("reflex_fault_pressure", 0.0) or 0.0)
    diag_delta = float(st.get("last_diag_delta", 0.0) or 0.0)

    in_recovery = bool(st.get("recovery_mode", False))

    if policy.get("cautious", False) and (pressure >= 2.0 or frustration >= 0.75 or stability <= 0.25):
        in_recovery = True

    if in_recovery:
        if diag_delta >= 0:
            frustration -= 0.08
            stability += 0.07
            confidence += 0.03
            pressure = max(0.0, pressure - 0.20)
        else:
            frustration += 0.03
            stability -= 0.02
            pressure += 0.05

        curiosity -= 0.03

        if pressure <= 1.2 and frustration <= 0.45 and stability >= 0.45:
            in_recovery = False

    emo["confidence"] = clamp01(confidence)
    emo["frustration"] = clamp01(frustration)
    emo["curiosity"] = clamp01(curiosity)
    emo["stability"] = clamp01(stability)
    _sync_flat_emotion_fields(state)

    st["reflex_fault_pressure"] = round(max(0.0, pressure), 3)
    st["recovery_mode"] = in_recovery
    st["last_recovery_ts"] = now_ts()

    return {
        "recovery_mode": in_recovery,
        "confidence": emo["confidence"],
        "frustration": emo["frustration"],
        "curiosity": emo["curiosity"],
        "stability": emo["stability"],
        "pressure": st["reflex_fault_pressure"],
    }


def nerve_reset(
    state: Dict[str, Any],
    target_pressure: float = 0.8,
    *,
    now_ts: Callable[[], str],
    ensure_working_memory: Callable[[Dict[str, Any]], Dict[str, Any]],
) -> Dict[str, Any]:
    st = state.get("internal_state", {})
    old_pressure = float(st.get("reflex_fault_pressure", 0.0) or 0.0)
    st["reflex_fault_pressure"] = round(max(0.0, float(target_pressure)), 3)
    st["last_reflex_kind"] = ""
    st["last_reflex_source"] = ""
    st["last_reflex_detail"] = ""
    st["last_reflex_severity"] = 0.0

    update_emotional_state(state, now_ts=now_ts)
    apply_recovery_cycle(
        state,
        now_ts=now_ts,
        ensure_working_memory=ensure_working_memory,
    )

    return {
        "old_pressure": round(old_pressure, 3),
        "new_pressure": st["reflex_fault_pressure"],
        "recovery_mode": bool(st.get("recovery_mode", False)),
    }


def nerve_reset_text(
    state: Dict[str, Any],
    target_pressure: float = 0.8,
    *,
    now_ts: Callable[[], str],
    ensure_working_memory: Callable[[Dict[str, Any]], Dict[str, Any]],
) -> str:
    info = nerve_reset(
        state,
        target_pressure=target_pressure,
        now_ts=now_ts,
        ensure_working_memory=ensure_working_memory,
    )
    return (
        "NERVE RESET\n\n"
        f"Old Pressure: {info['old_pressure']}\n"
        f"New Pressure: {info['new_pressure']}\n"
        f"Recovery Mode: {info['recovery_mode']}"
    )


def reflex_status_text(state: Dict[str, Any]) -> str:
    st = state.get("internal_state", {})
    lines = [
        "REFLEX STATUS",
        "",
        f"Total Reflex Events: {st.get('reflex_total_count', 0)}",
        f"Fault Pressure: {st.get('reflex_fault_pressure', 0.0)}",
        f"Last Reflex Kind: {st.get('last_reflex_kind', '')}",
        f"Last Reflex Source: {st.get('last_reflex_source', '')}",
        f"Last Reflex Severity: {st.get('last_reflex_severity', 0.0)}",
        f"Last Reflex Detail: {str(st.get('last_reflex_detail', ''))[:120]}",
        f"Reflex Counts: {st.get('reflex_counts', {})}",
    ]
    return "\n".join(lines)


def reflex_history_text(state: Dict[str, Any], limit: int = 12) -> str:
    st = state.get("internal_state", {})
    events = list(st.get("reflex_events", []) or [])
    if not events:
        return "REFLEX HISTORY\n\nNo reflex events recorded."

    lines = ["REFLEX HISTORY", ""]
    for i, evt in enumerate(events[-limit:], start=1):
        lines.append(
            f"{i}. kind={evt.get('kind','')} | source={evt.get('source','')} | "
            f"severity={evt.get('severity',0)} | detail={str(evt.get('detail',''))[:120]}"
        )
    return "\n".join(lines)


def set_recovery_mode(
    state: Dict[str, Any],
    mode: str,
    *,
    now_ts: Callable[[], str],
) -> str:
    st = state.get("internal_state", {})
    mode = str(mode or "standard").strip().lower()

    if mode not in {"standard", "reflect", "art"}:
        mode = "standard"

    st["recovery_mode_type"] = mode
    st["recovery_mode"] = True
    st["last_recovery_ts"] = now_ts()
    return mode


def recovery_mode_text(state: Dict[str, Any]) -> str:
    st = state.get("internal_state", {})
    mode = st.get("recovery_mode_type", "standard")

    lines = [
        "RECOVERY MODE",
        "",
        f"Mode: {mode}",
        "",
    ]

    if mode == "standard":
        lines.append("Purpose: stabilize system and reduce fault pressure")
        lines.append("Behavior: safer strategies, exploit preference")
    elif mode == "reflect":
        lines.append("Purpose: identity re-anchoring and coherence")
        lines.append("Behavior: reinforce identity and purpose")
    elif mode == "art":
        lines.append("Purpose: decompression through structured output")
        lines.append("Behavior: visual / SVG practice tasks")

    return "\n".join(lines)


def recovery_status_text(state: Dict[str, Any]) -> str:
    st = state.get("internal_state", {})
    lines = [
        "RECOVERY STATUS",
        "",
        f"Recovery Mode: {st.get('recovery_mode', False)}",
        f"Recovery Mode Type: {st.get('recovery_mode_type', 'standard')}",
        f"Reflex Fault Pressure: {st.get('reflex_fault_pressure', 0.0)}",
        f"Last Recovery TS: {st.get('last_recovery_ts', '')}",
    ]
    return "\n".join(lines)
