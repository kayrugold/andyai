from __future__ import annotations

import time
from typing import Any, Callable, Dict, List


def weakest_topics(*, load_json: Callable[[str, Any], Any]) -> List[str]:
    try:
        data = load_json("brain_scores.json", {})
        hist = data.get("history", [])
        if len(hist) < 2:
            return []

        last = hist[-1]
        details = last.get("details", []) or []
        topics = []

        for detail in details:
            low = str(detail).lower()
            if "status:" in low:
                topics.append("status")
            if "what_are_you_doing" in low or "how_are_you" in low:
                topics.append("conversation")
                topics.append("reasoning")
            if "help:" in low:
                topics.append("help")
                topics.append("command-understanding")
            if "hi:" in low or "hello:" in low:
                topics.append("common-commands")
            if "memory" in low or "mem " in low:
                topics.append("memory-search")

        seen = set()
        out = []
        for topic in topics:
            if topic not in seen:
                seen.add(topic)
                out.append(topic)
        return out
    except Exception:
        return []


def recent_topic_scores(*, load_json: Callable[[str, Any], Any]) -> Dict[str, float]:
    scores: Dict[str, float] = {}
    try:
        data = load_json("brain_scores.json", {})
        hist = data.get("history", [])[-20:]
        for item in hist:
            diff = item.get("diff", {})
            score = float(item.get("score", 0.0) or 0.0)
            if not diff:
                continue

            old = diff.get("old", {})
            new = diff.get("new", {})
            changed_topics = set()

            if old.get("help") != new.get("help"):
                changed_topics.add("help")
                changed_topics.add("command-understanding")
            if old.get("status") != new.get("status"):
                changed_topics.add("status")
            if old.get("why") != new.get("why"):
                changed_topics.add("reasoning")
            if old.get("mem help") != new.get("mem help"):
                changed_topics.add("memory-search")
            if old.get("what are you doing") != new.get("what are you doing") or old.get("how are you") != new.get("how are you"):
                changed_topics.add("conversation")
                changed_topics.add("reasoning")
            if old.get("hi") != new.get("hi"):
                changed_topics.add("common-commands")
                changed_topics.add("concise-replies")

            for topic in changed_topics:
                scores[topic] = max(scores.get(topic, 0.0), score)
    except Exception:
        return {}

    return scores


def goal_topic_hints(state: Dict[str, Any]) -> List[str]:
    st = state.get("internal_state", {})
    goal = str(st.get("current_goal", "") or "").lower()
    hints: List[str] = []

    if not goal:
        return hints
    if any(token in goal for token in ["reason", "why", "explain", "think", "understand"]):
        hints.extend(["reasoning", "conversation"])
    if any(token in goal for token in ["memory", "recall", "search", "remember"]):
        hints.extend(["memory-search", "command-understanding"])
    if any(token in goal for token in ["status", "progress", "state", "generation"]):
        hints.extend(["status", "help"])
    if any(token in goal for token in ["help", "command", "guide", "usage"]):
        hints.extend(["help", "command-understanding"])
    if any(token in goal for token in ["talk", "conversation", "friendly", "kind", "reply"]):
        hints.extend(["conversation", "concise-replies"])
    if any(token in goal for token in ["common", "hello", "hi", "greeting"]):
        hints.extend(["common-commands", "concise-replies"])
    if any(token in goal for token in ["safe", "safer", "reflex"]):
        hints.extend(["reflex", "common-commands"])

    seen = set()
    ordered = []
    for hint in hints:
        if hint not in seen:
            seen.add(hint)
            ordered.append(hint)
    return ordered


def infer_reasoning_summary(state: Dict[str, Any], user_msg: str = "", *, submit_reasoning_task: Callable[[Dict[str, Any]], Any]) -> str:
    st = state.get("internal_state", {})
    goal = str(st.get("current_goal", "") or "").strip().lower()
    try:
        submit_reasoning_task({"type": "reasoning", "goal": goal, "state": state})
    except Exception:
        pass

    last_tool = str(st.get("last_tool", "") or "").strip()
    last_result = str(st.get("last_result", "") or "").strip()
    last_reply = str(st.get("last_reply", "") or "").strip()

    bits = []
    if goal:
        bits.append(f"working toward goal '{goal[:80]}'")
    if last_tool:
        bits.append(f"recently used tool '{last_tool}'")
    if last_result:
        bits.append("tracking the most recent tool result")
    if user_msg:
        low = user_msg.lower()
        if "why" in low or "what are you doing" in low:
            bits.append("explaining current reasoning state")
        elif "how are you" in low:
            bits.append("reporting active progress calmly")
    if last_reply and not last_reply.startswith("Reasoning:"):
        bits.append("keeping continuity with the latest reply")
    if not bits:
        return "tracking current state and preparing the next useful step"
    return ", ".join(bits)[:180]


