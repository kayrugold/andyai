from subsystems.creative.art_engine import write_scene_art
from subsystems.linguistic.linguistic_sieve import extract_action_concepts, extract_scene_concepts
from subsystems.linguistic.sentence_memory import build_dream_seed
from subsystems.os.concept_clusters import (
    build_clusters_from_sentence_memory,
    cluster_bridge_text,
    cluster_reinforcement_text,
    cluster_summary_text,
    clusters_text,
)
from subsystems.os.concept_graph import (
    add_edge,
    build_from_memory,
    concepts_text,
    ensure_type_nodes,
    graph_infer_text,
    graph_text,
    neighbors_text,
    path_text,
    set_concept_category,
)
from subsystems.os.dream_engine import (
    auto_dream,
    dreams_text,
    latest_dream_bridge,
    latest_dream_text,
    latest_identity_note,
    make_dream,
)
from subsystems.os.exploration_engine import exploration_act, exploration_advice
from subsystems.os.identity_notes import (
    identity_notes_text,
    latest_identity_note_text,
    remember_identity_note,
)
from subsystems.os.recovery_engine import recovery_act, recovery_advice, recovery_choose
from subsystems.os.scene_variation_engine import imagination_bridge
from subsystems.os.taste_memory import taste_memory_text, taste_summary_text
from subsystems.os.theme_memory import (
    build_theme_memory,
    reinforce_top_theme,
    theme_bridge_text,
    theme_summary_text,
    themes_text,
)


def _run_draw_text(draw_text, state):
    if not draw_text:
        print("DREAM DRAW")
        print("")
        print("No drawable bridge found in latest dream.")
        return True

    if not state:
        print("DREAM DRAW")
        print("")
        print("State unavailable.")
        return True

    if not draw_text.lower().startswith("draw "):
        print("DREAM DRAW")
        print("")
        print(f"Invalid bridge: {draw_text}")
        return True

    text = draw_text[len("draw "):].strip()
    concepts = extract_scene_concepts(text)
    actions = extract_action_concepts(text)

    if not concepts:
        print("DREAM DRAW")
        print("")
        print("No known drawable concepts found in dream bridge.")
        return True

    result = write_scene_art(state, concepts, actions)

    print("DREAM DRAW")
    print("")
    print(f"Bridge: {draw_text}")
    print(f"Concepts: {', '.join(result['concepts'])}")
    print(f"Actions: {', '.join(result['actions']) if result['actions'] else '(none)'}")
    print(f"Path: {result['path']}")
    print(f"Score: {result['score']}")
    return True


