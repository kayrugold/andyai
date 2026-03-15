from __future__ import annotations

import importlib.util
import json
import os
import time
from typing import Any, Callable, Dict, List


def now_ts() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def log(line: str, *, now_ts: Callable[[], str], log_file: str) -> None:
    line = f"[{now_ts()}] {line}"
    print(line)
    try:
        with open(log_file, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except Exception:
        pass


def load_json(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return default


def save_json(path: str, obj: Any) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(obj, handle, indent=2)


def load_rules(rules_path: str, *, load_json: Callable[[str, Any], Any]) -> List[Dict[str, Any]]:
    obj = load_json(rules_path, [])
    return obj if isinstance(obj, list) else []


def add_rule(
    text: str,
    *,
    rules_path: str,
    now_ts: Callable[[], str],
    load_rules: Callable[[], List[Dict[str, Any]]],
    save_json: Callable[[str, Any], None],
    kind: str = "user_rule",
) -> None:
    rules = load_rules()
    rules.append({"type": kind, "text": text, "ts": now_ts()})
    save_json(rules_path, rules)


def rules_as_text(load_rules: Callable[[], List[Dict[str, Any]]], max_items: int = 25) -> str:
    rules = load_rules()[-max_items:]
    if not rules:
        return "- (none)"
    return "\n".join(f"- [{rule.get('type', 'rule')}] {rule.get('text', '')}" for rule in rules)


def load_identity(identity_path: str, *, load_json: Callable[[str, Any], Any]) -> Dict[str, Any]:
    obj = load_json(identity_path, {})
    return obj if isinstance(obj, dict) else {}


def identity_text(load_identity: Callable[[], Dict[str, Any]]) -> str:
    ident = load_identity()
    if not ident:
        return ""
    parts = []
    for key in ["name", "self_description", "purpose", "growth_notes", "self_reflection"]:
        val = ident.get(key)
        if isinstance(val, str) and val.strip():
            parts.append(f"{key}: {val.strip()}")
    for key in ["personality", "core_traits"]:
        val = ident.get(key)
        if isinstance(val, list) and val:
            parts.append(f"{key}: {', '.join(str(item) for item in val)}")
    return "\n".join(parts)


def load_meta(meta_path: str, *, load_json: Callable[[str, Any], Any], now_ts: Callable[[], str]) -> Dict[str, Any]:
    meta = load_json(meta_path, {})
    if not isinstance(meta, dict):
        meta = {}
    meta.setdefault("generation", 0)
    meta.setdefault("last_goal", "")
    meta.setdefault("last_insight", "")
    meta.setdefault("started_at", now_ts())
    return meta


def save_meta(meta: Dict[str, Any], *, meta_path: str, save_json: Callable[[str, Any], None]) -> None:
    save_json(meta_path, meta)


def build_registry(
    state: Dict[str, Any],
    *,
    tool_registry_factory,
    tool_calc,
    tool_time,
    tool_read_json,
    tool_write_json,
    tool_memory_search_factory,
    tool_memory_add_factory,
):
    registry = tool_registry_factory()
    registry.register("calc", tool_calc)
    registry.register("time", tool_time)
    registry.register("read_json", tool_read_json)
    registry.register("write_json", tool_write_json)
    registry.register("memory_search", tool_memory_search_factory(state))
    registry.register("memory_add", tool_memory_add_factory(state))
    return registry


def run_brain(text: str, state: Dict[str, Any], *, brain_file: str) -> Dict[str, Any]:
    spec = importlib.util.spec_from_file_location("brain_evolved", brain_file)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)  # type: ignore
    return module.process(text, state)  # type: ignore
