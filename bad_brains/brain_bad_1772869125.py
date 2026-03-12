# Auto-generated rule brain
SPEC_RULES = [{'match': ['hi', 'hello', 'hey', 'yo'], 'reply': 'Hello. Check system status or type help for commands.', 'handled': True, 'actions': []}, {'match': ['status'], 'reply': 'System status: Active. Generation in progress.', 'handled': True, 'actions': []}, {'match': ['help'], 'reply': 'Try status for system state, why for reasoning, rules, step, run for running, or mutate common', 'handled': True, 'actions': []}, {'match': ['what are you doing'], 'reply': "I'm running generation work and tracking self-improvement.", 'handled': True, 'actions': []}, {'match': ['how are you'], 'reply': "I'm running generation work and tracking self-improvement.", 'handled': True, 'actions': []}, {'match': ['why'], 'reply': 'I can explain my current goal, recent reasoning, and latest tool use. Try why or status.', 'handled': True, 'actions': []}, {'match': ['mem help'], 'reply': 'Use mem <query> to search stored memory entries for similar past context.', 'handled': True, 'actions': []}]

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
