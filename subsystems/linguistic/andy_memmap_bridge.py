#!/usr/bin/env python3
"""
andy_memmap_bridge.py

1MB memory-mapped float32 phonetic distillation bridge for AndyAI.

What this does:
- Initializes a 1MB memmap weights file (262,144 float32 params).
- Converts text -> phonemes using g2p_en.
- Builds a Gemini teacher prompt for phonetic "soft labels".
- Calls Gemini generateContent REST API.
- Applies a simple backprop-style update directly into the memmap.
- Prints a transparency report showing raw float32 values for the active sector.

This is a scratch-built distillation bridge and live training scaffold.
It is NOT a complete Transformer implementation.
It gives you:
- visible weights
- direct memory control
- phonetic token pathway
- teacher-student loop
"""

from __future__ import annotations

import json
import math
import os
import re
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Iterable, Optional

import numpy as np
import requests
from g2p_en import G2p


# ============================================================
# Config
# ============================================================

WEIGHTS_FILE = "andy_brain.weights"
WEIGHTS_BYTES = 1 * 1024 * 1024  # 1MB
FLOAT32_BYTES = 4
PARAM_COUNT = WEIGHTS_BYTES // FLOAT32_BYTES  # 262,144

DEFAULT_MODEL = "gemini-2.0-flash-001"
GEMINI_API_KEY_ENV = "GEMINI_API_KEY"

# Number of memmap indices to activate per phoneme token.
INDICES_PER_TOKEN = 4

# Safety clamp for direct updates.
MIN_WEIGHT = -8.0
MAX_WEIGHT = 8.0

# Small epsilon for normalization.
EPS = 1e-8


# ============================================================
# Data structures
# ============================================================

@dataclass
class DistillationExample:
    text: str
    phonemes: List[str]
    teacher_distribution: Dict[str, float]
    active_indices: List[int]


# ============================================================
# Utilities
# ============================================================

def stable_hash_u64(text: str) -> int:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def softmax(xs: np.ndarray) -> np.ndarray:
    xs = np.asarray(xs, dtype=np.float64)
    m = np.max(xs)
    ex = np.exp(xs - m)
    return ex / (np.sum(ex) + EPS)


def normalize_probabilities(d: Dict[str, float]) -> Dict[str, float]:
    cleaned: Dict[str, float] = {}
    total = 0.0
    for k, v in d.items():
        try:
            fv = float(v)
        except Exception:
            continue
        if fv < 0:
            fv = 0.0
        cleaned[str(k)] = fv
        total += fv

    if total <= EPS:
        return {}

    return {k: v / total for k, v in cleaned.items()}


def top_items(d: Dict[str, float], n: int = 10) -> List[Tuple[str, float]]:
    return sorted(d.items(), key=lambda kv: kv[1], reverse=True)[:n]


# ============================================================
# 1MB memmap brain
# ============================================================

def initialize_weights_file(
    path: str = WEIGHTS_FILE,
    seed: int = 1337,
    init_scale: float = 0.01,
    force_reinit: bool = False,
) -> np.memmap:
    """
    Create a 1MB float32 memmap file if needed.
    1MB / 4 bytes = 262,144 params.
    """
    p = Path(path)
    mode = "r+" if p.exists() and not force_reinit else "w+"

    mm = np.memmap(path, dtype=np.float32, mode=mode, shape=(PARAM_COUNT,))

    if mode == "w+":
        rng = np.random.default_rng(seed)
        mm[:] = rng.normal(loc=0.0, scale=init_scale, size=PARAM_COUNT).astype(np.float32)
        mm.flush()

    return mm


def open_weights(path: str = WEIGHTS_FILE) -> np.memmap:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Missing weights file: {path}. Run initialize_weights_file() first.")
    return np.memmap(path, dtype=np.float32, mode="r+", shape=(PARAM_COUNT,))


# ============================================================
# Phoneme tokenization
# ============================================================

_G2P = G2p()


def text_to_phonemes(text: str) -> List[str]:
    """
    Convert English text to ARPAbet-ish phoneme sequence using g2p_en.
    Filter whitespace/punctuation-like items but keep meaningful phones.
    """
    raw = _G2P(text)

    phonemes: List[str] = []
    for tok in raw:
        t = str(tok).strip()
        if not t:
            continue

        # Drop spaces and punctuation-only tokens.
        if re.fullmatch(r"[\s\.,;:\?!\"'\-\(\)\[\]\{\}/\\]+", t):
            continue

        phonemes.append(t)

    return phonemes


