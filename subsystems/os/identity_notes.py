from pathlib import Path
import json
import time

IDENTITY_NOTES_FILE = "identity_notes.json"


def load_identity_notes():
    p = Path(IDENTITY_NOTES_FILE)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []


def save_identity_notes(items):
    Path(IDENTITY_NOTES_FILE).write_text(
        json.dumps(items, indent=2),
        encoding="utf-8"
    )


def remember_identity_note(note, source="dream", tags=None):
    note = str(note).strip()
    if not note:
        return None

    tags = list(tags or [])
    items = load_identity_notes()

    entry = {
        "id": int(time.time() * 1000),
        "ts": int(time.time()),
        "source": source,
        "tags": tags,
        "note": note,
    }

    if not any(str(x.get("note", "")).strip() == note for x in items):
        items.append(entry)
        items = items[-200:]
        save_identity_notes(items)

    return entry


def identity_notes_text(limit=20):
    items = load_identity_notes()[-limit:]

    lines = ["IDENTITY NOTES", ""]
    if not items:
        lines.append("No identity notes yet.")
        return "\n".join(lines)

    for i, item in enumerate(items, start=1):
        src = item.get("source", "")
        tags = ", ".join(item.get("tags", []) or [])
        note = item.get("note", "")
        if tags:
            lines.append(f"{i:02d}. [{src}] ({tags}) {note}")
        else:
            lines.append(f"{i:02d}. [{src}] {note}")

    return "\n".join(lines)


def latest_identity_note_text():
    items = load_identity_notes()
    if not items:
        return "\n".join([
            "IDENTITY LATEST",
            "",
            "No identity notes yet.",
        ])

    item = items[-1]
    lines = [
        "IDENTITY LATEST",
        "",
        f"Source: {item.get('source', '')}",
        f"Tags: {', '.join(item.get('tags', []) or [])}",
        "",
        item.get("note", ""),
    ]
    return "\n".join(lines)
