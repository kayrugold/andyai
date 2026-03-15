from __future__ import annotations

from typing import Any, Dict, List, Tuple


def summarize_goal_cycle_result(goal: str, steps: List[str]) -> Dict[str, str]:
    goal_low = str(goal or "").lower()
    joined = " ".join(steps).lower()

    if "reason" in goal_low or "clarity" in goal_low:
        result = "generated a clearer reasoning plan"
        reflection = "the plan improved structure and clarity for the current goal"
    elif "memory" in goal_low:
        result = "generated a memory-focused improvement plan"
        reflection = "the plan identified ways to improve memory use for the current goal"
    elif "tool" in goal_low:
        result = "generated a tool-usage improvement plan"
        reflection = "the plan clarified how tools could support the current goal"
    elif "summarize" in joined or "summary" in joined:
        result = "generated a compact summary-oriented plan"
        reflection = "the plan improved how the goal could be explained and tracked"
    else:
        result = "generated a structured next-step plan"
        reflection = "the plan produced a clearer path forward for the current goal"

    return {
        "result": result,
        "reflection": reflection,
    }


def score_diagnostics_from_state(
    state: Dict[str, Any],
    meta: Dict[str, Any],
) -> Tuple[float, Dict[str, float]]:
    st = state.get("internal_state", {})
    db = state.get("db", [])

    memory_entries = len(db)
    reasoning_traces = 0
    reflections = 0
    goal_cycles = 0

    learning_entries = []
    for entry in db:
        tags = entry.get("tags", []) or []
        text = str(entry.get("text", "") or "")
        if "reasoning_trace" in tags:
            reasoning_traces += 1
        if "reflection" in tags:
            reflections += 1
        if "goal_cycle" in tags:
            goal_cycles += 1
        if "goal_cycle" in tags or ("reasoning_trace" in tags and "result=" in text):
            learning_entries.append(text)

    current_goal = str(st.get("current_goal", meta.get("last_goal", "")) or "").strip()
    last_reason = str(st.get("last_reason_summary", "") or "").strip()
    last_result = str(st.get("last_result", "") or "").strip()
    last_reflection = str(st.get("last_reflection", "") or "").strip()
    last_plan = st.get("last_plan", []) or []

    recent_learning = learning_entries[-3:]

    core_behavior = 100.0
    if current_goal:
        core_behavior += 10.0
    if last_reason:
        core_behavior += 10.0

    reasoning_clarity = 0.0
    if last_reason:
        reasoning_clarity += 30.0
    if "working through" in last_reason.lower():
        reasoning_clarity += 15.0
    if current_goal and current_goal.lower() in (last_reason + " " + last_result).lower():
        reasoning_clarity += 15.0

    if isinstance(last_plan, list):
        plan_len = len([x for x in last_plan if str(x).strip()])
        reasoning_clarity += min(plan_len * 5.0, 15.0)

    learning_loop = 0.0
    learning_loop += min(goal_cycles * 12.0, 36.0)
    if last_result:
        learning_loop += 12.0
    if last_reflection:
        learning_loop += 16.0

    for text in recent_learning:
        low = text.lower()
        if "generated a clearer reasoning plan" in low:
            learning_loop += 6.0
        if "reflection=" in low:
            learning_loop += 4.0
        if "result=recorded" in low:
            learning_loop -= 2.0

    memory_quality = 0.0
    memory_quality += min(memory_entries * 0.8, 16.0)
    memory_quality += min(reasoning_traces * 3.0, 18.0)
    memory_quality += min(reflections * 4.0, 12.0)

    recent_compact = [x[:180] for x in recent_learning]
    duplicate_penalty = max(0, len(recent_compact) - len(set(recent_compact))) * 3.0
    memory_quality -= duplicate_penalty

    diagnostics = 10.0
    if st.get("champion_score") is not None:
        diagnostics += 5.0
    if current_goal:
        diagnostics += 5.0
    if last_plan:
        diagnostics += 5.0

    hint_usage_count = int(st.get("hint_usage_count", 0) or 0)
    diagnostics += min(hint_usage_count * 2.0, 10.0)

    subscores = {
        "core_behavior": round(max(core_behavior, 0.0), 1),
        "reasoning_clarity": round(max(reasoning_clarity, 0.0), 1),
        "learning_loop": round(max(learning_loop, 0.0), 1),
        "memory_quality": round(max(memory_quality, 0.0), 1),
        "diagnostics": round(max(diagnostics, 0.0), 1),
    }

    total = round(sum(subscores.values()), 1)
    return total, subscores


def count_learning_entries(db: List[Dict[str, Any]]) -> int:
    count = 0
    for entry in db:
        tags = entry.get("tags", []) or []
        text = str(entry.get("text", "") or "")
        if "goal_cycle" in tags or ("reasoning_trace" in tags and "result=" in text):
            count += 1
    return count
