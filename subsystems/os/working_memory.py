from __future__ import annotations

from typing import Any, Callable, Dict


def ensure_working_memory(state: Dict[str, Any]) -> Dict[str, Any]:
    st = state.get("internal_state", {})
    wm = st.setdefault("working_memory", {})
    wm.setdefault("recent_user_messages", [])
    wm.setdefault("recent_replies", [])
    wm.setdefault("recent_tools", [])
    wm.setdefault("recent_results", [])
    wm.setdefault("recent_hints", [])
    wm.setdefault("active_strategy", "")
    wm.setdefault("current_goal", "")
    wm.setdefault("last_updated", "")
    return wm


def wm_push_list(wm: Dict[str, Any], key: str, value: str, limit: int = 6) -> None:
    arr = list(wm.get(key, []) or [])
    value = str(value or "").strip()
    if not value:
        return
    arr.append(value[:240])
    if len(arr) > limit:
        arr = arr[-limit:]
    wm[key] = arr


def refresh_working_memory_from_state(
    state: Dict[str, Any],
    *,
    now_ts: Callable[[], str],
) -> Dict[str, Any]:
    st = state.get("internal_state", {})
    wm = ensure_working_memory(state)

    wm["current_goal"] = str(st.get("current_goal", "") or "")[:240]
    wm["active_strategy"] = str(st.get("last_strategy_name", "") or "")[:120]
    wm["last_updated"] = now_ts()

    last_tool = str(st.get("last_tool", "") or "").strip()
    if last_tool:
        wm_push_list(wm, "recent_tools", last_tool, limit=6)

    last_result = str(st.get("last_result", "") or "").strip()
    if last_result:
        wm_push_list(wm, "recent_results", last_result, limit=6)

    last_hint = str(st.get("last_background_hint", "") or "").strip()
    if last_hint:
        wm_push_list(wm, "recent_hints", last_hint, limit=6)

    return wm


def working_memory_text(state: Dict[str, Any]) -> str:
    wm = ensure_working_memory(state)

    lines = [
        "WORKING MEMORY",
        "",
        f"Current Goal: {wm.get('current_goal', '')}",
        f"Active Strategy: {wm.get('active_strategy', '')}",
        f"Last Updated: {wm.get('last_updated', '')}",
        "",
        "Recent User Messages:",
    ]
    for x in wm.get("recent_user_messages", [])[-6:]:
        lines.append(f"  - {x}")

    lines.append("")
    lines.append("Recent Replies:")
    for x in wm.get("recent_replies", [])[-6:]:
        lines.append(f"  - {x}")

    lines.append("")
    lines.append("Recent Tools:")
    for x in wm.get("recent_tools", [])[-6:]:
        lines.append(f"  - {x}")

    lines.append("")
    lines.append("Recent Results:")
    for x in wm.get("recent_results", [])[-6:]:
        lines.append(f"  - {x}")

    lines.append("")
    lines.append("Recent Hints:")
    for x in wm.get("recent_hints", [])[-6:]:
        lines.append(f"  - {x}")

    return "\n".join(lines)
