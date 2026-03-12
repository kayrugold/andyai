# state_store.py - persistent internal state for AndyAI v6
import os
import json
import time
from typing import Any, Dict


STATE_PATH = "state.json"


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def default_state() -> Dict[str, Any]:
    return {
        "current_goal": "",
        "last_plan": [],
        "last_tool": "",
        "last_result": "",
        "last_reply": "",
        "last_user_message": "",
        "last_reason_summary": "",
        "confidence": 0.0,
        "brain_version": "unknown",
        "champion_score": 0.0,
        "recent_failures": [],
        "recent_successes": [],
        "style": "practical, direct, compact",
        "updated_at": _now(),
    }


def load_state(path: str = STATE_PATH) -> Dict[str, Any]:
    if not os.path.exists(path):
        return default_state()
    try:
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
        if not isinstance(obj, dict):
            return default_state()
        base = default_state()
        base.update(obj)
        return base
    except Exception:
        return default_state()


def save_state(state: Dict[str, Any], path: str = STATE_PATH) -> None:
    state = dict(state)
    state["updated_at"] = _now()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def push_limited(lst, item, limit=20):
    lst.append(item)
    while len(lst) > limit:
        del lst[0]