from __future__ import annotations

import json
from pathlib import Path
from collections import deque
from typing import Dict, List, Tuple

GRAPH_FILE = Path("concept_graph.json")

REL_WORDS = {
    "above", "below", "beside", "near", "under", "over",
    "in", "on", "by", "behind", "around", "through", "at"
}

SKIP_WORDS = {
    "the", "a", "an", "and", "of", "to", "is", "was", "were",
    "with", "that", "this", "it", "as", "for", "from"
}



ARTICLES = {"the","a","an"}

VERB_BLOCK = {
    "is","was","were","be","been",
    "stood","stand","stands",
    "run","runs","running",
    "walk","walked","walking"
}

def next_entity(words, start):

    for i in range(start, len(words)):
        w = words[i]

        if w in ARTICLES:
            continue

        if w in VERB_BLOCK:
            continue

        if valid_concept(w):
            return w

    return None


def prev_entity(words, start):

    for i in range(start, -1, -1):
        w = words[i]

        if w in ARTICLES:
            continue

        if w in VERB_BLOCK:
            continue

        if valid_concept(w):
            return w

    return None



TYPE_NODES = {
    "animal",
    "plant",
    "water",
    "sky",
    "place",
    "land",
    "object",
    "type",
}

def ensure_type_nodes():
    g = load_graph()
    changed = False

    for t in TYPE_NODES:
        if t not in g["concepts"]:
            g["concepts"][t] = {"category": "type"}
            changed = True
        elif g["concepts"][t].get("category") != "type":
            g["concepts"][t]["category"] = "type"
            changed = True

    if changed:
        save_graph(g)

CATEGORY_MAP = {

    "night": "time",
    "table": "object",
    "hand": "body",
    "candle": "object",
    "light": "phenomenon",

    "wolf": "animal",
    "bird": "animal",
    "dog": "animal",
    "tree": "plant",
    "river": "water",
    "moon": "sky",
    "sun": "sky",
    "star": "sky",
    "sky": "place",
    "ground": "land",
    "mountain": "land",
    "road": "land",
}



PRONOUNS = {
    "i","you","he","she","it","we","they",
    "me","him","her","them","us","my","your",
    "his","hers","their","our"
}

ADJECTIVE_STOP = {
    "quiet","bright","dark","quickly","slowly"
}

def valid_concept(word):

    if not word:
        return False

    if word in PRONOUNS:
        return False

    if word in ADJECTIVE_STOP:
        return False

    if len(word) < 3:
        return False

    return True

VERB_REL = {
    "flies": "in",
    "fly": "in",
    "runs": "on",
    "run": "on",
    "stands": "on",
    "stand": "on",
    "grows": "on",
    "grow": "on",
}


def norm(x: str) -> str:
    return str(x or "").lower().strip()


def singular(w: str) -> str:
    w = norm(w)
    if w.endswith("s") and len(w) > 3:
        return w[:-1]
    return w


def load_graph() -> Dict:
    if not GRAPH_FILE.exists():
        return {"edges": [], "concepts": {}}
    try:
        data = json.loads(GRAPH_FILE.read_text(encoding="utf-8"))
    except Exception:
        data = {"edges": [], "concepts": {}}

    if not isinstance(data, dict):
        data = {"edges": [], "concepts": {}}

    data.setdefault("edges", [])
    data.setdefault("concepts", {})
    return data


def save_graph(g: Dict) -> None:
    g.setdefault("edges", [])
    g.setdefault("concepts", {})
    GRAPH_FILE.write_text(json.dumps(g, indent=2), encoding="utf-8")


def set_concept_category(concept: str, category: str) -> None:
    concept = singular(concept)
    category = norm(category)
    if not concept or not category:
        return

    g = load_graph()
    g["concepts"][concept] = {"category": category}
    save_graph(g)


def concept_category(concept: str) -> str:
    concept = singular(concept)
    g = load_graph()

    if concept in TYPE_NODES:
        return "type"

    if concept in g.get("concepts", {}):
        return norm(g["concepts"][concept].get("category", "unknown"))

    if concept in CATEGORY_MAP:
        return CATEGORY_MAP[concept]

    return "unknown"


def add_edge(src: str, rel: str, tgt: str, w: float = 1.0):
    src = singular(src)
    tgt = singular(tgt)
    rel = norm(rel)

    g = load_graph()

    if src in CATEGORY_MAP:
        g["concepts"].setdefault(src, {"category": CATEGORY_MAP[src]})
    if tgt in CATEGORY_MAP:
        g["concepts"].setdefault(tgt, {"category": CATEGORY_MAP[tgt]})

    for e in g["edges"]:
        if e["source"] == src and e["relation"] == rel and e["target"] == tgt:
            e["weight"] = round(float(e.get("weight", 1.0)) + float(w), 3)
            save_graph(g)
            return False

    edge = {
        "source": src,
        "relation": rel,
        "target": tgt,
        "weight": round(float(w), 3),
    }
    g["edges"].append(edge)
    save_graph(g)
    return edge


def tokenize(s: str) -> List[str]:
    s = (
        str(s or "")
        .replace(",", " ")
        .replace(".", " ")
        .replace("!", " ")
        .replace("?", " ")
        .replace(";", " ")
        .replace(":", " ")
    )
    return [singular(w) for w in s.split() if singular(w)]


