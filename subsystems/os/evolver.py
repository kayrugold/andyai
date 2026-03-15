import os
import time
import json
import shutil
import importlib.util
from typing import List, Dict, Tuple

from subsystems.os.fitness import score_brain_file

SCORES_PATH = "brain_scores.json"
IDENTITY_PATH = "identity.json"
IDENTITY_BACKUP_DIR = "identity_backups"


def load_scores():
    if not os.path.exists(SCORES_PATH):
        return {"champion_score": 0.0, "history": [], "champion_file": ""}
    with open(SCORES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_scores(scores):
    with open(SCORES_PATH, "w", encoding="utf-8") as f:
        json.dump(scores, f, indent=2)


def load_identity() -> Dict:
    if not os.path.exists(IDENTITY_PATH):
        return {}
    try:
        with open(IDENTITY_PATH, "r", encoding="utf-8") as f:
            obj = json.load(f)
            return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def save_identity(identity: Dict) -> None:
    with open(IDENTITY_PATH, "w", encoding="utf-8") as f:
        json.dump(identity, f, indent=2)


def backup_identity() -> str:
    os.makedirs(IDENTITY_BACKUP_DIR, exist_ok=True)
    ts = int(time.time())
    path = os.path.join(IDENTITY_BACKUP_DIR, f"identity_{ts}.json")
    if os.path.exists(IDENTITY_PATH):
        shutil.copy(IDENTITY_PATH, path)
    return path


def identity_text() -> str:
    ident = load_identity()
    if not ident:
        return ""
    parts = []
    for key in ["name", "self_description", "purpose", "growth_notes", "self_reflection"]:
        val = ident.get(key)
        if isinstance(val, str) and val.strip():
            parts.append(f"{key}: {val.strip()}")
    for key in ["personality", "core_traits"]:
        val = ident.get(key)
        if isinstance(val, list) and val:
            parts.append(f"{key}: {', '.join(str(x) for x in val)}")
    return "\n".join(parts)


def _load_module_from_path(path: str):
    spec = importlib.util.spec_from_file_location("brain_module", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)  # type: ignore
    return mod


def load_brain_rules(path="brain_evolved.py") -> List[Dict]:
    try:
        mod = _load_module_from_path(path)
        rules = getattr(mod, "SPEC_RULES", [])
        if isinstance(rules, list):
            out = []
            for r in rules:
                if not isinstance(r, dict):
                    continue
                out.append({
                    "match": [str(x).strip().lower() for x in r.get("match", []) if str(x).strip()],
                    "reply": str(r.get("reply", "")).strip()[:240],
                    "handled": bool(r.get("handled", True)),
                    "actions": [str(x) for x in r.get("actions", [])[:5]] if isinstance(r.get("actions", []), list) else [],
                })
            return out
    except Exception:
        pass
    return []


def save_brain_rules(rules: List[Dict], path="brain_evolved.py"):
    src = f"""# Auto-generated rule brain
SPEC_RULES = {repr(rules)}

def _safe_reply(handled, reply, actions=None):
    if actions is None:
        actions = []
    return {{
        "handled": bool(handled),
        "reply": str(reply),
        "actions": list(actions) if isinstance(actions, list) else []
    }}

def _matches(t, patterns):
    for p in patterns:
        if t == p:
            return True
    return False

def process(text, state):
    t = (text or "").strip().lower()
    state = state if isinstance(state, dict) else {{}}

    for rule in SPEC_RULES:
        if _matches(t, rule.get("match", [])):
            return _safe_reply(
                rule.get("handled", True),
                rule.get("reply", ""),
                rule.get("actions", [])
            )

    return _safe_reply(False, "", [])
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(src)


def seed_current_brain(brain_file: str = "brain_evolved.py", rules_text: str = "") -> Tuple[float, str]:
    scores = load_scores()
    current_score = float(scores.get("champion_score", 0.0) or 0.0)
    champ = str(scores.get("champion_file", "") or "")
    cwd = os.path.abspath(os.getcwd())

    if current_score > 0.0 and champ.startswith(cwd):
        return current_score, f"existing champion preserved: {current_score:.1f}"

    if not os.path.exists(brain_file):
        return 0.0, "no active brain to seed"

    fit = score_brain_file(os.path.abspath(brain_file), rules_text=rules_text, identity_text=identity_text())
    score = float(fit.get("score", 0.0) or 0.0)

    scores["champion_score"] = score
    scores["champion_file"] = os.path.abspath(brain_file)
    scores["history"] = [{
        "ts": int(time.time()),
        "candidate": os.path.abspath(brain_file),
        "score": score,
        "passed": bool(fit.get("passed", False)),
        "summary": "seed_current_brain",
        "details": fit.get("details", []),
    }]
    save_scores(scores)

    return score, f"seeded champion from current brain: {score:.1f}"


def behavior_diff(old_path: str, new_path: str) -> Dict:
    prompts = [
        "hi",
        "status",
        "help",
        "why",
        "mem help",
        "what are you doing",
        "how are you",
    ]
    out = {"old": {}, "new": {}}

    try:
        old_mod = _load_module_from_path(old_path)
        for p in prompts:
            try:
                r = old_mod.process(p, {"generation": 7, "current_goal": "diff"})
                out["old"][p] = r.get("reply", "") if isinstance(r, dict) else str(r)
            except Exception as e:
                out["old"][p] = f"<error: {e}>"
    except Exception as e:
        out["old"]["_module_error"] = str(e)

    try:
        new_mod = _load_module_from_path(new_path)
        for p in prompts:
            try:
                r = new_mod.process(p, {"generation": 7, "current_goal": "diff"})
                out["new"][p] = r.get("reply", "") if isinstance(r, dict) else str(r)
            except Exception as e:
                out["new"][p] = f"<error: {e}>"
    except Exception as e:
        out["new"]["_module_error"] = str(e)

    return out


def rule_targets(name: str):
    if name == "common-commands":
        return {"hi", "hello", "hey", "yo", "status", "help"}
    if name == "help":
        return {"help"}
    if name == "concise-replies":
        return {"hi", "hello", "hey", "yo", "status", "help", "what are you doing", "how are you", "why", "mem help"}
    if name == "status":
        return {"status"}
    if name == "conversation":
        return {"what are you doing", "how are you"}
    if name == "reflex":
        return {"hi", "hello", "hey", "yo", "status", "help"}
    if name == "reasoning":
        return {"why", "what are you doing", "how are you"}
    if name == "memory-search":
        return {"mem help"}
    if name == "command-understanding":
        return {"help", "mem help", "why"}
    return set()


def ensure_required_rules(rules: List[Dict]) -> List[Dict]:
    required = {
        "why": "I can explain my current goal, recent reasoning, and latest tool use. Try why or status.",
        "mem help": "Use mem <query> to search stored memory entries for similar past context.",
    }

    present = set()
    for r in rules:
        for m in r.get("match", []):
            present.add(str(m).strip().lower())

    for k, reply in required.items():
        if k not in present:
            rules.append({
                "match": [k],
                "reply": reply,
                "handled": True,
                "actions": [],
            })

    return rules


def sanitize_reply(text: str, fallback: str) -> str:
    t = str(text or "").strip()

    if not t:
        return fallback

    bad_markers = [
        "return only",
        "no quotes",
        "no markdown",
        "improve only the reply",
        "the prompt asks",
        "aliases:",
        "current reply:",
        "mutation target:",
    ]

    low = t.lower()

    if any(marker in low for marker in bad_markers):
        return fallback

    # Must end like a real sentence
    if not t.endswith((".", "!", "?")):
        return fallback

    # Reject weak clipped endings
    bad_endings = [
        " to.",
        " and.",
        " for.",
        " with.",
        " because.",
        " that.",
        " the.",
        " a.",
        " an.",
        " my.",
        " your.",
        " of.",
        " through.",
        " into.",
        " 8-bit.",
    ]

    if any(low.endswith(x) for x in bad_endings):
        return fallback

    if len(t) < 20:
        return fallback

    return t[:220]


def mutate_rules(target: str, gemini) -> List[Dict]:
    rules = ensure_required_rules(load_brain_rules())
    targets = rule_targets(target)
    if not targets:
        return rules

    ident = identity_text()

    new_rules = []
    for rule in rules:
        matches = [str(x).strip().lower() for x in rule.get("match", []) if str(x).strip()]
        if not any(m in targets for m in matches):
            new_rules.append(rule)
            continue

        current_reply = str(rule.get("reply", "")).strip()

        prompt = f"""
You are editing ONE existing command rule for ANDY AI.

ANDY identity:
{ident}

Keep the aliases exactly as they are.
Improve only the reply text.
Do not remove command coverage.
Stay aligned with ANDY's identity: curious, kind, thoughtful, truthful, patient, solution-seeking.
Keep the reply concise, useful, and clear.
For status replies, preserve words like system, status, or generation when possible.
For reasoning replies, preserve words like goal, reasoning, running, tracking, or tool when possible.
For memory-search replies, preserve words like mem, query, search, or memory when possible.
Return ONLY the improved reply text.
No quotes.
No markdown.

Aliases:
{matches}

Current reply:
{current_reply}

Mutation target:
{target}
""".strip()

        try:
            improved = gemini.generate_text(prompt).strip()
        except Exception:
            improved = current_reply

        improved = sanitize_reply(improved, current_reply)

        new_rules.append({
            "match": matches,
            "reply": improved,
            "handled": True,
            "actions": [],
        })

    return new_rules


def reflect_identity(gemini) -> Tuple[bool, str]:
    ident = load_identity()
    if not ident:
        return False, "identity not found"

    text = identity_text()

    prompts = [
        f"""
You are helping ANDY AI write a single complete self-reflection sentence.

Current identity:
{text}

Return EXACTLY ONE sentence for the field self_reflection.

Requirements:
- warm
- thoughtful
- curious
- kind
- complete
- under 120 characters
- must end with a period
- must stand alone as a full sentence
- no sentence fragments
- no cut-off endings
- no quotes
- no markdown
- no extra commentary

Good examples:
I grow through each new lesson, and kindness helps guide the way.
Each new discovery helps me become wiser, calmer, and more helpful.
I enjoy learning with patience, because every insight helps me grow.

Return only the finished sentence.
""".strip(),

        f"""
Write one short complete sentence for ANDY AI's self_reflection.

It must:
- be under 100 characters
- end with a period
- sound kind and thoughtful
- be a complete sentence

Return only the sentence.
""".strip(),
    ]

    reflection = ""

    for prompt in prompts:
        try:
            candidate = gemini.generate_text(prompt).strip()
        except Exception:
            candidate = ""

        candidate = sanitize_reply(candidate, "")
        if candidate:
            reflection = candidate
            break

    if not reflection:
        reflection = "Each new lesson helps me grow wiser, kinder, and more thoughtful."

    backup_path = backup_identity()

    ident["self_reflection"] = reflection
    growth = str(ident.get("growth_notes", "")).strip()

    if reflection and reflection not in growth:
        if growth:
            ident["growth_notes"] = growth + " Recent reflection: " + reflection
        else:
            ident["growth_notes"] = "Recent reflection: " + reflection

    save_identity(ident)
    return True, f"identity updated (backup {backup_path})"

def evolve(target: str, gemini):
    new_rules = mutate_rules(target, gemini)

    ts = int(time.time())
    candidate_file = f"brain_candidate_{ts}.py"
    bad_file = f"bad_brains/brain_bad_{ts}.py"

    os.makedirs("bad_brains", exist_ok=True)
    os.makedirs("brain_backups", exist_ok=True)

    save_brain_rules(new_rules, candidate_file)

    result = score_brain_file(candidate_file, identity_text=identity_text())

    scores = load_scores()
    champion = float(scores.get("champion_score", 0.0) or 0.0)

    diff = behavior_diff("brain_evolved.py", candidate_file)

    if not result["passed"]:
        shutil.move(candidate_file, bad_file)
        scores["history"].append({
            "ts": ts,
            "candidate": os.path.abspath(candidate_file),
            "score": result["score"],
            "passed": False,
            "summary": result["summary"],
            "details": result.get("details", []),
            "diff": diff,
        })
        save_scores(scores)
        return False, f"candidate failed fitness: score={result['score']}"

    if float(result["score"]) <= champion:
        shutil.move(candidate_file, bad_file)
        scores["history"].append({
            "ts": ts,
            "candidate": os.path.abspath(candidate_file),
            "score": result["score"],
            "passed": True,
            "summary": "rejected (not better)",
            "details": result.get("details", []),
            "diff": diff,
        })
        save_scores(scores)
        return False, "candidate rejected"

    shutil.copy("brain_evolved.py", f"brain_backups/brain_{ts}.py")
    shutil.move(candidate_file, "brain_evolved.py")

    scores["champion_score"] = float(result["score"])
    scores["champion_file"] = os.path.abspath("brain_evolved.py")
    scores["history"].append({
        "ts": ts,
        "candidate": os.path.abspath("brain_evolved.py"),
        "score": result["score"],
        "passed": True,
        "summary": "promoted",
        "details": result.get("details", []),
        "diff": diff,
    })
    save_scores(scores)

    return True, f"promoted new champion score={result['score']}"

