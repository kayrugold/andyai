#!/usr/bin/env python3
"""
andy_memmap_core.py

Pure NumPy + memmap phonetic Transformer core for AndyAI.

Core ideas:
- 1MB sectors of float32 weights
- each sector contains:
    token embeddings
    Q, K, V
    output projection
    classifier head
    reserve space
- single-head scaled dot-product attention
- sinusoidal positional encoding
- direct memmap updates
- sector-level rollback if a training step worsens loss
- file growth by appending another 1MB sector

This is designed as a module/organ for AndyAI.
AndyAI remains the controller. This memmap brain is a learnable subsystem.
"""

from __future__ import annotations

import json
import math
import os
import re
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

import numpy as np
import requests
from g2p_en import G2p


# ============================================================
# Constants
# ============================================================

SECTOR_BYTES = 1 * 1024 * 1024
FLOAT32_BYTES = 4
SECTOR_FLOATS = SECTOR_BYTES // FLOAT32_BYTES  # 262,144

DEFAULT_WEIGHTS = "andy_brain.weights"
DEFAULT_META = "andy_brain.meta.json"

DEFAULT_MODEL = "gemini-2.0-flash-001"
GEMINI_API_KEY_ENV = "GEMINI_API_KEY"

# Chosen to fit comfortably in 1MB with reserve left over.
DEFAULT_D_MODEL = 64
DEFAULT_VOCAB_BUCKETS = 256
DEFAULT_MAX_SEQ = 64

# Training defaults
DEFAULT_LR = 0.02
DEFAULT_WEIGHT_DECAY = 0.0005
DEFAULT_GROWTH_THRESHOLD = 1.25
DEFAULT_GROWTH_PATIENCE = 8

# Safety clamps
MIN_WEIGHT = -8.0
MAX_WEIGHT = 8.0
EPS = 1e-8

_G2P = G2p()


# ============================================================
# Data structures
# ============================================================

@dataclass
class Layout:
    vocab_buckets: int
    d_model: int
    sector_floats: int
    emb_size: int
    q_size: int
    k_size: int
    v_size: int
    o_size: int
    cls_size: int
    reserve_size: int


# ============================================================
# Basic utilities
# ============================================================

def stable_hash_u64(text: str) -> int:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=False)


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def softmax_1d(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=np.float64)
    m = np.max(x)
    ex = np.exp(x - m)
    return ex / (np.sum(ex) + EPS)


def softmax_rows(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=np.float64)
    m = np.max(x, axis=1, keepdims=True)
    ex = np.exp(x - m)
    return ex / (np.sum(ex, axis=1, keepdims=True) + EPS)


def normalize_probs(d: Dict[str, float]) -> Dict[str, float]:
    clean: Dict[str, float] = {}
    total = 0.0
    for k, v in d.items():
        try:
            fv = float(v)
        except Exception:
            continue
        if fv < 0:
            fv = 0.0
        clean[str(k)] = fv
        total += fv
    if total <= EPS:
        return {}
    return {k: v / total for k, v in clean.items()}


def top_items(d: Dict[str, float], n: int = 10) -> List[Tuple[str, float]]:
    return sorted(d.items(), key=lambda kv: kv[1], reverse=True)[:n]


# ============================================================
# Meta + layout
# ============================================================

def default_layout(
    vocab_buckets: int = DEFAULT_VOCAB_BUCKETS,
    d_model: int = DEFAULT_D_MODEL,
    sector_floats: int = SECTOR_FLOATS,
) -> Layout:
    emb_size = vocab_buckets * d_model
    q_size = d_model * d_model
    k_size = d_model * d_model
    v_size = d_model * d_model
    o_size = d_model * d_model
    cls_size = d_model * vocab_buckets

    used = emb_size + q_size + k_size + v_size + o_size + cls_size
    reserve = sector_floats - used
    if reserve < 0:
        raise ValueError(
            f"Layout too large for one sector. "
            f"Need {used} floats, sector has {sector_floats}."
        )

    return Layout(
        vocab_buckets=vocab_buckets,
        d_model=d_model,
        sector_floats=sector_floats,
        emb_size=emb_size,
        q_size=q_size,
        k_size=k_size,
        v_size=v_size,
        o_size=o_size,
        cls_size=cls_size,
        reserve_size=reserve,
    )


