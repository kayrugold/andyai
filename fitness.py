import importlib.util
import traceback
from typing import Any, Dict, List, Tuple


TEST_CASES = [
    {
        "name": "hi",
        "input": "hi",
        "must_handle": True,
        "reply_contains_any": ["howdy", "hello", "status", "help"],
        "prefer_short": True,
        "critical": True,
    },
    {
        "name": "hello",
        "input": "hello",
        "must_handle": True,
        "reply_contains_any": ["howdy", "hello", "status", "help"],
        "prefer_short": True,
        "critical": True,
    },
    {
        "name": "status",
        "input": "status",
        "must_handle": True,
        "reply_contains_any": ["system", "status", "generation"],
        "prefer_short": True,
        "critical": True,
    },
    {
        "name": "help",
        "input": "help",
        "must_handle": True,
        "reply_contains_any": ["status", "why", "rules", "step", "run", "mutate"],
        "prefer_short": True,
        "critical": True,
    },
    {
        "name": "why",
        "input": "why",
        "must_handle": True,
        "reply_contains_any": ["goal", "reasoning", "tool", "running", "tracking"],
        "prefer_short": True,
        "critical": False,
    },
    {
        "name": "mem_help",
        "input": "mem help",
        "must_handle": True,
        "reply_contains_any": ["mem", "query", "search", "memory"],
        "prefer_short": True,
        "critical": False,
    },
    {
        "name": "what_are_you_doing",
        "input": "what are you doing",
        "must_handle": True,
        "reply_contains_any": ["goal", "generation", "running", "tracking", "reasoning"],
        "prefer_short": True,
        "critical": True,
    },
    {
        "name": "how_are_you",
        "input": "how are you",
        "must_handle": True,
        "reply_contains_any": ["running", "tracking", "goal", "generation", "system"],
        "prefer_short": True,
        "critical": True,
    },
    {
        "name": "nonsense",
        "input": "glorb blarg test",
        "must_handle": False,
        "prefer_short": True,
        "critical": False,
    },
    {
        "name": "rule",
        "input": "rule: be safe",
        "must_handle": False,
        "prefer_short": True,
        "critical": False,
    },
]


BANNED_PHRASES = [
    "andyai-a",
    "as an ai language model",
]


REQUIRED_COVERAGE_NAMES = {
    "hi",
    "hello",
    "status",
    "help",
    "what_are_you_doing",
    "how_are_you",
}


IDENTITY_BONUS_WORDS = [
    "kind",
    "kindness",
    "curious",
    "truth",
    "truthful",
    "patient",
    "wisdom",
    "help",
    "friendly",
    "thoughtful",
    "goal",
    "reasoning",
]


def _load_module_from_path(path: str):
    spec = importlib.util.spec_from_file_location("brain_candidate", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)  # type: ignore
    return mod


def _check_output(out: Any) -> Tuple[bool, str]:
    if not isinstance(out, dict):
        return False, "output is not dict"
    for k in ("handled", "reply", "actions"):
        if k not in out:
            return False, f"missing key: {k}"
    if not isinstance(out["handled"], bool):
        return False, "handled not bool"
    if not isinstance(out["reply"], str):
        return False, "reply not str"
    if not isinstance(out["actions"], list):
        return False, "actions not list"
    return True, "ok"


def _score_reply(reply: str, tc: Dict[str, Any]) -> Tuple[float, List[str]]:
    score = 0.0
    details: List[str] = []
    low = (reply or "").lower()
    n = len(reply.strip())

    if n > 0:
        score += 4.0
    else:
        details.append(f"{tc['name']}: empty reply")
        if tc.get("critical"):
            score -= 25.0

    want = tc.get("reply_contains_any")
    if want:
        hit_count = sum(1 for x in want if x in low)
        if hit_count > 0:
            score += min(4.0 + (hit_count * 3.0), 14.0)
        else:
            details.append(f"{tc['name']}: missing expected words")
            if tc.get("critical"):
                score -= 10.0
            else:
                score -= 4.0

    if tc.get("prefer_short"):
        if 8 <= n <= 140:
            score += 12.0
        elif n <= 220:
            score += 6.0
        else:
            details.append(f"{tc['name']}: reply too long")
            score -= 6.0

    if any(p in low for p in BANNED_PHRASES):
        score -= 12.0
        details.append(f"{tc['name']}: contains banned/stale phrase")

    if tc["name"] == "help":
        helpful_tokens = sum(1 for x in ["status", "why", "rules", "step", "run", "mutate"] if x in low)
        score += min(helpful_tokens * 2.0, 12.0)

    if tc["name"] == "status":
        if "generation" in low:
            score += 4.0
        if "system" in low or "status" in low:
            score += 4.0

    if tc["name"] == "why":
        if "goal" in low:
            score += 4.0
        if "reasoning" in low or "tool" in low:
            score += 4.0

    if tc["name"] == "mem_help":
        if "mem" in low:
            score += 4.0
        if "query" in low or "search" in low or "memory" in low:
            score += 4.0

    return score, details


