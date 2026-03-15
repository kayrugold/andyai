from __future__ import annotations

from typing import Any, Callable

from subsystems.os.conscious_surface import ConsciousSurface


def compose_identity_reply(surface: ConsciousSurface) -> str:
    if surface.self_reflection:
        return f"{surface.self_description or 'I am ANDY AI.'} Reflection: {surface.self_reflection}"
    return surface.self_description or "I am ANDY AI."


def compose_reasoning_view(surface: ConsciousSurface, *, asked: str = "", trace: str = "") -> str:
    parts = []

    if surface.current_goal:
        parts.append(f"Goal: {surface.current_goal[:80]}")
    if surface.last_strategy_name:
        parts.append(f"Strategy: {surface.last_strategy_name}")
    if surface.last_strategy_mode:
        parts.append(f"Strategy mode: {surface.last_strategy_mode}")
    parts.append(f"Recovery[{surface.recovery_mode}]")
    parts.append(f"RecoveryMode[{surface.recovery_mode_type}]")
    parts.append(f"Pressure[{surface.pressure}]")
    parts.append(
        f"Emotion[c={surface.emotion_confidence}, f={surface.emotion_frustration}, q={surface.emotion_curiosity}, s={surface.emotion_stability}]"
    )

    if surface.last_background_hint:
        parts.append(f"Background hint: {surface.last_background_hint[:80]}")
    if surface.background_reasoning:
        parts.append(f"Background reasoning: {surface.background_reasoning[:80]}")
    if surface.wm_active_strategy:
        parts.append(f"WM strategy: {surface.wm_active_strategy[:60]}")
    if surface.wm_recent_user:
        parts.append(f"WM recent user: {surface.wm_recent_user[:60]}")
    if trace:
        parts.append(f"Recent trace: {trace[:120]}")
    if surface.last_reply and not surface.last_reply.startswith("Reasoning:"):
        parts.append(f"Last reply: {surface.last_reply[:80]}")
    parts.append(f"Generation: {surface.generation}")
    if asked:
        parts.append(f"Asked: {asked[:50]}")

    return " | ".join(parts[:12]) if parts else "No active reasoning summary yet."


def compose_local_reply(
    user_msg: str,
    surface: ConsciousSurface,
    hits,
    *,
    reasoning_summary_for: Callable[[str], str],
) -> str:
    low = user_msg.lower().strip()

    if low == "why":
        return reasoning_summary_for("why")

    if low.startswith("mem ") and len(low) > 4:
        return "Use mem <query> to search stored memory entries for similar past context."

    if low == "who are you":
        return surface.self_description or "I am ANDY AI."

    if low == "identity":
        return compose_identity_reply(surface)

    if "what are you doing" in low or "what are you trying" in low:
        return reasoning_summary_for("what are you doing")

    if "how are you" in low:
        goal = surface.current_goal or "no active goal"
        if surface.pressure >= 1.5:
            return f"I'm under some system pressure and staying cautious. Current goal: {goal}."
        return f"I'm running generation work and tracking self-improvement. Current goal: {goal}."

    if low == "status":
        return (
            f"Generation {surface.generation}. "
            f"Goal: {surface.current_goal or 'none'}. "
            f"Last tool: {surface.last_tool or 'none'}. "
            f"Champion score: {surface.champion_score:.1f}."
        )

    if low == "help":
        return "Try status, why, who are you, identity, mem <query>, rules, step, run 3, mutate help, reflect identity, or autotrain 8."

    if hits:
        top = hits[0][1].get("text", "")
        return f"My best memory match is: {top[:180]}"

    if surface.self_description:
        return surface.self_description[:220]

    return f"I’m tracking surfaced state, memory, and brain fitness. Current goal is {surface.current_goal or 'not set yet'}."
