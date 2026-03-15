
from runtime.task_queue import TaskQueue, Worker
from runtime.workers import gemini_worker, reasoning_worker, diagnostics_worker
from subsystems.creative.art_engine import write_svg_art, art_status_text, art_gallery_text, art_profile_text, art_modes_text, evolve_art
from runtime.art_commands import handle_art_command
from runtime.language_commands import handle_language_command
from subsystems.os.drive_scheduler import run_drive_tick
from runtime.boot import attach_runtime_basics, ensure_internal_defaults
from runtime.background_threads import start_background_threads
from runtime.cli import run_cli_loop
from runtime.context import RuntimeContext
from runtime.foundation import (
    add_rule as foundation_add_rule,
    build_registry as foundation_build_registry,
    identity_text as foundation_identity_text,
    load_identity as foundation_load_identity,
    load_json as foundation_load_json,
    load_meta as foundation_load_meta,
    load_rules as foundation_load_rules,
    log as foundation_log,
    now_ts as foundation_now_ts,
    rules_as_text as foundation_rules_as_text,
    run_brain as foundation_run_brain,
    save_json as foundation_save_json,
    save_meta as foundation_save_meta,
)
from runtime.regulation_commands import handle_regulation_command
from runtime.memory_commands import handle_memory_command
from subsystems.ai.andy_ai import (
    compose_identity_reply as compose_ai_identity_reply,
    compose_local_reply as compose_ai_local_reply,
    compose_reasoning_view as compose_ai_reasoning_view,
)
from subsystems.ai.conscious_interface import (
    compose_local_reply_from_surface,
    conscious_identity_text as ai_conscious_identity_text,
    conscious_reasoning_summary as ai_conscious_reasoning_summary,
)
from subsystems.os.andy_os import (
    display_hint_gene_text,
    get_used_hint_gene,
    handle_worker_results as handle_os_worker_results,
    has_similar_background_hint,
    latest_background_hint_context,
    normalize_hint_gene_text,
    store_background_hint as os_store_background_hint,
    status_line as os_status_line,
    submit_queue_task as os_submit_queue_task,
    submit_background_gemini_task as submit_os_background_gemini_task,
    update_hint_genome,
)
from subsystems.os.conscious_surface import build_conscious_surface
from subsystems.regulation.nervous_system import (
    apply_recovery_cycle as nervous_apply_recovery_cycle,
    apply_recovery_mode_behavior as nervous_apply_recovery_mode_behavior,
    behavior_policy as nervous_behavior_policy,
    behavior_policy_text as nervous_behavior_policy_text,
    clamp01,
    decay_reflex_pressure as nervous_decay_reflex_pressure,
    emotional_state_text as nervous_emotional_state_text,
    ensure_emotional_state as ensure_nervous_emotional_state,
    nerve_reset as nervous_nerve_reset,
    nerve_reset_text as nervous_nerve_reset_text,
    recovery_mode_text as nervous_recovery_mode_text,
    recovery_status_text as nervous_recovery_status_text,
    reflex_history_text as nervous_reflex_history_text,
    reflex_status_text as nervous_reflex_status_text,
    register_reflex_event as nervous_register_reflex_event,
    set_recovery_mode as nervous_set_recovery_mode,
    update_emotional_state as nervous_update_emotional_state,
)
from subsystems.os.working_memory import (
    ensure_working_memory as ensure_runtime_working_memory,
    refresh_working_memory_from_state as refresh_runtime_working_memory_from_state,
    wm_push_list as runtime_wm_push_list,
    working_memory_text as runtime_working_memory_text,
)
from subsystems.os.status_reports import (
    arena_status_text as report_arena_status_text,
    brain_history_text as report_brain_history_text,
    brain_status_text as report_brain_status_text,
    idle_debug_text as report_idle_debug_text,
    learning_history_text as report_learning_history_text,
    protected_memory_status_text as report_protected_memory_status_text,
    strategy_genome_text as report_strategy_genome_text,
    strategy_selection_text as report_strategy_selection_text,
)
from subsystems.os.left_brain import (
    background_drive_loop as left_background_drive_loop,
    chat_once as left_chat_once,
    maintenance_worker as left_maintenance_worker,
    run_goal_cycle as left_run_goal_cycle,
    run_goal_cycle_forced_strategy as left_run_goal_cycle_forced_strategy,
)
from subsystems.os.strategy_system import (
    auto_evolve_hints as strategy_auto_evolve_hints,
    best_hint_gene_text as strategy_best_hint_gene_text,
    best_strategy_gene_text as strategy_best_strategy_gene_text,
    choose_strategy_gene as strategy_choose_strategy_gene,
    choose_strategy_gene_with_exploration as strategy_choose_strategy_gene_with_exploration,
    choose_strategy_source as strategy_choose_strategy_source,
    choose_strategy_source_forced as strategy_choose_strategy_source_forced,
    gene_score as strategy_gene_score,
    get_best_hint_gene as strategy_get_best_hint_gene,
    get_best_strategy_gene as strategy_get_best_strategy_gene,
    list_strategy_genes as strategy_list_strategy_genes,
    maybe_promote_mutant_hint as strategy_maybe_promote_mutant_hint,
    maybe_promote_mutant_strategy as strategy_maybe_promote_mutant_strategy,
    mutate_best_hint_gene as strategy_mutate_best_hint_gene,
    mutate_best_strategy_gene as strategy_mutate_best_strategy_gene,
    run_strategy_arena as strategy_run_strategy_arena,
    seed_strategy_genome as strategy_seed_strategy_genome,
)
from subsystems.os.autotrain_support import (
    autotrain_loop as os_autotrain_loop,
    choose_autotrain_topic as os_choose_autotrain_topic,
    goal_topic_hints as os_goal_topic_hints,
    infer_reasoning_summary as os_infer_reasoning_summary,
    print_mutation_topics as os_print_mutation_topics,
    recent_failure_topics as os_recent_failure_topics,
    recent_topic_scores as os_recent_topic_scores,
    weakest_topics as os_weakest_topics,
)
from subsystems.os.diagnostics_support import (
    count_learning_entries as os_count_learning_entries,
    score_diagnostics_from_state as os_score_diagnostics_from_state,
    summarize_goal_cycle_result as os_summarize_goal_cycle_result,
)

