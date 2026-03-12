
from task_queue import TaskQueue, Worker
from workers import gemini_worker, reasoning_worker, diagnostics_worker
from art_engine import write_svg_art, art_status_text, art_gallery_text, art_profile_text, art_modes_text, evolve_art
from art_commands import handle_art_command
from language_commands import handle_language_command
from regulation_commands import handle_regulation_command
from memory_commands import handle_memory_command

import threading
import time
import os
import json
import time
import importlib.util
import traceback
from typing import Any, Dict, List

from planner import create_plan
from llm_gemini import GeminiClient
from embedder import Embedder
from memory_store import load_db, save_db, add_entry
from recall import top_k
from tool_registry import ToolRegistry
from tools_basic import (
    tool_calc,
    tool_time,
    tool_read_json,
    tool_write_json,
    tool_memory_search_factory,
    tool_memory_add_factory,
)
from galaxy import write_galaxy_html
from evolver import seed_current_brain, evolve, reflect_identity
from state_store import load_state, save_state, push_limited
from archive_commands import archive_project

APP = "AndyAI-v182 (Curiosity-Driven Exploration Behavior)"
DB_PATH = "memory.json"
META_PATH = "meta.json"
RULES_PATH = "rules.json"
IDENTITY_PATH = "identity.json"
BRAIN_FILE = "brain_evolved.py"
LOG_FILE = "andy.log"

TARGETED_MUTATIONS = {
    "common-commands": "Improve common command handling for hi, hello, help, and status while keeping replies concise.",
    "concise-replies": "Make replies shorter and cleaner for simple local conversations while preserving usefulness.",
    "conversation": "Improve local conversation replies for prompts like what are you doing and how are you while preserving clarity.",
    "help": "Improve the help-related local response behavior so it is concise and useful.",
    "reflex": "Improve safer reflex brain behavior for common commands without adding network calls or long replies.",
    "status": "Improve the status command reply so it stays concise but still mentions system state or generation progress.",
    "reasoning": "Improve replies for why and reasoning-style prompts so they sound more aware of current goals and recent activity.",
    "memory-search": "Improve help and guidance around memory search so the user better understands mem <query>.",
    "command-understanding": "Improve short guidance for what commands exist and how to use them clearly.",
}


def now_ts() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def log(line: str) -> None:
    line = f"[{now_ts()}] {line}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def load_json(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path: str, obj: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)


def load_rules() -> List[Dict[str, Any]]:
    obj = load_json(RULES_PATH, [])
    return obj if isinstance(obj, list) else []


def add_rule(text: str, kind: str = "user_rule") -> None:
    rules = load_rules()
    rules.append({"type": kind, "text": text, "ts": now_ts()})
    save_json(RULES_PATH, rules)


def rules_as_text(max_items: int = 25) -> str:
    rules = load_rules()[-max_items:]
    if not rules:
        return "- (none)"
    return "\n".join(f"- [{r.get('type','rule')}] {r.get('text','')}" for r in rules)


def load_identity() -> Dict[str, Any]:
    obj = load_json(IDENTITY_PATH, {})
    return obj if isinstance(obj, dict) else {}


def identity_text() -> str:
    ident = load_identity()
    if not ident:
        return ""
    parts = []
    for key in ["name", "self_description", "purpose", "growth_notes", "self_reflection"]:
        val = ident.get(key)
        if isinstance(val, str) and val.strip():
            parts.append(f"{key}: {val.strip()}")
    for key in ["personality", "core_traits"]:
        val = ident.get(key)
        if isinstance(val, list) and val:
            parts.append(f"{key}: {', '.join(str(x) for x in val)}")
    return "\n".join(parts)


def load_meta() -> Dict[str, Any]:
    meta = load_json(META_PATH, {})
    if not isinstance(meta, dict):
        meta = {}
    meta.setdefault("generation", 0)
    meta.setdefault("last_goal", "")
    meta.setdefault("last_insight", "")
    meta.setdefault("started_at", now_ts())
    return meta


def save_meta(meta: Dict[str, Any]) -> None:
    save_json(META_PATH, meta)


def build_registry(state: Dict[str, Any]) -> ToolRegistry:
    reg = ToolRegistry()
    reg.register("calc", tool_calc)
    reg.register("time", tool_time)
    reg.register("read_json", tool_read_json)
    reg.register("write_json", tool_write_json)
    reg.register("memory_search", tool_memory_search_factory(state))
    reg.register("memory_add", tool_memory_add_factory(state))
    return reg


def run_brain(text: str, state: Dict[str, Any]) -> Dict[str, Any]:
    spec = importlib.util.spec_from_file_location("brain_evolved", BRAIN_FILE)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)  # type: ignore
    return mod.process(text, state)  # type: ignore






def propose_new_goal(state: Dict[str, Any]) -> str:

    ideas = [
        "improve reasoning trace quality",
        "analyze memory ranking behavior",
        "improve trace summarization accuracy",
        "optimize goal reasoning clarity",
        "improve tool usage reasoning"
    ]

    import random
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
        "verify the reduction in execution time"
    ]

    for p in stale_patterns:
        if p in goal:
            return True

    return False



def has_trace_for_current_goal(state: Dict[str, Any]) -> bool:
    st = state.get("internal_state", {})
    db = state.get("db", [])
    goal = str(st.get("current_goal", "") or "").strip().lower()

    try:
        rq = state.get("reason_queue")
        dq = state.get("diag_queue")

        if rq is not None:
            rq.submit({
                "goal": goal,
                "state": state
            })

        if dq is not None:
            dq.submit({
                "state": state
            })

    except Exception:
        pass

    try:
        task_queue.submit({
            "type": "reasoning",
            "goal": goal,
            "state": state
        })
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

        matches = sum(1 for w in goal_words if w in text)
        if matches >= 2:
            return True

    return False

def seed_trace_for_current_goal(state: Dict[str, Any]):
    st = state.get("internal_state", {})
    db = state.get("db", [])

    goal = str(st.get("current_goal", "") or "").strip().lower()
    try:
        task_queue.submit({
            "type": "reasoning",
            "goal": goal,
            "state": state
        })
    except Exception:
        pass

    if not goal:
        return False

    goal_low = goal.lower()
    goal_words = [w for w in goal_low.split() if len(w) > 3][:6]

    for entry in reversed(db[-40:]):
        tags = entry.get("tags", []) or []
        text = str(entry.get("text", "") or "").lower()
        if "reasoning_trace" not in tags:
            continue

        if goal_low in text:
            return False

        matches = sum(1 for w in goal_words if w in text)
        if matches >= 3:
            return False

    trace = f"goal={goal} | reasoning=working toward the current goal"
    add_entry(
        db,
        text=trace,
        embedding=state["embedder"].embed(trace),
        tags=["reasoning_trace", "goal_seed"]
    )
    return True

def refresh_goal_if_needed(state: Dict[str, Any], meta: Dict[str, Any]) -> bool:
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

