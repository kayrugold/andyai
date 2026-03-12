from typing import Any, Dict, List, Optional
from llm_gemini import GeminiClient

def create_plan(goal: str, context: List[Dict[str, Any]], tools: List[str], gemini: Optional[GeminiClient] = None) -> List[Dict[str, Any]]:
    # Offline basic plan
    base = [
        {"step": f"Search memory for relevant past attempts about: {goal}"},
        {"step": f"Use a tool if needed to progress goal: {goal}"},
        {"step": f"Summarize what worked and what failed for: {goal}"},
    ]

    if not (gemini and gemini.available()):
        return base[:2]

    prompt = (
        "Create a compact plan (1-3 steps) for this agent goal.\n"
        f"GOAL: {goal}\n"
        f"TOOLS: {tools}\n"
        "Return JSON list of objects: [{'step': '...'}]\n"
        "No markdown."
    )
    txt = gemini.generate_text(prompt).strip()

    # best effort parse
    try:
        import json
        obj = json.loads(txt)
        if isinstance(obj, list) and obj:
            out = []
            for x in obj[:3]:
                if isinstance(x, dict) and "step" in x:
                    out.append({"step": str(x["step"])})
            return out or base[:2]
    except Exception:
        pass

    return base[:2]