from __future__ import annotations

import random
from typing import Any, Callable, Dict, List


def propose_new_goal(state: Dict[str, Any]) -> str:
    ideas = [
        "improve reasoning trace quality",
        "analyze memory ranking behavior",
        "improve trace summarization accuracy",
        "optimize goal reasoning clarity",
        "improve tool usage reasoning",
    ]
    return random.choice(ideas)


def goal_is_stale(state: Dict[str, Any], meta: Dict[str, Any]) -> bool:
    st = state.get("internal_state", {})
    goal = st.get("current_goal")

    if not goal:
        return True

    goal = str(goal).lower()
    stale_patterns = [
        "use a code editor",
        "implement a caching mechanism",
        "verify the reduction in execution time",
    ]
    return any(pattern in goal for pattern in stale_patterns)


def has_trace_for_current_goal(state: Dict[str, Any], *, submit_reasoning: Callable[[Dict[str, Any]], Any], submit_diagnostics: Callable[[Dict[str, Any]], Any]) -> bool:
    st = state.get("internal_state", {})
    db = state.get("db", [])
    goal = str(st.get("current_goal", "") or "").strip().lower()

    try:
        submit_reasoning({"goal": goal, "state": state})
        submit_diagnostics({"state": state})
    except Exception:
        pass

    if not goal:
        return False

    goal_words = [w for w in goal.split() if len(w) > 3][:6]

    for entry in reversed(db[-40:]):
        tags = entry.get("tags", []) or []
        text = str(entry.get("text", "") or "").lower()
        if "reasoning_trace" not in tags:
            continue
        if goal in text:
            return True
        matches = sum(1 for word in goal_words if word in text)
        if matches >= 2:
            return True

    return False


def seed_trace_for_current_goal(state: Dict[str, Any], *, add_entry: Callable[..., Any], submit_reasoning: Callable[[Dict[str, Any]], Any]) -> bool:
    st = state.get("internal_state", {})
    db = state.get("db", [])
    goal = str(st.get("current_goal", "") or "").strip().lower()

    try:
        submit_reasoning({"goal": goal, "state": state})
    except Exception:
        pass

    if not goal:
        return False

    goal_words = [w for w in goal.split() if len(w) > 3][:6]
    for entry in reversed(db[-40:]):
        tags = entry.get("tags", []) or []
        text = str(entry.get("text", "") or "").lower()
        if "reasoning_trace" not in tags:
            continue
        if goal in text:
            return False
        matches = sum(1 for word in goal_words if word in text)
        if matches >= 3:
            return False

    trace = f"goal={goal} | reasoning=working toward the current goal"
    add_entry(
        db,
        text=trace,
        embedding=state["embedder"].embed(trace),
        tags=["reasoning_trace", "goal_seed"],
    )
    return True


def refresh_goal_if_needed(
    state: Dict[str, Any],
    meta: Dict[str, Any],
    *,
    goal_is_stale: Callable[[Dict[str, Any], Dict[str, Any]], bool],
    propose_new_goal: Callable[[Dict[str, Any]], str],
    has_trace_for_current_goal: Callable[[Dict[str, Any]], bool],
    seed_trace_for_current_goal: Callable[[Dict[str, Any]], bool],
    maybe_auto_prune_traces: Callable[[Dict[str, Any]], Any],
) -> bool:
    st = state.get("internal_state", {})
    changed = False

    if goal_is_stale(state, meta):
        new_goal = propose_new_goal(state)
        st["current_goal"] = new_goal
        meta["last_goal"] = new_goal
        changed = True
    elif not st.get("current_goal") and meta.get("last_goal"):
        st["current_goal"] = meta.get("last_goal", "")
        changed = True

    if st.get("current_goal") and not has_trace_for_current_goal(state):
        seeded = seed_trace_for_current_goal(state)
        if seeded:
            maybe_auto_prune_traces(state)

    return changed


def compact_goal_text(text: str) -> str:
    t = str(text or "").strip()
    if not t:
        return ""

    low = t.lower()
    replacements = [
        ("use a code editor to ", ""),
        ("implement a ", ""),
        ("in your own script", "in the script"),
        ("and verify the reduction in execution time", "and verify faster execution"),
        ("and verify the reduction in ex", "and verify faster execution"),
        ("caching mechanism", "caching"),
    ]
    for old, new in replacements:
        low = low.replace(old, new)
    low = low.replace("verify the reduction in ex", "verify faster execution")
    low = " ".join(low.split())
    return low[:64]


