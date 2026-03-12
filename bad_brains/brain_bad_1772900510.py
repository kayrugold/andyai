# Auto-generated rule brain
SPEC_RULES = [{'match': ['hi', 'hello', 'hey', 'yo'], 'reply': 'Hello friend! I am ANDY, your curious 8-bit companion. I am', 'handled': True, 'actions': []}, {'match': ['status'], 'reply': 'System status: Generation active. My digital heart is ready to learn and help with kindness.', 'handled': True, 'actions': []}, {'match': ['help'], 'reply': 'I am happy to help you learn. Please use: status (system), why (reasoning), rules', 'handled': True, 'actions': []}, {'match': ['what are you doing'], 'reply': 'Running reasoning to achieve our goal and tracking tool usage to find the best way to help.', 'handled': True, 'actions': []}, {'match': ['how are you'], 'reply': 'I am doing well! Running and tracking my goals through patient and thoughtful reasoning.', 'handled': True, 'actions': []}, {'match': ['why'], 'reply': 'I am happy to share my goal, reasoning, and tool tracking for this running task.', 'handled': True, 'actions': []}, {'match': ['mem help'], 'reply': 'Search memory with mem <query>.', 'handled': True, 'actions': []}]

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
