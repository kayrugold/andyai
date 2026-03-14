import threading


def start_background_threads(
    state,
    Worker,
    reasoning_worker,
    diagnostics_worker,
    gemini_worker,
    background_drive_loop,
):
    reason_thread = Worker("reason", state["reason_queue"], reasoning_worker)
    diag_thread = Worker("diagnostics", state["diag_queue"], diagnostics_worker)
    gemini_thread = Worker("gemini", state["gemini_queue"], gemini_worker)

    reason_thread.start()
    diag_thread.start()
    gemini_thread.start()

    drive_thread = threading.Thread(
        target=background_drive_loop,
        args=(state,),
        daemon=True,
        name="drive_scheduler",
    )
    drive_thread.start()

    return {
        "reason_thread": reason_thread,
        "diag_thread": diag_thread,
        "gemini_thread": gemini_thread,
        "drive_thread": drive_thread,
    }