import threading
import time
import os
import json
import time
import importlib.util
import traceback
from functools import partial
from typing import Any, Dict, List

from subsystems.os.planner import create_plan
from plugins.mentors.gemini import GeminiClient
from subsystems.os.embedder import Embedder
from infra.storage.memory_store import load_db, save_db, add_entry
from subsystems.os.recall import top_k
from infra.tools.tool_registry import ToolRegistry
from infra.tools.tools_basic import (
    tool_calc,
    tool_time,
    tool_read_json,
    tool_write_json,
    tool_memory_search_factory,
    tool_memory_add_factory,
)
from runtime.galaxy import write_galaxy_html
from subsystems.os.evolver import seed_current_brain, evolve, reflect_identity
from infra.storage.state_store import load_state, save_state, push_limited
from runtime.archive_commands import archive_project
from subsystems.os.memory_reasoning import (
    best_goal_trace as memory_best_goal_trace,
    build_reasoning_trace as memory_build_reasoning_trace,
    classify_memory_lane as memory_classify_memory_lane,
    compact_goal_text as memory_compact_goal_text,
    compact_reasoning_text as memory_compact_reasoning_text,
    consolidate_reasoning_traces as memory_consolidate_reasoning_traces,
    fact_exists as memory_fact_exists,
    goal_is_stale as memory_goal_is_stale,
    has_trace_for_current_goal as memory_has_trace_for_current_goal,
    lane_tags_for as memory_lane_tags_for,
    local_reasoning_summary as memory_local_reasoning_summary,
    maybe_auto_prune_traces as memory_maybe_auto_prune_traces,
    normalize_trace_text as memory_normalize_trace_text,
    promote_user_fact as memory_promote_user_fact,
    propose_new_goal as memory_propose_new_goal,
    refresh_goal_if_needed as memory_refresh_goal_if_needed,
    seed_trace_for_current_goal as memory_seed_trace_for_current_goal,
    summarize_trace_text as memory_summarize_trace_text,
)
from infra.retrieval.retrieval_utils import rerank_memory_hits

