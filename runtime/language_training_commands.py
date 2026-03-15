from subsystems.linguistic.model_evolution_handler import (
    force_grow_phonetic_text,
    init_phonetic_brain_text,
    report_phonetic_text,
    train_phonetic_once_text,
)
from subsystems.linguistic.word_model_evolution_handler import (
    force_grow_word_text,
    init_word_brain_text,
    report_word_text,
    train_word_once_text,
)
from subsystems.os.concept_clusters import cluster_reinforcement_text


def handle_language_training_command(cmd, low, state=None):
    if low == "cluster reinforce":
        text = cluster_reinforcement_text()
        print("CLUSTER REINFORCE")
        print("")
        if text:
            print(text)
        else:
            print("No reinforcement text available yet.")
        return True

    if low == "cluster reinforce-word":
        text = cluster_reinforcement_text()
        print("CLUSTER REINFORCE WORD")
        print("")
        if not text:
            print("No reinforcement text available yet.")
            return True
        print(train_word_once_text(state, text))
        return True

    if low == "cluster reinforce-phonetic":
        text = cluster_reinforcement_text()
        print("CLUSTER REINFORCE PHONETIC")
        print("")
        if not text:
            print("No reinforcement text available yet.")
            return True
        print(train_phonetic_once_text(state, text))
        return True

    if low == "lang init-word":
        print(init_word_brain_text())
        return True

    if low.startswith("lang train-word "):
        text = cmd[len("lang train-word "):].strip()
        if not text:
            print("Usage: lang train-word <text>")
            return True
        print(train_word_once_text(state, text))
        return True

    if low.startswith("lang report-word "):
        text = cmd[len("lang report-word "):].strip()
        if not text:
            print("Usage: lang report-word <text>")
            return True
        print(report_word_text(text))
        return True

    if low == "lang grow-word":
        print(force_grow_word_text())
        return True

    if low == "lang init-phonetic":
        print(init_phonetic_brain_text())
        return True

    if low.startswith("lang train-phonetic "):
        text = cmd[len("lang train-phonetic "):].strip()
        if not text:
            print("Usage: lang train-phonetic <text>")
            return True
        print(train_phonetic_once_text(state, text))
        return True

    if low.startswith("lang report-phonetic "):
        text = cmd[len("lang report-phonetic "):].strip()
        if not text:
            print("Usage: lang report-phonetic <text>")
            return True
        print(report_phonetic_text(text))
        return True

    if low == "lang grow-phonetic":
        print(force_grow_phonetic_text())
        return True

    return False
