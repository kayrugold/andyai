from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
from plugins.mentors.base import generate_text_via_mentor

from subsystems.linguistic.andy_memmap_core import (
    DEFAULT_LR,
    DEFAULT_WEIGHT_DECAY,
    SECTOR_BYTES,
    SECTOR_FLOATS,
    active_sector_indices_for_text,
    build_teacher_prompt,
    cross_entropy_loss,
    default_layout,
    evolve_brain,
    forward_all_sectors,
    initialize_brain_file,
    load_meta,
    open_brain,
    parse_teacher_json,
    fallback_teacher_from_phonemes,
    teacher_phoneme_probs_to_bucket_target,
    text_to_token_ids,
    transparency_report,
    update_sector_with_revert,
    save_meta,
)

PHONETIC_WEIGHTS = "phonetic_brain.weights"
PHONETIC_META = "phonetic_brain.meta.json"


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _state_update_after_train(state, improved: bool) -> None:
    st = state.get("internal_state", {}) or {}

    confidence = float(st.get("emotion_confidence", 0.5) or 0.5)
    frustration = float(st.get("emotion_frustration", 0.0) or 0.0)
    curiosity = float(st.get("emotion_curiosity", 0.0) or 0.0)
    pressure = float(st.get("reflex_fault_pressure", 0.0) or 0.0)

    if improved:
        confidence += 0.02
        curiosity += 0.01
        frustration -= 0.01
        pressure -= 0.02
    else:
        frustration += 0.02
        pressure += 0.05

    st["emotion_confidence"] = _clamp(confidence, 0.0, 1.0)
    st["emotion_frustration"] = _clamp(frustration, 0.0, 1.0)
    st["emotion_curiosity"] = _clamp(curiosity, 0.0, 1.0)
    st["reflex_fault_pressure"] = max(0.0, pressure)

    state["internal_state"] = st


def phonetic_training_allowed(state) -> Tuple[bool, str]:
    st = state.get("internal_state", {}) or {}

    stability = float(st.get("emotion_stability", 1.0) or 1.0)
    frustration = float(st.get("emotion_frustration", 0.0) or 0.0)
    pressure = float(st.get("reflex_fault_pressure", 0.0) or 0.0)
    recovery_mode = bool(st.get("recovery_mode", False))

    if recovery_mode:
        return False, "Recovery mode active."
    if pressure > 2.0:
        return False, "Fault pressure too high."
    if frustration > 0.65:
        return False, "Frustration too high."
    if stability < 0.55:
        return False, "Stability too low."

    return True, "Training allowed."


def _gemini_generate_text(state, prompt: str) -> str:
    return generate_text_via_mentor(state.get("gemini"), prompt)


def init_phonetic_brain_text() -> str:
    mm, meta = initialize_brain_file(
        weights_path=PHONETIC_WEIGHTS,
        meta_path=PHONETIC_META,
        force_reinit=False,
    )
    return "\n".join([
        "PHONETIC BRAIN INIT",
        "",
        f"Weights: {PHONETIC_WEIGHTS}",
        f"Meta: {PHONETIC_META}",
        f"Sectors: {meta['sector_count']}",
        f"Params/Sector: {SECTOR_FLOATS}",
        f"Bytes/Sector: {SECTOR_BYTES}",
    ])


def report_phonetic_text(text: str) -> str:
    if not Path(PHONETIC_WEIGHTS).exists() or not Path(PHONETIC_META).exists():
        return "\n".join([
            "PHONETIC REPORT",
            "",
            "Phonetic brain not initialized yet.",
            "Run: lang init-phonetic",
        ])

    mm = open_brain(PHONETIC_WEIGHTS)
    meta = load_meta(PHONETIC_META)
    layout = default_layout(
        vocab_buckets=int(meta["vocab_buckets"]),
        d_model=int(meta["d_model"]),
    )
    _phonemes, token_ids = text_to_token_ids(
        text,
        vocab_buckets=layout.vocab_buckets,
        max_seq=int(meta["max_seq"]),
    )
    active = active_sector_indices_for_text(token_ids, layout)
    report = transparency_report(mm, meta, active_indices_local=active, sector_idx=0)
    return report


def force_grow_phonetic_text() -> str:
    if not Path(PHONETIC_WEIGHTS).exists() or not Path(PHONETIC_META).exists():
        initialize_brain_file(
            weights_path=PHONETIC_WEIGHTS,
            meta_path=PHONETIC_META,
            force_reinit=False,
        )

    meta = load_meta(PHONETIC_META)
    # Force the next evolve_brain check to grow by stuffing high loss history
    patience = int(meta.get("growth_patience", 8))
    threshold = float(meta.get("growth_threshold", 1.25))
    meta["loss_history"] = [threshold + 0.1] * patience
    save_meta(PHONETIC_META, meta)

    mm, meta, grew = evolve_brain(PHONETIC_WEIGHTS, PHONETIC_META)

    return "\n".join([
        "PHONETIC BRAIN GROW",
        "",
        f"Grew: {grew}",
        f"Sectors: {meta['sector_count']}",
        f"Weights: {PHONETIC_WEIGHTS}",
        f"Meta: {PHONETIC_META}",
    ])