APP = "AndyAI-v211 (Inference Reporting + Grounding)"
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


now_ts = foundation_now_ts
load_json = foundation_load_json
save_json = foundation_save_json
load_rules = partial(foundation_load_rules, RULES_PATH, load_json=load_json)
load_identity = partial(foundation_load_identity, IDENTITY_PATH, load_json=load_json)


def log(line: str) -> None:
    foundation_log(line, now_ts=now_ts, log_file=LOG_FILE)


def add_rule(text: str, kind: str = "user_rule") -> None:
    foundation_add_rule(
        text,
        rules_path=RULES_PATH,
        now_ts=now_ts,
        load_rules=load_rules,
        save_json=save_json,
        kind=kind,
    )


def rules_as_text(max_items: int = 25) -> str:
    return foundation_rules_as_text(load_rules, max_items=max_items)


def build_surface_for_consciousness(state: Dict[str, Any], meta: Dict[str, Any]):
    return build_conscious_surface(
        state,
        meta,
        load_identity=load_identity,
        ensure_emotional_state=ensure_emotional_state,
        ensure_working_memory=ensure_working_memory,
    )


compose_local_reply = partial(
    compose_local_reply_from_surface,
    build_conscious_surface=build_surface_for_consciousness,
    compose_ai_local_reply=compose_ai_local_reply,
    reasoning_summary_for=lambda prompt, state, meta: conscious_reasoning_summary(prompt, state, meta),
)


_store_background_hint = partial(
    os_store_background_hint,
    add_entry=add_entry,
    save_db=save_db,
    write_galaxy_html=write_galaxy_html,
    db_path=DB_PATH,
)

submit_background_gemini_task = partial(submit_os_background_gemini_task, log=log)
status_line = partial(os_status_line, app_name=APP, load_identity=load_identity)
register_reflex_event = partial(nervous_register_reflex_event, now_ts=now_ts)
decay_reflex_pressure = nervous_decay_reflex_pressure
ensure_emotional_state = ensure_nervous_emotional_state
update_emotional_state = partial(nervous_update_emotional_state, now_ts=now_ts)
emotional_state_text = nervous_emotional_state_text
ensure_working_memory = ensure_runtime_working_memory
wm_push_list = runtime_wm_push_list
behavior_policy = partial(nervous_behavior_policy, ensure_working_memory=ensure_working_memory)
behavior_policy_text = partial(nervous_behavior_policy_text, ensure_working_memory=ensure_working_memory)
apply_recovery_mode_behavior = nervous_apply_recovery_mode_behavior
apply_recovery_cycle = partial(
    nervous_apply_recovery_cycle,
    now_ts=now_ts,
    ensure_working_memory=ensure_working_memory,
)
nerve_reset = partial(
    nervous_nerve_reset,
    now_ts=now_ts,
    ensure_working_memory=ensure_working_memory,
)
nerve_reset_text = partial(
    nervous_nerve_reset_text,
    now_ts=now_ts,
    ensure_working_memory=ensure_working_memory,
)
reflex_status_text = nervous_reflex_status_text
reflex_history_text = nervous_reflex_history_text
set_recovery_mode = partial(nervous_set_recovery_mode, now_ts=now_ts)
recovery_mode_text = nervous_recovery_mode_text
recovery_status_text = nervous_recovery_status_text
refresh_working_memory_from_state = partial(
    refresh_runtime_working_memory_from_state,
    now_ts=now_ts,
)
working_memory_text = runtime_working_memory_text
protected_memory_status_text = report_protected_memory_status_text
idle_debug_text = report_idle_debug_text
arena_status_text = report_arena_status_text
brain_history_text = report_brain_history_text


def handle_worker_results(state: Dict[str, Any]) -> None:
    handle_os_worker_results(
        state,
        log=log,
        now_ts=now_ts,
        embed_text=state["embedder"].embed,
        add_memory_entry=_store_background_hint,
    )


