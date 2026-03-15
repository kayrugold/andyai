from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict


@dataclass
class RuntimeContext:
    state: Dict[str, Any]
    meta: Dict[str, Any]
    gemini: Any
    internal_state: Dict[str, Any]
    db: list
    log: Callable[[str], None]
    traceback: Any
    save_db: Callable[..., Any]
    save_meta: Callable[..., Any]
    save_state: Callable[..., Any]
    db_path: str
    handle_worker_results: Callable[..., Any]
    status_line: Callable[..., Any]
    local_reasoning_summary: Callable[..., Any]
    conscious_identity_text: Callable[..., Any]
    load_identity: Callable[..., Any]
    reflect_identity: Callable[..., Any]
    rules_as_text: Callable[..., Any]
    consolidate_reasoning_traces: Callable[..., Any]
    write_galaxy_html: Callable[..., Any]
    seed_trace_for_current_goal: Callable[..., Any]
    run_goal_cycle: Callable[..., Any]
    load_json: Callable[..., Any]
    idle_debug_text: Callable[..., Any]
    brain_status_text: Callable[..., Any]
    brain_history_text: Callable[..., Any]
    learning_history_text: Callable[..., Any]
    strategy_genome_text: Callable[..., Any]
    strategy_selection_text: Callable[..., Any]
    arena_status_text: Callable[..., Any]
    run_strategy_arena: Callable[..., Any]
    auto_evolve_hints: Callable[..., Any]
    nerve_reset_text: Callable[..., Any]
    emotional_state_text: Callable[..., Any]
    set_recovery_mode: Callable[..., Any]
    recovery_mode_text: Callable[..., Any]
    handle_regulation_command: Callable[..., Any]
    recovery_status_text: Callable[..., Any]
    behavior_policy_text: Callable[..., Any]
    reflex_status_text: Callable[..., Any]
    reflex_history_text: Callable[..., Any]
    nerve_reset: Callable[..., Any]
    run_drive_tick: Callable[..., Any]
    handle_memory_command: Callable[..., Any]
    handle_language_command: Callable[..., Any]
    handle_art_command: Callable[..., Any]
    archive_project: Callable[..., Any]
    chat_once: Callable[..., Any]
    register_reflex_event: Callable[..., Any]
    top_k: Callable[..., Any]
    rerank_memory_hits: Callable[..., Any]