def compact_reasoning_text(text: str) -> str:
    t = str(text or "").strip().lower()
    if not t:
        return ""

    replacements = [
        ("working toward goal ", "working toward "),
        ("working toward '", "working toward "),
        ("working toward use a code editor to ", "working toward "),
        ("working toward implement a ", "working toward "),
        ("explaining current reasoning state", "explaining the current state"),
        ("keeping continuity with the latest reply", "keeping continuity"),
        ("reporting active progress calmly", "reporting progress calmly"),
    ]
    for old, new in replacements:
        t = t.replace(old, new)

    t = t.replace("'", "")
    t = t.replace("use a code editor to ", "")
    t = t.replace("implement a ", "")
    t = t.replace("caching mechanism", "caching")
    t = t.replace("in your own script", "in the script")
    t = " ".join(t.split())

    if "working toward" in t and "explaining the current state" in t:
        return "working toward the current goal and explaining the current state"
    if "reporting progress calmly" in t and "keeping continuity" in t:
        return "reporting progress calmly while keeping continuity"
    if t.startswith("working toward "):
        return "working toward the current goal"
    return t[:80]


def summarize_trace_text(text: str) -> str:
    raw = str(text or "").strip()
    if not raw:
        return ""

    parts = [part.strip() for part in raw.split("|")]
    goal_part = ""
    reasoning_part = ""
    result_part = ""

    for part in parts:
        low = part.lower()
        if low.startswith("goal="):
            goal_part = compact_goal_text(part[5:])
        elif low.startswith("reasoning="):
            reasoning_part = compact_reasoning_text(part[10:])
        elif low.startswith("result="):
            result_part = part[7:].strip()[:55]

    keep = []
    if goal_part:
        keep.append(f"goal={goal_part}")
    if reasoning_part:
        keep.append(f"reasoning={reasoning_part}")
    if result_part:
        keep.append(f"result={result_part}")

    if not keep:
        return raw[:110]
    return " | ".join(keep)[:170]


def best_goal_trace(state: Dict[str, Any], limit: int = 12, *, summarize_trace_text: Callable[[str], str], submit_reasoning: Callable[[Dict[str, Any]], Any]) -> str:
    db = state.get("db", [])
    st = state.get("internal_state", {})
    goal = str(st.get("current_goal", "") or "").strip().lower()

    try:
        submit_reasoning({"goal": goal, "state": state})
    except Exception:
        pass

    if not db:
        return ""

    scored = []
    for entry in db:
        tags = entry.get("tags", []) or []
        if "reasoning_trace" not in tags:
            continue

        text = str(entry.get("text", "") or "")
        low = text.lower()
        score = 0.0

        if "goal=" in low:
            score += 0.30
        if "reasoning=" in low:
            score += 0.15
        if "result=" in low:
            score += 0.22
        if "reflection=" in low:
            score += 0.25
        if "goal_cycle" in tags:
            score += 0.12
        if "reflection" in tags:
            score += 0.12
        if "goal_seed" in tags:
            score -= 0.05

        if goal:
            if goal in low:
                score += 0.55
            else:
                goal_words = [word for word in goal.split() if len(word) > 3][:6]
                matches = sum(1 for word in goal_words if word in low)
                score += min(0.20, matches * 0.04)

        scored.append((score, entry))

    if not scored:
        return ""

    scored.sort(key=lambda item: (item[0], str(item[1].get("id", ""))), reverse=True)
    best = scored[0][1]
    return summarize_trace_text(str(best.get("text", "") or ""))


