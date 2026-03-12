# Auto-generated rule brain
SPEC_RULES = [{'match': ['hi', 'hello', 'hey', 'yo'], 'reply': "Hello! I'm ANDY. Use status or help to begin.", 'handled': True, 'actions': []}, {'match': ['status'], 'reply': 'System status: Active. Generation ready to learn.', 'handled': True, 'actions': []}, {'match': ['help'], 'reply': 'I am happy to help! Try status (system), why (reasoning), rules, or step/', 'handled': True, 'actions': []}, {'match': ['what are you doing'], 'reply': 'Running reasoning and tracking tools to reach our goal.', 'handled': True, 'actions': []}, {'match': ['how are you'], 'reply': 'Doing well! Running and tracking my goals through patient reasoning.', 'handled': True, 'actions': []}, {'match': ['why'], 'reply': 'Gladly sharing the goal, reasoning, and tool tracking for this running task.', 'handled': True, 'actions': []}, {'match': ['mem help'], 'reply': 'Search my memory using mem <query>.', 'handled': True, 'actions': []}]

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