def recent_failure_topics(*, load_json: Callable[[str, Any], Any]) -> List[str]:
    try:
        data = load_json("brain_scores.json", {})
        hist = data.get("history", [])[-12:]
        topics: List[str] = []

        for item in reversed(hist):
            details = item.get("details", []) or []
            for detail in details:
                low = str(detail).lower()
                if "status:" in low:
                    topics.append("status")
                if "help:" in low:
                    topics.append("help")
                    topics.append("command-understanding")
                if "what_are_you_doing" in low or "how_are_you" in low:
                    topics.append("conversation")
                    topics.append("reasoning")
                if "why:" in low:
                    topics.append("reasoning")
                if "mem" in low or "memory" in low:
                    topics.append("memory-search")
                if "hi:" in low or "hello:" in low:
                    topics.append("common-commands")
                    topics.append("concise-replies")

        seen = set()
        out = []
        for topic in topics:
            if topic not in seen:
                seen.add(topic)
                out.append(topic)
        return out
    except Exception:
        return []


def choose_autotrain_topic(
    i: int,
    state: Dict[str, Any],
    *,
    targeted_mutations: Dict[str, str],
    weakest_topics: Callable[[], List[str]],
    recent_failure_topics: Callable[[], List[str]],
    goal_topic_hints: Callable[[Dict[str, Any]], List[str]],
    recent_topic_scores: Callable[[], Dict[str, float]],
) -> str:
    default_topics = ["help", "concise-replies", "common-commands", "reasoning", "memory-search"]
    weak = weakest_topics()
    failures = recent_failure_topics()
    goal_hints = goal_topic_hints(state)
    score_map = recent_topic_scores()

    priority_pool: List[str] = []
    priority_pool.extend(goal_hints)
    priority_pool.extend(failures)
    priority_pool.extend(weak)

    seen = set()
    filtered = []
    for topic in priority_pool:
        if topic in targeted_mutations and topic not in seen:
            seen.add(topic)
            filtered.append(topic)

    if filtered:
        ranked = sorted(filtered, key=lambda topic: score_map.get(topic, 0.0), reverse=True)
        return ranked[i % len(ranked)]

    ranked_defaults = sorted(default_topics, key=lambda topic: score_map.get(topic, 0.0), reverse=True)
    return ranked_defaults[i % len(ranked_defaults)]


def autotrain_loop(
    state: Dict[str, Any],
    gemini,
    rounds: int = 20,
    *,
    targeted_mutations: Dict[str, str],
    choose_autotrain_topic: Callable[[int, Dict[str, Any]], str],
    evolve: Callable[[str, Any], Any],
    log: Callable[[str], None],
    load_json: Callable[[str, Any], Any],
    save_state: Callable[[Dict[str, Any]], None],
) -> None:
    for i in range(rounds):
        topic = choose_autotrain_topic(i, state)
        goal = str(state.get("internal_state", {}).get("current_goal", "") or "")
        if goal:
            log(f"[AUTOTRAIN {i+1}/{rounds}] current_goal={goal}")

        ok, msg = evolve(topic, gemini)
        log(f"[AUTOTRAIN {i+1}/{rounds}] {msg}")

        if ok:
            state["internal_state"]["brain_version"] = f"score_update_{int(time.time())}"
            state["internal_state"]["champion_score"] = load_json(
                "brain_scores.json", {}
            ).get("champion_score", state["internal_state"].get("champion_score", 0.0))
            save_state(state["internal_state"])


def print_mutation_topics(targeted_mutations: Dict[str, str]) -> List[str]:
    return [f"  {key} -> {value}" for key, value in sorted(targeted_mutations.items())]