# ============================================================
# Active sector mapping
# ============================================================

def phoneme_to_indices(
    phoneme: str,
    total_params: int = PARAM_COUNT,
    k: int = INDICES_PER_TOKEN,
) -> List[int]:
    """
    Deterministically map one phoneme to k indices in the 1MB brain.
    """
    base = stable_hash_u64(f"phoneme::{phoneme}")
    indices: List[int] = []

    for i in range(k):
        h = stable_hash_u64(f"{phoneme}::{i}::{base}")
        idx = h % total_params
        indices.append(idx)

    # Preserve order, remove accidental duplicates
    seen = set()
    out: List[int] = []
    for idx in indices:
        if idx not in seen:
            seen.add(idx)
            out.append(idx)
    return out


def text_to_active_indices(
    phonemes: Iterable[str],
    total_params: int = PARAM_COUNT,
    k: int = INDICES_PER_TOKEN,
) -> List[int]:
    indices: List[int] = []
    seen = set()

    for ph in phonemes:
        for idx in phoneme_to_indices(ph, total_params=total_params, k=k):
            if idx not in seen:
                seen.add(idx)
                indices.append(idx)

    return indices


# ============================================================
# Gemini teacher prompt + API call
# ============================================================

def build_teacher_prompt(text: str, phonemes: List[str]) -> str:
    """
    Prompt Gemini for soft labels over the phoneme sequence.
    Output format is deliberately strict JSON for easier parsing.
    """
    phones_json = json.dumps(phonemes, ensure_ascii=False)

    return f"""
You are a phonetic teacher model for a tiny experimental student brain.

Task:
Given the original text and its phoneme sequence, return a JSON object with:
1. "phoneme_probs": a probability distribution over the phonemes present
2. "confidence": teacher confidence from 0.0 to 1.0
3. "notes": a short diagnostic string

Rules:
- Return JSON only. No markdown.
- "phoneme_probs" keys must be phoneme strings.
- Values must be floats between 0 and 1.
- Probabilities should sum to about 1.0.
- Emphasize phonemes that are most informative for pronunciation identity.

Text:
{text}

Phonemes:
{phones_json}

Required JSON schema:
{{
  "phoneme_probs": {{
    "PHONEME": 0.123
  }},
  "confidence": 0.95,
  "notes": "short explanation"
}}
""".strip()


def call_gemini_teacher(
    prompt: str,
    model: str = DEFAULT_MODEL,
    api_key: Optional[str] = None,
    timeout_s: int = 45,
) -> Dict[str, object]:
    """
    REST call to Gemini generateContent.
    Official Gemini docs describe generateContent as a primary REST endpoint. 1
    """
    key = api_key or os.getenv(GEMINI_API_KEY_ENV)
    if not key:
        raise RuntimeError(f"Missing Gemini API key. Set {GEMINI_API_KEY_ENV}.")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    resp = requests.post(url, json=payload, timeout=timeout_s)
    resp.raise_for_status()
    data = resp.json()

    text = extract_text_from_gemini_response(data)
    parsed = parse_teacher_json(text)
    return parsed


def extract_text_from_gemini_response(data: Dict[str, object]) -> str:
    """
    Extract text from Gemini REST response.
    """
    try:
        candidates = data.get("candidates", [])
        if not candidates:
            raise ValueError("No candidates in Gemini response.")

        content = candidates[0]["content"]
        parts = content.get("parts", [])
        texts = [p.get("text", "") for p in parts if isinstance(p, dict)]
        out = "\n".join(t for t in texts if t)
        if not out.strip():
            raise ValueError("Gemini response contained no text parts.")
        return out.strip()
    except Exception as e:
        raise RuntimeError(f"Failed to extract text from Gemini response: {e}") from e


def parse_teacher_json(text: str) -> Dict[str, object]:
    """
    Parse JSON from Gemini text. Handles fenced blocks too.
    """
    cleaned = text.strip()

    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if len(lines) >= 3:
            cleaned = "\n".join(lines[1:-1]).strip()

    try:
        data = json.loads(cleaned)
    except Exception as e:
        raise RuntimeError(f"Teacher did not return valid JSON. Raw reply:\n{cleaned}") from e

    phoneme_probs = normalize_probabilities(data.get("phoneme_probs", {}) or {})
    confidence = float(data.get("confidence", 0.0) or 0.0)
    notes = str(data.get("notes", "") or "")

    return {
        "phoneme_probs": phoneme_probs,
        "confidence": confidence,
        "notes": notes,
        "raw_text": text,
    }


