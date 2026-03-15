from pathlib import Path
import json
import time

SENTENCE_MEMORY_FILE = "sentence_memory.json"


def load_sentence_memory():
    p = Path(SENTENCE_MEMORY_FILE)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []


def save_sentence_memory(items):
    Path(SENTENCE_MEMORY_FILE).write_text(
        json.dumps(items, indent=2),
        encoding="utf-8"
    )


def remember_sentence(text, source="manual", tags=None):
    text = str(text).strip()
    if not text:
        return None

    tags = list(tags or [])
    items = load_sentence_memory()

    entry = {
        "id": int(time.time() * 1000),
        "text": text,
        "source": source,
        "tags": tags,
        "ts": int(time.time()),
    }

    if not any(str(x.get("text", "")).strip().lower() == text.lower() for x in items):
        items.append(entry)
        items = items[-200:]
        save_sentence_memory(items)

    return entry


def sentence_memories_text(limit=20):
    items = load_sentence_memory()[-limit:]

    lines = ["SENTENCE MEMORIES", ""]
    if not items:
        lines.append("No sentence memories yet.")
        return "\n".join(lines)

    for i, item in enumerate(items, start=1):
        tags = ", ".join(item.get("tags", []))
        src = item.get("source", "")
        text = item.get("text", "")
        if tags:
            lines.append(f"{i:02d}. [{src}] ({tags}) {text}")
        else:
            lines.append(f"{i:02d}. [{src}] {text}")

    return "\n".join(lines)


def build_dream_seed():
    items = load_sentence_memory()
    recent = items[-5:]

    lines = ["DREAM SEED", ""]

    if not recent:
        lines.append("No sentence memories available.")
        return "\n".join(lines)

    lines.append("Recent fragments:")
    for item in recent:
        lines.append(f"- {item.get('text', '')}")

    lines.extend([
        "",
        "Reflection:",
        "These recent language fragments may be replayed during idle consolidation.",
        "Possible dream mode: recombine sentence patterns, art concepts, and identity notes.",
    ])

    return "\n".join(lines)