def train_phonetic_once_text(
    state,
    text: str,
    lr: float = DEFAULT_LR,
    weight_decay: float = DEFAULT_WEIGHT_DECAY,
) -> str:
    allowed, reason = phonetic_training_allowed(state)
    if not allowed:
        return "\n".join([
            "PHONETIC TRAIN",
            "",
            f"Blocked: {reason}",
        ])

    mm, meta = initialize_brain_file(
        weights_path=PHONETIC_WEIGHTS,
        meta_path=PHONETIC_META,
        force_reinit=False,
    )

    layout = default_layout(
        vocab_buckets=int(meta["vocab_buckets"]),
        d_model=int(meta["d_model"]),
    )

    phonemes, token_ids = text_to_token_ids(
        text,
        vocab_buckets=layout.vocab_buckets,
        max_seq=int(meta["max_seq"]),
    )

    prompt = build_teacher_prompt(text, phonemes)
    teacher_raw = _gemini_generate_text(state, prompt)
    print("PHONETIC TEACHER RAW")
    print(teacher_raw)

    try:
        teacher = parse_teacher_json(teacher_raw)
    except Exception as e:
        print("PHONETIC TEACHER PARSE FAILED")
        print(repr(e))
        teacher = fallback_teacher_from_phonemes(phonemes)

    teacher_probs = teacher["phoneme_probs"]

    target_probs = teacher_phoneme_probs_to_bucket_target(
        teacher_probs,
        vocab_buckets=layout.vocab_buckets,
    )

    pre = forward_all_sectors(mm, meta, token_ids)
    total_probs_before = pre["total_probs"]
    loss_before = cross_entropy_loss(total_probs_before, target_probs)

    sector_updates = []
    for sector_idx in range(int(meta["sector_count"])):
        info = update_sector_with_revert(
            mm=mm,
            sector_idx=sector_idx,
            meta=meta,
            token_ids=token_ids,
            target_probs=target_probs,
            lr=lr,
            weight_decay=weight_decay,
        )
        sector_updates.append(info)

    mm = open_brain(PHONETIC_WEIGHTS)
    post = forward_all_sectors(mm, meta, token_ids)
    total_probs_after = post["total_probs"]
    loss_after = cross_entropy_loss(total_probs_after, target_probs)

    meta["training_steps"] = int(meta.get("training_steps", 0)) + 1
    loss_history = list(meta.get("loss_history", []))
    loss_history.append(float(loss_after))
    meta["loss_history"] = loss_history[-200:]
    save_meta(PHONETIC_META, meta)

    mm, meta, grew = evolve_brain(PHONETIC_WEIGHTS, PHONETIC_META)
    active = active_sector_indices_for_text(token_ids, layout)
    report = transparency_report(mm, meta, active_indices_local=active, sector_idx=0)

    improved = bool(loss_after <= loss_before)
    _state_update_after_train(state, improved)

    st = state.get("internal_state", {}) or {}
    st["last_phonetic_loss_before"] = float(loss_before)
    st["last_phonetic_loss_after"] = float(loss_after)
    st["last_phonetic_teacher_confidence"] = float(teacher.get("confidence", 0.0) or 0.0)
    st["last_phonetic_grew"] = bool(grew)
    st["last_phonetic_sector_count"] = int(meta["sector_count"])
    st["last_phonetic_text"] = str(text)
    state["internal_state"] = st

    lines = [
        "PHONETIC TRAIN",
        "",
        f"Text: {text}",
        f"Phonemes: {' '.join(phonemes)}",
        f"Teacher confidence: {float(teacher.get('confidence', 0.0) or 0.0):.4f}",
        f"Teacher notes: {str(teacher.get('notes', '') or '')}",
        f"Loss before: {loss_before:.8f}",
        f"Loss after:  {loss_after:.8f}",
        f"Improved: {improved}",
        f"Grew brain: {grew}",
        f"Sectors: {meta['sector_count']}",
        "",
        "Sector updates:",
    ]

    for item in sector_updates:
        lines.append(
            f"  sector={item['sector_idx']} "
            f"old={item['old_loss']:.8f} "
            f"new={item['new_loss']:.8f} "
            f"final={item['final_loss']:.8f} "
            f"reverted={item['reverted']}"
        )

    lines.extend([
        "",
        report,
    ])

    return "\n".join(lines)