identity_text = partial(foundation_identity_text, load_identity)
load_meta = partial(foundation_load_meta, META_PATH, load_json=load_json, now_ts=now_ts)
save_meta = partial(foundation_save_meta, meta_path=META_PATH, save_json=save_json)
build_registry = partial(
    foundation_build_registry,
    tool_registry_factory=ToolRegistry,
    tool_calc=tool_calc,
    tool_time=tool_time,
    tool_read_json=tool_read_json,
    tool_write_json=tool_write_json,
    tool_memory_search_factory=tool_memory_search_factory,
    tool_memory_add_factory=tool_memory_add_factory,
)
run_brain = partial(foundation_run_brain, brain_file=BRAIN_FILE)






submit_reasoning_task = partial(os_submit_queue_task, queue_key="reason_queue")
submit_diag_task = partial(os_submit_queue_task, queue_key="diag_queue")

propose_new_goal = memory_propose_new_goal
goal_is_stale = memory_goal_is_stale
has_trace_for_current_goal = partial(
    memory_has_trace_for_current_goal,
    submit_reasoning=submit_reasoning_task,
    submit_diagnostics=submit_diag_task,
)
seed_trace_for_current_goal = partial(
    memory_seed_trace_for_current_goal,
    add_entry=add_entry,
    submit_reasoning=submit_reasoning_task,
)
compact_goal_text = memory_compact_goal_text
compact_reasoning_text = memory_compact_reasoning_text
summarize_trace_text = memory_summarize_trace_text
best_goal_trace = partial(
    memory_best_goal_trace,
    summarize_trace_text=summarize_trace_text,
    submit_reasoning=submit_reasoning_task,
)
local_reasoning_summary = partial(
    memory_local_reasoning_summary,
    best_goal_trace=best_goal_trace,
    compact_goal_text=compact_goal_text,
    compact_reasoning_text=compact_reasoning_text,
    load_identity=load_identity,
    ensure_emotional_state=ensure_emotional_state,
    behavior_policy=behavior_policy,
    ensure_working_memory=ensure_working_memory,
)


conscious_reasoning_summary = partial(
    ai_conscious_reasoning_summary,
    build_conscious_surface=build_surface_for_consciousness,
    best_goal_trace=best_goal_trace,
    compose_reasoning_view=compose_ai_reasoning_view,
)

conscious_identity_text = partial(
    ai_conscious_identity_text,
    build_conscious_surface=build_surface_for_consciousness,
    compose_identity_reply=compose_ai_identity_reply,
)
fact_exists = memory_fact_exists
promote_user_fact = partial(
    memory_promote_user_fact,
    add_entry=add_entry,
    fact_exists=fact_exists,
)
classify_memory_lane = memory_classify_memory_lane
lane_tags_for = memory_lane_tags_for
build_reasoning_trace = partial(
    memory_build_reasoning_trace,
    submit_reasoning=submit_reasoning_task,
)
refresh_goal_if_needed = partial(
    memory_refresh_goal_if_needed,
    goal_is_stale=goal_is_stale,
    propose_new_goal=propose_new_goal,
    has_trace_for_current_goal=has_trace_for_current_goal,
    seed_trace_for_current_goal=seed_trace_for_current_goal,
    maybe_auto_prune_traces=lambda state: maybe_auto_prune_traces(state),
)

weakest_topics = partial(os_weakest_topics, load_json=load_json)
recent_topic_scores = partial(os_recent_topic_scores, load_json=load_json)
goal_topic_hints = os_goal_topic_hints
infer_reasoning_summary = partial(
    os_infer_reasoning_summary,
    submit_reasoning_task=submit_reasoning_task,
)
recent_failure_topics = partial(os_recent_failure_topics, load_json=load_json)
choose_autotrain_topic = partial(
    os_choose_autotrain_topic,
    targeted_mutations=TARGETED_MUTATIONS,
    weakest_topics=weakest_topics,
    recent_failure_topics=recent_failure_topics,
    goal_topic_hints=goal_topic_hints,
    recent_topic_scores=recent_topic_scores,
)
autotrain_loop = partial(
    os_autotrain_loop,
    targeted_mutations=TARGETED_MUTATIONS,
    choose_autotrain_topic=choose_autotrain_topic,
    evolve=evolve,
    log=log,
    load_json=load_json,
    save_state=save_state,
)


