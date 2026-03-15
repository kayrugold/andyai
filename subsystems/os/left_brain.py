from __future__ import annotations

import time
from typing import Any, Callable, Dict, List


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

    return {"result": result, "reflection": reflection}


def run_goal_cycle(
    state: Dict[str, Any],
    meta: Dict[str, Any],
    gemini,
    *,
    task_queue=None,
    score_diagnostics_from_state: Callable[[Dict[str, Any], Dict[str, Any]], Any],
    submit_background_gemini_task: Callable[[Dict[str, Any], Any, str], None],
    count_learning_entries: Callable[[list], int],
    top_k: Callable[..., Any],
    rerank_memory_hits: Callable[[str, Any], Any],
    choose_strategy_source: Callable[[Dict[str, Any]], Any],
    choose_strategy_source_forced: Callable[[Dict[str, Any], str], Any],
    latest_background_hint_context: Callable[[Dict[str, Any]], str],
    now_ts: Callable[[], str],
    update_hint_genome: Callable[[Dict[str, Any], str], Any],
    normalize_hint_gene_text: Callable[[str], str],
    create_plan: Callable[[str, Any, Any, Any], Any],
    add_entry: Callable[..., Any],
    maybe_auto_prune_traces: Callable[[Dict[str, Any]], Any],
    save_db: Callable[..., Any],
    write_galaxy_html: Callable[..., Any],
    db_path: str,
    register_reflex_event: Callable[..., Any],
    decay_reflex_pressure: Callable[..., Any],
    maybe_promote_mutant_hint: Callable[[Dict[str, Any]], Any],
    get_used_hint_gene: Callable[[Dict[str, Any]], Any],
    maybe_promote_mutant_strategy: Callable[[Dict[str, Any]], Any],
    update_emotional_state: Callable[[Dict[str, Any]], Any],
    apply_recovery_mode_behavior: Callable[[Dict[str, Any]], Any],
    apply_recovery_cycle: Callable[[Dict[str, Any]], Any],
    refresh_working_memory_from_state: Callable[[Dict[str, Any]], Any],
    save_state: Callable[..., Any],
) -> str:
    st = state.get("internal_state", {})
    db = state.get("db", [])
    diag_before, _ = score_diagnostics_from_state(state, meta)
    goal = str(st.get("current_goal", "") or "").strip().lower()
    try:
        queue = task_queue if task_queue is not None else state.get("reason_queue")
        if queue is not None:
            queue.submit({"goal": goal, "state": state})
    except Exception:
        pass

    submit_background_gemini_task(state, gemini, goal)
    before_learning_entries = count_learning_entries(db)
    after_learning_entries = count_learning_entries(db)
    added_entries = after_learning_entries - before_learning_entries

    if not goal:
        return "No current goal set."

    emb = state["embedder"].embed(goal)
    hits = top_k(db, emb, k=5)
    hits = rerank_memory_hits(goal, hits)
    context = [e for _, e in hits[:3]]

    forced_mode = str(st.get("arena_forced_mode", "") or "").strip().lower()
    strategy_pick = choose_strategy_source_forced(state, forced_mode) if forced_mode else choose_strategy_source(state)
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
            "tags": ["strategy_gene", "planning_context"],
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
            "tags": ["background_hint", "planning_context"],
        })
        hint_used = True

    st["last_hint_used"] = hint_used
    st["last_hint_used_ts"] = now_ts() if hint_used else ""
    st["last_hint_used_text"] = chosen_hint if hint_used else ""
    if hint_used:
        st["hint_usage_count"] = int(st.get("hint_usage_count", 0) or 0) + 1
        gene = update_hint_genome(state, hint_ctx)
        mutant = st.get("latest_mutant_hint")
        if mutant and normalize_hint_gene_text(hint_ctx) == normalize_hint_gene_text(mutant):
            st["mutant_usage"] = int(st.get("mutant_usage", 0) or 0) + 1
        gene["usage"] += 1

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
        tags=["reasoning_trace", "goal_cycle", "reflection"],
    )

    maybe_auto_prune_traces(state)
    save_db(db_path, db)
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
            severity=0.6,
        )
    elif st["last_diag_delta"] > 0:
        decay_reflex_pressure(state, 0.15)

    mu = int(st.get("mutant_usage", 0) or 0)
    ms = int(st.get("mutant_success", 0) or 0)
    if mu:
        st["mutant_score"] = round(ms / mu, 2)

    maybe_promote_mutant_hint(state)

    if st.get("last_hint_used", False):
        used = str(st.get("last_hint_used_text", ""))
        mutant = str(st.get("latest_mutant_hint", "")).strip()
        if mutant and mutant in used:
            st["mutant_usage"] = int(st.get("mutant_usage", 0) or 0) + 1
            if diag_after >= diag_before:
                st["mutant_success"] = int(st.get("mutant_success", 0) or 0) + 1

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


