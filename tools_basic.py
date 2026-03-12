import time
import json
from typing import Any, Dict

def tool_calc(inp: Dict[str, Any]) -> Dict[str, Any]:
    expr = str(inp.get("expr", "")).strip()
    if not expr:
        return {"ok": False, "error": "missing expr"}
    allowed = set("0123456789+-*/(). %")
    if any(c not in allowed for c in expr):
        return {"ok": False, "error": "invalid characters"}
    try:
        val = eval(expr, {"__builtins__": {}}, {})
        return {"ok": True, "expr": expr, "value": val}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def tool_time(inp: Dict[str, Any]) -> Dict[str, Any]:
    return {"ok": True, "epoch": time.time(), "local": time.strftime("%Y-%m-%d %H:%M:%S")}

def tool_read_json(inp: Dict[str, Any]) -> Dict[str, Any]:
    path = str(inp.get("path", "")).strip()
    if not path:
        return {"ok": False, "error": "missing path"}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return {"ok": True, "data": json.load(f)}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def tool_write_json(inp: Dict[str, Any]) -> Dict[str, Any]:
    path = str(inp.get("path", "")).strip()
    data = inp.get("data", None)
    if not path:
        return {"ok": False, "error": "missing path"}
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return {"ok": True, "path": path}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def tool_memory_search_factory(state: Dict[str, Any]):
    from recall import top_k
    def tool(inp: Dict[str, Any]) -> Dict[str, Any]:
        q = str(inp.get("q", "")).strip()
        k = int(inp.get("k", 6))
        emb = state["embedder"].embed(q)
        hits = top_k(state["db"], emb, k=k)
        return {
            "ok": True,
            "q": q,
            "hits": [{"score": float(s), "id": e.get("id"), "text": e.get("text","")[:240], "tags": e.get("tags", [])} for s, e in hits]
        }
    return tool

def tool_memory_add_factory(state: Dict[str, Any]):
    from memory_store import add_entry
    def tool(inp: Dict[str, Any]) -> Dict[str, Any]:
        text = str(inp.get("text", "")).strip()
        tags = inp.get("tags", [])
        if not text:
            return {"ok": False, "error": "missing text"}
        e = add_entry(state["db"], text=text, embedding=state["embedder"].embed(text), tags=tags if isinstance(tags, list) else [])
        return {"ok": True, "id": e.get("id")}
    return tool