# ============================================================
# Student readout + update
# ============================================================

def read_student_logits_for_phonemes(
    weights: np.memmap,
    phonemes: List[str],
) -> Dict[str, float]:
    """
    Build one scalar logit per phoneme by averaging its mapped indices.
    """
    logits: Dict[str, float] = {}

    unique_phonemes = []
    seen = set()
    for ph in phonemes:
        if ph not in seen:
            seen.add(ph)
            unique_phonemes.append(ph)

    for ph in unique_phonemes:
        idxs = phoneme_to_indices(ph)
        vals = weights[idxs].astype(np.float64)
        logits[ph] = float(np.mean(vals))

    return logits


def student_distribution_from_logits(logits: Dict[str, float]) -> Dict[str, float]:
    keys = list(logits.keys())
    if not keys:
        return {}
    arr = np.array([logits[k] for k in keys], dtype=np.float64)
    probs = softmax(arr)
    return {k: float(p) for k, p in zip(keys, probs)}


def update_weights_from_teacher(
    weights: np.memmap,
    phonemes: List[str],
    teacher_probs: Dict[str, float],
    lr: float = 0.10,
    weight_decay: float = 0.0005,
) -> Dict[str, object]:
    """
    Basic backprop-style direct rewrite:
    - student forms a phoneme distribution from current weights
    - error = teacher_prob - student_prob
    - each phoneme's mapped indices are nudged in proportion to error

    This is intentionally simple and transparent.
    """
    logits = read_student_logits_for_phonemes(weights, phonemes)
    student_probs = student_distribution_from_logits(logits)

    updates = []
    total_abs_delta = 0.0

    unique_phonemes = list(student_probs.keys())
    for ph in unique_phonemes:
        t = float(teacher_probs.get(ph, 0.0))
        s = float(student_probs.get(ph, 0.0))
        error = t - s

        idxs = phoneme_to_indices(ph)
        current_vals = weights[idxs].astype(np.float64)

        # Gradient-like update toward teacher.
        # Also lightly decay weights to avoid runaway drift.
        delta = (lr * error) - (weight_decay * current_vals)
        new_vals = current_vals + delta
        new_vals = np.clip(new_vals, MIN_WEIGHT, MAX_WEIGHT)

        weights[idxs] = new_vals.astype(np.float32)

        total_abs_delta += float(np.sum(np.abs(delta)))
        updates.append({
            "phoneme": ph,
            "teacher_prob": t,
            "student_prob": s,
            "error": error,
            "indices": idxs,
            "mean_before": float(np.mean(current_vals)),
            "mean_after": float(np.mean(new_vals)),
        })

    weights.flush()

    return {
        "student_probs_before": student_probs,
        "teacher_probs": teacher_probs,
        "total_abs_delta": total_abs_delta,
        "updates": updates,
    }


# ============================================================
# Transparency
# ============================================================

def transparency_report(
    weights: np.memmap,
    indices: List[int],
    max_rows: int = 64,
) -> str:
    """
    Print raw float32 values of the active weight sector.
    """
    lines = [
        "TRANSPARENCY REPORT",
        "",
        f"Active indices shown: {min(len(indices), max_rows)} / {len(indices)}",
        "index | raw_float32",
        "-------------------",
    ]

    for idx in indices[:max_rows]:
        val = float(weights[idx])
        lines.append(f"{idx:6d} | {val:+.8f}")

    return "\n".join(lines)


# ============================================================
# High-level training bridge
# ============================================================