normalize_trace_text = memory_normalize_trace_text
consolidate_reasoning_traces = memory_consolidate_reasoning_traces
maybe_auto_prune_traces = partial(
    memory_maybe_auto_prune_traces,
    consolidate_reasoning_traces=consolidate_reasoning_traces,
    save_db=save_db,
    write_galaxy_html=write_galaxy_html,
    db_path=DB_PATH,
)

def print_mutation_topics() -> None:
    print("Mutation topics:")
    for line in os_print_mutation_topics(TARGETED_MUTATIONS):
        print(line)

summarize_goal_cycle_result = os_summarize_goal_cycle_result
score_diagnostics_from_state = os_score_diagnostics_from_state
count_learning_entries = os_count_learning_entries


best_hint_gene_text = strategy_best_hint_gene_text
mutate_best_hint_gene = partial(strategy_mutate_best_hint_gene, now_ts=now_ts)
gene_score = strategy_gene_score
get_best_hint_gene = strategy_get_best_hint_gene
maybe_promote_mutant_hint = partial(
    strategy_maybe_promote_mutant_hint,
    update_hint_genome=update_hint_genome,
)
seed_strategy_genome = strategy_seed_strategy_genome
get_best_strategy_gene = strategy_get_best_strategy_gene
choose_strategy_gene = strategy_choose_strategy_gene
best_strategy_gene_text = strategy_best_strategy_gene_text
mutate_best_strategy_gene = strategy_mutate_best_strategy_gene
maybe_promote_mutant_strategy = strategy_maybe_promote_mutant_strategy
list_strategy_genes = strategy_list_strategy_genes
choose_strategy_gene_with_exploration = strategy_choose_strategy_gene_with_exploration
choose_strategy_source = partial(
    strategy_choose_strategy_source,
    behavior_policy=behavior_policy,
)
choose_strategy_source_forced = partial(
    strategy_choose_strategy_source_forced,
    behavior_policy=behavior_policy,
    choose_strategy_source=choose_strategy_source,
)

