# Auto-generated rule brain
SPEC_RULES = [{'match': ['hi', 'hello', 'hey', 'yo'], 'reply': 'Hello. Use status or help.', 'handled': True, 'actions': []}, {'match': ['status'], 'reply': 'System status: generation active.', 'handled': True, 'actions': []}, {'match': ['help'], 'reply': 'Available: status, why (reasoning), rules, step, run, or mutate common-', 'handled': True, 'actions': []}, {'match': ['what are you doing'], 'reply': 'Running generation and tracking goals.', 'handled': True, 'actions': []}, {'match': ['how are you'], 'reply': 'System running; tracking generation.', 'handled': True, 'actions': []}, {'match': ['why'], 'reply': 'Tracking goal, reasoning, and tool use.', 'handled': True, 'actions': []}, {'match': ['mem help'], 'reply': 'Search memory with mem <query>', 'handled': True, 'actions': []}]

def _safe_reply(handled, reply, actions=None):
    if actions is None:
        actions = []
    return {
        "handled": bool(handled),
        "reply": str(reply),
        "actions": list(actions) if isinstance(actions, list) else []
    }

def _matches(t, patterns):
    for p in patterns:
        if t == p:
            return True
    return False

def process(text, state):
    t = (text or "").strip().lower()
    state = state if isinstance(state, dict) else {}

    for rule in SPEC_RULES:
        if _matches(t, rule.get("match", [])):
            return _safe_reply(
                rule.get("handled", True),
                rule.get("reply", ""),
                rule.get("actions", [])
            )

    return _safe_reply(False, "", [])