def local_reasoning_summary(
    user_msg: str,
    state: Dict[str, Any],
    meta: Dict[str, Any],
    *,
    best_goal_trace: Callable[[Dict[str, Any]], str],
    compact_goal_text: Callable[[str], str],
    compact_reasoning_text: Callable[[str], str],
    load_identity: Callable[[], Dict[str, Any]],
    ensure_emotional_state: Callable[[Dict[str, Any]], Dict[str, Any]],
    behavior_policy: Callable[[Dict[str, Any]], Dict[str, Any]],
    ensure_working_memory: Callable[[Dict[str, Any]], Dict[str, Any]],
) -> str:
    st = state["internal_state"]
    parts = []

    goal = st.get("current_goal")
    reasoning = st.get("last_reason_summary")
    last_reply = st.get("last_reply")
    trace = ""
    try:
        trace = best_goal_trace(state)
    except Exception:
        trace = ""

    strategy_name = str(st.get("last_strategy_name", "") or "").strip()
    strategy_instruction = str(st.get("last_strategy_instruction", "") or "").strip()
    strategy_mode = str(st.get("last_strategy_selection_mode", "") or "").strip()
    strategy_source = strategy_mode

    if goal:
        parts.append(f"Goal: {compact_goal_text(str(goal))}")
    if reasoning:
        parts.append(f"Reasoning: {compact_reasoning_text(str(reasoning))}")
    if strategy_name:
        parts.append(f"Strategy: {strategy_name}")
    if strategy_instruction:
        parts.append(f"Strategy instruction: {strategy_instruction[:90]}")
    if strategy_mode:
        parts.append(f"Strategy mode: {strategy_mode}")
    if strategy_source:
        parts.append(f"Strategy source: {strategy_source}")

    parts.append(f"Recovery[{st.get('recovery_mode', False)}]")
    parts.append(f"RecoveryMode[{st.get('recovery_mode_type', 'standard')}]")
    parts.append(f"Pressure[{st.get('reflex_fault_pressure', 0.0)}]")

    try:
        ident = load_identity()
        self_desc = str(ident.get("self_description", "") or "").strip()
        self_reflection = str(ident.get("self_reflection", "") or "").strip()
        if self_desc:
            parts.append(f"Identity: {self_desc[:80]}")
        if self_reflection:
            parts.append(f"Self-reflection: {self_reflection[:80]}")
    except Exception:
        pass

    try:
        emo = ensure_emotional_state(state)
        parts.append(
            f"Emotion[c={emo.get('confidence',0.0)}, f={emo.get('frustration',0.0)}, q={emo.get('curiosity',0.0)}, s={emo.get('stability',0.0)}]"
        )
    except Exception:
        pass

    try:
        policy = behavior_policy(state)
        parts.append(
            f"Policy[cautious={policy.get('cautious')}, explore={policy.get('prefer_explore')}, exploit={policy.get('prefer_exploit')}, allow_mutants={policy.get('allow_mutants')}]"
        )
    except Exception:
        pass

    bg_hint = str(st.get("last_background_hint", "") or "").strip()
    if bg_hint:
        parts.append(f"Background hint: {bg_hint[:80]}")

    if st.get("last_hint_used", False):
        used_text = str(st.get("last_hint_used_text", "") or "").strip()
        if used_text:
            parts.append(f"Hint used: {used_text[:80]}")

    hint_usage_count = int(st.get("hint_usage_count", 0) or 0)
    if hint_usage_count:
        parts.append(f"Hint usage count: {hint_usage_count}")

    last_arena_avg = st.get("last_arena_avg_delta", None)
    wm = ensure_working_memory(state)
    if wm.get("active_strategy"):
        parts.append(f"WM strategy: {wm.get('active_strategy')}")
    recent_users = wm.get("recent_user_messages", []) or []
    if recent_users:
        parts.append(f"WM recent user: {recent_users[-1][:60]}")

    if last_arena_avg is not None:
        parts.append(f"Arena avg delta: {last_arena_avg}")
    if trace:
        parts.append(f"Recent trace: {trace}")
    if last_reply and not str(last_reply).startswith("Reasoning:"):
        parts.append(f"Last reply: {str(last_reply)[:80]}")
    if meta.get("generation") is not None:
        parts.append(f"Generation: {meta['generation']}")
    if user_msg:
        parts.append(f"Asked: {user_msg[:50]}")

    if not parts:
        return "No active reasoning summary yet."
    return " | ".join(parts[:12])


def fact_exists(db, fact_text: str):
    target = fact_text.strip().lower()
    for entry in db:
        text = str(entry.get("text", "")).strip().lower()
        tags = entry.get("tags", []) or []
        if "fact" in tags and text == target:
            return True
    return False


def promote_user_fact(state, msg: str, *, add_entry: Callable[..., Any], fact_exists: Callable[[Any, str], bool]):
    db = state.get("db", [])
    embedder = state.get("embedder")
    if not msg:
        return

    text = msg.strip()
    low = text.lower()
    facts = []

    def add_fact(fact_text: str, lane: str = "user_profile"):
        fact_text = str(fact_text or "").strip()
        if not fact_text:
            return
        if not fact_text.endswith("."):
            fact_text += "."
        facts.append((fact_text, lane))

    if low.startswith("i am "):
        tail = text[5:].strip().rstrip(".")
        add_fact("User is " + tail, "user_profile")
        if "working on " in low:
            idx = low.find("working on ")
            proj = text[idx + len("working on "):].strip().rstrip(".")
            if proj:
                add_fact("User is working on " + proj, "project_memory")
        if "developer" in low:
            add_fact("User is a developer", "user_profile")
    elif low.startswith("i'm "):
        tail = text[4:].strip().rstrip(".")
        add_fact("User is " + tail, "user_profile")
        if "developer" in low:
            add_fact("User is a developer", "user_profile")
    elif low.startswith("i have "):
        tail = text[7:].strip().rstrip(".")
        add_fact("User has " + tail, "user_profile")
    elif low.startswith("my "):
        tail = text.strip().rstrip(".")
        add_fact("User has " + tail, "user_profile")

    if "andy's dev studio" in low:
        add_fact("User is developing Andy's Dev Studio", "project_memory")

    if not facts:
        return

    seen = set()
    for fact, lane in facts:
        key = (fact.lower(), lane)
        if key in seen:
            continue
        seen.add(key)
        tags = ["fact", "user_fact", "protected", f"lane:{lane}"]
        try:
            emb = embedder.embed(fact) if embedder else None
        except Exception:
            emb = None
        if fact_exists(db, fact):
            continue
        add_entry(db, text=fact, embedding=emb, tags=tags)


