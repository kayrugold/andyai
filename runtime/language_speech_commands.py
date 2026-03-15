from subsystems.linguistic.voice_box import speech_plan_text, speech_say_text, speech_status_text


def handle_language_speech_command(cmd, low, state=None):
    if low == "speak status":
        print(speech_status_text(state))
        return True

    if low.startswith("speak plan "):
        text = cmd[len("speak plan "):].strip()
        if not text:
            print("Usage: speak plan <text>")
            return True
        print(speech_plan_text(state, text))
        return True

    if low.startswith("speak say "):
        text = cmd[len("speak say "):].strip()
        if not text:
            print("Usage: speak say <text>")
            return True
        print(speech_say_text(state, text))
        return True

    return False
