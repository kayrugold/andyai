def run_cli_loop(
    state,
    meta,
    gemini,
    internal_state,
    db,
    log,
    traceback,
    save_db,
    save_meta,
    save_state,
    DB_PATH,

    handle_worker_results,

    status_line,
    local_reasoning_summary,
    load_identity,
    reflect_identity,
    rules_as_text,
    consolidate_reasoning_traces,
    write_galaxy_html,
    seed_trace_for_current_goal,
    run_goal_cycle,
    load_json,
    idle_debug_text,
    brain_status_text,
    brain_history_text,
    learning_history_text,
    strategy_genome_text,
    strategy_selection_text,
    arena_status_text,
    nerve_reset_text,
    emotional_state_text,
    set_recovery_mode,
    recovery_mode_text,
    handle_regulation_command,
    recovery_status_text,
    behavior_policy_text,
    reflex_status_text,
    reflex_history_text,
    nerve_reset,
    run_drive_tick,
    handle_memory_command,
    handle_language_command,
    handle_art_command,
    archive_project,
    chat_once,
    register_reflex_event,
    top_k,
    rerank_memory_hits,
):
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
                )
            except Exception:
                pass

            log("ERROR: " + str(e))
            log(traceback.format_exc())

    save_db(DB_PATH, db)
    save_meta(meta)
    save_state(internal_state)
    log("bye.")