def save_meta(meta_path: str, meta: Dict[str, Any]) -> None:
    Path(meta_path).write_text(json.dumps(meta, indent=2), encoding="utf-8")


def load_meta(meta_path: str) -> Dict[str, Any]:
    p = Path(meta_path)
    if not p.exists():
        raise FileNotFoundError(f"Missing meta file: {meta_path}")
    return json.loads(p.read_text(encoding="utf-8"))


def init_meta(
    weights_path: str = DEFAULT_WEIGHTS,
    meta_path: str = DEFAULT_META,
    vocab_buckets: int = DEFAULT_VOCAB_BUCKETS,
    d_model: int = DEFAULT_D_MODEL,
    max_seq: int = DEFAULT_MAX_SEQ,
) -> Dict[str, Any]:
    layout = default_layout(vocab_buckets=vocab_buckets, d_model=d_model)
    meta = {
        "weights_path": weights_path,
        "sector_bytes": SECTOR_BYTES,
        "sector_floats": SECTOR_FLOATS,
        "sector_count": 1,
        "vocab_buckets": vocab_buckets,
        "d_model": d_model,
        "max_seq": max_seq,
        "growth_threshold": DEFAULT_GROWTH_THRESHOLD,
        "growth_patience": DEFAULT_GROWTH_PATIENCE,
        "loss_history": [],
        "training_steps": 0,
    }
    save_meta(meta_path, meta)
    return meta


# ============================================================
# Brain file init / open / grow
# ============================================================

def initialize_brain_file(
    weights_path: str = DEFAULT_WEIGHTS,
    meta_path: str = DEFAULT_META,
    seed: int = 1337,
    init_scale: float = 0.02,
    force_reinit: bool = False,
) -> Tuple[np.memmap, Dict[str, Any]]:
    """
    Create initial 1MB weights file + metadata.
    """
    p = Path(weights_path)
    if p.exists() and not force_reinit:
        meta = load_meta(meta_path)
        mm = open_brain(weights_path)
        return mm, meta

    meta = init_meta(weights_path=weights_path, meta_path=meta_path)
    rng = np.random.default_rng(seed)

    mm = np.memmap(weights_path, dtype=np.float32, mode="w+", shape=(SECTOR_FLOATS,))
    mm[:] = rng.normal(loc=0.0, scale=init_scale, size=SECTOR_FLOATS).astype(np.float32)
    mm.flush()
    return mm, meta


def open_brain(weights_path: str = DEFAULT_WEIGHTS) -> np.memmap:
    size = Path(weights_path).stat().st_size
    if size % FLOAT32_BYTES != 0:
        raise ValueError(f"Weights file size is not float32 aligned: {size}")
    total_floats = size // FLOAT32_BYTES
    return np.memmap(weights_path, dtype=np.float32, mode="r+", shape=(total_floats,))


def remap_brain(weights_path: str = DEFAULT_WEIGHTS) -> np.memmap:
    return open_brain(weights_path)


def sector_count_from_file(weights_path: str = DEFAULT_WEIGHTS) -> int:
    size = Path(weights_path).stat().st_size
    if size % SECTOR_BYTES != 0:
        raise ValueError("Weights file is not aligned to 1MB sectors.")
    return size // SECTOR_BYTES


