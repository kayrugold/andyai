from pathlib import Path
import json
import hashlib

VOCAB_FILE = "language_vocab.json"

GRAMMAR_ANCHORS = {
    "is": "copula",
    "are": "copula",
    "was": "copula",
    "were": "copula",
    "be": "copula",
    "very": "intensifier",
    "so": "intensifier",
    "quite": "intensifier",
    "please": "command",
    "turn": "verb",
    "off": "particle"
}

def load_vocab():
    if not Path(VOCAB_FILE).exists():
        return {}
    return json.loads(Path(VOCAB_FILE).read_text())


def save_vocab(vocab):
    Path(VOCAB_FILE).write_text(json.dumps(vocab, indent=2))


def word_address(word):
    h = hashlib.sha256(word.encode()).hexdigest()
    return int(h[:8], 16)


def normalize_vocab(vocab):
    changed = False

    for word, entry in list(vocab.items()):
        if "roles" not in entry:
            cat = entry.get("cat", "unknown")
            count = int(entry.get("count", 1) or 1)
            entry["roles"] = {cat: count}
            entry["count"] = count
            entry["addr"] = entry.get("addr", word_address(word))
            entry["examples"] = entry.get("examples", [])
            changed = True

    if changed:
        save_vocab(vocab)

    return vocab


def learn_word(word, category):
    vocab = normalize_vocab(load_vocab())

    word = word.lower().strip()

    if word not in vocab:
        vocab[word] = {
            "addr": word_address(word),
            "roles": {category: 1},
            "count": 1,
            "examples": []
        }
    else:
        vocab[word]["roles"][category] = vocab[word]["roles"].get(category, 0) + 1
        vocab[word]["count"] += 1

    save_vocab(vocab)
    return vocab[word]


def add_examples(word, examples):
    vocab = normalize_vocab(load_vocab())

    if word not in vocab:
        return

    for ex in examples:
        if ex not in vocab[word]["examples"]:
            vocab[word]["examples"].append(ex)

    save_vocab(vocab)


def role_counts_text(roles):
    return ", ".join(f"{k}:{v}" for k,v in roles.items())


def vocab_text():
    vocab = normalize_vocab(load_vocab())

    lines = ["ANDY VOCAB",""]

    for w in sorted(vocab):
        e=vocab[w]
        lines.append(
            f"{w} | roles=[{role_counts_text(e['roles'])}] | addr={e['addr']} | seen={e['count']} | examples={len(e['examples'])}"
        )

    return "\n".join(lines)


def anchor_type(word):
    return GRAMMAR_ANCHORS.get(word)


def score_role(words,i,role,entry):
    score=entry["roles"].get(role,0)*10

    prev=words[i-1] if i>0 else ""
    next=words[i+1] if i+1<len(words) else ""

    prev_anchor=anchor_type(prev)
    next_anchor=anchor_type(next)

    if prev_anchor=="copula" and role=="adjective":
        score+=40

    if prev_anchor=="intensifier" and role=="adjective":
        score+=35

    if prev_anchor=="command" and role=="verb":
        score+=30

    if prev=="the" and role=="noun":
        score+=20

    if prev_anchor=="verb" and role=="particle":
        score+=10

    for ex in entry.get("examples",[]):
        if role=="verb" and prev in ex.lower():
            score+=5

    return score


def resolve_role(words,i,vocab):

    word=words[i]

    if word not in vocab:
        return "unknown",word_address(word),{},[]

    entry=vocab[word]
    roles=entry["roles"]

    if len(roles)==1:
        role=list(roles.keys())[0]
        return role,entry["addr"],roles,entry["examples"]

    scored=[]
    for r in roles:
        scored.append((r,score_role(words,i,r,entry)))

    scored.sort(key=lambda x:-x[1])

    return scored[0][0],entry["addr"],roles,entry["examples"]


def parse_sentence(text):
    vocab=normalize_vocab(load_vocab())
    words=text.lower().split()

    result=[]

    for i,w in enumerate(words):
        role,addr,roles,examples=resolve_role(words,i,vocab)
        result.append((w,role,addr,roles,examples))

    return result


def parse_text(text):
    parsed=parse_sentence(text)

    lines=["PARSE RESULT",""]

    for w,role,addr,roles,examples in parsed:
        if roles:
            lines.append(
                f"{w} -> {role} ({addr}) | roles=[{role_counts_text(roles)}] | examples={len(examples)}"
            )
        else:
            lines.append(f"{w} -> {role} ({addr})")

    return "\n".join(lines)


def extract_scene_concepts(text):
    parsed=parse_sentence(text)
    return [w for w,r,_,_,_ in parsed if r in ["noun","scene"]]


def extract_action_concepts(text):
    parsed=parse_sentence(text)
    return [w for w,r,_,_,_ in parsed if r in ["verb","action"]]
