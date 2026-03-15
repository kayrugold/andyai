from typing import Any, Dict, Optional

from plugins.mentors.gemini import GeminiClient


ALLOWED_BRAIN_TOPICS = [
    "common command",
    "command handling",
    "reflex",
    "reply",
    "replies",
    "concise",
    "conversation",
    "local conversation",
    "status",
    "help",
    "hi",
    "hello",
]


def _allowed_brain_request(content: Any) -> bool:
    text = str(content or "").strip().lower()
    if not text:
        return False
    return any(key in text for key in ALLOWED_BRAIN_TOPICS)


def reflect(
    goal: str,
    step: str,
    tool: str,
    result: Any,
    rules_text: str = "",
    gemini: Optional[GeminiClient] = None,
) -> Dict[str, Any]:
    base = {
        "text": f"Goal='{goal}' | Step='{step}' | Tool='{tool}' | Result='{str(result)[:200]}' | Takeaway: log outcome and adjust next run.",
        "tags": ["insight"],
        "learning": {"type": "none", "content": None, "confidence": 0.0},
    }

    if not (gemini and gemini.available()):
        return base

    prompt = (
        "You are the REFLECTOR for a self-rewriting agent.\n"
        "Produce ONE compact insight and optionally ONE learning.\n\n"
        "IMPORTANT:\n"
        "- Brain evolution is allowed only when it improves common command handling, concise replies, or local conversation behavior.\n"
        "- If proposing brain evolution: propose ONLY ONE SHORT change request.\n"
        "- Include a confidence score from 0.0 to 1.0.\n"
        "- If confidence < 0.90, set learning.type = 'none'.\n"
        "- Follow the rules/policy below.\n\n"
        f"RULES/POLICY:\n{rules_text}\n\n"
        "Return STRICT JSON only. No markdown.\n"
        "Schema:\n"
        "{\n"
        "  \"text\": \"...\",\n"
        "  \"tags\": [\"...\"],\n"
        "  \"learning\": {\"type\": \"none|rule|brain\", \"content\": ..., \"confidence\": 0.0}\n"
        "}\n\n"
        f"GOAL: {goal}\n"
        f"STEP: {step}\n"
        f"TOOL: {tool}\n"
        f"RESULT: {str(result)[:1200]}\n"
    )

    txt = gemini.generate_text(prompt).strip()
    try:
        import json

        obj = json.loads(txt)
        if not isinstance(obj, dict) or "text" not in obj:
            return base

        if "tags" not in obj or not isinstance(obj["tags"], list):
            obj["tags"] = ["insight"]

        learning = obj.get("learning", {})
        if not isinstance(learning, dict):
            obj["learning"] = {"type": "none", "content": None, "confidence": 0.0}
            return obj

        learning.setdefault("type", "none")
        learning.setdefault("content", None)
        try:
            learning["confidence"] = float(learning.get("confidence", 0.0))
        except Exception:
            learning["confidence"] = 0.0

        if learning["confidence"] < 0.90:
            learning["type"] = "none"
            learning["content"] = None

        if learning.get("type") == "brain" and not _allowed_brain_request(learning.get("content")):
            learning["type"] = "none"
            learning["content"] = None
            learning["confidence"] = 0.0

        obj["learning"] = learning
        return obj

    except Exception:
        return base