def local_reasoning_summary(user_msg: str, state: Dict[str, Any], meta: Dict[str, Any]) -> str:
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
            f"Emotion[c={emo.get('confidence',0.0)}, f={emo.get('frustration',0.0)}, "
            f"q={emo.get('curiosity',0.0)}, s={emo.get('stability',0.0)}]"
        )
    except Exception:
        pass

    try:
        policy = behavior_policy(state)
        parts.append(
            f"Policy[cautious={policy.get('cautious')}, explore={policy.get('prefer_explore')}, "
            f"exploit={policy.get('prefer_exploit')}, allow_mutants={policy.get('allow_mutants')}]"
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
    f = fact_text.strip().lower()
    for entry in db:
        text = str(entry.get("text","")).strip().lower()
        tags = entry.get("tags",[]) or []
        if "fact" in tags and text == f:
            return True
    return False


def promote_user_fact(state, msg: str):
    db = state.get("db", [])
    embedder = state.get("embedder")

    if not msg:
        return

    t = msg.strip()
    low = t.lower()

    facts = []

    def add_fact(text: str, lane: str = "user_profile"):
        text = str(text or "").strip()
        if not text:
            return
        if not text.endswith("."):
            text += "."
        facts.append((text, lane))

    if low.startswith("i am "):
        tail = t[5:].strip().rstrip(".")
        add_fact("User is " + tail, "user_profile")

        if "working on " in low:
            idx = low.find("working on ")
            proj = t[idx + len("working on "):].strip().rstrip(".")
            if proj:
                add_fact("User is working on " + proj, "project_memory")

        if "developer" in low:
            add_fact("User is a developer", "user_profile")

    elif low.startswith("i'm "):
        tail = t[4:].strip().rstrip(".")
        add_fact("User is " + tail, "user_profile")

        if "developer" in low:
            add_fact("User is a developer", "user_profile")

    elif low.startswith("i have "):
        tail = t[7:].strip().rstrip(".")
        add_fact("User has " + tail, "user_profile")

    elif low.startswith("my "):
        tail = t.strip().rstrip(".")
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

        add_entry(
            db,
            text=fact,
            embedding=emb,
            tags=tags
        )

def classify_memory_lane(text: str, source: str = "user") -> str:
    t = str(text or "").strip().lower()
    source = str(source or "").strip().lower()

    # identity / self memory
    if source == "identity":
        return "self_memory"

    # reasoning traces and internal goal/result chains
    if "reasoning=" in t or "goal=" in t or "result=" in t:
        return "reasoning_memory"

    # raw chat wrappers
    if t.startswith("u: ") or "| ai:" in t or "| local:" in t:
        return "chat_memory"

    # durable user facts
    if "user is " in t or "user has " in t:
        return "user_profile"

    # project-related content
    if "andy's dev studio" in t or "andyai" in t or "andy ai" in t:
        return "project_memory"

    # gemini hints / transient context
    if source == "gemini":
        return "working_memory"

    return "working_memory"

def lane_tags_for(text: str, source: str = "user", base_tags=None):
    lane = classify_memory_lane(text, source=source)
    tags = list(base_tags or [])
    lane_tag = f"lane:{lane}"

    if lane_tag not in tags:
        tags.append(lane_tag)

    # Only structured facts / identity / project memory should become protected.
    # Raw chat wrappers should remain searchable, but not protected.
    is_fact = "fact" in tags or "user_fact" in tags
    is_identity = source == "identity"

    if (is_fact or is_identity) and lane in ("user_profile", "project_memory", "self_memory"):
        if "protected" not in tags:
            tags.append("protected")

    return tags

def protected_memory_status_text(state) -> str:
    db = state.get("db", []) or []
    counts = {}
    protected = 0

    for entry in db:
        tags = entry.get("tags", []) or []
        for tag in tags:
            if str(tag).startswith("lane:"):
                counts[tag] = counts.get(tag, 0) + 1
        if "protected" in tags:
            protected += 1

    lines = ["PROTECTED MEMORY STATUS", ""]
    for k in sorted(counts):
        lines.append(f"{k}: {counts[k]}")
    lines.append("")
    lines.append(f"Protected Entries: {protected}")
    return "\n".join(lines)
def compose_local_reply(user_msg: str, state: Dict[str, Any], meta: Dict[str, Any], hits) -> str:
    st = state["internal_state"]
    low = user_msg.lower().strip()
    ident = load_identity()

    if low == "why":
        return local_reasoning_summary("why", state, meta)

    if low.startswith("mem ") and len(low) > 4:
        return "Use mem <query> to search stored memory entries for similar past context."

    if low == "who are you":
        return ident.get("self_description", "I am ANDY AI.")

    if low == "identity":
        reflection = ident.get("self_reflection", "")
        if reflection:
            return f"{ident.get('self_description', 'I am ANDY AI.')} Reflection: {reflection}"
        return ident.get("self_description", "I am ANDY AI.")

    if "what are you doing" in low or "what are you trying" in low:
        return local_reasoning_summary("what are you doing", state, meta)

    if "how are you" in low:
        goal = st.get("current_goal", "no active goal")
        return f"I'm running generation work and tracking self-improvement. Current goal: {goal}."

    if low == "status":
        return (
            f"Generation {meta.get('generation', 0)}. "
            f"Goal: {st.get('current_goal', 'none')}. "
            f"Last tool: {st.get('last_tool', 'none')}. "
            f"Champion score: {st.get('champion_score', 0.0):.1f}."
        )

    if low == "help":
        return "Try status, why, who are you, identity, mem <query>, rules, step, run 3, mutate help, reflect identity, or autotrain 8."

    if hits:
        top = hits[0][1].get("text", "")
        return f"My best memory match is: {top[:180]}"

    if ident.get("self_description"):
        return ident["self_description"][:220]

    return f"I’m tracking state, memory, and brain fitness. Current goal is {st.get('current_goal', 'not set yet')}."



def build_reasoning_trace(state: Dict[str, Any], user_msg: str, reply: str) -> str:
    st = state.get("internal_state", {})
    goal = str(st.get("current_goal", "") or "").strip().lower()
    try:
        task_queue.submit({
            "type": "reasoning",
            "goal": goal,
            "state": state
        })
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

def weakest_topics() -> List[str]:
    try:
        with open("brain_scores.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        hist = data.get("history", [])
        if len(hist) < 2:
            return []

        last = hist[-1]
        details = last.get("details", []) or []
        topics = []

        for d in details:
            low = str(d).lower()

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
        for t in topics:
            if t not in seen:
                seen.add(t)
                out.append(t)

        return out

    except Exception:
        return []


def recent_topic_scores() -> Dict[str, float]:
    scores: Dict[str, float] = {}
    try:
        with open("brain_scores.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        hist = data.get("history", [])[-20:]
        for h in hist:
            diff = h.get("diff", {})
            score = float(h.get("score", 0.0) or 0.0)
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

            for t in changed_topics:
                scores[t] = max(scores.get(t, 0.0), score)

    except Exception:
        return {}

    return scores

def goal_topic_hints(state: Dict[str, Any]) -> List[str]:
    st = state.get("internal_state", {})
    goal = str(st.get("current_goal", "") or "").lower()

    hints: List[str] = []

    if not goal:
        return hints

    if any(x in goal for x in ["reason", "why", "explain", "think", "understand"]):
        hints.extend(["reasoning", "conversation"])

    if any(x in goal for x in ["memory", "recall", "search", "remember"]):
        hints.extend(["memory-search", "command-understanding"])

    if any(x in goal for x in ["status", "progress", "state", "generation"]):
        hints.extend(["status", "help"])

    if any(x in goal for x in ["help", "command", "guide", "usage"]):
        hints.extend(["help", "command-understanding"])

    if any(x in goal for x in ["talk", "conversation", "friendly", "kind", "reply"]):
        hints.extend(["conversation", "concise-replies"])

    if any(x in goal for x in ["common", "hello", "hi", "greeting"]):
        hints.extend(["common-commands", "concise-replies"])

    if any(x in goal for x in ["safe", "safer", "reflex"]):
        hints.extend(["reflex", "common-commands"])

    seen = set()
    ordered = []
    for h in hints:
        if h not in seen:
            seen.add(h)
            ordered.append(h)
    return ordered


def infer_reasoning_summary(state: Dict[str, Any], user_msg: str = "") -> str:
    st = state.get("internal_state", {})
    goal = str(st.get("current_goal", "") or "").strip().lower()
    try:
        task_queue.submit({
            "type": "reasoning",
            "goal": goal,
            "state": state
        })
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

    text = ", ".join(bits)
    return text[:180]


def recent_failure_topics() -> List[str]:
    try:
        data = load_json("brain_scores.json", {})
        hist = data.get("history", [])[-12:]
        topics: List[str] = []

        for h in reversed(hist):
            details = h.get("details", []) or []
            for d in details:
                low = str(d).lower()

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
        for t in topics:
            if t not in seen:
                seen.add(t)
                out.append(t)
        return out
    except Exception:
        return []


def choose_autotrain_topic(i: int, state: Dict[str, Any]) -> str:
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
    for t in priority_pool:
        if t in TARGETED_MUTATIONS and t not in seen:
            seen.add(t)
            filtered.append(t)

    if filtered:
        ranked = sorted(filtered, key=lambda t: score_map.get(t, 0.0), reverse=True)
        return ranked[i % len(ranked)]

    ranked_defaults = sorted(default_topics, key=lambda t: score_map.get(t, 0.0), reverse=True)
    return ranked_defaults[i % len(ranked_defaults)]


def autotrain_loop(state: Dict[str, Any], gemini: GeminiClient, rounds: int = 20) -> None:
    for i in range(rounds):
        topic = choose_autotrain_topic(i, state)
        req = TARGETED_MUTATIONS.get(topic, topic)
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


def chat_once(state: Dict[str, Any], meta: Dict[str, Any], gemini: GeminiClient, msg: str) -> None:
    db = state["db"]
    internal = state["internal_state"]

    t = threading.Thread(target=maintenance_worker, args=(state,), daemon=True)
    t.start()
    log("MAINT: background maintenance thread started.")

    goal_changed = refresh_goal_if_needed(state, meta)
    if goal_changed:
        save_meta(meta)
        save_state(state["internal_state"])
        save_db(DB_PATH, state["db"])
        write_galaxy_html(state["db"], "galaxy.html")

    if goal_is_stale(state, meta):
        new_goal = propose_new_goal(state)
        internal["current_goal"] = new_goal
        meta["last_goal"] = new_goal


    if not internal.get("current_goal") and meta.get("last_goal"):
        internal["current_goal"] = meta.get("last_goal", "")

    internal["last_user_message"] = msg
    internal["last_reason_summary"] = infer_reasoning_summary(state, msg)

    if msg.strip().lower().startswith("rule:"):
        rule_text = msg.split(":", 1)[1].strip()
        if rule_text:
            add_rule(rule_text, kind="user_rule")
            log("RULE STORED: " + rule_text)
            push_limited(internal["recent_successes"], "stored user rule")
            save_state(internal)
        else:
            log("RULE ERROR: empty rule.")
        return

    try:
        res = run_brain(msg, state)
    except Exception as e:
        res = {"handled": False, "reply": f"(brain error: {e})", "actions": []}

    if res.get("handled"):
        reply = str(res.get("reply", ""))
        log("LOCAL: " + reply)
        internal["last_reply"] = reply
        trace = build_reasoning_trace(state, msg, reply)
        promote_user_fact(state, msg)
        chat_text = f"u: {msg} | local: {reply}"
        add_entry(
            db,
            text=chat_text,
            embedding=state["embedder"].embed(msg),
            tags=lane_tags_for(msg, source="user", base_tags=["chat", "local"])
        )
        add_entry(
            db,
            text=trace,
            embedding=state["embedder"].embed(trace),
            tags=lane_tags_for(trace, source="system", base_tags=["reasoning_trace"])
        )
        removed = maybe_auto_prune_traces(state)
        if removed:
            log(f"AUTO-PRUNE: removed {removed} duplicate reasoning traces.")
    else:
        emb = state["embedder"].embed(msg)
        hits = top_k(db, emb, k=4)

        reply = compose_local_reply(msg, state, meta, hits)
        wm = refresh_working_memory_from_state(state)
        wm_push_list(wm, "recent_user_messages", msg, limit=6)
        wm_push_list(wm, "recent_replies", reply, limit=6)
        log("LOCAL-COMPOSED: " + reply)

        internal["last_reply"] = reply
        trace = build_reasoning_trace(state, msg, reply)
        promote_user_fact(state, msg)
        chat_text = f"u: {msg} | ai: {reply}"
        add_entry(
            db,
            text=chat_text,
            embedding=state["embedder"].embed(msg),
            tags=lane_tags_for(msg, source="user", base_tags=["chat", "composed"])
        )
        add_entry(
            db,
            text=trace,
            embedding=state["embedder"].embed(trace),
            tags=lane_tags_for(trace, source="system", base_tags=["reasoning_trace"])
        )
        removed = maybe_auto_prune_traces(state)
        if removed:
            log(f"AUTO-PRUNE: removed {removed} duplicate reasoning traces.")

    save_db(DB_PATH, db)
    save_meta(meta)
    save_state(internal)
    write_galaxy_html(db, "galaxy.html")




def normalize_trace_text(text: str) -> str:
    t = str(text or "").strip().lower()
    t = " ".join(t.split())

    # Keep only the stable reasoning part for grouping
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

    for key, entries in grouped.items():
        # Keep newest entries by id when possible
        entries_sorted = sorted(
            entries,
            key=lambda e: str(e.get("id", "")),
            reverse=True
        )
        kept.extend(entries_sorted[:keep_per_key])
        removed += max(0, len(entries_sorted) - keep_per_key)

    new_db = other_entries + kept
    return new_db, removed




def idle_debug_text(state, meta, gemini, idle_seconds=45):
    now = time.time()
    last = float(state.get("last_user_activity", now))
    idle = now - last
    running = state.get("auto_cycle_running", False)

    gemini_ok = False
    try:
        if gemini and gemini.available():
            gemini_ok = True
    except Exception:
        gemini_ok = False

    st = state.get("internal_state", {})
    goal = st.get("current_goal", meta.get("last_goal", ""))

    lines = [
        "IDLE DEBUG",
        "",
        f"Idle Seconds: {idle:.1f}",
        f"Idle Threshold: {idle_seconds}",
        f"Auto Cycle Running: {running}",
        f"Gemini Available: {gemini_ok}",
        f"Current Goal: {goal}",
        f"Memory Entries: {len(state.get('db', []))}",
    ]

    if idle >= idle_seconds and not running:
        lines.append("")
        lines.append("AUTO-CYCLE WOULD TRIGGER NOW")

    return "\n".join(lines)

def maybe_auto_prune_traces(state: Dict[str, Any], threshold: int = 8, keep_per_key: int = 1):
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
    save_db(DB_PATH, db)
    write_galaxy_html(db, "galaxy.html")
    return removed




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

    parts = [x.strip() for x in raw.split("|")]
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

def best_goal_trace(state: Dict[str, Any], limit: int = 12) -> str:
    db = state.get("db", [])
    st = state.get("internal_state", {})
    goal = str(st.get("current_goal", "") or "").strip().lower()
    try:
        task_queue.submit({
            "type": "reasoning",
            "goal": goal,
            "state": state
        })
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
                goal_words = [w for w in goal.split() if len(w) > 3][:6]
                matches = sum(1 for w in goal_words if w in low)
                score += min(0.20, matches * 0.04)

        scored.append((score, entry))

    if not scored:
        return ""

    scored.sort(key=lambda x: (x[0], str(x[1].get("id", ""))), reverse=True)
    best = scored[0][1]
    return summarize_trace_text(str(best.get("text", "") or ""))

def rerank_memory_hits(query: str, hits):
    q = str(query or "").strip().lower()
    terms = [t for t in q.split() if t.strip()]
    ranked = []

    for score, entry in hits:
        try:
            base = float(score)
        except Exception:
            base = 0.0

        bonus = 0.0
        text = str(entry.get("text", "") or "")
        low = text.lower()
        tags = entry.get("tags", []) or []

        if "fact" in tags:
            bonus += 0.35
        if "user_fact" in tags:
            bonus += 0.25
        if "protected" in tags:
            bonus += 0.20

        if "reasoning_trace" in tags:
            bonus += 0.05

        exact_hits = 0
        for term in terms:
            if term in low:
                exact_hits += 1

        bonus += min(exact_hits * 0.12, 0.36)

        if q and q in low:
            bonus += 0.20

        if "chat" in tags and "reasoning_trace" not in tags:
            bonus -= 0.04

        ranked.append((round(base + bonus, 3), entry))

    ranked.sort(key=lambda x: x[0], reverse=True)
    return ranked







def submit_background_gemini_task(state: Dict[str, Any], gemini, goal: str) -> None:
    try:
        gq = state.get("gemini_queue")
        if gq is None:
            log("[WORKER gemini_debug] gemini_queue missing")
            return

        prompt = f"Give one short background reasoning hint for goal: {goal}"
        gq.submit({
            "gemini": gemini,
            "prompt": prompt,
            "state": state
        })
        log("[WORKER gemini_debug] submitted gemini background task")
    except Exception as e:
        log("[WORKER gemini_debug] failed to submit gemini task: " + repr(e))





def latest_background_hint_context(state: Dict[str, Any]) -> str:
    st = state.get("internal_state", {})
    hint = str(st.get("last_background_hint", "") or "").strip()
    if not hint:
        return ""
    return f"background_hint={hint}"





def normalize_hint_gene_text(text: str) -> str:
    t = str(text or "").strip().lower()

    if t.startswith("background_hint="):
        t = t[len("background_hint="):].strip()

    t = t.replace("**", "")
    t = t.replace('"', "")
    t = t.replace("“", "")
    t = t.replace("”", "")
    t = " ".join(t.split())

    return t[:240]


def display_hint_gene_text(text: str) -> str:
    t = str(text or "").strip()
    if t.startswith("background_hint="):
        t = t[len("background_hint="):].strip()
    return t[:240]


def update_hint_genome(state, hint_text):
    st = state.get("internal_state", {})
    genome = st.setdefault("hint_genome", {})

    key = normalize_hint_gene_text(hint_text)
    clean_text = display_hint_gene_text(hint_text)

    gene = genome.setdefault(key, {
        "text": clean_text,
        "usage": 0,
        "success": 0,
    })

    if not gene.get("text"):
        gene["text"] = clean_text

    return gene


def get_used_hint_gene(state):
    st = state.get("internal_state", {})
    genome = st.get("hint_genome", {}) or {}
    used_text = str(st.get("last_hint_used_text", "") or "").strip()

    if not used_text:
        return None

    key = normalize_hint_gene_text(used_text)
    return genome.get(key)

def has_similar_background_hint(state: Dict[str, Any], hint_text: str) -> bool:
    db = state.get("db", [])
    target = str(hint_text or "").strip().lower()
    if not target:
        return True

    target_words = {w for w in target.split() if len(w) > 4}

    for entry in reversed(db[-40:]):
        tags = entry.get("tags", []) or []
        if "background_hint" not in tags:
            continue

        text = str(entry.get("text", "") or "").strip().lower()
        if not text:
            continue

        if text == target:
            return True

        if target in text or text in target:
            return True

        text_words = {w for w in text.split() if len(w) > 4}
        overlap = len(target_words & text_words)
        if overlap >= 4:
            return True

    return False

def worker_results_text(state: Dict[str, Any]) -> str:
    results = state.get("worker_results", [])
    if not isinstance(results, list) or not results:
        return "No pending worker results."

    lines = ["PENDING WORKER RESULTS", ""]
    for i, item in enumerate(results[:20], start=1):
        kind = str(item.get("type", "") or "")
        if kind == "reasoning":
            text = str(item.get("thought", ""))[:180]
        elif kind == "diagnostic":
            text = str(item.get("data", ""))[:180]
        elif kind == "gemini":
            text = str(item.get("result", ""))[:180]
        elif kind == "gemini_error":
            text = str(item.get("error", ""))[:180]
        elif kind == "gemini_debug":
            text = str(item.get("message", ""))[:180]
        else:
            text = str(item)[:180]
        lines.append(f"{i}. [{kind}] {text}")

    lines.extend([
        "",
        f"Total Pending: {len(results)}",
    ])
    return "\n".join(lines)

def handle_worker_results(state: Dict[str, Any]) -> None:
    results = state.get("worker_results", [])
    if not isinstance(results, list) or not results:
        return

    while results:
        item = results.pop(0)
        kind = str(item.get("type", "") or "")

        if kind == "reasoning":
            log("[WORKER reasoning] " + str(item.get("thought", ""))[:220])
        elif kind == "diagnostic":
            data = item.get("data", {})
            if isinstance(data, dict):
                log("[WORKER diagnostics] " + str(data))
            else:
                log("[WORKER diagnostics] " + str(data)[:220])
        elif kind == "gemini":
            text = str(item.get("result", ""))[:220]
            log("[WORKER gemini] " + text)
            st = state.get("internal_state", {})
            if isinstance(st, dict):
                st["last_background_hint"] = text
                st["last_background_hint_ts"] = now_ts()

            if text and not has_similar_background_hint(state, text):

                update_hint_genome(state, text)

                db = state.get("db", [])
                emb = state["embedder"].embed(text)
                add_entry(
                    db,
                    text=text,
                    embedding=emb,
                    tags=["background_hint", "gemini_hint", "reasoning_trace"]
                )
                save_db(DB_PATH, db)
                write_galaxy_html(db, "galaxy.html")
                log("[WORKER gemini_commit] stored background hint in memory")
        elif kind == "gemini_error":
            log("[WORKER gemini_error] " + str(item.get("error", ""))[:220])
        elif kind == "gemini_debug":
            log("[WORKER gemini_debug] " + str(item.get("message", ""))[:220])
        else:
            log("[WORKER unknown] " + str(item)[:220])

def status_line(state: Dict[str, Any], meta: Dict[str, Any], gemini: GeminiClient) -> str:
    db = state["db"]
    st = state["internal_state"]
    ident = load_identity()
    return (
        f"{APP}\n"
        f"  name: {ident.get('name', 'ANDY AI')}\n"
        f"  generation: {meta.get('generation')}\n"
        f"  memory_entries: {len(db)}\n"
        f"  last_goal: {meta.get('last_goal','')}\n"
        f"  last_insight: {str(meta.get('last_insight',''))[:120]}\n"
        f"  champion_score: {st.get('champion_score', 0.0):.1f}\n"
        f"  brain_version: {st.get('brain_version','unknown')}\n"
        f"  gemini: {'ON' if gemini.available() else 'OFF'}\n"
        f"  outputs: memory.json, meta.json, state.json, galaxy.html, andy.log, brain_scores.json, identity.json\n"
    )


def print_mutation_topics() -> None:
    print("Mutation topics:")
    for k, v in sorted(TARGETED_MUTATIONS.items()):
        print(f"  {k} -> {v}")




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



def run_goal_cycle_forced_strategy(state: Dict[str, Any], meta: Dict[str, Any], gemini, forced_mode: str) -> str:
    st = state.get("internal_state", {})
    st["arena_forced_mode"] = str(forced_mode or "").strip().lower()
    try:
        return run_goal_cycle(state, meta, gemini)
    finally:
        st["arena_forced_mode"] = ""
def run_goal_cycle(state: Dict[str, Any], meta: Dict[str, Any], gemini) -> str:
    st = state.get("internal_state", {})
    db = state.get("db", [])
    diag_before, _ = score_diagnostics_from_state(state, meta)
    goal = str(st.get("current_goal", "") or "").strip().lower()
    try:
        task_queue.submit({
            "type": "reasoning",
            "goal": goal,
            "state": state
        })
    except Exception:
        pass

    
    submit_background_gemini_task(state, gemini, goal)

    before_learning_entries = count_learning_entries(db)

    after_learning_entries = count_learning_entries(db)
    added_entries = after_learning_entries - before_learning_entries

# restore learning delta calculation


    if not goal:
        return "No current goal set."

    emb = state["embedder"].embed(goal)
    hits = top_k(db, emb, k=5)
    hits = rerank_memory_hits(goal, hits)
    context = [e for _, e in hits[:3]]

    forced_mode = str(st.get("arena_forced_mode", "") or "").strip().lower()
    if forced_mode:
        strategy_pick = choose_strategy_source_forced(state, forced_mode)
    else:
        strategy_pick = choose_strategy_source(state)
    if strategy_pick:
        strategy_name = str(strategy_pick.get("name", "") or "").strip()
        strategy_instruction = str(strategy_pick.get("instruction", "") or "").strip()
    else:
        strategy_name = ""
        strategy_instruction = ""

    if strategy_name and strategy_instruction:
        context.append({
            "id": f"strategy_{now_ts()}",
            "text": f"strategy={strategy_name} | instruction={strategy_instruction}",
            "tags": ["strategy_gene", "planning_context"]
        })

    hint_ctx = latest_background_hint_context(state)
    mutant_hint = str(st.get("latest_mutant_hint", "") or "").strip()
    hint_used = False
    chosen_hint = ""

    if mutant_hint:
        chosen_hint = f"background_hint={mutant_hint}"
    elif hint_ctx:
        chosen_hint = hint_ctx

    if chosen_hint:
        context.append({
            "id": f"bg_hint_{now_ts()}",
            "text": chosen_hint,
            "tags": ["background_hint", "planning_context"]
        })
        hint_used = True

    st["last_hint_used"] = hint_used
    st["last_hint_used_ts"] = now_ts() if hint_used else ""
    st["last_hint_used_text"] = chosen_hint if hint_used else ""
    if hint_used:
        st["hint_usage_count"] = int(st.get("hint_usage_count", 0) or 0) + 1

        gene = update_hint_genome(state, hint_ctx)

        mutant = st.get("latest_mutant_hint")
        if mutant:
            if normalize_hint_gene_text(hint_ctx) == normalize_hint_gene_text(mutant):
                st["mutant_usage"] = int(st.get("mutant_usage", 0) or 0) + 1

        gene["usage"] += 1

    tools = []
    try:
        tools = state["tools"].list_tools()
    except Exception:
        tools = []

    plan = create_plan(goal, context, tools, gemini)
    if not isinstance(plan, list):
        plan = [{"step": "Summarize the current goal and continue."}]

    step_texts = []
    for item in plan[:3]:
        step = str(item.get("step", "") if isinstance(item, dict) else item).strip()
        if step:
            step_texts.append(step)

    if not step_texts:
        step_texts = [f"Summarize progress toward: {goal}"]

    outcome = summarize_goal_cycle_result(goal, step_texts)
    result_text = outcome["result"]
    reflection_text = outcome["reflection"]

    summary = f"Goal cycle for '{goal}': " + " | ".join(step_texts[:3])

    st["last_plan"] = step_texts
    st["last_reason_summary"] = f"working through a {len(step_texts)}-step plan for the current goal"
    st["last_result"] = result_text
    st["last_reflection"] = reflection_text

    trace = (
        f"goal={goal} | "
        f"reasoning=working through a {len(step_texts)}-step plan | "
        f"result={result_text} | "
        f"reflection={reflection_text}"
    )

    add_entry(
        db,
        text=trace,
        embedding=state["embedder"].embed(trace),
        tags=["reasoning_trace", "goal_cycle", "reflection"]
    )

    maybe_auto_prune_traces(state)
    save_db(DB_PATH, db)
    write_galaxy_html(db, "galaxy.html")
    

    diag_after, _ = score_diagnostics_from_state(state, meta)
    st["last_diag_before"] = diag_before
    st["last_diag_after"] = diag_after
    st["last_diag_delta"] = round(diag_after - diag_before, 1)

    if st["last_diag_delta"] < 0:
        register_reflex_event(
            state,
            kind="diag_drop",
            source="run_goal_cycle",
            detail=f"diagnostics delta dropped to {st['last_diag_delta']}",
            severity=0.6
        )
    elif st["last_diag_delta"] > 0:
        decay_reflex_pressure(state, 0.15)

    mu = int(st.get("mutant_usage", 0) or 0)
    ms = int(st.get("mutant_success", 0) or 0)
    if mu:
        st["mutant_score"] = round(ms / mu, 2)

    maybe_promote_mutant_hint(state)

    if st.get("last_hint_used", False):

        used = str(st.get("last_hint_used_text",""))

        mutant = str(st.get("latest_mutant_hint","")).strip()

        if mutant and mutant in used:
            st["mutant_usage"] = int(st.get("mutant_usage",0) or 0) + 1
            if diag_after >= diag_before:
                st["mutant_success"] = int(st.get("mutant_success",0) or 0) + 1

        gene = get_used_hint_gene(state)
        if gene is not None and diag_after >= diag_before:
            gene["success"] = int(gene.get("success", 0) or 0) + 1

    strategy_name = str(st.get("last_strategy_name", "") or "").strip().lower()
    mutant_strategy_name = str(st.get("latest_mutant_strategy_name", "") or "").strip().lower()

    if strategy_name:
        if mutant_strategy_name and strategy_name == mutant_strategy_name:
            if diag_after >= diag_before:
                st["mutant_strategy_success"] = int(st.get("mutant_strategy_success", 0) or 0) + 1

            mu = int(st.get("mutant_strategy_usage", 0) or 0)
            ms = int(st.get("mutant_strategy_success", 0) or 0)
            st["mutant_strategy_score"] = round((ms / mu), 3) if mu else 0.0
        else:
            genome = st.get("strategy_genome", {}) or {}
            strategy_gene = genome.get(strategy_name)
            if strategy_gene is not None:
                if diag_after >= diag_before:
                    strategy_gene["success"] = int(strategy_gene.get("success", 0) or 0) + 1

                usage = int(strategy_gene.get("usage", 0) or 0)
                success = int(strategy_gene.get("success", 0) or 0)
                strategy_gene["score"] = round((success / usage), 3) if usage else 0.0

    maybe_promote_mutant_strategy(state)

    update_emotional_state(state)
    apply_recovery_mode_behavior(state)
    apply_recovery_cycle(state)
    refresh_working_memory_from_state(state)

    st["last_commit_before_learning_entries"] = before_learning_entries
    st["last_commit_after_learning_entries"] = after_learning_entries
    st["last_commit_added_entries"] = added_entries
    st["last_commit_status"] = "new_learning" if added_entries > 0 else "no_op"
    save_state(state["internal_state"])

    return summary + f" || Result: {result_text}. Reflection: {reflection_text}. Commit: {st.get('last_commit_status', 'unknown')} (+{st.get('last_commit_added_entries', 0)} learning entries)."


def maintenance_worker(state):
    while True:
        try:
            db = state.get("db", [])
            write_galaxy_html(db, "galaxy.html")
            log("MAINT: galaxy rebuild complete.")
        except Exception as e:
            log(f"MAINT ERROR: {e}")
        time.sleep(60)




def score_diagnostics_from_state(state, meta):
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

    # Sensitive signal: richer plans are rewarded slightly
    if isinstance(last_plan, list):
        plan_len = len([x for x in last_plan if str(x).strip()])
        reasoning_clarity += min(plan_len * 5.0, 15.0)
    else:
        plan_len = 0

    learning_loop = 0.0
    learning_loop += min(goal_cycles * 12.0, 36.0)
    if last_result:
        learning_loop += 12.0
    if last_reflection:
        learning_loop += 16.0

    # Sensitive signal: reward meaningful recent learning entries
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

    # Sensitive signal: penalize repeated identical recent learning entries
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


def best_hint_gene_text(state) -> str:
    st = state.get("internal_state", {})
    genome = st.get("hint_genome", {}) or {}
    if not genome:
        return ""

    best = None
    best_score = None

    for gene in genome.values():
        usage = int(gene.get("usage", 0) or 0)
        success = int(gene.get("success", 0) or 0)
        score = (success, usage)
        if best is None or score > best_score:
            best = gene
            best_score = score

    if not best:
        return ""

    text = str(best.get("text", "") or "")[:90]
    usage = int(best.get("usage", 0) or 0)
    success = int(best.get("success", 0) or 0)
    return f"{text} | usage={usage} success={success}"



def mutate_best_hint_gene(state):
    st = state.get("internal_state", {})
    genome = st.get("hint_genome", {}) or {}
    if not genome:
        return ""

    best = None
    best_score = None

    for gene in genome.values():
        usage = int(gene.get("usage", 0) or 0)
        success = int(gene.get("success", 0) or 0)
        score = (success, usage)
        if best is None or score > best_score:
            best = gene
            best_score = score

    if not best:
        return ""

    text = str(best.get("text", "") or "").strip()
    if not text:
        return ""

    mutated = text
    mutated = mutated.replace("explicitly", "deliberately")
    mutated = mutated.replace("logical bridge", "reasoning bridge")
    mutated = mutated.replace("causal link", "cause-and-effect link")
    mutated = mutated.replace("primary objective", "core objective")
    mutated = mutated.replace("sub-step", "micro-step")
    mutated = mutated.replace("sub-task", "micro-task")

    if mutated == text:
        mutated = "State the purpose of each step before selecting the action so the reasoning chain stays visible."

    st["latest_mutant_hint"] = mutated[:240]
    st["mutant_usage"] = 0
    st["mutant_success"] = 0
    st["mutant_score"] = 0
    st["latest_mutant_hint_ts"] = now_ts()
    return mutated[:240]




def gene_score(gene) -> float:
    if not gene:
        return 0.0
    usage = int(gene.get("usage", 0) or 0)
    success = int(gene.get("success", 0) or 0)
    if usage <= 0:
        return float(success)
    return round(success / usage, 3)


def get_best_hint_gene(state):
    st = state.get("internal_state", {})
    genome = st.get("hint_genome", {}) or {}
    if not genome:
        return None

    best = None
    best_tuple = None

    for gene in genome.values():
        usage = int(gene.get("usage", 0) or 0)
        success = int(gene.get("success", 0) or 0)
        tup = (gene_score(gene), success, usage)
        if best is None or tup > best_tuple:
            best = gene
            best_tuple = tup

    return best


def maybe_promote_mutant_hint(state):
    st = state.get("internal_state", {})
    mutant_text = str(st.get("latest_mutant_hint", "") or "").strip()
    if not mutant_text:
        return "no_mutant"

    mu = int(st.get("mutant_usage", 0) or 0)
    ms = int(st.get("mutant_success", 0) or 0)

    if mu <= 0:
        st["last_evolution_decision"] = "hold_mutant_no_usage"
        st["last_evolution_detail"] = "Mutant has no usage yet."
        return "hold"

    mutant_score = round(ms / mu, 3) if mu else 0.0

    best_gene = get_best_hint_gene(state)
    parent_score = gene_score(best_gene)
    parent_text = ""
    if best_gene:
        parent_text = str(best_gene.get("text", "") or "").strip()

    st["last_parent_hint"] = parent_text[:240]
    st["last_parent_score"] = parent_score
    st["last_mutant_score"] = mutant_score

    if mutant_score > parent_score:
        gene = update_hint_genome(state, mutant_text)
        gene["usage"] = max(int(gene.get("usage", 0) or 0), mu)
        gene["success"] = max(int(gene.get("success", 0) or 0), ms)
        st["last_evolution_decision"] = "promoted_mutant"
        st["last_evolution_detail"] = f"Mutant promoted ({mutant_score} > {parent_score})."
        return "promoted"

    st["last_evolution_decision"] = "kept_parent"
    st["last_evolution_detail"] = f"Parent kept ({parent_score} >= {mutant_score})."
    return "kept_parent"



def auto_evolve_hints(state, meta, gemini, rounds: int = 3):
    rounds = max(1, min(int(rounds), 12))
    lines = [f"AUTO EVOLVE START ({rounds} rounds)", ""]

    for i in range(rounds):
        lines.append(f"[round {i+1}] mutating best hint")
        mutant = mutate_best_hint_gene(state)
        if not mutant:
            lines.append("  no mutant available")
            break

        lines.append(f"  mutant: {mutant[:120]}")
        save_state(state["internal_state"])

        lines.append(f"[round {i+1}] running goal cycle")
        result = run_goal_cycle(state, meta, gemini)
        lines.append("  " + result[:220])

        try:
            time.sleep(2.5)
        except Exception:
            pass

        try:
            handle_worker_results(state)
        except Exception as e:
            register_reflex_event(
                state,
                kind="worker_fault",
                source="run_strategy_arena",
                detail=repr(e),
                severity=0.8
            )
            lines.append(f"  worker drain error: {e}")

        decision = maybe_promote_mutant_hint(state)
        save_state(state["internal_state"])

        st = state.get("internal_state", {})
        lines.append(f"  evolution: {decision}")
        lines.append(f"  mutant_usage={st.get('mutant_usage', 0)} mutant_success={st.get('mutant_success', 0)} mutant_score={st.get('mutant_score', 0)}")
        lines.append(f"  detail: {str(st.get('last_evolution_detail', ''))[:160]}")
        lines.append("")

    return "\n".join(lines)


def seed_strategy_genome(state):
    st = state.get("internal_state", {})
    genome = st.setdefault("strategy_genome", {})

    starters = [
        {
            "name": "outcome_first",
            "instruction": "State the desired end state first, then justify each step by how it moves toward that outcome.",
        },
        {
            "name": "constraint_first",
            "instruction": "List constraints and limits first, then build reasoning that respects them.",
        },
        {
            "name": "decompose_then_verify",
            "instruction": "Break the goal into smaller parts, solve each part, then verify the whole chain.",
        },
        {
            "name": "backward_from_goal",
            "instruction": "Start from the final goal and reason backward to determine necessary prior steps.",
        },
        {
            "name": "trace_then_prune",
            "instruction": "Generate a full reasoning trace, then remove redundant or weak steps.",
        },
    ]

    added = 0
    for item in starters:
        key = str(item["name"]).strip().lower()
        if key not in genome:
            genome[key] = {
                "name": item["name"],
                "instruction": item["instruction"],
                "usage": 0,
                "success": 0,
                "score": 0.0,
                "kind": "strategy",
                "parent": "",
            }
            added += 1

    return added


def get_best_strategy_gene(state):
    st = state.get("internal_state", {})
    genome = st.get("strategy_genome", {}) or {}
    if not genome:
        return None

    best = None
    best_tuple = None

    for gene in genome.values():
        usage = int(gene.get("usage", 0) or 0)
        success = int(gene.get("success", 0) or 0)
        score = float(gene.get("score", 0.0) or 0.0)
        tup = (score, success, usage, str(gene.get("name", "")))
        if best is None or tup > best_tuple:
            best = gene
            best_tuple = tup

    return best


def choose_strategy_gene(state):
    st = state.get("internal_state", {})
    seed_strategy_genome(state)

    best = get_best_strategy_gene(state)
    if best is None:
        return None

    st["last_strategy_name"] = str(best.get("name", "") or "")
    st["last_strategy_instruction"] = str(best.get("instruction", "") or "")
    st["strategy_usage_count"] = int(st.get("strategy_usage_count", 0) or 0) + 1

    best["usage"] = int(best.get("usage", 0) or 0) + 1
    return best


def best_strategy_gene_text(state) -> str:
    gene = get_best_strategy_gene(state)
    if not gene:
        return ""

    name = str(gene.get("name", "") or "")
    usage = int(gene.get("usage", 0) or 0)
    success = int(gene.get("success", 0) or 0)
    score = float(gene.get("score", 0.0) or 0.0)
    return f"{name} | usage={usage} success={success} score={score:.2f}"


def mutate_best_strategy_gene(state):
    st = state.get("internal_state", {})
    parent = get_best_strategy_gene(state)
    if not parent:
        return ""

    name = str(parent.get("name", "") or "").strip()
    instruction = str(parent.get("instruction", "") or "").strip()
    if not name or not instruction:
        return ""

    mutant_name = name
    mutant_instruction = instruction

    mutant_name = mutant_name.replace("trace_then_prune", "trace_then_verify")
    mutant_name = mutant_name.replace("backward_from_goal", "backward_verify")
    mutant_name = mutant_name.replace("constraint_first", "constraint_then_verify")
    mutant_name = mutant_name.replace("decompose_then_verify", "decompose_score_verify")
    mutant_name = mutant_name.replace("outcome_first", "outcome_then_verify")

    mutant_instruction = mutant_instruction.replace("remove redundant or weak steps", "verify and score each step, then remove weak ones")
    mutant_instruction = mutant_instruction.replace("build reasoning that respects them", "build reasoning that respects them, then verify each dependency")
    mutant_instruction = mutant_instruction.replace("verify the whole chain", "score the whole chain and verify each link")
    mutant_instruction = mutant_instruction.replace("determine necessary prior steps", "determine necessary prior steps and verify each dependency")
    mutant_instruction = mutant_instruction.replace("moves toward that outcome", "moves toward that outcome and explain why it is necessary")

    if mutant_name == name and mutant_instruction == instruction:
        mutant_name = name + "_variant"
        mutant_instruction = instruction + " Add an explicit verification pass before finalizing the reasoning."

    st["latest_mutant_strategy_name"] = mutant_name[:120]
    st["latest_mutant_strategy_instruction"] = mutant_instruction[:240]
    st["mutant_strategy_usage"] = 0
    st["mutant_strategy_success"] = 0
    st["mutant_strategy_score"] = 0.0
    st["latest_mutant_strategy_parent"] = name[:120]
    return mutant_name


def maybe_promote_mutant_strategy(state):
    st = state.get("internal_state", {})
    mutant_name = str(st.get("latest_mutant_strategy_name", "") or "").strip()
    mutant_instruction = str(st.get("latest_mutant_strategy_instruction", "") or "").strip()

    if not mutant_name or not mutant_instruction:
        st["last_strategy_evolution_decision"] = "no_mutant_strategy"
        st["last_strategy_evolution_detail"] = "No mutant strategy available."
        return "no_mutant"

    mu = int(st.get("mutant_strategy_usage", 0) or 0)
    ms = int(st.get("mutant_strategy_success", 0) or 0)

    if mu <= 0:
        st["last_strategy_evolution_decision"] = "hold_mutant_strategy_no_usage"
        st["last_strategy_evolution_detail"] = "Mutant strategy has no usage yet."
        return "hold"

    mutant_score = round(ms / mu, 3) if mu else 0.0

    parent = get_best_strategy_gene(state)
    parent_score = 0.0
    parent_name = ""
    if parent:
        parent_score = float(parent.get("score", 0.0) or 0.0)
        parent_name = str(parent.get("name", "") or "").strip()

    st["last_strategy_parent_name"] = parent_name[:120]
    st["last_strategy_parent_score"] = parent_score
    st["last_strategy_mutant_score"] = mutant_score

    if mutant_score > parent_score:
        genome = st.setdefault("strategy_genome", {})
        genome[mutant_name.lower()] = {
            "name": mutant_name,
            "instruction": mutant_instruction,
            "usage": mu,
            "success": ms,
            "score": mutant_score,
            "kind": "strategy",
            "parent": parent_name,
        }
        st["last_strategy_evolution_decision"] = "promoted_mutant_strategy"
        st["last_strategy_evolution_detail"] = f"Mutant strategy promoted ({mutant_score} > {parent_score})."
        return "promoted"

    st["last_strategy_evolution_decision"] = "kept_parent_strategy"
    st["last_strategy_evolution_detail"] = f"Parent strategy kept ({parent_score} >= {mutant_score})."
    return "kept_parent"


def list_strategy_genes(state):
    st = state.get("internal_state", {})
    genome = st.get("strategy_genome", {}) or {}
    return list(genome.values())


def choose_strategy_gene_with_exploration(state):
    st = state.get("internal_state", {})
    seed_strategy_genome(state)

    genes = list_strategy_genes(state)
    if not genes:
        return None

    strategy_usage_count = int(st.get("strategy_usage_count", 0) or 0)

    # Every 3rd pick, try exploration instead of pure best-pick
    explore = (strategy_usage_count % 3 == 2)

    chosen = None
    if explore:
        ranked = sorted(
            genes,
            key=lambda g: (
                int(g.get("usage", 0) or 0),
                float(g.get("score", 0.0) or 0.0),
                str(g.get("name", "") or "")
            )
        )
        if ranked:
            chosen = ranked[0]
            st["last_strategy_selection_mode"] = "explore"
    else:
        chosen = get_best_strategy_gene(state)
        st["last_strategy_selection_mode"] = "exploit"

    if not chosen:
        return None

    st["last_strategy_name"] = str(chosen.get("name", "") or "")
    st["last_strategy_instruction"] = str(chosen.get("instruction", "") or "")
    st["strategy_usage_count"] = strategy_usage_count + 1

    chosen["usage"] = int(chosen.get("usage", 0) or 0) + 1
    return chosen


def choose_strategy_source(state):
    st = state.get("internal_state", {})
    seed_strategy_genome(state)

    policy = behavior_policy(state)

    mutant_name = str(st.get("latest_mutant_strategy_name", "") or "").strip()
    mutant_instruction = str(st.get("latest_mutant_strategy_instruction", "") or "").strip()

    # Mutant route
    if (
        mutant_name
        and mutant_instruction
        and policy.get("allow_mutants", False)
        and not policy.get("suppress_mutant_temporarily", False)
        and not policy.get("prefer_exploit", False)
    ):
        ms = float(st.get("mutant_strategy_score", 0.0) or 0.0)
        parent = get_best_strategy_gene(state)
        parent_score = gene_score(parent) if parent else 0.0

        if ms >= max(0.45, parent_score * 0.75):
            st["last_strategy_selection_mode"] = "mutant"
            st["last_strategy_name"] = mutant_name
            st["last_strategy_instruction"] = mutant_instruction
            st["strategy_usage_count"] = int(st.get("strategy_usage_count", 0) or 0) + 1
            st["mutant_strategy_usage"] = int(st.get("mutant_strategy_usage", 0) or 0) + 1
            return {
                "name": mutant_name,
                "instruction": mutant_instruction,
                "source": "mutant",
            }

    # Exploit route
    if policy.get("prefer_exploit", False):
        gene = get_best_strategy_gene(state)
        if gene:
            gene["usage"] = int(gene.get("usage", 0) or 0) + 1
            st["last_strategy_selection_mode"] = "exploit"
            st["last_strategy_name"] = str(gene.get("name", "") or "")
            st["last_strategy_instruction"] = str(gene.get("instruction", "") or "")
            st["strategy_usage_count"] = int(st.get("strategy_usage_count", 0) or 0) + 1
            return {
                "name": str(gene.get("name", "") or "").strip(),
                "instruction": str(gene.get("instruction", "") or "").strip(),
                "source": "exploit",
            }

    # Explore route
    genes = list_strategy_genes(state)
    if genes:
        if policy.get("prefer_explore", False):
            ranked = sorted(
                genes,
                key=lambda g: (
                    int(g.get("usage", 0) or 0),
                    float(g.get("score", 0.0) or 0.0),
                    str(g.get("name", "") or "")
                )
            )
        else:
            ranked = sorted(
                genes,
                key=lambda g: (
                    -float(g.get("score", 0.0) or 0.0),
                    int(g.get("usage", 0) or 0),
                    str(g.get("name", "") or "")
                )
            )

        gene = ranked[0]
        gene["usage"] = int(gene.get("usage", 0) or 0) + 1
        st["last_strategy_selection_mode"] = "explore" if policy.get("prefer_explore", False) else "exploit"
        st["last_strategy_name"] = str(gene.get("name", "") or "")
        st["last_strategy_instruction"] = str(gene.get("instruction", "") or "")
        st["strategy_usage_count"] = int(st.get("strategy_usage_count", 0) or 0) + 1
        return {
            "name": str(gene.get("name", "") or "").strip(),
            "instruction": str(gene.get("instruction", "") or "").strip(),
            "source": st["last_strategy_selection_mode"],
        }

    return {
        "name": "",
        "instruction": "",
        "source": "none",
    }

def choose_strategy_source_forced(state, forced_mode: str):
    st = state.get("internal_state", {})
    seed_strategy_genome(state)

    forced_mode = str(forced_mode or "").strip().lower()

    mutant_name = str(st.get("latest_mutant_strategy_name", "") or "").strip()
    mutant_instruction = str(st.get("latest_mutant_strategy_instruction", "") or "").strip()

    policy = behavior_policy(state)

    if forced_mode == "mutant" and policy.get("suppress_mutant_temporarily", False):
        forced_mode = "exploit"

    if forced_mode == "mutant" and mutant_name and mutant_instruction:
        st["last_strategy_selection_mode"] = "mutant"
        st["last_strategy_name"] = mutant_name
        st["last_strategy_instruction"] = mutant_instruction
        st["strategy_usage_count"] = int(st.get("strategy_usage_count", 0) or 0) + 1
        st["mutant_strategy_usage"] = int(st.get("mutant_strategy_usage", 0) or 0) + 1
        return {
            "name": mutant_name,
            "instruction": mutant_instruction,
            "source": "mutant",
        }

    if forced_mode == "exploit":
        gene = get_best_strategy_gene(state)
        if gene:
            gene["usage"] = int(gene.get("usage", 0) or 0) + 1
            st["last_strategy_selection_mode"] = "exploit"
            st["last_strategy_name"] = str(gene.get("name", "") or "")
            st["last_strategy_instruction"] = str(gene.get("instruction", "") or "")
            st["strategy_usage_count"] = int(st.get("strategy_usage_count", 0) or 0) + 1
            return {
                "name": str(gene.get("name", "") or "").strip(),
                "instruction": str(gene.get("instruction", "") or "").strip(),
                "source": "exploit",
            }

    if forced_mode == "explore":
        genes = list_strategy_genes(state)
        if genes:
            ranked = sorted(
                genes,
                key=lambda g: (
                    int(g.get("usage", 0) or 0),
                    float(g.get("score", 0.0) or 0.0),
                    str(g.get("name", "") or "")
                )
            )
            gene = ranked[0]
            gene["usage"] = int(gene.get("usage", 0) or 0) + 1
            st["last_strategy_selection_mode"] = "explore"
            st["last_strategy_name"] = str(gene.get("name", "") or "")
            st["last_strategy_instruction"] = str(gene.get("instruction", "") or "")
            st["strategy_usage_count"] = int(st.get("strategy_usage_count", 0) or 0) + 1
            return {
                "name": str(gene.get("name", "") or "").strip(),
                "instruction": str(gene.get("instruction", "") or "").strip(),
                "source": "explore",
            }

    return choose_strategy_source(state)
def run_strategy_arena(state, meta, gemini, rounds: int = 6):
    rounds = max(1, min(int(rounds), 20))
    lines = [f"STRATEGY ARENA START ({rounds} rounds)", ""]

    st = state.get("internal_state", {})
    mode_counts = {}
    strategy_counts = {}
    deltas = []

    schedule = ["exploit", "mutant", "explore"]

    for i in range(rounds):
        forced_mode = schedule[i % len(schedule)]
        lines.append(f"[round {i+1}] running goal cycle")
        lines.append(f"  forced_mode={forced_mode}")

        result = run_goal_cycle_forced_strategy(state, meta, gemini, forced_mode)
        lines.append("  " + result[:220])

        try:
            time.sleep(2.0)
        except Exception:
            pass

        try:
            handle_worker_results(state)
        except Exception as e:
            lines.append(f"  worker drain error: {e}")

        mode = str(st.get("last_strategy_selection_mode", "") or "").strip() or "unknown"
        name = str(st.get("last_strategy_name", "") or "").strip() or "unknown"
        delta = float(st.get("last_diag_delta", 0.0) or 0.0)

        mode_counts[mode] = mode_counts.get(mode, 0) + 1
        strategy_counts[name] = strategy_counts.get(name, 0) + 1
        deltas.append(delta)

        lines.append(f"  strategy={name}")
        lines.append(f"  mode={mode}")
        lines.append(f"  diag_delta={delta}")
        lines.append("")

    avg_delta = round(sum(deltas) / len(deltas), 3) if deltas else 0.0

    lines.append("ARENA SUMMARY")
    lines.append("")
    lines.append("Mode Counts:")
    for k in sorted(mode_counts):
        lines.append(f"  {k}: {mode_counts[k]}")

    lines.append("")
    lines.append("Strategy Counts:")
    for k in sorted(strategy_counts):
        lines.append(f"  {k}: {strategy_counts[k]}")

    lines.append("")
    lines.append(f"Average Diagnostics Delta: {avg_delta}")
    lines.append(f"Last Strategy Evolution Decision: {str(st.get('last_strategy_evolution_decision', ''))}")
    lines.append(f"Last Evolution Detail: {str(st.get('last_strategy_evolution_detail', ''))[:160]}")

    st["last_arena_rounds"] = rounds
    st["last_arena_avg_delta"] = avg_delta
    st["last_arena_mode_counts"] = mode_counts
    st["last_arena_strategy_counts"] = strategy_counts
    save_state(state["internal_state"])

    return "\n".join(lines)

def arena_status_text(state) -> str:
    st = state.get("internal_state", {})
    lines = [
        "ARENA STATUS",
        "",
        f"Last Arena Rounds: {st.get('last_arena_rounds', 0)}",
        f"Last Arena Avg Delta: {st.get('last_arena_avg_delta', 0.0)}",
        f"Last Arena Mode Counts: {st.get('last_arena_mode_counts', {})}",
        f"Last Arena Strategy Counts: {st.get('last_arena_strategy_counts', {})}",
    ]
    return "\n".join(lines)


def register_reflex_event(state, kind: str, source: str, detail: str, severity: float = 0.5):
    st = state.get("internal_state", {})
    events = st.setdefault("reflex_events", [])

    evt = {
        "ts": now_ts(),
        "kind": str(kind or "").strip(),
        "source": str(source or "").strip(),
        "detail": str(detail or "").strip()[:240],
        "severity": round(float(severity or 0.0), 3),
    }

    events.append(evt)
    if len(events) > 100:
        del events[:-100]

    st["last_reflex_kind"] = evt["kind"]
    st["last_reflex_source"] = evt["source"]
    st["last_reflex_detail"] = evt["detail"]
    st["last_reflex_severity"] = evt["severity"]

    st["reflex_total_count"] = int(st.get("reflex_total_count", 0) or 0) + 1
    st["reflex_fault_pressure"] = round(float(st.get("reflex_fault_pressure", 0.0) or 0.0) + evt["severity"], 3)

    counts = st.setdefault("reflex_counts", {})
    counts[evt["kind"]] = int(counts.get(evt["kind"], 0) or 0) + 1

    return evt


def decay_reflex_pressure(state, amount: float = 0.1):
    st = state.get("internal_state", {})
    cur = float(st.get("reflex_fault_pressure", 0.0) or 0.0)
    cur = max(0.0, cur - float(amount))
    st["reflex_fault_pressure"] = round(cur, 3)
    return cur




def nerve_reset(state, target_pressure: float = 0.8):
    st = state.get("internal_state", {})

    old_pressure = float(st.get("reflex_fault_pressure", 0.0) or 0.0)
    st["reflex_fault_pressure"] = round(max(0.0, float(target_pressure)), 3)

    st["last_reflex_kind"] = ""
    st["last_reflex_source"] = ""
    st["last_reflex_detail"] = ""
    st["last_reflex_severity"] = 0.0

    update_emotional_state(state)
    apply_recovery_cycle(state)
    refresh_working_memory_from_state(state)

    return {
        "old_pressure": round(old_pressure, 3),
        "new_pressure": st["reflex_fault_pressure"],
        "recovery_mode": bool(st.get("recovery_mode", False)),
    }


def nerve_reset_text(state, target_pressure: float = 0.8) -> str:
    info = nerve_reset(state, target_pressure=target_pressure)
    return (
        "NERVE RESET\n\n"
        f"Old Pressure: {info['old_pressure']}\n"
        f"New Pressure: {info['new_pressure']}\n"
        f"Recovery Mode: {info['recovery_mode']}"
    )
def reflex_status_text(state) -> str:
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


def reflex_history_text(state, limit: int = 12) -> str:
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


def clamp01(x):
    x = float(x)
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return round(x, 3)


def ensure_emotional_state(state):
    st = state.get("internal_state", {})
    emo = st.setdefault("emotional_state", {})
    emo.setdefault("confidence", 0.5)
    emo.setdefault("frustration", 0.0)
    emo.setdefault("curiosity", 0.5)
    emo.setdefault("stability", 0.5)
    return emo


def update_emotional_state(state):
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

    st["last_emotion_update_ts"] = now_ts()
    return emo


def emotional_state_text(state) -> str:
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


def behavior_policy(state):
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

def behavior_policy_text(state) -> str:
    policy = behavior_policy(state)
    lines = ["BEHAVIOR POLICY", ""]
    for k in sorted(policy):
        lines.append(f"{k}: {policy[k]}")
    return "\n".join(lines)




def apply_recovery_mode_behavior(state):
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

    st["reflex_fault_pressure"] = round(max(0, pressure),3)

def apply_recovery_cycle(state):
    st = state.get("internal_state", {})
    emo = ensure_emotional_state(state)
    policy = behavior_policy(state)

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






def legacy_svg_wrap(content: str, width: int = 512, height: int = 512, bg: str = "black") -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<rect width="100%" height="100%" fill="{bg}"/>
{content}
</svg>
"""


def legacy_svg_spiral(width: int = 512, height: int = 512) -> str:
    cx = width // 2
    cy = height // 2
    pts = []
    import math
    for i in range(220):
        t = i * 0.22
        r = 6 + i * 0.9
        x = cx + math.cos(t) * r
        y = cy + math.sin(t) * r
        pts.append(f"{x:.2f},{y:.2f}")
    poly = " ".join(pts)
    return svg_wrap(f'<polyline points="{poly}" fill="none" stroke="cyan" stroke-width="2"/>', width, height)


def legacy_svg_grid(width: int = 512, height: int = 512, step: int = 32) -> str:
    lines = []
    for x in range(0, width + 1, step):
        lines.append(f'<line x1="{x}" y1="0" x2="{x}" y2="{height}" stroke="#224" stroke-width="1"/>')
    for y in range(0, height + 1, step):
        lines.append(f'<line x1="0" y1="{y}" x2="{width}" y2="{y}" stroke="#224" stroke-width="1"/>')
    lines.append(f'<rect x="32" y="32" width="{width-64}" height="{height-64}" fill="none" stroke="gold" stroke-width="2"/>')
    return svg_wrap("\n".join(lines), width, height)


def legacy_svg_orbit(width: int = 512, height: int = 512) -> str:
    cx = width // 2
    cy = height // 2
    parts = [
        f'<circle cx="{cx}" cy="{cy}" r="16" fill="gold"/>',
        f'<circle cx="{cx}" cy="{cy}" r="64" fill="none" stroke="#3af" stroke-width="2"/>',
        f'<circle cx="{cx}" cy="{cy}" r="128" fill="none" stroke="#6cf" stroke-width="2"/>',
        f'<circle cx="{cx}" cy="{cy}" r="192" fill="none" stroke="#9ff" stroke-width="2"/>',
        f'<circle cx="{cx+64}" cy="{cy}" r="8" fill="white"/>',
        f'<circle cx="{cx-128}" cy="{cy}" r="10" fill="#8ff"/>',
        f'<circle cx="{cx}" cy="{cy-192}" r="12" fill="#f8f"/>',
    ]
    return svg_wrap("\n".join(parts), width, height)


def legacy_svg_art_text(state, mode: str = "spiral") -> str:
    mode = str(mode or "spiral").strip().lower()
    if mode == "grid":
        return svg_grid()
    if mode == "orbit":
        return svg_orbit()
    return svg_spiral()


def legacy_write_svg_art(state, mode: str = "spiral", path: str = "andy_art.svg") -> str:
    svg = svg_art_text(state, mode=mode)
    from pathlib import Path as _Path
    _Path(path).write_text(svg, encoding="utf-8")

    html_path = "andy_art.html"
    write_art_html_viewer(svg_path=path, html_path=html_path)

    st = state.get("internal_state", {})
    st["last_art_mode"] = mode
    st["last_art_path"] = path
    st["last_art_html_path"] = html_path
    st["last_art_ts"] = now_ts()

    store_art_artifact_memory(state, mode=mode, svg_path=path, html_path=html_path)

    return path




def legacy_write_art_html_viewer(svg_path: str = "andy_art.svg", html_path: str = "andy_art.html") -> str:
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ANDY AI Art Viewer</title>
<style>
body {{
    margin: 0;
    background: #0b1020;
    color: #e5f0ff;
    font-family: Arial, sans-serif;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: flex-start;
    min-height: 100vh;
}}
.wrap {{
    width: 100%;
    max-width: 900px;
    padding: 20px;
    box-sizing: border-box;
}}
.card {{
    background: #111933;
    border: 1px solid #243055;
    border-radius: 16px;
    padding: 16px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.25);
}}
h1 {{
    font-size: 22px;
    margin: 0 0 12px 0;
}}
p {{
    opacity: 0.9;
}}
.viewer {{
    background: #000;
    border-radius: 12px;
    overflow: hidden;
    margin-top: 12px;
}}
.viewer img {{
    display: block;
    width: 100%;
    height: auto;
    background: #000;
}}
.path {{
    margin-top: 10px;
    font-size: 13px;
    opacity: 0.8;
    word-break: break-all;
}}
</style>
</head>
<body>
<div class="wrap">
  <div class="card">
    <h1>ANDY AI Art Viewer</h1>
    <p>Structured SVG output generated by AndyAI.</p>
    <div class="viewer">
      <img src="{svg_path}" alt="ANDY AI SVG Art">
    </div>
    <div class="path">SVG: {svg_path}</div>
  </div>
</div>
</body>
</html>
"""
    from pathlib import Path as _Path
    _Path(html_path).write_text(html, encoding="utf-8")
    return html_path


def legacy_art_artifact_summary(state, mode: str, svg_path: str, html_path: str = "") -> str:
    st = state.get("internal_state", {})
    emo = ensure_emotional_state(state)

    return (
        f"type=art_artifact | mode={mode} | svg={svg_path} | html={html_path} | "
        f"goal={str(st.get('current_goal', '') or '')[:80]} | "
        f"recovery_mode={st.get('recovery_mode_type', 'standard')} | "
        f"pressure={st.get('reflex_fault_pressure', 0.0)} | "
        f"emotion[c={emo.get('confidence', 0.0)},f={emo.get('frustration', 0.0)},"
        f"q={emo.get('curiosity', 0.0)},s={emo.get('stability', 0.0)}]"
    )


def legacy_store_art_artifact_memory(state, mode: str, svg_path: str, html_path: str = ""):
    db = state.get("db", [])
    embedder = state.get("embedder")

    text = art_artifact_summary(state, mode, svg_path, html_path)

    try:
        emb = embedder.embed(text) if embedder else None
    except Exception:
        emb = None

    add_entry(
        db,
        text=text,
        embedding=emb,
        tags=["art", "art_artifact", "skill:visual", "lane:art_memory", "protected"]
    )
    save_db(DB_PATH, db)
def legacy_art_status_text(state) -> str:
    st = state.get("internal_state", {})
    return "\n".join([
        "ART STATUS",
        "",
        f"Last Art Mode: {st.get('last_art_mode', '')}",
        f"Last Art Path: {st.get('last_art_path', '')}",
        f"Last Art HTML Path: {st.get('last_art_html_path', '')}",
        f"Last Art TS: {st.get('last_art_ts', '')}",
    ])
def set_recovery_mode(state, mode: str):
    st = state.get("internal_state", {})
    mode = str(mode or "standard").strip().lower()

    if mode not in {"standard", "reflect", "art"}:
        mode = "standard"

    st["recovery_mode_type"] = mode
    st["recovery_mode"] = True
    st["last_recovery_ts"] = now_ts()

    return mode


def recovery_mode_text(state):
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

def recovery_status_text(state) -> str:
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


def ensure_working_memory(state):
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


def wm_push_list(wm, key: str, value: str, limit: int = 6):
    arr = list(wm.get(key, []) or [])
    value = str(value or "").strip()
    if not value:
        return
    arr.append(value[:240])
    if len(arr) > limit:
        arr = arr[-limit:]
    wm[key] = arr


def refresh_working_memory_from_state(state):
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


def working_memory_text(state) -> str:
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
def brain_status_text(state: Dict[str, Any], meta: Dict[str, Any]) -> str:
    st = state.get("internal_state", {})
    db = state.get("db", [])

    trace_count = 0
    reflection_count = 0
    goal_cycle_count = 0
    background_hint_count = 0

    for entry in db:
        tags = entry.get("tags", []) or []
        if "reasoning_trace" in tags:
            trace_count += 1
        if "reflection" in tags:
            reflection_count += 1
        if "goal_cycle" in tags:
            goal_cycle_count += 1
        if "background_hint" in tags:
            background_hint_count += 1

    champion_score = "unknown"
    try:
        import json
        with open("brain_scores.json", "r", encoding="utf-8") as f:
            scores = json.load(f)
        champion_score = scores.get("champion_score", "unknown")
    except Exception:
        pass

    score_total, subscores = score_diagnostics_from_state(state, meta)

    lines = [
        "ANDY AI Internal State",
        "",
        f"Generation: {meta.get('generation')}",
        f"Current Goal: {st.get('current_goal', meta.get('last_goal', ''))}",
        f"Champion Brain Score: {champion_score}",
        f"Live Diagnostic Score: {score_total}",
        "",
        f"Memory Entries: {len(db)}",
        f"Reasoning Traces: {trace_count}",
        f"Reflections Stored: {reflection_count}",
        f"Goal Cycles Stored: {goal_cycle_count}",
        f"Background Hints Stored: {background_hint_count}",
        f"Hint Usage Count: {st.get('hint_usage_count', 0)}",
        f"Hint Genome Size: {len(st.get('hint_genome', {}))}",
        f"Last Diagnostics Delta: {st.get('last_diag_delta', 0.0)}",
        f"Reflex Fault Pressure: {st.get('reflex_fault_pressure', 0.0)}",
        f"Last Reflex Kind: {st.get('last_reflex_kind', '')}",
        f"Emotion Confidence: {ensure_emotional_state(state).get('confidence', 0.0)}",
        f"Emotion Frustration: {ensure_emotional_state(state).get('frustration', 0.0)}",
        f"Emotion Curiosity: {ensure_emotional_state(state).get('curiosity', 0.0)}",
        f"Emotion Stability: {ensure_emotional_state(state).get('stability', 0.0)}",
        f"Behavior Policy: {behavior_policy(state)}",
        f"Recovery Mode: {state.get('internal_state', {}).get('recovery_mode', False)}",
        "",
        f"Last Reasoning: {str(st.get('last_reason_summary', ''))[:120]}",
        f"Last Result: {str(st.get('last_result', ''))[:120]}",
        f"Last Reflection: {str(st.get('last_reflection', ''))[:120]}",
        f"Last Background Hint: {str(st.get('last_background_hint', ''))[:120]}",
        f"Best Hint Gene: {best_hint_gene_text(state)}",
        f"Best Strategy Gene: {best_strategy_gene_text(state)}",
        f"Last Strategy Name: {str(st.get('last_strategy_name', ''))[:120]}",
        f"Last Strategy Instruction: {str(st.get('last_strategy_instruction', ''))[:120]}",
        f"Last Strategy Selection Mode: {str(st.get('last_strategy_selection_mode', ''))[:120]}",
        f"Strategy Usage Count: {st.get('strategy_usage_count', 0)}",
        f"Strategy Genome Size: {len(st.get('strategy_genome', {}))}",
        f"Latest Mutant Strategy: {str(st.get('latest_mutant_strategy_name', ''))[:120]}",
        f"Latest Mutant Strategy Instruction: {str(st.get('latest_mutant_strategy_instruction', ''))[:120]}",
        f"Mutant Strategy Usage: {st.get('mutant_strategy_usage', 0)}",
        f"Mutant Strategy Success: {st.get('mutant_strategy_success', 0)}",
        f"Mutant Strategy Score: {st.get('mutant_strategy_score', 0)}",
        f"Last Strategy Parent Score: {st.get('last_strategy_parent_score', 0)}",
        f"Last Strategy Mutant Score: {st.get('last_strategy_mutant_score', 0)}",
        f"Last Strategy Evolution Decision: {st.get('last_strategy_evolution_decision', '')}",
        f"Last Strategy Evolution Detail: {str(st.get('last_strategy_evolution_detail', ''))[:120]}",
        f"Last Arena Rounds: {st.get('last_arena_rounds', 0)}",
        f"Last Arena Avg Delta: {st.get('last_arena_avg_delta', 0.0)}",
        f"Latest Mutant Hint: {str(st.get('latest_mutant_hint', ''))[:120]}",
        f"Mutant Usage: {st.get('mutant_usage', 0)}",
        f"Mutant Success: {st.get('mutant_success', 0)}",
        f"Mutant Score: {st.get('mutant_score', 0)}",
        f"Last Parent Score: {st.get('last_parent_score', 0)}",
        f"Last Mutant Score: {st.get('last_mutant_score', 0)}",
        f"Last Evolution Decision: {st.get('last_evolution_decision', '')}",
        f"Last Evolution Detail: {str(st.get('last_evolution_detail', ''))[:120]}",
        f"Auto Evolution Ready: True",
        f"Hint Used In Goal Cycle: {st.get('last_hint_used', False)}",
        f"Last Hint Used Text: {str(st.get('last_hint_used_text', ''))[:120]}",
        f"Last Commit Status: {st.get('last_commit_status', 'unknown')}",
        f"Last Commit Added Entries: {st.get('last_commit_added_entries', 0)}",
        f"Learning Entries Before/After: {st.get('last_commit_before_learning_entries', '?')} -> {st.get('last_commit_after_learning_entries', '?')}",
        "",
        f"Gemini: {'ON' if meta.get('gemini_enabled', True) else 'OFF'}",
        "",
        "Score Breakdown:",
        f"  core_behavior: {subscores['core_behavior']}",
        f"  reasoning_clarity: {subscores['reasoning_clarity']}",
        f"  learning_loop: {subscores['learning_loop']}",
        f"  memory_quality: {subscores['memory_quality']}",
        f"  diagnostics: {subscores['diagnostics']}",
    ]

    return "\n".join(lines)





def memory_result_bonus(entry, query: str) -> float:
    q = str(query or "").strip().lower()
    text = str(entry.get("text", "") or "")
    low = text.lower()
    tags = entry.get("tags", []) or []

    bonus = 0.0

    if "fact" in tags:
        bonus += 0.35
    if "user_fact" in tags:
        bonus += 0.25
    if "protected" in tags:
        bonus += 0.20

    terms = [t for t in q.split() if t.strip()]
    exact_hits = 0
    for term in terms:
        if term in low:
            exact_hits += 1

    bonus += min(exact_hits * 0.12, 0.36)

    if q and q in low:
        bonus += 0.20

    return round(bonus, 3)


def sort_memory_hits(hits, query: str):
    rescored = []
    for score, entry in hits:
        try:
            base = float(score)
        except Exception:
            base = 0.0
        bonus = memory_result_bonus(entry, query)
        rescored.append((round(base + bonus, 3), entry))
    rescored.sort(key=lambda x: x[0], reverse=True)
    return rescored
def brain_history_text(limit: int = 12) -> str:
    try:
        import json
        from pathlib import Path as _Path

        path = _Path("brain_scores.json")
        if not path.exists():
            return "No brain history file found."

        data = json.loads(path.read_text(encoding="utf-8"))
        history = data.get("history", [])

        if not history:
            return "No brain history recorded yet."

        lines = ["ANDY AI Brain History", ""]
        recent = history[-limit:]

        for i, item in enumerate(recent, start=max(1, len(history) - len(recent) + 1)):
            ts = item.get("ts", "")
            score = item.get("score", "unknown")
            summary = str(item.get("summary", ""))
            passed = item.get("passed", False)
            candidate = str(item.get("candidate", ""))

            label = "PASS" if passed else "FAIL"
            short_candidate = candidate.split("/")[-1] if candidate else "unknown"

            lines.append(
                f"{i}. [{label}] score={score} | summary={summary} | file={short_candidate} | ts={ts}"
            )

        champion_score = data.get("champion_score", "unknown")
        champion_file = str(data.get("champion_file", "unknown")).split("/")[-1]

        lines.extend([
            "",
            f"Current Champion Score: {champion_score}",
            f"Current Champion File: {champion_file}",
        ])

        return "\n".join(lines)

    except Exception as e:
        return f"Failed to load brain history: {e}"






def classify_learning_novelty(new_text, recent_entries):
    """
    Classify a learning entry as duplicate, near_duplicate, or novel.
    """

    new_text = str(new_text or "").lower().strip()

    if not new_text:
        return "duplicate"

    for old in recent_entries:
        old = str(old or "").lower().strip()

        if new_text == old:
            return "duplicate"

        if new_text in old or old in new_text:
            return "near_duplicate"

        overlap = len(set(new_text.split()) & set(old.split()))
        if overlap >= 6:
            return "near_duplicate"

    return "novel"
def count_learning_entries(db):
    count = 0
    for entry in db:
        tags = entry.get("tags", []) or []
        text = str(entry.get("text", "") or "")
        if "goal_cycle" in tags or ("reasoning_trace" in tags and "result=" in text):
            count += 1
    return count
def learning_history_text(state: Dict[str, Any], limit: int = 12) -> str:
    db = state.get("db", [])
    items = []

    for entry in db:
        tags = entry.get("tags", []) or []
        text = str(entry.get("text", "") or "")

        if "goal_cycle" in tags or ("reasoning_trace" in tags and "result=" in text):
            items.append(entry)

    if not items:
        return "No learning history recorded yet."

    recent = items[-limit:]
    lines = ["ANDY AI Learning History", ""]

    start_index = max(1, len(items) - len(recent) + 1)
    for i, entry in enumerate(recent, start=start_index):
        text = str(entry.get("text", "") or "")
        short = summarize_trace_text(text) if "goal=" in text else text[:150]
        lines.append(f"{i}. {short}")

    lines.extend([
        "",
        f"Total Learning Entries: {len(items)}",
    ])

    return "\n".join(lines)



def strategy_genome_text(state) -> str:
    genes = list_strategy_genes(state)
    if not genes:
        return "No strategy genes recorded yet."

    genes = sorted(
        genes,
        key=lambda g: (
            float(g.get("score", 0.0) or 0.0),
            int(g.get("success", 0) or 0),
            int(g.get("usage", 0) or 0),
            str(g.get("name", "") or "")
        ),
        reverse=True
    )

    lines = ["STRATEGY GENOME", ""]
    for i, gene in enumerate(genes[:20], start=1):
        lines.append(
            f"{i}. {str(gene.get('name', ''))} | usage={int(gene.get('usage', 0) or 0)} "
            f"success={int(gene.get('success', 0) or 0)} "
            f"score={float(gene.get('score', 0.0) or 0.0):.2f}"
        )

    lines.extend([
        "",
        f"Total Strategies: {len(genes)}"
    ])
    return "\n".join(lines)




def strategy_selection_text(state) -> str:
    st = state.get("internal_state", {})
    lines = [
        "STRATEGY SELECTION",
        "",
        f"Last Strategy Name: {str(st.get('last_strategy_name', ''))}",
        f"Last Strategy Mode: {str(st.get('last_strategy_selection_mode', ''))}",
        f"Latest Mutant Strategy: {str(st.get('latest_mutant_strategy_name', ''))}",
        f"Mutant Strategy Usage: {st.get('mutant_strategy_usage', 0)}",
        f"Mutant Strategy Success: {st.get('mutant_strategy_success', 0)}",
        f"Mutant Strategy Score: {st.get('mutant_strategy_score', 0)}",
    ]
    return "\n".join(lines)


def main():

    gemini = GeminiClient()
    meta = load_meta()
    db = load_db(DB_PATH)
    internal_state = load_state()


    if not internal_state.get("current_goal") and meta.get("last_goal"):
        internal_state["current_goal"] = meta.get("last_goal", "")

    state: Dict[str, Any] = {
        "gemini": gemini,
        "embedder": Embedder(gemini=gemini),
        "db": db,
        "internal_state": internal_state,
        "identity_text": identity_text(),
    }

    # --- Separated Worker Queues ---
    state["reason_queue"] = TaskQueue()
    state["diag_queue"] = TaskQueue()
    state["gemini_queue"] = TaskQueue()
    state["worker_results"] = []

    reason_thread = Worker("reason", state["reason_queue"], reasoning_worker)
    diag_thread = Worker("diagnostics", state["diag_queue"], diagnostics_worker)
    gemini_thread = Worker("gemini", state["gemini_queue"], gemini_worker)

    reason_thread.start()
    diag_thread.start()
    gemini_thread.start()

    log("[WORKER init] reason worker started")
    log("[WORKER init] diagnostics worker started")
    log("[WORKER init] gemini worker started")

    seed_strategy_genome(state)

    if refresh_goal_if_needed(state, meta):
        save_meta(meta)
        save_state(state["internal_state"])
    state["registry"] = build_registry(state)

    seeded_score, seeded_msg = seed_current_brain(BRAIN_FILE, rules_text=rules_as_text())
    internal_state["champion_score"] = seeded_score
    if not internal_state.get("brain_version") or internal_state.get("brain_version") == "unknown":
        internal_state["brain_version"] = f"seeded_{seeded_score:.1f}"
    save_state(internal_state)

    log(f"{APP} online.")
    log(seeded_msg)
    log("Type: help")

    while True:
        try:
            handle_worker_results(state)
            cmd = input("\nandyai> ").strip()
            if not cmd:
                continue

            low = cmd.lower()

            if low in ("exit", "quit"):
                break

            if low in ("help", "?"):
                print(
                    "\nCommands:\n"
                    "  help\n"
                    "  status\n"
                    "  why\n"
                    "  who are you\n"
                    "  identity\n"
                    "  reflect identity\n"
                    "  run [N]\n"
                    "  step\n"
                    "  chat <msg>\n"
                    "  mem <q>\n"
                    "  rules\n"
                    "  rule: <text>\n"
                    "  mutate list\n"
                    "  mutate <topic>\n"
                    "  autotrain [N]\n"
                    "  brain <text>\n"
                    "  exit\n"
                )
                continue

            if low == "status":
                print(status_line(state, meta, gemini))
                continue

            if low == "why":
                print(local_reasoning_summary("", state, meta))
                continue

            if low == "who are you" or low == "identity":
                ident = load_identity()
                reflection = ident.get("self_reflection", "")
                print(ident.get("self_description", "I am ANDY AI."))
                if reflection:
                    print("Reflection:", reflection)
                continue

            if low == "reflect identity":
                ok, msg = reflect_identity(gemini)
                if ok:
                    print(msg)
                else:
                    print("identity reflection failed:", msg)
                continue

            if low == "rules":
                print(rules_as_text())
                continue

            if low == "prune traces":
                before = len(db)
                new_db, removed = consolidate_reasoning_traces(db, keep_per_key=2)
                state["db"] = new_db
                db.clear()
                db.extend(new_db)
                save_db(DB_PATH, db)
                write_galaxy_html(db, "galaxy.html")
                print(f"Pruned reasoning traces. Removed {removed} duplicate entries. Memory now has {len(db)} entries (was {before}).")
                continue

            if low == "seed goal trace":
                seeded = seed_trace_for_current_goal(state)
                if seeded:
                    save_db(DB_PATH, db)
                    write_galaxy_html(db, "galaxy.html")
                    print("Seeded a reasoning trace for the current goal.")
                else:
                    print("A reasoning trace for the current goal already exists.")
                continue

            if low == "goal cycle":
                result = run_goal_cycle(state, meta, gemini)
                print(result)
                continue

            if low == "idle debug":
                meta = load_json("meta.json", {})
                gemini = state.get("gemini_client")
                print(idle_debug_text(state, meta, gemini))
                continue

            if low == "brain status":
                print(brain_status_text(state, meta))
                continue

            if low == "brain history":
                print(brain_history_text())
                continue

            if low == "learning history":
                print(learning_history_text(state))
                continue

            if low == "strategies":
                print(strategy_genome_text(state))
                continue

            if low == "selection":
                print(strategy_selection_text(state))
                continue

            if low == "arena status":
                print(arena_status_text(state))
                continue

            if low.startswith("nerve reset"):
                parts = cmd.split()
                target = 0.8
                if len(parts) >= 3:
                    try:
                        target = float(parts[2])
                    except Exception:
                        target = 0.8
                print(nerve_reset_text(state, target_pressure=target))
                save_state(state["internal_state"])
                continue

            if low == "emotion":
                print(emotional_state_text(state))
                continue

            
            if low.startswith("recovery mode"):
                parts = cmd.split()
                mode = "standard"
                if len(parts) >= 3:
                    mode = parts[2]
                m = set_recovery_mode(state, mode)
                print(recovery_mode_text(state))
                continue

            handled = handle_regulation_command(
                cmd,
                low,
                state,
                set_recovery_mode,
                recovery_mode_text,
                recovery_status_text,
                emotional_state_text,
                behavior_policy_text,
                reflex_status_text,
                reflex_history_text,
                nerve_reset,
            )
            if handled:
                continue

            handled = handle_memory_command(
                cmd,
                low,
                state,
                db,
                top_k,
                rerank_memory_hits,
            )
            if handled:
                continue

            
            handled = handle_language_command(cmd, state)

            if handled:
                continue

            handled = handle_art_command(
                cmd,
                low,
                state,
                db,
                save_state,
                top_k,
                rerank_memory_hits,
            )
            if handled:
                continue

            if low == "archive":
                path = archive_project(state)
                print("ARCHIVE CREATED\n")
                print(path)
                continue

            chat_once(state, meta, gemini, cmd)

        except KeyboardInterrupt:
            break
        except Exception as e:
            try:
                register_reflex_event(
                    state,
                    kind="main_fault",
                    source="main_loop",
                    detail=repr(e),
                    severity=0.9
                )
            except Exception:
                pass

            log("ERROR: " + str(e))
            log(traceback.format_exc())

    save_db(DB_PATH, db)
    save_meta(meta)
    save_state(internal_state)
    log("bye.")


if __name__ == "__main__":
    main()
