from typing import Any, Dict, List, Optional

from plugins.mentors.gemini import GeminiClient


def create_plan(
    goal: str,
    context: List[Dict[str, Any]],
    tools: List[str],
    gemini: Optional[GeminiClient] = None,
) -> List[Dict[str, Any]]:
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

    try:
        import json

        obj = json.loads(txt)
        if isinstance(obj, list) and obj:
            out = []
            for item in obj[:3]:
                if isinstance(item, dict) and "step" in item:
                    out.append({"step": str(item["step"])})
            return out or base[:2]
    except Exception:
        pass

    return base[:2]
