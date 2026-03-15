from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable, Dict


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


def brain_status_text(
    state: Dict[str, Any],
    meta: Dict[str, Any],
    *,
    ensure_emotional_state: Callable[[Dict[str, Any]], Dict[str, Any]],
    behavior_policy: Callable[[Dict[str, Any]], Dict[str, Any]],
    best_hint_gene_text: Callable[[Dict[str, Any]], str],
    best_strategy_gene_text: Callable[[Dict[str, Any]], str],
    score_diagnostics_from_state: Callable[[Dict[str, Any], Dict[str, Any]], Any],
) -> str:
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
        with open("brain_scores.json", "r", encoding="utf-8") as f:
            scores = json.load(f)
        champion_score = scores.get("champion_score", "unknown")
    except Exception:
        pass

    score_total, subscores = score_diagnostics_from_state(state, meta)
    emo = ensure_emotional_state(state)

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
        f"Emotion Confidence: {emo.get('confidence', 0.0)}",
        f"Emotion Frustration: {emo.get('frustration', 0.0)}",
        f"Emotion Curiosity: {emo.get('curiosity', 0.0)}",
        f"Emotion Stability: {emo.get('stability', 0.0)}",
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


def brain_history_text(limit: int = 12) -> str:
    try:
        path = Path("brain_scores.json")
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


def learning_history_text(
    state: Dict[str, Any],
    *,
    summarize_trace_text: Callable[[str], str],
    limit: int = 12,
) -> str:
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

    lines.extend(["", f"Total Learning Entries: {len(items)}"])
    return "\n".join(lines)


def strategy_genome_text(
    state,
    *,
    list_strategy_genes: Callable[[Dict[str, Any]], Any],
) -> str:
    genes = list_strategy_genes(state)
    if not genes:
        return "No strategy genes recorded yet."

    genes = sorted(
        genes,
        key=lambda g: (
            float(g.get("score", 0.0) or 0.0),
            int(g.get("success", 0) or 0),
            int(g.get("usage", 0) or 0),
            str(g.get("name", "") or ""),
        ),
        reverse=True,
    )

    lines = ["STRATEGY GENOME", ""]
    for i, gene in enumerate(genes[:20], start=1):
        lines.append(
            f"{i}. {str(gene.get('name', ''))} | usage={int(gene.get('usage', 0) or 0)} "
            f"success={int(gene.get('success', 0) or 0)} "
            f"score={float(gene.get('score', 0.0) or 0.0):.2f}"
        )

    lines.extend(["", f"Total Strategies: {len(genes)}"])
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
