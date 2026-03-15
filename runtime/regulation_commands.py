def handle_regulation_command(
    cmd: str,
    low: str,
    state,
    set_recovery_mode_fn,
    recovery_mode_text_fn,
    recovery_status_text_fn,
    emotion_status_text_fn,
    behavior_policy_text_fn,
    reflex_status_text_fn,
    reflex_history_text_fn,
    nerve_reset_fn,
):
    if low == "emotion":
        print(emotion_status_text_fn(state))
        return True

    if low == "behavior":
        print(behavior_policy_text_fn(state))
        return True

    if low == "recovery":
        print(recovery_status_text_fn(state))
        return True

    if low.startswith("recovery mode "):
        mode = cmd[len("recovery mode "):].strip().lower()
        set_recovery_mode_fn(state, mode)
        print(recovery_mode_text_fn(state))
        return True

    if low == "reflex status":
        print(reflex_status_text_fn(state))
        return True

    if low == "reflex history":
        print(reflex_history_text_fn(state))
        return True

    if low == "nerve reset":
        result = nerve_reset_fn(state, 0.85)
        print(result)
        return True

    if low.startswith("nerve reset "):
        arg = cmd[len("nerve reset "):].strip()
        try:
            target = float(arg)
        except Exception:
            print("NERVE RESET ERROR\n\nUsage: nerve reset <number>")
            return True

        result = nerve_reset_fn(state, target)
        print(result)
        return True

    return False
