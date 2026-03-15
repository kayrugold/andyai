from __future__ import annotations

from typing import Any, Callable, Dict


def submit_background_gemini_task(
    state: Dict[str, Any],
    gemini,
    goal: str,
    *,
    log: Callable[[str], None],
) -> None:
    try:
        gq = state.get("gemini_queue")
        if gq is None:
            log("[WORKER gemini_debug] gemini_queue missing")
            return

        prompt = f"Give one short background reasoning hint for goal: {goal}"
        gq.submit({
            "gemini": gemini,
            "prompt": prompt,
            "state": state,
        })
        log("[WORKER gemini_debug] submitted gemini background task")
    except Exception as e:
        log("[WORKER gemini_debug] failed to submit gemini task: " + repr(e))


def submit_queue_task(payload: Any, *, queue_key: str) -> None:
    state = payload.get("state", {}) if isinstance(payload, dict) else {}
    queue = state.get(queue_key)
    if queue is not None:
        queue.submit(payload)


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


def update_hint_genome(state: Dict[str, Any], hint_text: str):
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


def get_used_hint_gene(state: Dict[str, Any]):
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


def handle_worker_results(
    state: Dict[str, Any],
    *,
    log: Callable[[str], None],
    now_ts: Callable[[], str],
    embed_text: Callable[[str], Any],
    add_memory_entry: Callable[[Dict[str, Any], str, Any], None],
) -> None:
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
                embedding = embed_text(text)
                add_memory_entry(state, text, embedding)
                log("[WORKER gemini_commit] stored background hint in memory")
        elif kind == "gemini_error":
            log("[WORKER gemini_error] " + str(item.get("error", ""))[:220])
        elif kind == "gemini_debug":
            log("[WORKER gemini_debug] " + str(item.get("message", ""))[:220])
        else:
            log("[WORKER unknown] " + str(item)[:220])


def store_background_hint(
    state: Dict[str, Any],
    text: str,
    embedding: Any,
    *,
    add_entry: Callable[..., Any],
    save_db: Callable[..., Any],
    write_galaxy_html: Callable[..., Any],
    db_path: str,
    galaxy_path: str = "galaxy.html",
) -> None:
    db = state.get("db", [])
    add_entry(
        db,
        text=text,
        embedding=embedding,
        tags=["background_hint", "gemini_hint", "reasoning_trace"],
    )
    save_db(db_path, db)
    write_galaxy_html(db, galaxy_path)


def status_line(
    state: Dict[str, Any],
    meta: Dict[str, Any],
    gemini,
    *,
    app_name: str,
    load_identity: Callable[[], Dict[str, Any]],
) -> str:
    db = state["db"]
    st = state["internal_state"]
    ident = load_identity()
    return (
        f"{app_name}\n"
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
