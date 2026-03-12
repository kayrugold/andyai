import json

from linguistic_sieve import (
    learn_word,
    vocab_text,
    parse_text,
    extract_scene_concepts,
    extract_action_concepts,
    load_vocab,
    normalize_vocab,
    add_examples,
)
from art_engine import write_scene_art
from sentence_memory import (
    remember_sentence,
    sentence_memories_text,
    build_dream_seed,
)
from dream_engine import (
    make_dream,
    auto_dream,
    dreams_text,
    latest_dream_text,
    latest_dream_bridge,
    latest_identity_note,
)
from identity_notes import (
    remember_identity_note,
    identity_notes_text,
    latest_identity_note_text,
)
from recovery_engine import (
    recovery_advice,
    recovery_choose,
    recovery_act,
)
from exploration_engine import (
    exploration_advice,
    exploration_act,
)


def _show_word(word):
    vocab = normalize_vocab(load_vocab())
    entry = vocab.get(word)

    if not entry:
        print("LANG SHOW")
        print("")
        print(f"{word} -> unknown")
        return True

    print("LANG SHOW")
    print("")
    print(f"word: {word}")
    print(f"addr: {entry['addr']}")
    print(f"roles: {entry.get('roles', {})}")
    print(f"seen: {entry.get('count', 0)}")

    examples = list(entry.get("examples", []) or [])
    if examples:
        print("examples:")
        for ex in examples[:10]:
            print(f"  {ex}")

    return True


def _teach_word_with_gemini(word, state=None):
    word = word.strip().lower()
    print("LANG TEACH")
    print("")
    print(f"Target word: {word}")

    if state is None:
        print("")
        print("Teacher unavailable: no state provided.")
        return True

    gemini = state.get("gemini")
    if gemini is None:
        print("")
        print("Teacher unavailable: Gemini handle not found in state.")
        return True

    prompt = (
        "You are teaching a small offline AI vocabulary system.\n"
        "Return strict JSON only.\n"
        "For the word below, provide likely roles and up to 3 short example sentences.\n"
        "Use this schema:\n"
        '{'
        '"word":"...",'
        '"roles":["noun","verb"],'
        '"examples":["...","..."]'
        '}\n'
        f"Word: {word}"
    )

    try:
        reply = gemini.generate_text(prompt)
    except Exception as e:
        print("")
        print(f"Teacher request failed: {e}")
        return True

    print("")
    print("Teacher Raw Reply:")
    print(reply)

    data = None
    try:
        data = json.loads(reply)
    except Exception:
        cleaned = reply.strip()

        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if len(lines) >= 3:
                cleaned = "\n".join(lines[1:-1]).strip()

        try:
            data = json.loads(cleaned)
        except Exception as e:
            print("")
            print(f"Could not parse teacher JSON: {e}")
            return True

    roles = data.get("roles", []) or []
    examples = data.get("examples", []) or []

    if not roles:
        print("")
        print("Teacher returned no roles.")
        return True

    print("")
    print("Accepted Roles:")
    for role in roles:
        entry = learn_word(word, role)
        print(f"  learned {word} -> {role} | addr={entry['addr']}")

    if examples:
        add_examples(word, examples)

        for ex in examples[:10]:
            remember_sentence(ex, source="teacher", tags=["example", word])

        print("")
        print("Teacher Examples:")
        for ex in examples[:3]:
            print(f"  {ex}")

    return True


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


def handle_language_command(cmd, state=None):
    low = cmd.lower().strip()

    if low == "lang vocab":
        print(vocab_text())
        return True

    if low.startswith("lang learn "):
        parts = cmd.split()

        if len(parts) < 4:
            print("Usage: lang learn <word> <category>")
            return True

        word = parts[2]
        cat = parts[3]

        entry = learn_word(word, cat)

        print("LEARNED WORD")
        print("")
        print(f"{word} -> roles={entry['roles']} | addr={entry['addr']}")
        return True

    if low.startswith("lang parse "):
        text = cmd[len("lang parse "):]
        print(parse_text(text))
        return True

    if low.startswith("lang show "):
        word = cmd[len("lang show "):].strip().lower()
        return _show_word(word)

    if low.startswith("lang teach "):
        word = cmd[len("lang teach "):].strip().lower()
        if not word:
            print("Usage: lang teach <word>")
            return True
        return _teach_word_with_gemini(word, state)

    if low.startswith("lang remember "):
        text = cmd[len("lang remember "):].strip()
        if not text:
            print("Usage: lang remember <sentence>")
            return True

        remember_sentence(text, source="manual", tags=["user"])
        print("LANG REMEMBER")
        print("")
        print(text)
        return True

    if low == "lang memories":
        print(sentence_memories_text())
        return True

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
