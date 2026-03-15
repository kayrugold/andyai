#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import os
import re
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

import numpy as np

SECTOR_BYTES = 1 * 1024 * 1024
FLOAT32_BYTES = 4
SECTOR_FLOATS = SECTOR_BYTES // FLOAT32_BYTES

DEFAULT_WEIGHTS = "word_brain.weights"
DEFAULT_META = "word_brain.meta.json"

DEFAULT_D_MODEL = 64
DEFAULT_VOCAB_BUCKETS = 512
DEFAULT_MAX_SEQ = 64

DEFAULT_LR = 0.02
DEFAULT_WEIGHT_DECAY = 0.0005
DEFAULT_GROWTH_THRESHOLD = 1.25
DEFAULT_GROWTH_PATIENCE = 8

MIN_WEIGHT = -8.0
MAX_WEIGHT = 8.0
EPS = 1e-8


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
    clean = {}
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


def save_meta(meta_path: str, meta: Dict[str, Any]) -> None:
    Path(meta_path).write_text(json.dumps(meta, indent=2), encoding="utf-8")


def load_meta(meta_path: str) -> Dict[str, Any]:
    return json.loads(Path(meta_path).read_text(encoding="utf-8"))


def default_layout(
    vocab_buckets: int = DEFAULT_VOCAB_BUCKETS,
    d_model: int = DEFAULT_D_MODEL,
    sector_floats: int = SECTOR_FLOATS,
) -> Dict[str, int]:
    emb_size = vocab_buckets * d_model
    q_size = d_model * d_model
    k_size = d_model * d_model
    v_size = d_model * d_model
    o_size = d_model * d_model
    cls_size = d_model * vocab_buckets

    used = emb_size + q_size + k_size + v_size + o_size + cls_size
    reserve = sector_floats - used
    if reserve < 0:
        raise ValueError("Word brain layout exceeds sector size")

    return {
        "vocab_buckets": vocab_buckets,
        "d_model": d_model,
        "sector_floats": sector_floats,
        "emb_size": emb_size,
        "q_size": q_size,
        "k_size": k_size,
        "v_size": v_size,
        "o_size": o_size,
        "cls_size": cls_size,
        "reserve_size": reserve,
    }


def initialize_brain_file(
    weights_path: str = DEFAULT_WEIGHTS,
    meta_path: str = DEFAULT_META,
    seed: int = 7331,
    init_scale: float = 0.02,
    force_reinit: bool = False,
):
    p = Path(weights_path)
    if p.exists() and not force_reinit:
        meta = load_meta(meta_path)
        mm = open_brain(weights_path)
        return mm, meta

    meta = {
        "weights_path": weights_path,
        "sector_bytes": SECTOR_BYTES,
        "sector_floats": SECTOR_FLOATS,
        "sector_count": 1,
        "vocab_buckets": DEFAULT_VOCAB_BUCKETS,
        "d_model": DEFAULT_D_MODEL,
        "max_seq": DEFAULT_MAX_SEQ,
        "growth_threshold": DEFAULT_GROWTH_THRESHOLD,
        "growth_patience": DEFAULT_GROWTH_PATIENCE,
        "loss_history": [],
        "training_steps": 0,
    }
    save_meta(meta_path, meta)

    rng = np.random.default_rng(seed)
    mm = np.memmap(weights_path, dtype=np.float32, mode="w+", shape=(SECTOR_FLOATS,))
    mm[:] = rng.normal(0.0, init_scale, size=SECTOR_FLOATS).astype(np.float32)
    mm.flush()
    return mm, meta


def open_brain(weights_path: str = DEFAULT_WEIGHTS) -> np.memmap:
    size = Path(weights_path).stat().st_size
    total_floats = size // FLOAT32_BYTES
    return np.memmap(weights_path, dtype=np.float32, mode="r+", shape=(total_floats,))