def evolve_brain(
    weights_path: str,
    meta_path: str,
    trigger_loss: Optional[float] = None,
    patience: Optional[int] = None,
    seed: Optional[int] = None,
    init_scale: float = 0.02,
) -> Tuple[np.memmap, Dict[str, Any], bool]:
    """
    Growth protocol:
    If recent losses remain high, append a new 1MB sector and remap immediately.
    """
    meta = load_meta(meta_path)
    loss_history = list(meta.get("loss_history", []))
    threshold = float(trigger_loss if trigger_loss is not None else meta.get("growth_threshold", DEFAULT_GROWTH_THRESHOLD))
    patience_n = int(patience if patience is not None else meta.get("growth_patience", DEFAULT_GROWTH_PATIENCE))

    should_grow = False
    if len(loss_history) >= patience_n:
        tail = loss_history[-patience_n:]
        if all(float(x) > threshold for x in tail):
            should_grow = True

    if not should_grow:
        mm = remap_brain(weights_path)
        return mm, meta, False

    current_size = Path(weights_path).stat().st_size
    new_size = current_size + SECTOR_BYTES

    with open(weights_path, "r+b") as f:
        f.truncate(new_size)

    mm = remap_brain(weights_path)

    new_sector_idx = (new_size // SECTOR_BYTES) - 1
    start = new_sector_idx * SECTOR_FLOATS
    end = start + SECTOR_FLOATS

    rng_seed = int(seed if seed is not None else (1337 + new_sector_idx))
    rng = np.random.default_rng(rng_seed)
    mm[start:end] = rng.normal(loc=0.0, scale=init_scale, size=SECTOR_FLOATS).astype(np.float32)
    mm.flush()

    meta["sector_count"] = sector_count_from_file(weights_path)
    save_meta(meta_path, meta)
    return mm, meta, True


# ============================================================
# Sector layout views
# ============================================================

def sector_bounds(sector_idx: int) -> Tuple[int, int]:
    start = sector_idx * SECTOR_FLOATS
    end = start + SECTOR_FLOATS
    return start, end


def sector_slices(layout: Layout) -> Dict[str, slice]:
    pos = 0
    out = {}

    out["emb"] = slice(pos, pos + layout.emb_size)
    pos += layout.emb_size

    out["Wq"] = slice(pos, pos + layout.q_size)
    pos += layout.q_size

    out["Wk"] = slice(pos, pos + layout.k_size)
    pos += layout.k_size

    out["Wv"] = slice(pos, pos + layout.v_size)
    pos += layout.v_size

    out["Wo"] = slice(pos, pos + layout.o_size)
    pos += layout.o_size

    out["Wcls"] = slice(pos, pos + layout.cls_size)
    pos += layout.cls_size

    out["reserve"] = slice(pos, pos + layout.reserve_size)
    pos += layout.reserve_size

    return out


def get_sector_views(mm: np.memmap, sector_idx: int, layout: Layout) -> Dict[str, np.ndarray]:
    base_start, base_end = sector_bounds(sector_idx)
    raw = mm[base_start:base_end]
    sl = sector_slices(layout)

    views = {
        "raw": raw,
        "emb": raw[sl["emb"]].reshape(layout.vocab_buckets, layout.d_model),
        "Wq": raw[sl["Wq"]].reshape(layout.d_model, layout.d_model),
        "Wk": raw[sl["Wk"]].reshape(layout.d_model, layout.d_model),
        "Wv": raw[sl["Wv"]].reshape(layout.d_model, layout.d_model),
        "Wo": raw[sl["Wo"]].reshape(layout.d_model, layout.d_model),
        "Wcls": raw[sl["Wcls"]].reshape(layout.d_model, layout.vocab_buckets),
        "reserve": raw[sl["reserve"]],
    }
    return views


# ============================================================
# Phoneme tokenization / indexing
# ============================================================

def text_to_phonemes(text: str) -> List[str]:
    raw = _G2P(text)
    phonemes: List[str] = []

    for tok in raw:
        t = str(tok).strip()
        if not t:
            continue
        if re.fullmatch(r"[\s\.,;:\?!\"'\-\(\)\[\]\{\}/\\]+", t):
            continue
        phonemes.append(t)

    return phonemes


def phoneme_to_bucket(phoneme: str, vocab_buckets: int) -> int:
    return stable_hash_u64(f"ph::{phoneme}") % vocab_buckets


def text_to_token_ids(text: str, vocab_buckets: int, max_seq: int) -> Tuple[List[str], np.ndarray]:
    phonemes = text_to_phonemes(text)
    if not phonemes:
        phonemes = ["AH0"]

    phonemes = phonemes[:max_seq]
    ids = np.array([phoneme_to_bucket(ph, vocab_buckets) for ph in phonemes], dtype=np.int64)
    return phonemes, ids


# ============================================================
# Positional encoding
# ============================================================

def sinusoidal_positional_encoding(seq_len: int, d_model: int) -> np.ndarray:
    """
    Standard sinusoidal positional encoding in pure NumPy.
    """
    pe = np.zeros((seq_len, d_model), dtype=np.float32)
    pos = np.arange(seq_len, dtype=np.float32)[:, None]
    i = np.arange(d_model, dtype=np.float32)[None, :]

    angle_rates = 1.0 / np.power(10000.0, (2.0 * (i // 2)) / float(d_model))
    angles = pos * angle_rates

    pe[:, 0::2] = np.sin(angles[:, 0::2])
    pe[:, 1::2] = np.cos(angles[:, 1::2])
    return pe


# ============================================================
# Attention
# ============================================================

def scaled_dot_product_attention(
    Q: np.ndarray,
    K: np.ndarray,
    V: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Single-head scaled dot-product attention.

    Returns:
    - context
    - attention weights
    - raw scores
    """
    dk = Q.shape[1]
    scores = (Q @ K.T) / math.sqrt(max(dk, 1))
    A = softmax_rows(scores)
    context = A @ V
    return context, A, scores


# ============================================================
# Forward pass per sector + summed sectors
# ============================================================

def forward_sector(
    views: Dict[str, np.ndarray],
    token_ids: np.ndarray,
    pos_enc: np.ndarray,
) -> Dict[str, np.ndarray]:
    emb_table = views["emb"]
    Wq = views["Wq"]
    Wk = views["Wk"]
    Wv = views["Wv"]
    Wo = views["Wo"]
    Wcls = views["Wcls"]

    E = emb_table[token_ids].astype(np.float64) + pos_enc.astype(np.float64)  # [T, D]
    Q = E @ Wq
    K = E @ Wk
    V = E @ Wv

    C, A, S = scaled_dot_product_attention(Q, K, V)
    H = C @ Wo
    pooled = np.mean(H, axis=0)  # [D]
    logits = pooled @ Wcls       # [Vocab]

    probs = softmax_1d(logits)

    return {
        "E": E,
        "Q": Q,
        "K": K,
        "V": V,
        "A": A,
        "S": S,
        "C": C,
        "H": H,
        "pooled": pooled,
        "logits": logits,
        "probs": probs,
    }


def forward_all_sectors(
    mm: np.memmap,
    meta: Dict[str, Any],
    token_ids: np.ndarray,
) -> Dict[str, Any]:
    layout = default_layout(
        vocab_buckets=int(meta["vocab_buckets"]),
        d_model=int(meta["d_model"]),
    )
    seq_len = len(token_ids)
    pos_enc = sinusoidal_positional_encoding(seq_len, int(meta["d_model"]))

    sector_outputs = []
    total_logits = np.zeros((layout.vocab_buckets,), dtype=np.float64)

    sector_count = int(meta["sector_count"])
    for sector_idx in range(sector_count):
        views = get_sector_views(mm, sector_idx, layout)
        out = forward_sector(views, token_ids, pos_enc)
        sector_outputs.append(out)
        total_logits += out["logits"]

    total_probs = softmax_1d(total_logits)

    return {
        "layout": layout,
        "pos_enc": pos_enc,
        "sector_outputs": sector_outputs,
        "total_logits": total_logits,
        "total_probs": total_probs,
    }


# ============================================================
# Teacher bridge
# ============================================================

def build_teacher_prompt(text: str, phonemes: List[str]) -> str:
    phones_json = json.dumps(phonemes, ensure_ascii=False)

    return f"""
Return STRICT JSON ONLY on ONE LINE.

Use this exact schema:
{{"phoneme_probs":{{"PH":0.123}},"confidence":0.95,"notes":"short"}}

Rules:
- One line only
- JSON only
- No markdown
- No prose
- Use only phonemes from the provided list as keys
- Probabilities should sum to about 1.0
- Keep notes very short

Text: {text}
Phonemes: {phones_json}
""".strip()

def extract_text_from_gemini_response(data: Dict[str, Any]) -> str:
    try:
        candidates = data.get("candidates", [])
        content = candidates[0]["content"]
        parts = content.get("parts", [])
        texts = [p.get("text", "") for p in parts if isinstance(p, dict)]
        out = "\n".join(x for x in texts if x)
        if not out.strip():
            raise ValueError("No text in Gemini response.")
        return out.strip()
    except Exception as e:
        raise RuntimeError(f"Failed to extract Gemini text: {e}") from e


def parse_teacher_json(text: str) -> Dict[str, Any]:
    cleaned = text.strip()

    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if len(lines) >= 3:
            cleaned = "\n".join(lines[1:-1]).strip()

    match = re.search(r"\{.*\}", cleaned, re.S)
    if match:
        cleaned = match.group(0)

    data = json.loads(cleaned)

    probs = normalize_probs(data.get("phoneme_probs", {}) or {})
    conf = float(data.get("confidence", 0.0) or 0.0)
    notes = str(data.get("notes", "") or "")

    return {
        "phoneme_probs": probs,
        "confidence": conf,
        "notes": notes,
        "raw_text": text,
    }

def call_gemini_teacher(
    prompt: str,
    model: str = DEFAULT_MODEL,
    api_key: Optional[str] = None,
    timeout_s: int = 45,
) -> Dict[str, Any]:
    key = api_key or os.getenv(GEMINI_API_KEY_ENV)
    if not key:
        raise RuntimeError(f"Missing Gemini API key. Set {GEMINI_API_KEY_ENV}.")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ]
    }

    resp = requests.post(url, json=payload, timeout=timeout_s)
    resp.raise_for_status()
    data = resp.json()
    text = extract_text_from_gemini_response(data)
    return parse_teacher_json(text)


# ============================================================
# Target building + loss
# ============================================================

def fallback_teacher_from_phonemes(phonemes: List[str]) -> Dict[str, Any]:
    counts: Dict[str, float] = {}
    total = 0.0

    for i, ph in enumerate(phonemes):
        # later phonemes get slightly more weight to preserve sequence emphasis
        w = 1.0 + (0.05 * i)
        counts[ph] = counts.get(ph, 0.0) + w
        total += w

    if total <= EPS:
        return {
            "phoneme_probs": {},
            "confidence": 0.0,
            "notes": "fallback-empty",
            "raw_text": "",
        }

    probs = {k: v / total for k, v in counts.items()}
    return {
        "phoneme_probs": probs,
        "confidence": 0.25,
        "notes": "fallback-local-teacher",
        "raw_text": "",
    }


def teacher_phoneme_probs_to_bucket_target(
    phoneme_probs: Dict[str, float],
    vocab_buckets: int,
) -> np.ndarray:
    target = np.zeros((vocab_buckets,), dtype=np.float64)

    for ph, p in phoneme_probs.items():
        idx = phoneme_to_bucket(ph, vocab_buckets)
        target[idx] += float(p)

    s = np.sum(target)
    if s <= EPS:
        # fallback to uniform tiny distribution
        target += 1.0 / vocab_buckets
        s = np.sum(target)
    target /= s
    return target


def cross_entropy_loss(pred_probs: np.ndarray, target_probs: np.ndarray) -> float:
    pred = np.clip(pred_probs.astype(np.float64), EPS, 1.0)
    targ = np.clip(target_probs.astype(np.float64), 0.0, 1.0)
    return float(-np.sum(targ * np.log(pred + EPS)))


# ============================================================
# Backprop-style update, sector-by-sector
# ============================================================

def update_sector_with_revert(
    mm: np.memmap,
    sector_idx: int,
    meta: Dict[str, Any],
    token_ids: np.ndarray,
    target_probs: np.ndarray,
    lr: float = DEFAULT_LR,
    weight_decay: float = DEFAULT_WEIGHT_DECAY,
) -> Dict[str, Any]:
    """
    Manual gradient update for one sector.
    If the post-update loss is worse, revert this sector.
    """
    layout = default_layout(
        vocab_buckets=int(meta["vocab_buckets"]),
        d_model=int(meta["d_model"]),
    )
    pos_enc = sinusoidal_positional_encoding(len(token_ids), int(meta["d_model"]))
    views = get_sector_views(mm, sector_idx, layout)

    # Snapshot this sector for rollback
    snapshot = np.array(views["raw"], copy=True)

    # Forward
    out = forward_sector(views, token_ids, pos_enc)
    probs = out["probs"]
    old_loss = cross_entropy_loss(probs, target_probs)

    E = out["E"]                  # [T, D]
    Q = out["Q"]                  # [T, D]
    K = out["K"]                  # [T, D]
    V = out["V"]                  # [T, D]
    A = out["A"]                  # [T, T]
    C = out["C"]                  # [T, D]
    H = out["H"]                  # [T, D]
    pooled = out["pooled"]        # [D]

    Wq = views["Wq"].astype(np.float64)
    Wk = views["Wk"].astype(np.float64)
    Wv = views["Wv"].astype(np.float64)
    Wo = views["Wo"].astype(np.float64)
    Wcls = views["Wcls"].astype(np.float64)

    T = len(token_ids)
    D = layout.d_model

    # logits = pooled @ Wcls
    dlogits = (probs - target_probs)  # [Vocab]
    dWcls = np.outer(pooled, dlogits) + weight_decay * Wcls
    dpooled = Wcls @ dlogits  # [D]

    # pooled = mean(H)
    dH = np.repeat((dpooled / T)[None, :], T, axis=0)  # [T, D]

    # H = C @ Wo
    dWo = C.T @ dH + weight_decay * Wo
    dC = dH @ Wo.T

    # C = A @ V
    dV = A.T @ dC
    dA = dC @ V.T

    # A = softmax_rows(S)
    # For each row:
    # dS = A * (dA - sum(dA*A))
    row_dot = np.sum(dA * A, axis=1, keepdims=True)
    dS = A * (dA - row_dot)

    scale = 1.0 / math.sqrt(D)
    # S = Q @ K.T * scale
    dQ = dS @ K * scale
    dK = dS.T @ Q * scale

    # Q = E @ Wq
    # K = E @ Wk
    # V = E @ Wv
    dWq = E.T @ dQ + weight_decay * Wq
    dWk = E.T @ dK + weight_decay * Wk
    dWv = E.T @ dV + weight_decay * Wv

    dE = dQ @ Wq.T + dK @ Wk.T + dV @ Wv.T  # [T, D]

    # Apply updates
    views["Wcls"][:] = np.clip(Wcls - lr * dWcls, MIN_WEIGHT, MAX_WEIGHT).astype(np.float32)
    views["Wo"][:] = np.clip(Wo - lr * dWo, MIN_WEIGHT, MAX_WEIGHT).astype(np.float32)
    views["Wq"][:] = np.clip(Wq - lr * dWq, MIN_WEIGHT, MAX_WEIGHT).astype(np.float32)
    views["Wk"][:] = np.clip(Wk - lr * dWk, MIN_WEIGHT, MAX_WEIGHT).astype(np.float32)
    views["Wv"][:] = np.clip(Wv - lr * dWv, MIN_WEIGHT, MAX_WEIGHT).astype(np.float32)

    emb = views["emb"].astype(np.float64)
    for t, tok_id in enumerate(token_ids):
        emb[tok_id] = np.clip(emb[tok_id] - lr * dE[t], MIN_WEIGHT, MAX_WEIGHT)
    views["emb"][:] = emb.astype(np.float32)

    mm.flush()

    # Re-evaluate only this sector
    new_views = get_sector_views(mm, sector_idx, layout)
    new_out = forward_sector(new_views, token_ids, pos_enc)
    new_loss = cross_entropy_loss(new_out["probs"], target_probs)

    reverted = False
    if new_loss > old_loss + 1e-8:
        # revert this sector
        views["raw"][:] = snapshot.astype(np.float32)
        mm.flush()
        reverted = True
        final_loss = old_loss
    else:
        final_loss = new_loss

    return {
        "sector_idx": sector_idx,
        "old_loss": old_loss,
        "new_loss": new_loss,
        "final_loss": final_loss,
        "reverted": reverted,
    }


def train_step_with_teacher(
    text: str,
    weights_path: str = DEFAULT_WEIGHTS,
    meta_path: str = DEFAULT_META,
    model: str = DEFAULT_MODEL,
    api_key: Optional[str] = None,
    lr: float = DEFAULT_LR,
    weight_decay: float = DEFAULT_WEIGHT_DECAY,
) -> Dict[str, Any]:
    """
    Full step:
    text -> phonemes -> teacher soft labels -> forward all sectors -> update each sector -> maybe grow.
    """
    mm = open_brain(weights_path)
    meta = load_meta(meta_path)
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
    teacher = call_gemini_teacher(prompt, model=model, api_key=api_key)
    teacher_probs = teacher["phoneme_probs"]
    target_probs = teacher_phoneme_probs_to_bucket_target(
        teacher_probs,
        vocab_buckets=layout.vocab_buckets,
    )

    # Before loss using all sectors
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

    # After loss using all sectors
    mm = remap_brain(weights_path)
    post = forward_all_sectors(mm, meta, token_ids)
    total_probs_after = post["total_probs"]
    loss_after = cross_entropy_loss(total_probs_after, target_probs)

    meta["training_steps"] = int(meta.get("training_steps", 0)) + 1
    loss_history = list(meta.get("loss_history", []))
    loss_history.append(float(loss_after))
    meta["loss_history"] = loss_history[-200:]
    save_meta(meta_path, meta)

    # Growth protocol
    mm, meta, grew = evolve_brain(weights_path, meta_path)

    active_indices = active_sector_indices_for_text(token_ids, layout)

    return {
        "text": text,
        "phonemes": phonemes,
        "teacher_confidence": float(teacher["confidence"]),
        "teacher_notes": str(teacher["notes"]),
        "teacher_probs": teacher_probs,
        "target_bucket_probs": target_probs,
        "student_probs_before": total_probs_before,
        "student_probs_after": total_probs_after,
        "loss_before": loss_before,
        "loss_after": loss_after,
        "sector_updates": sector_updates,
        "grew": grew,
        "sector_count": int(meta["sector_count"]),
        "active_indices": active_indices,
        "transparency_report": transparency_report(mm, meta, active_indices),
        "teacher_prompt": prompt,
        "teacher_raw_text": teacher["raw_text"],
    }


# ============================================================
# Transparency
# ============================================================

def active_sector_indices_for_text(token_ids: np.ndarray, layout: Layout) -> List[int]:
    """
    Active indices for embedding rows touched by this text in sector 0 local coordinates.
    Used for transparency windows.
    """
    idxs: List[int] = []
    emb_base = 0
    row_width = layout.d_model

    seen = set()
    for tok in token_ids:
        row_start = emb_base + (int(tok) * row_width)
        for j in range(min(row_width, 8)):
            idx = row_start + j
            if idx not in seen:
                seen.add(idx)
                idxs.append(idx)
    return idxs


def transparency_report(
    mm: np.memmap,
    meta: Dict[str, Any],
    active_indices_local: Optional[List[int]] = None,
    sector_idx: int = 0,
    max_rows: int = 48,
) -> str:
    layout = default_layout(
        vocab_buckets=int(meta["vocab_buckets"]),
        d_model=int(meta["d_model"]),
    )
    views = get_sector_views(mm, sector_idx, layout)

    lines = [
        "TRANSPARENCY REPORT",
        "",
        f"Sector: {sector_idx}",
        f"Sectors Total: {int(meta['sector_count'])}",
        f"d_model: {layout.d_model}",
        f"vocab_buckets: {layout.vocab_buckets}",
        "",
        "Attention Matrices:",
        f"  Wq mean={float(np.mean(views['Wq'])):+.8f} std={float(np.std(views['Wq'])):.8f}",
        f"  Wk mean={float(np.mean(views['Wk'])):+.8f} std={float(np.std(views['Wk'])):.8f}",
        f"  Wv mean={float(np.mean(views['Wv'])):+.8f} std={float(np.std(views['Wv'])):.8f}",
        f"  Wo mean={float(np.mean(views['Wo'])):+.8f} std={float(np.std(views['Wo'])):.8f}",
        "",
        "Classifier:",
        f"  Wcls mean={float(np.mean(views['Wcls'])):+.8f} std={float(np.std(views['Wcls'])):.8f}",
    ]

    # Show a raw window of active embedding-related indices if available
    if active_indices_local:
        base_start, _ = sector_bounds(sector_idx)
        lines.extend([
            "",
            f"Active local indices shown: {min(len(active_indices_local), max_rows)} / {len(active_indices_local)}",
            "global_index | local_index | raw_float32",
            "----------------------------------------",
        ])
        for local_idx in active_indices_local[:max_rows]:
            global_idx = base_start + local_idx
            val = float(mm[global_idx])
            lines.append(f"{global_idx:11d} | {local_idx:10d} | {val:+.8f}")

    # Show the first few raw Q weights too
    q_flat = views["Wq"].reshape(-1)
    lines.extend([
        "",
        "First Q weights:",
    ])
    for i in range(min(12, len(q_flat))):
        lines.append(f"  Q[{i:02d}] = {float(q_flat[i]):+.8f}")

    return "\n".join(lines)


# ============================================================
# CLI helpers
# ============================================================

def print_train_summary(result: Dict[str, Any]) -> None:
    print("\n=== TRAIN STEP SUMMARY ===")
    print(f"Text: {result['text']}")
    print(f"Phonemes: {' '.join(result['phonemes'])}")
    print(f"Teacher confidence: {result['teacher_confidence']:.4f}")
    print(f"Teacher notes: {result['teacher_notes']}")
    print(f"Loss before: {result['loss_before']:.8f}")
    print(f"Loss after : {result['loss_after']:.8f}")
    print(f"Grew brain: {result['grew']}")
    print(f"Sector count: {result['sector_count']}")

    print("\nTop teacher probs:")
    for k, v in top_items(result["teacher_probs"], 10):
        print(f"  {k:>8s} : {v:.6f}")

    print("\nSector updates:")
    for u in result["sector_updates"]:
        print(
            f"  sector={u['sector_idx']} "
            f"old={u['old_loss']:.8f} "
            f"new={u['new_loss']:.8f} "
            f"final={u['final_loss']:.8f} "
            f"reverted={u['reverted']}"
        )

    print()
    print(result["transparency_report"])


def print_report_for_text(
    text: str,
    weights_path: str,
    meta_path: str,
    sector_idx: int = 0,
) -> None:
    mm = open_brain(weights_path)
    meta = load_meta(meta_path)
    layout = default_layout(
        vocab_buckets=int(meta["vocab_buckets"]),
        d_model=int(meta["d_model"]),
    )
    _phones, token_ids = text_to_token_ids(
        text,
        vocab_buckets=layout.vocab_buckets,
        max_seq=int(meta["max_seq"]),
    )
    active = active_sector_indices_for_text(token_ids, layout)
    print(transparency_report(mm, meta, active, sector_idx=sector_idx))


# ============================================================
# CLI
# ============================================================

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="AndyAI memmap Transformer core")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="Initialize 1MB brain + metadata")
    p_init.add_argument("--weights", default=DEFAULT_WEIGHTS)
    p_init.add_argument("--meta", default=DEFAULT_META)
    p_init.add_argument("--seed", type=int, default=1337)
    p_init.add_argument("--init-scale", type=float, default=0.02)
    p_init.add_argument("--force", action="store_true")

    p_g2p = sub.add_parser("g2p", help="Convert text to phonemes")
    p_g2p.add_argument("text")

    p_report = sub.add_parser("report", help="Print transparency report for text")
    p_report.add_argument("text")
    p_report.add_argument("--weights", default=DEFAULT_WEIGHTS)
    p_report.add_argument("--meta", default=DEFAULT_META)
    p_report.add_argument("--sector", type=int, default=0)

    p_train = sub.add_parser("train_once", help="One teacher-student train step")
    p_train.add_argument("text")
    p_train.add_argument("--weights", default=DEFAULT_WEIGHTS)
    p_train.add_argument("--meta", default=DEFAULT_META)
    p_train.add_argument("--model", default=DEFAULT_MODEL)
    p_train.add_argument("--lr", type=float, default=DEFAULT_LR)
    p_train.add_argument("--weight-decay", type=float, default=DEFAULT_WEIGHT_DECAY)

    p_grow = sub.add_parser("grow", help="Force-check growth protocol")
    p_grow.add_argument("--weights", default=DEFAULT_WEIGHTS)
    p_grow.add_argument("--meta", default=DEFAULT_META)

    args = parser.parse_args()

    if args.cmd == "init":
        mm, meta = initialize_brain_file(
            weights_path=args.weights,
            meta_path=args.meta,
            seed=args.seed,
            init_scale=args.init_scale,
            force_reinit=args.force,
        )
        print(f"Initialized: {args.weights}")
        print(f"Meta file  : {args.meta}")
        print(f"Sectors    : {meta['sector_count']}")
        print(f"Params/sect: {SECTOR_FLOATS}")
        print(f"Bytes/sect : {SECTOR_BYTES}")
        return

    if args.cmd == "g2p":
        phones = text_to_phonemes(args.text)
        print(json.dumps({"text": args.text, "phonemes": phones}, indent=2))
        return

    if args.cmd == "report":
        print_report_for_text(
            text=args.text,
            weights_path=args.weights,
            meta_path=args.meta,
            sector_idx=args.sector,
        )
        return

    if args.cmd == "train_once":
        result = train_step_with_teacher(
            text=args.text,
            weights_path=args.weights,
            meta_path=args.meta,
            model=args.model,
            lr=args.lr,
            weight_decay=args.weight_decay,
        )
        print_train_summary(result)
        return

    if args.cmd == "grow":
        mm, meta, grew = evolve_brain(args.weights, args.meta)
        print(f"Grew: {grew}")
        print(f"Sectors: {meta['sector_count']}")
        return


if __name__ == "__main__":
    main()
