from __future__ import annotations

from typing import Any, Callable, Dict


def compose_local_reply_from_surface(
    user_msg: str,
    state: Dict[str, Any],
    meta: Dict[str, Any],
    hits,
    *,
    build_conscious_surface: Callable[[Dict[str, Any], Dict[str, Any]], Any],
    compose_ai_local_reply: Callable[..., str],
    reasoning_summary_for: Callable[[str, Dict[str, Any], Dict[str, Any]], str],
) -> str:
    surface = build_conscious_surface(state, meta)
    return compose_ai_local_reply(
        user_msg,
        surface,
        hits,
        reasoning_summary_for=lambda prompt: reasoning_summary_for(prompt, state, meta),
    )


def conscious_reasoning_summary(
    user_msg: str,
    state: Dict[str, Any],
    meta: Dict[str, Any],
    *,
    build_conscious_surface: Callable[[Dict[str, Any], Dict[str, Any]], Any],
    best_goal_trace: Callable[[Dict[str, Any]], str],
    compose_reasoning_view: Callable[..., str],
) -> str:
    surface = build_conscious_surface(state, meta)
    trace = ""
    try:
        trace = best_goal_trace(state)
    except Exception:
        trace = ""
    return compose_reasoning_view(surface, asked=user_msg, trace=trace)


def conscious_identity_text(
    state: Dict[str, Any],
    meta: Dict[str, Any],
    *,
    build_conscious_surface: Callable[[Dict[str, Any], Dict[str, Any]], Any],
    compose_identity_reply: Callable[[Any], str],
) -> str:
    surface = build_conscious_surface(state, meta)
    return compose_identity_reply(surface)
