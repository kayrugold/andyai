# Auto-generated rule brain
SPEC_RULES = [{'match': ['hi', 'hello', 'hey', 'yo'], 'reply': 'Hello! I am ANDY. I am ready to learn and help. You can check', 'handled': True, 'actions': []}, {'match': ['status'], 'reply': 'System status: Generation active. I am ready to learn and help you!', 'handled': True, 'actions': []}, {'match': ['help'], 'reply': 'I am ANDY! You can check my system status, use why to see my reasoning, view my', 'handled': True, 'actions': []}, {'match': ['what are you doing'], 'reply': 'Running reasoning to achieve the goal and tracking tool usage.', 'handled': True, 'actions': []}, {'match': ['how are you'], 'reply': 'Running and tracking goals through active reasoning.', 'handled': True, 'actions': []}, {'match': ['why'], 'reply': 'Displaying current goal, reasoning, and tool tracking for the running task.', 'handled': True, 'actions': []}, {'match': ['mem help'], 'reply': 'Search memory with mem <query>.', 'handled': True, 'actions': []}]

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
