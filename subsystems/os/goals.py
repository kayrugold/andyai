import random
from typing import Any, Dict, List, Optional

from plugins.mentors.gemini import GeminiClient


DEFAULT_GOALS = [
    "Improve tool selection accuracy.",
    "Detect repeated failures and create a new rule to avoid them.",
    "Increase memory usefulness by summarizing recent insights.",
    "Write a safer reflex brain behavior for common commands.",
    "Improve concise replies for common commands.",
    "Improve local conversation behavior for simple status questions.",
]

ALLOWED_GOAL_KEYWORDS = [
    "tool selection",
    "repeated failures",
    "new rule",
    "memory usefulness",
    "summarizing recent insights",
    "safer reflex brain",
    "common commands",
    "concise replies",
    "local conversation",
    "status questions",
]


def _sanitize_goal(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return random.choice(DEFAULT_GOALS)

    low = text.lower()
    if any(keyword in low for keyword in ALLOWED_GOAL_KEYWORDS):
        text = " ".join(text.split())
        if not text.endswith("."):
            text += "."
        return text

    return random.choice(DEFAULT_GOALS)


def generate_goal(
    db: List[Dict[str, Any]],
    goals_path: str,
    gemini: Optional[GeminiClient] = None,
) -> str:
    goals = None
    try:
        import json
        import os

        if os.path.exists(goals_path):
            goals = json.load(open(goals_path, "r", encoding="utf-8"))
    except Exception:
        goals = None

    if isinstance(goals, list) and goals:
        safe_goals = [str(goal) for goal in goals if isinstance(goal, str)]
        safe_goals = [_sanitize_goal(goal) for goal in safe_goals]
        return random.choice(safe_goals) if safe_goals else random.choice(DEFAULT_GOALS)

    if gemini and gemini.available() and random.random() < 0.35:
        prompt = (
            "Propose ONE short goal for a self-improving tool-using agent.\n"
            "IMPORTANT: the goal must stay in one of these lanes only:\n"
            "- improve tool selection accuracy\n"
            "- detect repeated failures and create a rule\n"
            "- improve memory usefulness\n"
            "- improve safer reflex brain behavior for common commands\n"
            "- improve concise replies\n"
            "- improve local conversation behavior for status/help/common command handling\n"
            "The goal must be measurable within 1-3 steps.\n"
            "Return only the goal sentence.\n"
        )
        goal = gemini.generate_text(prompt).strip()
        return _sanitize_goal(goal)

    return random.choice(DEFAULT_GOALS)
