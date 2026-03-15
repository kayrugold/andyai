from __future__ import annotations

import time
from typing import Any, Callable, Dict


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


def mutate_best_hint_gene(state, *, now_ts: Callable[[], str]):
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
    effective_usage = max(usage, success, 1)
    return round(success / effective_usage, 3)


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


def maybe_promote_mutant_hint(state, *, update_hint_genome: Callable[..., Any]):
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
    parent_text = str(best_gene.get("text", "") or "").strip() if best_gene else ""

    st["mutant_score"] = mutant_score
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


def auto_evolve_hints(
    state,
    meta,
    gemini,
    rounds: int = 3,
    *,
    mutate_best_hint_gene: Callable[[Dict[str, Any]], str],
    save_state: Callable[..., Any],
    run_goal_cycle: Callable[..., str],
    handle_worker_results: Callable[[Dict[str, Any]], Any],
    register_reflex_event: Callable[..., Any],
    maybe_promote_mutant_hint: Callable[[Dict[str, Any]], Any],
):
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
                severity=0.8,
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
        {"name": "outcome_first", "instruction": "State the desired end state first, then justify each step by how it moves toward that outcome."},
        {"name": "constraint_first", "instruction": "List constraints and limits first, then build reasoning that respects them."},
        {"name": "decompose_then_verify", "instruction": "Break the goal into smaller parts, solve each part, then verify the whole chain."},
        {"name": "backward_from_goal", "instruction": "Start from the final goal and reason backward to determine necessary prior steps."},
        {"name": "trace_then_prune", "instruction": "Generate a full reasoning trace, then remove redundant or weak steps."},
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
    parent_score = float(parent.get("score", 0.0) or 0.0) if parent else 0.0
    parent_name = str(parent.get("name", "") or "").strip() if parent else ""

    st["mutant_strategy_score"] = mutant_score
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
    explore = strategy_usage_count % 3 == 2

    chosen = None
    if explore:
        ranked = sorted(genes, key=lambda g: (int(g.get("usage", 0) or 0), float(g.get("score", 0.0) or 0.0), str(g.get("name", "") or "")))
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


def choose_strategy_source(state, *, behavior_policy: Callable[[Dict[str, Any]], Dict[str, Any]]):
    st = state.get("internal_state", {})
    seed_strategy_genome(state)
    policy = behavior_policy(state)

    mutant_name = str(st.get("latest_mutant_strategy_name", "") or "").strip()
    mutant_instruction = str(st.get("latest_mutant_strategy_instruction", "") or "").strip()

    if mutant_name and mutant_instruction and policy.get("allow_mutants", False) and not policy.get("suppress_mutant_temporarily", False) and not policy.get("prefer_exploit", False):
        ms = float(st.get("mutant_strategy_score", 0.0) or 0.0)
        parent = get_best_strategy_gene(state)
        parent_score = gene_score(parent) if parent else 0.0
        if ms >= max(0.45, parent_score * 0.75):
            st["last_strategy_selection_mode"] = "mutant"
            st["last_strategy_name"] = mutant_name
            st["last_strategy_instruction"] = mutant_instruction
            st["strategy_usage_count"] = int(st.get("strategy_usage_count", 0) or 0) + 1
            st["mutant_strategy_usage"] = int(st.get("mutant_strategy_usage", 0) or 0) + 1
            return {"name": mutant_name, "instruction": mutant_instruction, "source": "mutant"}

    if policy.get("prefer_exploit", False):
        gene = get_best_strategy_gene(state)
        if gene:
            gene["usage"] = int(gene.get("usage", 0) or 0) + 1
            st["last_strategy_selection_mode"] = "exploit"
            st["last_strategy_name"] = str(gene.get("name", "") or "")
            st["last_strategy_instruction"] = str(gene.get("instruction", "") or "")
            st["strategy_usage_count"] = int(st.get("strategy_usage_count", 0) or 0) + 1
            return {"name": str(gene.get("name", "") or "").strip(), "instruction": str(gene.get("instruction", "") or "").strip(), "source": "exploit"}

    genes = list_strategy_genes(state)
    if genes:
        if policy.get("prefer_explore", False):
            ranked = sorted(genes, key=lambda g: (int(g.get("usage", 0) or 0), float(g.get("score", 0.0) or 0.0), str(g.get("name", "") or "")))
        else:
            ranked = sorted(genes, key=lambda g: (-float(g.get("score", 0.0) or 0.0), int(g.get("usage", 0) or 0), str(g.get("name", "") or "")))
        gene = ranked[0]
        gene["usage"] = int(gene.get("usage", 0) or 0) + 1
        st["last_strategy_selection_mode"] = "explore" if policy.get("prefer_explore", False) else "exploit"
        st["last_strategy_name"] = str(gene.get("name", "") or "")
        st["last_strategy_instruction"] = str(gene.get("instruction", "") or "")
        st["strategy_usage_count"] = int(st.get("strategy_usage_count", 0) or 0) + 1
        return {"name": str(gene.get("name", "") or "").strip(), "instruction": str(gene.get("instruction", "") or "").strip(), "source": st["last_strategy_selection_mode"]}

    return {"name": "", "instruction": "", "source": "none"}


