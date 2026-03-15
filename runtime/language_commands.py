from runtime.language_learning_commands import handle_language_learning_command
from runtime.language_speech_commands import handle_language_speech_command
from runtime.language_training_commands import handle_language_training_command
from runtime.language_world_commands import handle_language_world_command


def handle_language_command(cmd, state=None):
    low = cmd.lower().strip()

    for handler in (
        handle_language_learning_command,
        handle_language_world_command,
        handle_language_training_command,
        handle_language_speech_command,
    ):
        handled = handler(cmd, low, state)
        if handled:
            return True

    return False