def remap_brain(weights_path: str = DEFAULT_WEIGHTS) -> np.memmap:
    return open_brain(weights_path)


def sector_count_from_file(weights_path: str = DEFAULT_WEIGHTS) -> int:
    size = Path(weights_path).stat().st_size
    return size // SECTOR_BYTES


def evolve_brain(
    weights_path: str,
    meta_path: str,
    trigger_loss: Optional[float] = None,
    patience: Optional[int] = None,
    seed: Optional[int] = None,
    init_scale: float = 0.02,
):
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
        return remap_brain(weights_path), meta, False

    current_size = Path(weights_path).stat().st_size
    new_size = current_size + SECTOR_BYTES

    with open(weights_path, "r+b") as f:
        f.truncate(new_size)

    mm = remap_brain(weights_path)
    new_sector_idx = (new_size // SECTOR_BYTES) - 1
    start = new_sector_idx * SECTOR_FLOATS
    end = start + SECTOR_FLOATS

    rng_seed = int(seed if seed is not None else (7331 + new_sector_idx))
    rng = np.random.default_rng(rng_seed)
    mm[start:end] = rng.normal(0.0, init_scale, size=SECTOR_FLOATS).astype(np.float32)
    mm.flush()

    meta["sector_count"] = sector_count_from_file(weights_path)
    save_meta(meta_path, meta)
    return mm, meta, True


def sector_bounds(sector_idx: int) -> Tuple[int, int]:
    start = sector_idx * SECTOR_FLOATS
    end = start + SECTOR_FLOATS
    return start, end


def sector_slices(layout: Dict[str, int]) -> Dict[str, slice]:
    pos = 0
    out = {}

    out["emb"] = slice(pos, pos + layout["emb_size"])
    pos += layout["emb_size"]

    out["Wq"] = slice(pos, pos + layout["q_size"])
    pos += layout["q_size"]

    out["Wk"] = slice(pos, pos + layout["k_size"])
    pos += layout["k_size"]

    out["Wv"] = slice(pos, pos + layout["v_size"])
    pos += layout["v_size"]

    out["Wo"] = slice(pos, pos + layout["o_size"])
    pos += layout["o_size"]

    out["Wcls"] = slice(pos, pos + layout["cls_size"])
    pos += layout["cls_size"]

    out["reserve"] = slice(pos, pos + layout["reserve_size"])
    return out


def get_sector_views(mm: np.memmap, sector_idx: int, layout: Dict[str, int]) -> Dict[str, np.ndarray]:
    base_start, base_end = sector_bounds(sector_idx)
    raw = mm[base_start:base_end]
    sl = sector_slices(layout)

    d_model = layout["d_model"]
    vocab_buckets = layout["vocab_buckets"]

    return {
        "raw": raw,
        "emb": raw[sl["emb"]].reshape(vocab_buckets, d_model),
        "Wq": raw[sl["Wq"]].reshape(d_model, d_model),
        "Wk": raw[sl["Wk"]].reshape(d_model, d_model),
        "Wv": raw[sl["Wv"]].reshape(d_model, d_model),
        "Wo": raw[sl["Wo"]].reshape(d_model, d_model),
        "Wcls": raw[sl["Wcls"]].reshape(d_model, vocab_buckets),
        "reserve": raw[sl["reserve"]],
    }


def tokenize_words(text: str) -> List[str]:
    words = re.findall(r"[A-Za-z0-9']+", str(text).lower())
    return words[:DEFAULT_MAX_SEQ] if words else ["empty"]


def word_to_bucket(word: str, vocab_buckets: int) -> int:
    return stable_hash_u64(f"wd::{word}") % vocab_buckets


def text_to_token_ids(text: str, vocab_buckets: int, max_seq: int) -> Tuple[List[str], np.ndarray]:
    words = tokenize_words(text)[:max_seq]
    ids = np.array([word_to_bucket(w, vocab_buckets) for w in words], dtype=np.int64)
    return words, ids


def sinusoidal_positional_encoding(seq_len: int, d_model: int) -> np.ndarray:
    pe = np.zeros((seq_len, d_model), dtype=np.float32)
    pos = np.arange(seq_len, dtype=np.float32)[:, None]
    i = np.arange(d_model, dtype=np.float32)[None, :]

    angle_rates = 1.0 / np.power(10000.0, (2.0 * (i // 2)) / float(d_model))
    angles = pos * angle_rates

    pe[:, 0::2] = np.sin(angles[:, 0::2])
    pe[:, 1::2] = np.cos(angles[:, 1::2])
    return pe


def scaled_dot_product_attention(Q: np.ndarray, K: np.ndarray, V: np.ndarray):
    dk = Q.shape[1]
    scores = (Q @ K.T) / math.sqrt(max(dk, 1))
    A = softmax_rows(scores)
    context = A @ V
    return context, A, scores


def forward_sector(views: Dict[str, np.ndarray], token_ids: np.ndarray, pos_enc: np.ndarray) -> Dict[str, np.ndarray]:
    emb_table = views["emb"]
    Wq = views["Wq"]
    Wk = views["Wk"]
    Wv = views["Wv"]
    Wo = views["Wo"]
    Wcls = views["Wcls"]

    E = emb_table[token_ids].astype(np.float64) + pos_enc.astype(np.float64)
    Q = E @ Wq
    K = E @ Wk
    V = E @ Wv

    C, A, S = scaled_dot_product_attention(Q, K, V)
    H = C @ Wo
    pooled = np.mean(H, axis=0)
    logits = pooled @ Wcls
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


def forward_all_sectors(mm: np.memmap, meta: Dict[str, Any], token_ids: np.ndarray) -> Dict[str, Any]:
    layout = default_layout(
        vocab_buckets=int(meta["vocab_buckets"]),
        d_model=int(meta["d_model"]),
    )
    seq_len = len(token_ids)
    pos_enc = sinusoidal_positional_encoding(seq_len, int(meta["d_model"]))

    sector_outputs = []
    total_logits = np.zeros((layout["vocab_buckets"],), dtype=np.float64)

    for sector_idx in range(int(meta["sector_count"])):
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


def build_teacher_prompt(text: str, words: List[str]) -> str:
    words_json = json.dumps(words, ensure_ascii=False)

    return f"""
Return STRICT JSON ONLY on ONE LINE.

Use this exact schema:
{{"word_probs":{{"word":0.123}},"confidence":0.95,"notes":"short"}}

Rules:
- One line only
- JSON only
- No markdown
- No prose
- Use only words from the provided list as keys
- Probabilities should sum to about 1.0
- Keep notes very short

Text: {text}
Words: {words_json}
""".strip()


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

    probs = normalize_probs(data.get("word_probs", {}) or {})
    conf = float(data.get("confidence", 0.0) or 0.0)
    notes = str(data.get("notes", "") or "")

    return {
        "word_probs": probs,
        "confidence": conf,
        "notes": notes,
        "raw_text": text,
    }


def fallback_teacher_from_words(words: List[str]) -> Dict[str, Any]:
    counts: Dict[str, float] = {}
    total = 0.0

    for i, word in enumerate(words):
        w = 1.0 + (0.05 * i)
        counts[word] = counts.get(word, 0.0) + w
        total += w

    if total <= EPS:
        return {
            "word_probs": {},
            "confidence": 0.0,
            "notes": "fallback-empty",
            "raw_text": "",
        }

    probs = {k: v / total for k, v in counts.items()}
    return {
        "word_probs": probs,
        "confidence": 0.25,
        "notes": "fallback-local-teacher",
        "raw_text": "",
    }


def teacher_word_probs_to_bucket_target(word_probs: Dict[str, float], vocab_buckets: int) -> np.ndarray:
    target = np.zeros((vocab_buckets,), dtype=np.float64)

    for word, p in word_probs.items():
        idx = word_to_bucket(word, vocab_buckets)
        target[idx] += float(p)

    s = np.sum(target)
    if s <= EPS:
        target += 1.0 / vocab_buckets
        s = np.sum(target)
    target /= s
    return target


def cross_entropy_loss(pred_probs: np.ndarray, target_probs: np.ndarray) -> float:
    pred = np.clip(pred_probs.astype(np.float64), EPS, 1.0)
    targ = np.clip(target_probs.astype(np.float64), 0.0, 1.0)
    return float(-np.sum(targ * np.log(pred + EPS)))


def update_sector_with_revert(
    mm: np.memmap,
    sector_idx: int,
    meta: Dict[str, Any],
    token_ids: np.ndarray,
    target_probs: np.ndarray,
    lr: float = DEFAULT_LR,
    weight_decay: float = DEFAULT_WEIGHT_DECAY,
) -> Dict[str, Any]:
    layout = default_layout(
        vocab_buckets=int(meta["vocab_buckets"]),
        d_model=int(meta["d_model"]),
    )
    pos_enc = sinusoidal_positional_encoding(len(token_ids), int(meta["d_model"]))
    views = get_sector_views(mm, sector_idx, layout)

    snapshot = np.array(views["raw"], copy=True)

    out = forward_sector(views, token_ids, pos_enc)
    probs = out["probs"]
    old_loss = cross_entropy_loss(probs, target_probs)

    E = out["E"]
    K = out["K"]
    Q = out["Q"]
    V = out["V"]
    A = out["A"]
    C = out["C"]
    H = out["H"]
    pooled = out["pooled"]

    Wq = views["Wq"].astype(np.float64)
    Wk = views["Wk"].astype(np.float64)
    Wv = views["Wv"].astype(np.float64)
    Wo = views["Wo"].astype(np.float64)
    Wcls = views["Wcls"].astype(np.float64)

    T = len(token_ids)
    D = layout["d_model"]

    dlogits = (probs - target_probs)
    dWcls = np.outer(pooled, dlogits) + weight_decay * Wcls
    dpooled = Wcls @ dlogits

    dH = np.repeat((dpooled / T)[None, :], T, axis=0)

    dWo = C.T @ dH + weight_decay * Wo
    dC = dH @ Wo.T

    dV = A.T @ dC
    dA = dC @ V.T

    row_dot = np.sum(dA * A, axis=1, keepdims=True)
    dS = A * (dA - row_dot)

    scale = 1.0 / math.sqrt(D)
    dQ = dS @ K * scale
    dK = dS.T @ Q * scale

    dWq = E.T @ dQ + weight_decay * Wq
    dWk = E.T @ dK + weight_decay * Wk
    dWv = E.T @ dV + weight_decay * Wv

    dE = dQ @ Wq.T + dK @ Wk.T + dV @ Wv.T

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

    new_views = get_sector_views(mm, sector_idx, layout)
    new_out = forward_sector(new_views, token_ids, pos_enc)
    new_loss = cross_entropy_loss(new_out["probs"], target_probs)

    reverted = False
    if new_loss > old_loss + 1e-8:
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


def active_sector_indices_for_text(token_ids: np.ndarray, layout: Dict[str, int]) -> List[int]:
    idxs = []
    emb_base = 0
    row_width = layout["d_model"]

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
        "WORD BRAIN TRANSPARENCY REPORT",
        "",
        f"Sector: {sector_idx}",
        f"Sectors Total: {int(meta['sector_count'])}",
        f"d_model: {layout['d_model']}",
        f"vocab_buckets: {layout['vocab_buckets']}",
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

    q_flat = views["Wq"].reshape(-1)
    lines.extend([
        "",
        "First Q weights:",
    ])
    for i in range(min(12, len(q_flat))):
        lines.append(f"  Q[{i:02d}] = {float(q_flat[i]):+.8f}")

    return "\n".join(lines)
