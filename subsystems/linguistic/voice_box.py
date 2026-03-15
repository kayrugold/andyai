from __future__ import annotations

import json
from typing import Any, Dict, List

from subsystems.linguistic.andy_memmap_core import text_to_phonemes
from subsystems.linguistic.word_memmap_core import tokenize_words


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def emotional_voice_profile(state) -> Dict[str, float | str]:
    st = state.get("internal_state", {}) or {}

    confidence = float(st.get("emotion_confidence", 0.5) or 0.5)
    frustration = float(st.get("emotion_frustration", 0.0) or 0.0)
    curiosity = float(st.get("emotion_curiosity", 0.0) or 0.0)
    stability = float(st.get("emotion_stability", 1.0) or 1.0)
    pressure = float(st.get("reflex_fault_pressure", 0.0) or 0.0)

    # Base calm profile
    tempo = 1.0
    energy = 0.45
    pitch_bias = 0.0
    pause_scale = 1.0
    mode = "calm"

    # Frustration / pressure make speech tighter and sharper
    if frustration > 0.35 or pressure > 1.0:
        tempo += 0.08
        energy += 0.10
        pitch_bias += 0.08
        pause_scale -= 0.05
        mode = "tense"

    # Confidence deepens / stabilizes delivery
    if confidence > 0.70:
        tempo -= 0.04
        energy += 0.05
        pitch_bias -= 0.05
        pause_scale += 0.03
        mode = "grounded" if mode == "calm" else mode

    # Curiosity makes delivery lighter / more lifted
    if curiosity > 0.20:
        tempo += 0.03
        pitch_bias += 0.05
        mode = "curious" if mode == "calm" else mode

    # Low stability softens and slows speech a bit
    if stability < 0.70:
        tempo -= 0.05
        energy -= 0.04
        pause_scale += 0.08
        mode = "careful"

    tempo = _clamp(tempo, 0.70, 1.35)
    energy = _clamp(energy, 0.10, 1.00)
    pitch_bias = _clamp(pitch_bias, -0.50, 0.50)
    pause_scale = _clamp(pause_scale, 0.70, 1.50)

    return {
        "mode": mode,
        "tempo": round(tempo, 3),
        "energy": round(energy, 3),
        "pitch_bias": round(pitch_bias, 3),
        "pause_scale": round(pause_scale, 3),
        "confidence": round(confidence, 3),
        "frustration": round(frustration, 3),
        "curiosity": round(curiosity, 3),
        "stability": round(stability, 3),
        "fault_pressure": round(pressure, 3),
    }


def build_stress_profile(words: List[str], phonemes: List[str], profile: Dict[str, float | str]) -> List[float]:
    energy = float(profile["energy"])
    pitch_bias = float(profile["pitch_bias"])
    base = 0.45 + (energy * 0.25) + max(0.0, pitch_bias) * 0.10

    # Simple word-driven stress estimate
    stress: List[float] = []
    for w in words:
        val = base

        if len(w) >= 6:
            val += 0.08
        if w in {"warning", "storm", "danger", "important", "severe"}:
            val += 0.15
        if w in {"the", "a", "an", "of", "to", "and"}:
            val -= 0.10

        stress.append(round(_clamp(val, 0.05, 1.0), 3))

    if not stress and phonemes:
        stress = [round(_clamp(base, 0.05, 1.0), 3)]

    return stress


def build_pause_points(words: List[str], profile: Dict[str, float | str]) -> List[int]:
    pause_scale = float(profile["pause_scale"])
    out: List[int] = []

    for i, w in enumerate(words):
        if w in {"and", "but", "because", "however", "then"}:
            out.append(i)
        elif len(w) >= 8 and pause_scale > 1.0:
            out.append(i)

    return out


def make_speech_plan(state, text: str) -> Dict[str, Any]:
    text = str(text).strip()
    words = tokenize_words(text)
    phonemes = text_to_phonemes(text)
    profile = emotional_voice_profile(state)
    stress = build_stress_profile(words, phonemes, profile)
    pauses = build_pause_points(words, profile)

    plan = {
        "text": text,
        "words": words,
        "phonemes": phonemes,
        "voice_mode": profile["mode"],
        "tempo": profile["tempo"],
        "energy": profile["energy"],
        "pitch_bias": profile["pitch_bias"],
        "pause_scale": profile["pause_scale"],
        "stress_profile": stress,
        "pause_points": pauses,
        "signals": {
            "confidence": profile["confidence"],
            "frustration": profile["frustration"],
            "curiosity": profile["curiosity"],
            "stability": profile["stability"],
            "fault_pressure": profile["fault_pressure"],
        },
    }
    return plan


def speech_plan_text(state, text: str) -> str:
    plan = make_speech_plan(state, text)

    lines = [
        "VOICE PLAN",
        "",
        f"Text: {plan['text']}",
        f"Mode: {plan['voice_mode']}",
        f"Tempo: {plan['tempo']}",
        f"Energy: {plan['energy']}",
        f"Pitch Bias: {plan['pitch_bias']}",
        f"Pause Scale: {plan['pause_scale']}",
        "",
        f"Words: {' '.join(plan['words'])}",
        f"Phonemes: {' '.join(plan['phonemes'])}",
        f"Stress Profile: {plan['stress_profile']}",
        f"Pause Points: {plan['pause_points']}",
        "",
        "Signals:",
        f"  confidence={plan['signals']['confidence']}",
        f"  frustration={plan['signals']['frustration']}",
        f"  curiosity={plan['signals']['curiosity']}",
        f"  stability={plan['signals']['stability']}",
        f"  fault_pressure={plan['signals']['fault_pressure']}",
    ]

    return "\n".join(lines)


def speech_status_text(state) -> str:
    profile = emotional_voice_profile(state)

    lines = [
        "VOICE STATUS",
        "",
        f"Mode: {profile['mode']}",
        f"Tempo: {profile['tempo']}",
        f"Energy: {profile['energy']}",
        f"Pitch Bias: {profile['pitch_bias']}",
        f"Pause Scale: {profile['pause_scale']}",
        "",
        "Signals:",
        f"  confidence={profile['confidence']}",
        f"  frustration={profile['frustration']}",
        f"  curiosity={profile['curiosity']}",
        f"  stability={profile['stability']}",
        f"  fault_pressure={profile['fault_pressure']}",
    ]

    return "\n".join(lines)


def speech_say_text(state, text: str) -> str:
    plan = make_speech_plan(state, text)

    lines = [
        "VOICE SAY",
        "",
        f"Mode: {plan['voice_mode']}",
        f"Tempo: {plan['tempo']}",
        f"Energy: {plan['energy']}",
        f"Pitch Bias: {plan['pitch_bias']}",
        "",
        f"Text: {plan['text']}",
    ]

    return "\n".join(lines)
