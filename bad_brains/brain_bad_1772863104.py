# Auto-generated rule brain
SPEC_RULES = [{'match': ['hi', 'hello', 'hey', 'yo'], 'reply': 'Hello. Try status or help.', 'handled': True, 'actions': []}, {'match': ['status'], 'reply': 'Active. Processing.', 'handled': True, 'actions': []}, {'match': ['help'], 'reply': 'status, why, rules, step, run, mutate', 'handled': True, 'actions': []}, {'match': ['what are you doing'], 'reply': 'Processing and improving.', 'handled': True, 'actions': []}, {'match': ['how are you'], 'reply': 'Doing well, thank you.', 'handled': True, 'actions': []}]

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
