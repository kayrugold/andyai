def handle_memory_command(
    cmd: str,
    low: str,
    state,
    db,
    top_k_fn,
    rerank_memory_hits_fn,
):
    if low.startswith("mem "):
        q = cmd[4:].strip()
        emb = state["embedder"].embed(q)
        hits = top_k_fn(db, emb, k=12)
        hits = rerank_memory_hits_fn(q, hits)
        print("[MEMORY]")
        for score, entry in hits[:10]:
            txt = str(entry.get("text", ""))[:220].replace("\n", " ")
            print(f"  {score:.3f} | {entry.get('id')} | {txt}")
        return True

    return False
