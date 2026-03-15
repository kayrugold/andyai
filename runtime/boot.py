from subsystems.os.embedder import Embedder
from subsystems.regulation.nervous_system import ensure_emotional_state as ensure_nervous_emotional_state
from runtime.task_queue import TaskQueue


def attach_runtime_basics(state, gemini):
    state["embedder"] = Embedder(gemini=gemini)
    state["gemini"] = gemini
    state["reason_queue"] = TaskQueue()
    state["diag_queue"] = TaskQueue()
    state["gemini_queue"] = TaskQueue()
    state["worker_results"] = []
    return state


def ensure_internal_defaults(state):
    st = state.get("internal_state", {}) or {}

    st.setdefault("emotion_confidence", 0.5)
    st.setdefault("emotion_frustration", 0.0)
    st.setdefault("emotion_curiosity", 0.0)
    st.setdefault("emotion_stability", 1.0)
    st.setdefault("reflex_fault_pressure", 0.0)
    st.setdefault("recovery_mode", False)

    state["internal_state"] = st
    ensure_nervous_emotional_state(state)
    return state


def ensure_emotional_state(state):
    return ensure_nervous_emotional_state(state)