def distill_text_once(
    text: str,
    weights_path: str = WEIGHTS_FILE,
    model: str = DEFAULT_MODEL,
    api_key: Optional[str] = None,
    lr: float = 0.10,
    weight_decay: float = 0.0005,
) -> Dict[str, object]:
    """
    End-to-end one-step teacher-student distillation:
    text -> phonemes -> Gemini soft labels -> direct memmap update
    """
    weights = open_weights(weights_path)

    phonemes = text_to_phonemes(text)
    active_indices = text_to_active_indices(phonemes)

    prompt = build_teacher_prompt(text, phonemes)
    teacher = call_gemini_teacher(prompt, model=model, api_key=api_key)
    teacher_probs = teacher["phoneme_probs"]

    update_info = update_weights_from_teacher(
        weights=weights,
        phonemes=phonemes,
        teacher_probs=teacher_probs,
        lr=lr,
        weight_decay=weight_decay,
    )

    report = transparency_report(weights, active_indices)

    return {
        "text": text,
        "phonemes": phonemes,
        "active_indices": active_indices,
        "teacher_confidence": float(teacher.get("confidence", 0.0) or 0.0),
        "teacher_notes": str(teacher.get("notes", "") or ""),
        "teacher_probs": teacher_probs,
        "student_probs_before": update_info["student_probs_before"],
        "total_abs_delta": update_info["total_abs_delta"],
        "updates": update_info["updates"],
        "transparency_report": report,
        "teacher_prompt": prompt,
        "teacher_raw_text": teacher.get("raw_text", ""),
    }


# ============================================================
# CLI demo
# ============================================================

def print_distillation_summary(result: Dict[str, object]) -> None:
    print("\n=== DISTILLATION SUMMARY ===")
    print(f"Text: {result['text']}")
    print(f"Phonemes: {' '.join(result['phonemes'])}")
    print(f"Teacher confidence: {result['teacher_confidence']:.4f}")
    print(f"Teacher notes: {result['teacher_notes']}")
    print(f"Active indices: {len(result['active_indices'])}")
    print(f"Total |delta|: {result['total_abs_delta']:.8f}")

    print("\nTop teacher probs:")
    for k, v in top_items(result["teacher_probs"], 10):
        print(f"  {k:>8s} : {v:.6f}")

    print("\nTop student probs before update:")
    for k, v in top_items(result["student_probs_before"], 10):
        print(f"  {k:>8s} : {v:.6f}")

    print("\nFirst updates:")
    for item in result["updates"][:10]:
        print(
            f"  {item['phoneme']:>8s} | "
            f"t={item['teacher_prob']:.5f} "
            f"s={item['student_prob']:.5f} "
            f"err={item['error']:+.5f} "
            f"mean_before={item['mean_before']:+.6f} "
            f"mean_after={item['mean_after']:+.6f}"
        )

    print()
    print(result["transparency_report"])


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="AndyAI 1MB memmap phonetic distillation bridge")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="Initialize 1MB float32 memmap weights file")
    p_init.add_argument("--path", default=WEIGHTS_FILE)
    p_init.add_argument("--seed", type=int, default=1337)
    p_init.add_argument("--init-scale", type=float, default=0.01)
    p_init.add_argument("--force", action="store_true")

    p_g2p = sub.add_parser("g2p", help="Convert text to phonemes")
    p_g2p.add_argument("text")

    p_report = sub.add_parser("report", help="Print transparency report for text's active sector")
    p_report.add_argument("text")
    p_report.add_argument("--path", default=WEIGHTS_FILE)
    p_report.add_argument("--rows", type=int, default=64)

    p_train = sub.add_parser("train_once", help="Teacher-student distillation step")
    p_train.add_argument("text")
    p_train.add_argument("--path", default=WEIGHTS_FILE)
    p_train.add_argument("--model", default=DEFAULT_MODEL)
    p_train.add_argument("--lr", type=float, default=0.10)
    p_train.add_argument("--weight-decay", type=float, default=0.0005)

    args = parser.parse_args()

    if args.cmd == "init":
        mm = initialize_weights_file(
            path=args.path,
            seed=args.seed,
            init_scale=args.init_scale,
            force_reinit=args.force,
        )
        print(f"Initialized {args.path}")
        print(f"Params: {PARAM_COUNT}")
        print(f"Bytes: {WEIGHTS_BYTES}")
        print(f"dtype: {mm.dtype}")
        return

    if args.cmd == "g2p":
        phonemes = text_to_phonemes(args.text)
        print(json.dumps({"text": args.text, "phonemes": phonemes}, indent=2))
        return

    if args.cmd == "report":
        mm = open_weights(args.path)
        phonemes = text_to_phonemes(args.text)
        idxs = text_to_active_indices(phonemes)
        print(transparency_report(mm, idxs, max_rows=args.rows))
        return

    if args.cmd == "train_once":
        result = distill_text_once(
            text=args.text,
            weights_path=args.path,
            model=args.model,
            lr=args.lr,
            weight_decay=args.weight_decay,
        )
        print_distillation_summary(result)
        return


if __name__ == "__main__":
    main()
