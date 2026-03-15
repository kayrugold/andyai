import importlib.util
import traceback
from typing import Any, Dict, List, Tuple


TEST_CASES = [
    {"name": "hi", "input": "hi", "must_handle": True, "reply_contains_any": ["howdy", "hello", "status", "help"], "prefer_short": True, "critical": True},
    {"name": "hello", "input": "hello", "must_handle": True, "reply_contains_any": ["howdy", "hello", "status", "help"], "prefer_short": True, "critical": True},
    {"name": "status", "input": "status", "must_handle": True, "reply_contains_any": ["system", "status", "generation"], "prefer_short": True, "critical": True},
    {"name": "help", "input": "help", "must_handle": True, "reply_contains_any": ["status", "why", "rules", "step", "run", "mutate"], "prefer_short": True, "critical": True},
    {"name": "why", "input": "why", "must_handle": True, "reply_contains_any": ["goal", "reasoning", "tool", "running", "tracking"], "prefer_short": True, "critical": False},
    {"name": "mem_help", "input": "mem help", "must_handle": True, "reply_contains_any": ["mem", "query", "search", "memory"], "prefer_short": True, "critical": False},
    {"name": "what_are_you_doing", "input": "what are you doing", "must_handle": True, "reply_contains_any": ["goal", "generation", "running", "tracking", "reasoning"], "prefer_short": True, "critical": True},
    {"name": "how_are_you", "input": "how are you", "must_handle": True, "reply_contains_any": ["running", "tracking", "goal", "generation", "system"], "prefer_short": True, "critical": True},
    {"name": "nonsense", "input": "glorb blarg test", "must_handle": False, "prefer_short": True, "critical": False},
    {"name": "rule", "input": "rule: be safe", "must_handle": False, "prefer_short": True, "critical": False},
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

    return penalty, details


def score_brain_file(path: str) -> Tuple[float, Dict[str, Any], List[str]]:
    notes: List[str] = []
    details: Dict[str, Any] = {"cases": []}
    score = 0.0

    try:
        mod = _load_module_from_path(path)
    except Exception:
        return 0.0, {"error": traceback.format_exc()}, ["failed to import candidate"]

    penalty, penalty_notes = _rule_breadth_penalty(mod)
    score += penalty
    notes.extend(penalty_notes)

    handle = getattr(mod, "handle_input", None)
    if not callable(handle):
        return 0.0, {"error": "missing handle_input"}, ["candidate missing handle_input"]

    coverage = set()
    for tc in TEST_CASES:
        try:
            out = handle(tc["input"], {})
        except Exception:
            notes.append(f"{tc['name']}: exception during handling")
            details["cases"].append({"name": tc["name"], "score": -20.0})
            score -= 20.0
            continue

        ok, msg = _check_output(out)
        if not ok:
            notes.append(f"{tc['name']}: invalid output ({msg})")
            details["cases"].append({"name": tc["name"], "score": -20.0})
            score -= 20.0
            continue

        if out["handled"]:
            coverage.add(tc["name"])

        case_score = 0.0
        if tc["must_handle"] and not out["handled"]:
            case_score -= 18.0 if tc.get("critical") else -8.0
            notes.append(f"{tc['name']}: should handle but did not")
        elif (not tc["must_handle"]) and out["handled"]:
            case_score -= 2.0

        reply_score, reply_notes = _score_reply(out["reply"], tc)
        case_score += reply_score
        notes.extend(reply_notes)
        details["cases"].append({"name": tc["name"], "score": round(case_score, 2)})
        score += case_score

    missing_critical = REQUIRED_COVERAGE_NAMES - coverage
    if missing_critical:
        score -= 20.0
        notes.append(f"missing critical coverage: {sorted(missing_critical)}")

    ident_bonus = 0.0
    joined_notes = " ".join(notes).lower()
    for word in IDENTITY_BONUS_WORDS:
        if word in joined_notes:
            ident_bonus += 0.5
    score += min(ident_bonus, 5.0)

    details["coverage"] = sorted(coverage)
    details["final_score"] = round(score, 2)
    return round(score, 2), details, notes