def extract(sentence: str) -> List[Tuple[str, str, str]]:
    words = tokenize(sentence)
    triples = []

    def add(src, rel, tgt):
        src = singular(src)
        rel = norm(rel)
        tgt = singular(tgt)

        if valid_concept(src) and valid_concept(tgt) and src != tgt:
            triples.append((src, rel, tgt))

    # direct prep patterns with smarter source/target recovery
    for i, w in enumerate(words):
        if w in {"under", "by", "in", "on"}:
            src = prev_entity(words, i - 1)
            tgt = next_entity(words, i + 1)
            if src and tgt:
                add(src, w, tgt)

        if w == "at":
            src = prev_entity(words, i - 1)
            tgt = next_entity(words, i + 1)
            if src and tgt == "night":
                add(src, "at", "night")

    # subject + verb + relation patterns
    for i, w in enumerate(words):
        if w in {"stood", "stand", "stands"}:
            subj = prev_entity(words, i - 1)
            if not subj:
                continue

            for j in range(i + 1, len(words)):
                rel = words[j]
                if rel not in {"under", "by", "in", "on", "at"}:
                    continue

                tgt = next_entity(words, j + 1)
                if not tgt:
                    continue

                if rel == "at" and tgt != "night":
                    continue

                add(subj, rel, tgt)

    # category grounding
    for w in words:
        if w in CATEGORY_MAP and valid_concept(w):
            triples.append((w, "is_a", CATEGORY_MAP[w]))

    deduped = []
    seen = set()
    for t in triples:
        if t not in seen:
            seen.add(t)
            deduped.append(t)

    return deduped


def build(sentences: List[str]) -> int:
    n = 0
    for s in sentences:
        triples = extract(s)
        for src, rel, tgt in triples:
            add_edge(src, rel, tgt)
            n += 1
    return n


def build_from_memory(state):
    import json
    from pathlib import Path

    ensure_type_nodes()

    path = Path("sentence_memory.json")
    if not path.exists():
        return 0

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return 0

    sents = []

    for m in data:
        if isinstance(m, dict):
            t = m.get("text", "")
        else:
            t = str(m)

        if t:
            sents.append(t)

    return build(sents)





def infer_graph_relations():

    g = load_graph()
    edges = list(g.get("edges", []))

    new_edges = 0
    strengthened = 0

    for e in edges:

        src = e["source"]
        rel = e["relation"]
        tgt = e["target"]

        def apply(a, r, b):

            nonlocal new_edges, strengthened

            before = len(load_graph()["edges"])
            result = add_edge(a, r, b, 0.5)
            after = len(load_graph()["edges"])

            if result:
                new_edges += 1
            else:
                strengthened += 1

        if rel == "under":
            apply(tgt, "above", src)

        if rel == "above":
            apply(tgt, "under", src)

        if rel == "by":
            apply(src, "near", tgt)
            apply(tgt, "near", src)

        if rel == "near":
            apply(tgt, "near", src)

    return new_edges, strengthened
def graph_infer_text():

    new_edges, strengthened = infer_graph_relations()

    lines = [
        "GRAPH INFER",
        "",
        f"New inferred edges: {new_edges}",
        f"Strengthened edges: {strengthened}",
    ]

    return "\n".join(lines)

def graph_text() -> str:
    ensure_type_nodes()
    g = load_graph()
    lines = ["CONCEPT GRAPH", ""]

    if not g["edges"]:
        lines.append("Graph is empty.")
        return "\n".join(lines)

    for e in g["edges"]:
        src = e["source"]
        tgt = e["target"]
        lines.append(
            f"{src}[{concept_category(src)}] --{e['relation']}--> {tgt}[{concept_category(tgt)}] | weight={e['weight']}"
        )

    return "\n".join(lines)


def concepts_text() -> str:
    ensure_type_nodes()
    g = load_graph()
    lines = ["CONCEPT TYPES", ""]

    if not g["concepts"]:
        lines.append("No concept categories yet.")
        return "\n".join(lines)

    for k, v in sorted(g["concepts"].items()):
        lines.append(f"{k} -> {v['category']}")

    return "\n".join(lines)


def neighbors(concept: str):
    concept = singular(concept)
    g = load_graph()
    out = []

    for e in g["edges"]:
        if e["source"] == concept:
            out.append(("out", e["relation"], e["target"], e["weight"]))
        elif e["target"] == concept:
            out.append(("in", e["relation"], e["source"], e["weight"]))

    return out


def neighbors_text(concept: str) -> str:
    concept = singular(concept)
    items = neighbors(concept)

    lines = [f"GRAPH NEIGHBORS: {concept}", ""]
    if not items:
        lines.append("No neighbors.")
        return "\n".join(lines)

    lines.append(f"Category: {concept_category(concept)}")
    lines.append("")

    for direction, rel, other, weight in items:
        if direction == "out":
            lines.append(f"{concept} --{rel}--> {other}[{concept_category(other)}] | weight={weight}")
        else:
            lines.append(f"{other}[{concept_category(other)}] --{rel}--> {concept} | weight={weight}")

    return "\n".join(lines)


def shortest_path(start: str, goal: str) -> List[str]:
    start = singular(start)
    goal = singular(goal)

    if not start or not goal:
        return []

    g = load_graph()
    adj = {}

    for e in g["edges"]:
        adj.setdefault(e["source"], []).append(e["target"])
        adj.setdefault(e["target"], []).append(e["source"])

    q = deque([(start, [start])])
    seen = {start}

    while q:
        node, path = q.popleft()
        if node == goal:
            return path

        for nxt in adj.get(node, []):
            if nxt in seen:
                continue
            seen.add(nxt)
            q.append((nxt, path + [nxt]))

    return []


def path_text(start: str, goal: str) -> str:
    path = shortest_path(start, goal)

    lines = [f"GRAPH PATH: {start} -> {goal}", ""]
    if not path:
        lines.append("No path found.")
        return "\n".join(lines)

    lines.append(" -> ".join(path))
    return "\n".join(lines)
