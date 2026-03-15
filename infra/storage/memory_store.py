import json
import os
import time
from typing import Any, Dict, List, Optional


def load_db(path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
        return obj if isinstance(obj, list) else []
    except Exception:
        return []


def save_db(path: str, db: List[Dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2)


def _new_id() -> str:
    return str(int(time.time() * 1000))


def add_entry(
    db: List[Dict[str, Any]],
    text: str,
    embedding: List[float],
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    entry = {
        "id": _new_id(),
        "text": text,
        "embedding": embedding,
        "tags": tags or [],
        "ts": time.time(),
    }
    db.append(entry)
    return entry


def compact_db(db: List[Dict[str, Any]], keep_last: int = 5000) -> None:
    # Keep bounded on phone-class hardware.
    if len(db) > keep_last:
        del db[:-keep_last]