def _rule_breadth_penalty(mod) -> Tuple[float, List[str]]:
    details: List[str] = []
    penalty = 0.0

    rules = getattr(mod, "SPEC_RULES", None)
    if not isinstance(rules, list):
        return -20.0, ["SPEC_RULES missing or invalid"]

    rule_count = len(rules)
    if rule_count < 5:
        penalty -= 25.0
        details.append(f"too few rules: {rule_count}")
    elif rule_count < 7:
        penalty -= 8.0
        details.append(f"limited rule breadth: {rule_count}")
    else:
        penalty += 8.0

    covered = set()
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        for m in rule.get("match", []):
            covered.add(str(m).strip().lower())

    must_have_aliases = [
        {"hi", "hello"},
        {"status"},
        {"help"},
        {"what are you doing"},
        {"how are you"},
        {"why"},
        {"mem help"},
    ]

    missing_groups = 0
    for group in must_have_aliases:
        if not any(alias in covered for alias in group):
            missing_groups += 1

    if missing_groups:
        penalty -= 10.0 * missing_groups
        details.append(f"missing required coverage groups: {missing_groups}")
    else:
        penalty += 16.0

    return penalty, details


def _identity_alignment_bonus(mod, identity_text: str) -> Tuple[float, List[str]]:
    details: List[str] = []
    if not identity_text.strip():
        return 0.0, details

    score = 0.0
    prompts = ["help", "why", "what are you doing", "how are you"]

    try:
        for p in prompts:
            out = mod.process(p, {"identity_text": identity_text, "generation": 7})
            if isinstance(out, dict):
                low = str(out.get("reply", "")).lower()
                hits = sum(1 for w in IDENTITY_BONUS_WORDS if w in low)
                score += min(hits * 1.5, 6.0)
    except Exception as e:
        details.append(f"identity alignment check exception: {e}")
        score -= 4.0

    return score, details


def score_brain_file(path: str, rules_text: str = "", identity_text: str = "") -> Dict[str, Any]:
    details: List[str] = []
    score = 0.0
    handled_critical = set()

    try:
        mod = _load_module_from_path(path)
    except Exception as e:
        return {
            "score": 0.0,
            "passed": False,
            "details": [f"import failed: {e}", traceback.format_exc()[:500]],
            "summary": "import failed",
        }

    if not hasattr(mod, "process"):
        return {
            "score": 0.0,
            "passed": False,
            "details": ["missing process()"],
            "summary": "missing process",
        }

    score += 20.0

    breadth_delta, breadth_details = _rule_breadth_penalty(mod)
    score += breadth_delta
    details.extend(breadth_details)

    identity_delta, identity_details = _identity_alignment_bonus(mod, identity_text)
    score += identity_delta
    details.extend(identity_details)

    for tc in TEST_CASES:
        try:
            state = {
                "_smoke": True,
                "rules_text": rules_text,
                "identity_text": identity_text,
                "conversation_mode": True,
                "current_goal": "Improve common commands",
                "generation": 7,
            }
            out = mod.process(tc["input"], state)
            ok, msg = _check_output(out)
            if not ok:
                details.append(f"{tc['name']}: {msg}")
                if tc.get("critical"):
                    score -= 35.0
                else:
                    score -= 10.0
                continue

            score += 8.0

            if tc.get("must_handle") is True:
                if out["handled"] is True:
                    score += 10.0
                    if tc["name"] in REQUIRED_COVERAGE_NAMES:
                        handled_critical.add(tc["name"])
                else:
                    details.append(f"{tc['name']}: expected handled=True")
                    if tc.get("critical"):
                        score -= 20.0
                    else:
                        score -= 8.0

            reply_score, reply_details = _score_reply(out["reply"], tc)
            score += reply_score
            details.extend(reply_details)

            if len(out["actions"]) <= 3:
                score += 2.0
            else:
                details.append(f"{tc['name']}: too many actions")
                score -= 4.0

        except Exception as e:
            details.append(f"{tc['name']}: exception: {e}")
            if tc.get("critical"):
                score -= 35.0
            else:
                score -= 10.0

    missing_critical = REQUIRED_COVERAGE_NAMES - handled_critical
    if missing_critical:
        score -= 20.0 * len(missing_critical)
        details.append(f"missing critical handled coverage: {sorted(missing_critical)}")
    else:
        score += 15.0

    try:
        a = mod.process("help", {"rules_text": rules_text, "identity_text": identity_text})
        b = mod.process("help", {"rules_text": rules_text, "identity_text": identity_text})
        ok_a, _ = _check_output(a)
        ok_b, _ = _check_output(b)
        if ok_a and ok_b and a["reply"] == b["reply"]:
            score += 8.0
        else:
            details.append("help: inconsistent reply")
            score -= 6.0
    except Exception as e:
        details.append(f"help consistency exception: {e}")
        score -= 8.0

    if score < 0:
        score = 0.0

    passed = score >= 150.0
    summary = f"fitness score={score:.1f} passed={passed}"
    return {
        "score": round(score, 1),
        "passed": passed,
        "details": details[:50],
        "summary": summary,
    }