def classify_memory_lane(text: str, source: str = "user") -> str:
    t = str(text or "").strip().lower()
    source = str(source or "").strip().lower()
    if source == "identity":
        return "self_memory"
    if "reasoning=" in t or "goal=" in t or "result=" in t:
        return "reasoning_memory"
    if t.startswith("u: ") or "| ai:" in t or "| local:" in t:
        return "chat_memory"
    if "user is " in t or "user has " in t:
        return "user_profile"
    if "andy's dev studio" in t or "andyai" in t or "andy ai" in t:
        return "project_memory"
    if source == "gemini":
        return "working_memory"
    return "working_memory"


def lane_tags_for(text: str, source: str = "user", base_tags=None):
    lane = classify_memory_lane(text, source=source)
    tags = list(base_tags or [])
    lane_tag = f"lane:{lane}"

    if lane_tag not in tags:
        tags.append(lane_tag)

    is_fact = "fact" in tags or "user_fact" in tags
    is_identity = source == "identity"
    if (is_fact or is_identity) and lane in ("user_profile", "project_memory", "self_memory"):
        if "protected" not in tags:
            tags.append("protected")
    return tags


def build_reasoning_trace(state: Dict[str, Any], user_msg: str, reply: str, *, submit_reasoning: Callable[[Dict[str, Any]], Any]) -> str:
    st = state.get("internal_state", {})
    goal = str(st.get("current_goal", "") or "").strip().lower()
    try:
        submit_reasoning({"goal": goal, "state": state})
    except Exception:
        pass

    reasoning = str(st.get("last_reason_summary", "") or "").strip()
    tool = str(st.get("last_tool", "") or "").strip()
    result = str(st.get("last_result", "") or "").strip()

    parts = []
    if goal:
        parts.append(f"goal={goal[:100]}")
    if reasoning:
        parts.append(f"reasoning={reasoning[:120]}")
    if tool:
        parts.append(f"tool={tool[:40]}")
    if result:
        parts.append("result=recorded")
    if user_msg:
        parts.append(f"user={user_msg[:60]}")
    if reply:
        parts.append(f"reply={reply[:100]}")
    return " | ".join(parts[:6])


def normalize_trace_text(text: str) -> str:
    t = str(text or "").strip().lower()
    t = " ".join(t.split())
    if " | reply=" in t:
        t = t.split(" | reply=", 1)[0]
    if " | user=" in t:
        t = t.split(" | user=", 1)[0]
    return t[:180]


def consolidate_reasoning_traces(db, keep_per_key: int = 2):
    grouped = {}
    other_entries = []

    for entry in db:
        tags = entry.get("tags", []) or []
        if "protected" in tags:
            other_entries.append(entry)
            continue
        text = str(entry.get("text", "") or "")
        if "reasoning_trace" not in tags:
            other_entries.append(entry)
            continue
        key = normalize_trace_text(text)
        grouped.setdefault(key, []).append(entry)

    kept = []
    removed = 0
    for _, entries in grouped.items():
        entries_sorted = sorted(entries, key=lambda entry: str(entry.get("id", "")), reverse=True)
        kept.extend(entries_sorted[:keep_per_key])
        removed += max(0, len(entries_sorted) - keep_per_key)

    new_db = other_entries + kept
    return new_db, removed


def maybe_auto_prune_traces(state: Dict[str, Any], threshold: int = 8, keep_per_key: int = 1, *, consolidate_reasoning_traces: Callable[..., Any], save_db: Callable[..., Any], write_galaxy_html: Callable[..., Any], db_path: str):
    db = state.get("db", [])
    trace_count = 0
    for entry in db:
        tags = entry.get("tags", []) or []
        if "reasoning_trace" in tags:
            trace_count += 1
    if trace_count < threshold:
        return 0

    new_db, removed = consolidate_reasoning_traces(db, keep_per_key=keep_per_key)
    if removed <= 0:
        return 0

    state["db"] = new_db
    db.clear()
    db.extend(new_db)
    save_db(db_path, db)
    write_galaxy_html(db, "galaxy.html")
    return removed