def choose_strategy_source_forced(state, forced_mode: str, *, behavior_policy: Callable[[Dict[str, Any]], Dict[str, Any]], choose_strategy_source: Callable[[Dict[str, Any]], Dict[str, str]]):
    st = state.get("internal_state", {})
    seed_strategy_genome(state)

    forced_mode = str(forced_mode or "").strip().lower()
    requested_mode = forced_mode or "none"
    mutant_name = str(st.get("latest_mutant_strategy_name", "") or "").strip()
    mutant_instruction = str(st.get("latest_mutant_strategy_instruction", "") or "").strip()
    policy = behavior_policy(state)
    fallback_reason = ""

    st["last_strategy_requested_mode"] = requested_mode
    st["last_strategy_forced_mode"] = requested_mode
    st["last_strategy_fallback_reason"] = ""

    if forced_mode == "mutant" and policy.get("suppress_mutant_temporarily", False):
        fallback_reason = "mutant_suppressed"
        forced_mode = "exploit"

    if forced_mode == "mutant" and mutant_name and mutant_instruction:
        st["last_strategy_selection_mode"] = "mutant"
        st["last_strategy_name"] = mutant_name
        st["last_strategy_instruction"] = mutant_instruction
        st["strategy_usage_count"] = int(st.get("strategy_usage_count", 0) or 0) + 1
        st["mutant_strategy_usage"] = int(st.get("mutant_strategy_usage", 0) or 0) + 1
        st["last_strategy_actual_mode"] = "mutant"
        return {"name": mutant_name, "instruction": mutant_instruction, "source": "mutant"}

    if forced_mode == "exploit":
        gene = get_best_strategy_gene(state)
        if gene:
            gene["usage"] = int(gene.get("usage", 0) or 0) + 1
            st["last_strategy_selection_mode"] = "exploit"
            st["last_strategy_name"] = str(gene.get("name", "") or "")
            st["last_strategy_instruction"] = str(gene.get("instruction", "") or "")
            st["strategy_usage_count"] = int(st.get("strategy_usage_count", 0) or 0) + 1
            if requested_mode == "mutant" and not fallback_reason:
                fallback_reason = "mutant_unavailable"
            st["last_strategy_actual_mode"] = "exploit"
            st["last_strategy_fallback_reason"] = fallback_reason
            return {"name": str(gene.get("name", "") or "").strip(), "instruction": str(gene.get("instruction", "") or "").strip(), "source": "exploit"}

    if forced_mode == "explore":
        genes = list_strategy_genes(state)
        if genes:
            ranked = sorted(genes, key=lambda g: (int(g.get("usage", 0) or 0), float(g.get("score", 0.0) or 0.0), str(g.get("name", "") or "")))
            gene = ranked[0]
            gene["usage"] = int(gene.get("usage", 0) or 0) + 1
            st["last_strategy_selection_mode"] = "explore"
            st["last_strategy_name"] = str(gene.get("name", "") or "")
            st["last_strategy_instruction"] = str(gene.get("instruction", "") or "")
            st["strategy_usage_count"] = int(st.get("strategy_usage_count", 0) or 0) + 1
            st["last_strategy_actual_mode"] = "explore"
            st["last_strategy_fallback_reason"] = fallback_reason
            return {"name": str(gene.get("name", "") or "").strip(), "instruction": str(gene.get("instruction", "") or "").strip(), "source": "explore"}

    result = choose_strategy_source(state)
    actual_mode = str(st.get("last_strategy_selection_mode", "") or "").strip() or str(result.get("source", "") or "none")
    if requested_mode != actual_mode and not fallback_reason:
        fallback_reason = "forced_mode_unavailable"
    st["last_strategy_actual_mode"] = actual_mode
    st["last_strategy_fallback_reason"] = fallback_reason
    return result


def run_strategy_arena(
    state,
    meta,
    gemini,
    rounds: int = 6,
    *,
    run_goal_cycle_forced_strategy: Callable[..., str],
    handle_worker_results: Callable[[Dict[str, Any]], Any],
    save_state: Callable[..., Any],
):
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
        actual_mode = str(st.get("last_strategy_actual_mode", "") or "").strip() or mode
        fallback_reason = str(st.get("last_strategy_fallback_reason", "") or "").strip()
        name = str(st.get("last_strategy_name", "") or "").strip() or "unknown"
        delta = float(st.get("last_diag_delta", 0.0) or 0.0)
        mode_counts[mode] = mode_counts.get(mode, 0) + 1
        strategy_counts[name] = strategy_counts.get(name, 0) + 1
        deltas.append(delta)

        lines.append(f"  strategy={name}")
        lines.append(f"  mode={mode}")
        if actual_mode and actual_mode != forced_mode:
            lines.append(f"  actual_mode={actual_mode}")
        if fallback_reason:
            lines.append(f"  fallback_reason={fallback_reason}")
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
