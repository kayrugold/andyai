def run_cli_loop(runtime):
    state = runtime.state
    meta = runtime.meta
    gemini = runtime.gemini
    internal_state = runtime.internal_state
    db = runtime.db
    log = runtime.log
    traceback = runtime.traceback
    save_db = runtime.save_db
    save_meta = runtime.save_meta
    save_state = runtime.save_state
    DB_PATH = runtime.db_path
    handle_worker_results = runtime.handle_worker_results
    status_line = runtime.status_line
    local_reasoning_summary = runtime.local_reasoning_summary
    conscious_identity_text = runtime.conscious_identity_text
    load_identity = runtime.load_identity
    reflect_identity = runtime.reflect_identity
    rules_as_text = runtime.rules_as_text
    consolidate_reasoning_traces = runtime.consolidate_reasoning_traces
    write_galaxy_html = runtime.write_galaxy_html
    seed_trace_for_current_goal = runtime.seed_trace_for_current_goal
    run_goal_cycle = runtime.run_goal_cycle
    load_json = runtime.load_json
    idle_debug_text = runtime.idle_debug_text
    brain_status_text = runtime.brain_status_text
    brain_history_text = runtime.brain_history_text
    learning_history_text = runtime.learning_history_text
    strategy_genome_text = runtime.strategy_genome_text
    strategy_selection_text = runtime.strategy_selection_text
    arena_status_text = runtime.arena_status_text
    run_strategy_arena = runtime.run_strategy_arena
    auto_evolve_hints = runtime.auto_evolve_hints
    nerve_reset_text = runtime.nerve_reset_text
    emotional_state_text = runtime.emotional_state_text
    set_recovery_mode = runtime.set_recovery_mode
    recovery_mode_text = runtime.recovery_mode_text
    handle_regulation_command = runtime.handle_regulation_command
    recovery_status_text = runtime.recovery_status_text
    behavior_policy_text = runtime.behavior_policy_text
    reflex_status_text = runtime.reflex_status_text
    reflex_history_text = runtime.reflex_history_text
    nerve_reset = runtime.nerve_reset
    run_drive_tick = runtime.run_drive_tick
    handle_memory_command = runtime.handle_memory_command
    handle_language_command = runtime.handle_language_command
    handle_art_command = runtime.handle_art_command
    archive_project = runtime.archive_project
    chat_once = runtime.chat_once
    register_reflex_event = runtime.register_reflex_event
    top_k = runtime.top_k
    rerank_memory_hits = runtime.rerank_memory_hits

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
                    "  strategy arena [N]\n"
                    "  auto evolve [N]\n"
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
                print(conscious_identity_text(state, meta))
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
                meta2 = load_json("meta.json", {})
                gemini2 = state.get("gemini_client")
                print(idle_debug_text(state, meta2, gemini2))
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

            if low == "strategy arena" or low.startswith("strategy arena "):
                parts = cmd.split()
                rounds = 6
                if len(parts) >= 3:
                    try:
                        rounds = int(parts[2])
                    except Exception:
                        rounds = 6
                print(run_strategy_arena(state, meta, gemini, rounds=rounds))
                continue

            if low == "auto evolve" or low.startswith("auto evolve "):
                parts = cmd.split()
                rounds = 3
                if len(parts) >= 3:
                    try:
                        rounds = int(parts[2])
                    except Exception:
                        rounds = 3
                print(auto_evolve_hints(state, meta, gemini, rounds=rounds))
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
                set_recovery_mode(state, mode)
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

            if low == "drive tick":
                print(run_drive_tick(state))
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

            if low.startswith("rule:"):
                text = cmd.split(":", 1)[1].strip()
                if text:
                    runtime.add_rule(text)
                    print("Rule added.")
                else:
                    print("No rule text provided.")
                continue

            if low == "run" or low.startswith("run "):
                parts = cmd.split()
                n = 1
                if len(parts) >= 2:
                    try:
                        n = max(1, int(parts[1]))
                    except Exception:
                        n = 1
                for _ in range(n):
                    print(run_goal_cycle(state, meta, gemini))
                continue

            if low == "step":
                print(run_goal_cycle(state, meta, gemini))
                continue

            if low.startswith("chat "):
                prompt = cmd[5:].strip()
                print(chat_once(prompt, state, meta, gemini))
                continue

            if low.startswith("mem "):
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

            if low.startswith("brain "):
                print("Brain command handling remains in runtime shell flow.")
                continue

            print(chat_once(cmd, state, meta, gemini))

        except KeyboardInterrupt:
            print("\nInterrupted. Type 'exit' to quit.")
        except Exception as e:
            register_reflex_event(
                state,
                kind="cli_error",
                source="run_cli_loop",
                detail=repr(e),
                severity=0.8,
            )
            log(f"[CLI ERROR] {e}")
            log(traceback.format_exc())
