from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict


@dataclass
class ConsciousSurface:
    name: str
    generation: int
    self_description: str
    self_reflection: str
    current_goal: str
    last_tool: str
    champion_score: float
    last_background_hint: str
    background_reasoning: str
    last_strategy_name: str
    last_strategy_mode: str
    last_reply: str
    pressure: float
    recovery_mode: bool
    recovery_mode_type: str
    emotion_confidence: float
    emotion_frustration: float
    emotion_curiosity: float
    emotion_stability: float
    wm_active_strategy: str
    wm_recent_user: str


def build_conscious_surface(
    state: Dict[str, Any],
    meta: Dict[str, Any],
    *,
    load_identity: Callable[[], Dict[str, Any]],
    ensure_emotional_state: Callable[[Dict[str, Any]], Dict[str, Any]],
    ensure_working_memory: Callable[[Dict[str, Any]], Dict[str, Any]],
) -> ConsciousSurface:
    st = state.get("internal_state", {})
    ident = load_identity()
    emo = ensure_emotional_state(state)
    wm = ensure_working_memory(state)
    recent_users = wm.get("recent_user_messages", []) or []

    return ConsciousSurface(
        name=str(ident.get("name", "ANDY AI") or "ANDY AI"),
        generation=int(meta.get("generation", 0) or 0),
        self_description=str(ident.get("self_description", "") or ""),
        self_reflection=str(ident.get("self_reflection", "") or ""),
        current_goal=str(st.get("current_goal", "") or ""),
        last_tool=str(st.get("last_tool", "") or ""),
        champion_score=float(st.get("champion_score", 0.0) or 0.0),
        last_background_hint=str(st.get("last_background_hint", "") or ""),
        background_reasoning=str(st.get("background_reasoning", "") or ""),
        last_strategy_name=str(st.get("last_strategy_name", "") or ""),
        last_strategy_mode=str(st.get("last_strategy_selection_mode", "") or ""),
        last_reply=str(st.get("last_reply", "") or ""),
        pressure=float(st.get("reflex_fault_pressure", 0.0) or 0.0),
        recovery_mode=bool(st.get("recovery_mode", False)),
        recovery_mode_type=str(st.get("recovery_mode_type", "standard") or "standard"),
        emotion_confidence=float(emo.get("confidence", 0.0) or 0.0),
        emotion_frustration=float(emo.get("frustration", 0.0) or 0.0),
        emotion_curiosity=float(emo.get("curiosity", 0.0) or 0.0),
        emotion_stability=float(emo.get("stability", 0.0) or 0.0),
        wm_active_strategy=str(wm.get("active_strategy", "") or ""),
        wm_recent_user=str(recent_users[-1] if recent_users else ""),
    )
