import json
from typing import Any, Dict

from runtime.boot import ensure_emotional_state
from infra.storage.state_store import load_state
from subsystems.linguistic.voice_box import speech_say_text


def _compile_cognitive_prompt(msg: str, state: Dict[str, Any], meta: Dict[str, Any], hits: list) -> str:
    st = state.get("internal_state", {})
    emo = ensure_emotional_state(state)
    
    goal = str(st.get("current_goal", "none")).strip()
    frustration = round(emo.get("frustration", 0.0), 3)
    stability = round(emo.get("stability", 1.0), 3)
    confidence = round(emo.get("confidence", 0.5), 3)
    pressure = round(st.get("reflex_fault_pressure", 0.0), 3)

    recent_memory_text = ""
    if hits:
        top = hits[0][1].get("text", "")
        recent_memory_text = top[:150]

    prompt = (
        "You are generating the dialogue script for A.N.D.Y. based strictly on his current internal mechanical state. "
        "Do NOT break character. You are his internal language synthesis mentor.\n\n"
        "Current Mechanical State:\n"
        f"- Active Goal: {goal}\n"
        f"- Frustration Level: {frustration}\n"
        f"- Stability Level: {stability}\n"
        f"- Confidence: {confidence}\n"
        f"- Fault Pressure: {pressure}\n"
    )

    if recent_memory_text:
        prompt += f"- Best relevant memory match: {recent_memory_text}\n"

    prompt += (
        "\nConstraint: Generate exactly 1 to 3 short sentences of natural dialogue A.N.D.Y. would say in response to the user. "
        "His tone must reflect the stated emotional metrics (e.g. high frustration means terse/annoyed, high stability means calm/measured). "
        "Do NOT mention the metrics directly in the dialogue (e.g., do not say 'my fault pressure is high'). "
        "Just speak naturally as A.N.D.Y. going about his work.\n\n"
        f"User said: {msg}\n\n"
        "Return ONLY the strict dialogue string to be spoken."
    )
    
    return prompt


def generate_dynamic_reply(msg: str, state: Dict[str, Any], meta: Dict[str, Any], hits: list, gemini) -> str:
    """
    Compiles A.N.D.Y.'s current state, asks Gemini to act as a language synthesis Mentor
    to generate a strictly constrained reply, and returns the raw string.
    """
    if not gemini:
        return "I am unable to synthesize a response. Mentor connection unavailable."

    prompt = _compile_cognitive_prompt(msg, state, meta, hits)
    
    try:
        reply = gemini.generate_text(prompt)
        cleaned = reply.strip()
        if cleaned.startswith('"') and cleaned.endswith('"'):
            cleaned = cleaned[1:-1]
        return cleaned
    except Exception as e:
        return f"I experienced a cognition error while synthesizing my reply: {e}"