def handle_language_world_command(cmd, low, state=None):
    if low == "dream seed":
        print(build_dream_seed())
        return True

    if low == "dream make":
        if state is None:
            print("DREAM MAKE\n\nState unavailable.")
            return True
        print(make_dream(state))
        return True

    if low == "dream auto":
        if state is None:
            print("DREAM AUTO\n\nState unavailable.")
            return True
        print(auto_dream(state))
        return True

    if low == "dreams":
        print(dreams_text())
        return True

    if low == "dream latest":
        print(latest_dream_text())
        return True

    if low == "dream reflect":
        note = latest_identity_note()
        print("DREAM REFLECT")
        print("")
        if note:
            print(note)
        else:
            print("No dream reflection available yet.")
        return True

    if low == "dream keep":
        note = latest_identity_note()
        print("DREAM KEEP")
        print("")
        if not note:
            print("No dream reflection available yet.")
            return True

        remember_identity_note(note, source="dream", tags=["reflection"])
        print(note)
        return True

    if low == "identity notes":
        print(identity_notes_text())
        return True

    if low == "identity latest":
        print(latest_identity_note_text())
        return True

    if low == "recovery advise":
        if state is None:
            print("RECOVERY ADVICE\n\nState unavailable.")
            return True
        text, _method = recovery_advice(state)
        print(text)
        return True

    if low == "recovery choose":
        if state is None:
            print("RECOVERY CHOOSE\n\nState unavailable.")
            return True
        print(recovery_choose(state))
        return True

    if low == "recovery act":
        if state is None:
            print("RECOVERY ACT\n\nState unavailable.")
            return True
        print(recovery_act(state))
        return True

    if low == "explore advise":
        if state is None:
            print("EXPLORATION ADVICE\n\nState unavailable.")
            return True
        text, _method = exploration_advice(state)
        print(text)
        return True

    if low == "explore act":
        if state is None:
            print("EXPLORATION ACT\n\nState unavailable.")
            return True
        print(exploration_act(state))
        return True

    if low == "cluster build":
        clusters = build_clusters_from_sentence_memory()
        print("CLUSTER BUILD")
        print("")
        print(f"Built {len(clusters)} clusters.")
        return True

    if low == "clusters":
        print(clusters_text())
        return True

    if low == "cluster summary":
        print(cluster_summary_text())
        return True

    if low == "cluster bridge":
        print(cluster_bridge_text())
        return True

    if low == "theme build":
        items = build_theme_memory()
        print("THEME BUILD")
        print("")
        print(f"Built {len(items)} themes.")
        return True

    if low == "themes":
        print(themes_text())
        return True

    if low == "theme summary":
        print(theme_summary_text())
        return True

    if low == "theme bridge":
        print(theme_bridge_text())
        return True

    if low == "theme reinforce":
        text = reinforce_top_theme()
        print("THEME REINFORCE")
        print("")
        if text:
            print(text)
        else:
            print("No top theme available yet.")
        return True

    if low == "imagine":
        print(imagination_bridge())
        return True

    if low == "taste show":
        print(taste_memory_text())
        return True

    if low == "taste summary":
        print(taste_summary_text())
        return True

    if low == "graph show":
        print(graph_text())
        return True

    if low == "graph concepts":
        print(concepts_text())
        return True

    if low == "graph types":
        ensure_type_nodes()
        print(concepts_text())
        return True

    if low == "graph infer":
        print(graph_infer_text())
        return True

    if low == "graph build":
        count = build_from_memory(state)
        print("GRAPH BUILD")
        print("")
        print(f"Added {count} relations.")
        return True

    if low.startswith("graph neighbors "):
        concept = cmd[len("graph neighbors "):].strip()
        if not concept:
            print("Usage: graph neighbors <concept>")
            return True
        print(neighbors_text(concept))
        return True

    if low.startswith("graph add "):
        parts = cmd.split()
        if len(parts) < 5:
            print("Usage: graph add <source> <relation> <target>")
            return True
        source = parts[2]
        relation = parts[3]
        target = parts[4]
        edge = add_edge(source, relation, target)
        print("GRAPH ADD")
        print("")
        print(f"{edge['source']} --{edge['relation']}--> {edge['target']} | weight={edge['weight']}")
        return True

    if low.startswith("graph type "):
        parts = cmd.split()
        if len(parts) < 4:
            print("Usage: graph type <concept> <category>")
            return True
        concept = parts[2]
        category = parts[3]
        set_concept_category(concept, category)
        print("GRAPH TYPE")
        print("")
        print(f"{concept} -> {category}")
        return True

    if low.startswith("graph path "):
        parts = cmd.split()
        if len(parts) < 4:
            print("Usage: graph path <start> <goal>")
            return True
        print(path_text(parts[2], parts[3]))
        return True

    if low == "dream draw":
        return _run_draw_text(latest_dream_bridge(), state)

    if low.startswith("draw "):
        if state is None:
            print("DRAW ERROR\n\nState unavailable.")
            return True

        text = cmd[len("draw "):].strip()
        concepts = extract_scene_concepts(text)
        actions = extract_action_concepts(text)

        if not concepts:
            print("DRAW ERROR\n\nNo known drawable concepts found.")
            return True

        result = write_scene_art(state, concepts, actions)

        print("DRAW ROUTE\n")
        print(f"Concepts: {', '.join(result['concepts'])}")
        print(f"Actions: {', '.join(result['actions']) if result['actions'] else '(none)'}")
        print(f"Path: {result['path']}")
        print(f"Score: {result['score']}")
        return True

    return False