def run_goal_cycle_forced_strategy(state: Dict[str, Any], meta: Dict[str, Any], gemini, forced_mode: str, *, run_goal_cycle: Callable[..., str]) -> str:
    st = state.get("internal_state", {})
    st["arena_forced_mode"] = str(forced_mode or "").strip().lower()
    try:
        return run_goal_cycle(state, meta, gemini)
    finally:
        st["arena_forced_mode"] = ""


def maintenance_worker(
    state,
    *,
    write_galaxy_html: Callable[..., Any],
    log: Callable[[str], None],
) -> None:
    while True:
        try:
            db = state.get("db", [])
            write_galaxy_html(db, "galaxy.html")
            log("MAINT: galaxy rebuild complete.")
        except Exception as e:
            log(f"MAINT ERROR: {e}")
        time.sleep(60)


def background_drive_loop(state, *, run_drive_tick: Callable[[Dict[str, Any]], Any]) -> None:
    while True:
        try:
            run_drive_tick(state)
        except Exception:
            pass
        time.sleep(30)


def chat_once(
    state: Dict[str, Any],
    meta: Dict[str, Any],
    gemini,
    msg: str,
    *,
    maintenance_worker: Callable[[Dict[str, Any]], None],
    thread_factory,
    log: Callable[[str], None],
    refresh_goal_if_needed: Callable[[Dict[str, Any], Dict[str, Any]], bool],
    save_meta: Callable[..., Any],
    save_state: Callable[..., Any],
    save_db: Callable[..., Any],
    db_path: str,
    write_galaxy_html: Callable[..., Any],
    goal_is_stale: Callable[[Dict[str, Any], Dict[str, Any]], bool],
    propose_new_goal: Callable[[Dict[str, Any]], str],
    infer_reasoning_summary: Callable[[Dict[str, Any], str], str],
    add_rule: Callable[..., Any],
    push_limited: Callable[..., Any],
    run_brain: Callable[[str, Dict[str, Any]], Dict[str, Any]],
    build_reasoning_trace: Callable[[Dict[str, Any], str, str], str],
    promote_user_fact: Callable[[Dict[str, Any], str], Any],
    add_entry: Callable[..., Any],
    lane_tags_for: Callable[..., Any],
    maybe_auto_prune_traces: Callable[[Dict[str, Any]], Any],
    top_k: Callable[..., Any],
    compose_local_reply: Callable[[str, Dict[str, Any], Dict[str, Any], Any], str],
    refresh_working_memory_from_state: Callable[[Dict[str, Any]], Any],
    wm_push_list: Callable[..., Any],
) -> None:
    db = state["db"]
    internal = state["internal_state"]

    t = thread_factory(target=maintenance_worker, args=(state,), daemon=True)
    t.start()
    log("MAINT: background maintenance thread started.")

    goal_changed = refresh_goal_if_needed(state, meta)
    if goal_changed:
        save_meta(meta)
        save_state(state["internal_state"])
        save_db(db_path, state["db"])
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
            tags=lane_tags_for(msg, source="user", base_tags=["chat", "local"]),
        )
        add_entry(
            db,
            text=trace,
            embedding=state["embedder"].embed(trace),
            tags=lane_tags_for(trace, source="system", base_tags=["reasoning_trace"]),
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
            tags=lane_tags_for(msg, source="user", base_tags=["chat", "composed"]),
        )
        add_entry(
            db,
            text=trace,
            embedding=state["embedder"].embed(trace),
            tags=lane_tags_for(trace, source="system", base_tags=["reasoning_trace"]),
        )
        removed = maybe_auto_prune_traces(state)
        if removed:
            log(f"AUTO-PRUNE: removed {removed} duplicate reasoning traces.")

    save_db(db_path, db)
    save_meta(meta)
    save_state(internal)
    write_galaxy_html(db, "galaxy.html")
    return reply