brain_status_text = partial(
    report_brain_status_text,
    ensure_emotional_state=ensure_emotional_state,
    behavior_policy=behavior_policy,
    best_hint_gene_text=best_hint_gene_text,
    best_strategy_gene_text=best_strategy_gene_text,
    score_diagnostics_from_state=score_diagnostics_from_state,
)
learning_history_text = partial(
    report_learning_history_text,
    summarize_trace_text=summarize_trace_text,
)
strategy_genome_text = partial(
    report_strategy_genome_text,
    list_strategy_genes=list_strategy_genes,
)
strategy_selection_text = report_strategy_selection_text
run_goal_cycle = partial(
    left_run_goal_cycle,
    score_diagnostics_from_state=score_diagnostics_from_state,
    submit_background_gemini_task=submit_background_gemini_task,
    count_learning_entries=count_learning_entries,
    top_k=top_k,
    rerank_memory_hits=rerank_memory_hits,
    choose_strategy_source=choose_strategy_source,
    choose_strategy_source_forced=choose_strategy_source_forced,
    latest_background_hint_context=latest_background_hint_context,
    now_ts=now_ts,
    update_hint_genome=update_hint_genome,
    normalize_hint_gene_text=normalize_hint_gene_text,
    create_plan=create_plan,
    add_entry=add_entry,
    maybe_auto_prune_traces=maybe_auto_prune_traces,
    save_db=save_db,
    write_galaxy_html=write_galaxy_html,
    db_path=DB_PATH,
    register_reflex_event=register_reflex_event,
    decay_reflex_pressure=decay_reflex_pressure,
    maybe_promote_mutant_hint=maybe_promote_mutant_hint,
    get_used_hint_gene=get_used_hint_gene,
    maybe_promote_mutant_strategy=maybe_promote_mutant_strategy,
    update_emotional_state=update_emotional_state,
    apply_recovery_mode_behavior=apply_recovery_mode_behavior,
    apply_recovery_cycle=apply_recovery_cycle,
    refresh_working_memory_from_state=refresh_working_memory_from_state,
    save_state=save_state,
)
auto_evolve_hints = partial(
    strategy_auto_evolve_hints,
    mutate_best_hint_gene=mutate_best_hint_gene,
    save_state=save_state,
    run_goal_cycle=run_goal_cycle,
    handle_worker_results=handle_worker_results,
    register_reflex_event=register_reflex_event,
    maybe_promote_mutant_hint=maybe_promote_mutant_hint,
)
run_goal_cycle_forced_strategy = partial(
    left_run_goal_cycle_forced_strategy,
    run_goal_cycle=run_goal_cycle,
)
run_strategy_arena = partial(
    strategy_run_strategy_arena,
    run_goal_cycle_forced_strategy=run_goal_cycle_forced_strategy,
    handle_worker_results=handle_worker_results,
    save_state=save_state,
)
maintenance_worker = partial(
    left_maintenance_worker,
    write_galaxy_html=write_galaxy_html,
    log=log,
)
background_drive_loop = partial(
    left_background_drive_loop,
    run_drive_tick=run_drive_tick,
)
chat_once = partial(
    left_chat_once,
    maintenance_worker=maintenance_worker,
    thread_factory=threading.Thread,
    log=log,
    refresh_goal_if_needed=refresh_goal_if_needed,
    save_meta=save_meta,
    save_state=save_state,
    save_db=save_db,
    db_path=DB_PATH,
    write_galaxy_html=write_galaxy_html,
    goal_is_stale=goal_is_stale,
    propose_new_goal=propose_new_goal,
    infer_reasoning_summary=infer_reasoning_summary,
    add_rule=add_rule,
    push_limited=push_limited,
    run_brain=run_brain,
    build_reasoning_trace=build_reasoning_trace,
    promote_user_fact=promote_user_fact,
    add_entry=add_entry,
    lane_tags_for=lane_tags_for,
    maybe_auto_prune_traces=maybe_auto_prune_traces,
    top_k=top_k,
    compose_local_reply=compose_local_reply,
    refresh_working_memory_from_state=refresh_working_memory_from_state,
    wm_push_list=wm_push_list,
)



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
    attach_runtime_basics(state, gemini)
    ensure_internal_defaults(state)

    threads = start_background_threads(


        state,


        Worker,


        reasoning_worker,


        diagnostics_worker,


        gemini_worker,


        background_drive_loop,


    )

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

    runtime = RuntimeContext(
        state=state,
        meta=meta,
        gemini=gemini,
        internal_state=internal_state,
        db=db,
        log=log,
        traceback=traceback,
        save_db=save_db,
        save_meta=save_meta,
        save_state=save_state,
        db_path=DB_PATH,
        handle_worker_results=handle_worker_results,
        status_line=status_line,
        local_reasoning_summary=conscious_reasoning_summary,
        conscious_identity_text=conscious_identity_text,
        load_identity=load_identity,
        reflect_identity=reflect_identity,
        rules_as_text=rules_as_text,
        consolidate_reasoning_traces=consolidate_reasoning_traces,
        write_galaxy_html=write_galaxy_html,
        seed_trace_for_current_goal=seed_trace_for_current_goal,
        run_goal_cycle=run_goal_cycle,
        load_json=load_json,
        idle_debug_text=idle_debug_text,
        brain_status_text=brain_status_text,
        brain_history_text=brain_history_text,
        learning_history_text=learning_history_text,
        strategy_genome_text=strategy_genome_text,
        strategy_selection_text=strategy_selection_text,
        arena_status_text=arena_status_text,
        run_strategy_arena=run_strategy_arena,
        auto_evolve_hints=auto_evolve_hints,
        nerve_reset_text=nerve_reset_text,
        emotional_state_text=emotional_state_text,
        set_recovery_mode=set_recovery_mode,
        recovery_mode_text=recovery_mode_text,
        handle_regulation_command=handle_regulation_command,
        recovery_status_text=recovery_status_text,
        behavior_policy_text=behavior_policy_text,
        reflex_status_text=reflex_status_text,
        reflex_history_text=reflex_history_text,
        nerve_reset=nerve_reset,
        run_drive_tick=run_drive_tick,
        handle_memory_command=handle_memory_command,
        handle_language_command=handle_language_command,
        handle_art_command=handle_art_command,
        archive_project=archive_project,
        chat_once=chat_once,
        register_reflex_event=register_reflex_event,
        top_k=top_k,
        rerank_memory_hits=rerank_memory_hits,
    )
    run_cli_loop(runtime)


if __name__ == "__main__":
    main()
