from typing import Any, Dict, List, Optional
from llm_gemini import GeminiClient

def think(step_obj: Dict[str, Any], context: List[Dict[str, Any]], tools: List[str], gemini: Optional[GeminiClient] = None) -> Dict[str, Any]:
    step = str(step_obj.get("step", "")).strip()

    # Simple offline heuristic
    low = step.lower()
    if "search memory" in low or "memory" in low:
        return {"tool": "memory_search", "input": {"q": step, "k": 6}, "explain": "step mentions memory; search memory"}
    if "time" in low:
        return {"tool": "time", "input": {}, "explain": "step mentions time"}
    if "calc" in low or "calculate" in low:
        return {"tool": "calc", "input": {"expr": "1+1"}, "explain": "placeholder calc; adjust input if needed"}

    if not (gemini and gemini.available()):
        return {"tool": "none", "input": {}, "explain": "offline fallback; no tool chosen"}

    prompt = (
        "Choose ONE tool for this step or 'none'. Return JSON:\n"
        "{'tool': 'name|none', 'input': {...}, 'explain': 'short'}\n"
        f"TOOLS: {tools}\n"
        f"STEP: {step}\n"
        "No markdown."
    )
    txt = gemini.generate_text(prompt).strip()

    try:
        import json
        obj = json.loads(txt)
        if isinstance(obj, dict) and "tool" in obj:
            tool = str(obj.get("tool", "none"))
            if tool != "none" and tool not in tools:
                tool = "none"
            inp = obj.get("input", {})
            if not isinstance(inp, dict):
                inp = {}
            return {"tool": tool, "input": inp, "explain": str(obj.get("explain","")).strip()}
    except Exception:
        pass

    return {"tool": "none", "input": {}, "explain": "parse failed; no tool chosen"}