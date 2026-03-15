import time
from pathlib import Path

from subsystems.os.recovery_engine import recovery_advice, recovery_act
from subsystems.os.exploration_engine import exploration_advice, exploration_act
from subsystems.os.dream_engine import dream_allowed, auto_dream

DRIVE_LOG = "drive_scheduler.log"


def append_drive_log(line: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    Path(DRIVE_LOG).open("a", encoding="utf-8").write(f"[{ts}] {line}\n")


def _safe_idle_check(state):
    st = state.get("internal_state", {}) or {}

    recovery_mode = bool(st.get("recovery_mode", False))
    pressure = float(st.get("reflex_fault_pressure", 0.0) or 0.0)

    if recovery_mode:
        return False, "recovery mode active"

    if pressure > 2.2:
        return False, "fault pressure too high"

    return True, "idle-safe"


def _choose_drive(state, rec_method, exp_method, dream_ok):
    st = state.get("internal_state", {}) or {}
    last_action = str(st.get("last_drive_action", "") or "")

    urgent_recovery = rec_method in ("quiet", "reflect") or (
        rec_method == "art" and float(st.get("reflex_fault_pressure", 0.0) or 0.0) > 1.7
    )
    if urgent_recovery:
        return ("recovery", rec_method, "recovery urgent")

    recovery_valid = rec_method in ("art", "dream", "reflect", "quiet")
    exploration_valid = exp_method != "none"

    if recovery_valid and exploration_valid:
        if last_action.startswith("recovery:"):
            return ("exploration", exp_method, "alternating away from repeated recovery")
        if last_action.startswith("explore:"):
            return ("recovery", rec_method, "alternating away from repeated exploration")
        return ("exploration", exp_method, "exploration allowed alongside recovery")

    if exploration_valid:
        return ("exploration", exp_method, "exploration valid")

    if recovery_valid:
        return ("recovery", rec_method, "recovery valid")

    if dream_ok:
        return ("dream", "auto", "dream fallback")

    return ("none", "none", "no valid drive")


def run_drive_tick(state):
    ok, reason = _safe_idle_check(state)
    if not ok:
        append_drive_log(f"tick skipped: {reason}")
        return f"DRIVE TICK\n\nSkipped: {reason}"

    st = state.get("internal_state", {}) or {}
    last_drive_ts = float(st.get("last_drive_tick_ts", 0.0) or 0.0)
    now = time.time()

    if now - last_drive_ts < 20.0:
        append_drive_log("tick skipped: throttled")
        return "DRIVE TICK\n\nSkipped: throttled"

    _rec_text, rec_method = recovery_advice(state)
    _exp_text, exp_method = exploration_advice(state)
    dream_ok, dream_reason = dream_allowed(state)

    category, method, why = _choose_drive(state, rec_method, exp_method, dream_ok)

    result_lines = [
        "DRIVE TICK",
        "",
        f"Recovery Suggestion: {rec_method}",
        f"Exploration Suggestion: {exp_method}",
        f"Dream Allowed: {dream_ok}",
        f"Chosen Category: {category}",
        f"Chosen Method: {method}",
        f"Arbitration Reason: {why}",
    ]

    performed = "none"

    if category == "recovery":
        performed = f"recovery:{method}"
        append_drive_log(f"performing recovery action: {method} ({why})")
        result_lines.extend(["", recovery_act(state)])

    elif category == "exploration":
        performed = f"explore:{method}"
        append_drive_log(f"performing exploration action: {method} ({why})")
        result_lines.extend(["", exploration_act(state)])

    elif category == "dream":
        performed = "dream:auto"
        append_drive_log(f"performing dream auto ({why})")
        result_lines.extend(["", auto_dream(state)])

    else:
        append_drive_log(f"tick idle: no action ({dream_reason})")
        result_lines.extend(["", "No background action performed."])

    st["last_drive_tick_ts"] = now
    st["last_drive_action"] = performed

    return "\n".join(result_lines)
