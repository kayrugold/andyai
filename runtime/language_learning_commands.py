import json

from subsystems.linguistic.linguistic_sieve import (
    add_examples,
    learn_word,
    load_vocab,
    normalize_vocab,
    parse_text,
    vocab_text,
)
from subsystems.linguistic.sentence_memory import remember_sentence, sentence_memories_text


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


def handle_language_learning_command(cmd, low, state=None):
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

    return False
