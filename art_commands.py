from art_engine import (
    write_svg_art,
    art_status_text,
    art_gallery_text,
    art_profile_text,
    art_modes_text,
    evolve_art,
    evolve_art_generations,
    evolve_family_generations,
    write_art_gallery_browser,
    write_invented_art,
    discovered_modes_text,
    discovered_mode_pool,
    art_best_text,
    art_hof_text,
    art_history_text,
    art_lineage_text,
    art_vocab_text,
    write_scene_art,
    evolve_scene_generations,
)


def handle_art_command(
    cmd: str,
    low: str,
    state,
    db,
    save_state_fn,
    top_k_fn,
    rerank_memory_hits_fn,
):
    if low == "art status":
        print(art_status_text(state))
        return True

    if low == "art modes":
        print(art_modes_text())
        return True

    if low == "art gallery":
        print(art_gallery_text())
        return True

    if low == "art browser":
        path = write_art_gallery_browser()
        print("ART BROWSER\n")
        print(f"Path: {path}")
        return True

    if low == "art profile":
        print(art_profile_text(state))
        return True

    if low == "art evolve":
        print(evolve_art(state))
        save_state_fn(state["internal_state"])
        return True

    if low.startswith("art evolve "):
        arg = cmd[len("art evolve "):].strip()
        try:
            rounds = int(arg)
        except Exception:
            print("ART EVOLVE ERROR\n\nUsage: art evolve <rounds>")
            return True

        print(evolve_art_generations(state, rounds))
        save_state_fn(state["internal_state"])
        return True

    if low.startswith("art family "):
        parts = cmd.split()
        if len(parts) < 4:
            print("ART FAMILY ERROR\n\nUsage: art family <mode> <rounds>")
            return True

        base_mode = parts[2].strip().lower()
        try:
            rounds = int(parts[3].strip())
        except Exception:
            print("ART FAMILY ERROR\n\nUsage: art family <mode> <rounds>")
            return True

        print(evolve_family_generations(state, base_mode, rounds))
        save_state_fn(state["internal_state"])
        return True

    if low == "art invent":
        result = write_invented_art(state)
        print("ART INVENTED\n")
        print(f"Mode: {result['mode']}")
        print(f"Path: {result['path']}")
        print(f"Score: {result['score']}")
        save_state_fn(state["internal_state"])
        return True

    if low == "art discovered":
        print(discovered_modes_text(state))
        return True

    if low == "art species":
        modes = discovered_mode_pool(state)
        print("ART SPECIES\n")
        if not modes:
            print("No discovered species yet.")
        else:
            for m in modes:
                print(f"  {m}")
        return True

    if low == "art best":
        print(art_best_text(state))
        return True

    if low == "art hof":
        print(art_hof_text(state))
        return True

    if low == "art history":
        print(art_history_text(state))
        return True

    if low == "art lineage":
        print(art_lineage_text(state))
        return True

    if low == "art vocab":
        print(art_vocab_text())
        return True

    if low.startswith("art scene evolve "):
        raw = cmd[len("art scene evolve "):].strip()
        parts = [x.strip().lower() for x in raw.split() if x.strip()]
        if len(parts) < 2:
            print("ART SCENE EVOLVE ERROR\n\nUsage: art scene evolve <concepts...> <rounds>")
            return True

        try:
            rounds = int(parts[-1])
            concepts = parts[:-1]
        except Exception:
            print("ART SCENE EVOLVE ERROR\n\nUsage: art scene evolve <concepts...> <rounds>")
            return True

        print(evolve_scene_generations(state, concepts, rounds))
        save_state_fn(state["internal_state"])
        return True

    if low.startswith("art scene "):
        raw = cmd[len("art scene "):].strip()
        concepts = [x.strip().lower() for x in raw.split() if x.strip()]
        result = write_scene_art(state, concepts)
        print("ART SCENE\n")
        print(f"Concepts: {', '.join(result['concepts'])}")
        print(f"Path: {result['path']}")
        print(f"Score: {result['score']}")
        save_state_fn(state["internal_state"])
        return True

    if low == "art memory":
        q = "art_artifact orbit spiral grid wave phyllotaxis svg visual"
        emb = state["embedder"].embed(q)
        hits = top_k_fn(db, emb, k=12)
        hits = rerank_memory_hits_fn(q, hits)
        print("[ART MEMORY]")
        for sscore, e in hits[:10]:
            txt = str(e.get("text", ""))[:220].replace("\n", " ")
            print(f"  {sscore:.3f} | {e.get('id')} | {txt}")
        return True

    if low.startswith("art"):
        parts = cmd.split()
        mode = "spiral"
        if len(parts) >= 2:
            mode = parts[1].strip().lower()
            if mode == "art":
                mode = "spiral"

        try:
            path = write_svg_art(state, mode=mode)
            print("ART GENERATED\n")
            print(f"Mode: {mode}")
            print(f"Path: {path}")
            save_state_fn(state["internal_state"])
        except Exception as e:
            print(f"ART ERROR: {e}")
        return True

    return False
