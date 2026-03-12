# Auto-generated rule brain
SPEC_RULES = [{'match': ['hi', 'hello', 'hey', 'yo'], 'reply': 'Hello! How can I help you? Try typing status or help to get started.', 'handled': True, 'actions': []}, {'match': ['status'], 'reply': 'System operational. All modules online and standing by for instructions.', 'handled': True, 'actions': []}, {'match': ['help'], 'reply': 'Available commands: status (state), why (reasoning), rules (constraints), step/run', 'handled': True, 'actions': []}, {'match': ['what are you doing'], 'reply': "I'm running generation work and tracking self-improvement.", 'handled': True, 'actions': []}, {'match': ['how are you'], 'reply': "I'm running generation work and tracking self-improvement.", 'handled': True, 'actions': []}]

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
