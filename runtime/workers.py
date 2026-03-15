import time


def gemini_worker(task):
    state = task["state"]
    gemini = task["gemini"]
    prompt = task["prompt"]

    state["worker_results"].append({
        "type": "gemini_debug",
        "message": f"gemini worker received task | prompt={str(prompt)[:120]}",
    })

    try:
        state["worker_results"].append({
            "type": "gemini_debug",
            "message": "gemini worker starting request",
        })

        result = gemini.generate_text(prompt)

        state["worker_results"].append({
            "type": "gemini",
            "result": result,
        })

        state["worker_results"].append({
            "type": "gemini_debug",
            "message": "gemini worker completed request",
        })

    except Exception as e:
        state["worker_results"].append({
            "type": "gemini_error",
            "error": repr(e),
        })

        state["worker_results"].append({
            "type": "gemini_debug",
            "message": "gemini worker hit exception",
        })


def reasoning_worker(task):
    state = task["state"]
    goal = task["goal"]

    thought = f"background reasoning about goal: {goal}"

    time.sleep(1)

    state["worker_results"].append({
        "type": "reasoning",
        "thought": thought,
    })


def diagnostics_worker(task):
    state = task["state"]

    diag = {
        "memory_entries": len(state.get("db", [])),
        "timestamp": time.time(),
    }

    state["worker_results"].append({
        "type": "diagnostic",
        "data": diag,
    })
