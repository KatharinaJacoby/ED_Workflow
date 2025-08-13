
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple
import numpy as np

@dataclass
class GateConfig:
    tau: float = 0.5
    per_class: Dict[int, float] = field(default_factory=dict)
    top_k: int = 1

def gate_predictions(probs: np.ndarray, cfg: GateConfig) -> Tuple[np.ndarray, Dict[str,Any]]:
    N, K = probs.shape
    th = np.full(K, cfg.tau, dtype=float)
    for k, v in cfg.per_class.items():
        th[int(k)] = float(v)
    mask = probs >= th  # [N,K] broadcast
    top = probs.argmax(1)
    pred = np.where(mask[np.arange(N), top], top, 0)
    topk_idx = np.argsort(-probs, axis=1)[:, :cfg.top_k]
    return pred, {"thresholds": th.tolist(), "topk": topk_idx.tolist()}
