
from __future__ import annotations
from typing import Dict, Any, Optional
import time, numpy as np

class SLARecorder:
    def __init__(self):
        self.t = {}
        self.lat = {}
        self.counters = {"missed_critical": 0, "duplicates_blocked": 0, "contradictions_blocked": 0}
        self.samples = 0

    def start(self, key: str): self.t[key] = time.time()
    def end(self, key: str): self.lat[key] = self.lat.get(key, []) + [time.time() - self.t.get(key, time.time())]

    def add_sample(self): self.samples += 1
    def mark_missed_critical(self, n=1): self.counters["missed_critical"] += n
    def mark_duplicate_blocked(self, n=1): self.counters["duplicates_blocked"] += n
    def mark_contradiction_blocked(self, n=1): self.counters["contradictions_blocked"] += n

    def summary(self) -> Dict[str,Any]:
        lat = {k: {"p50": float(np.median(v)), "p95": float(np.percentile(v,95)), "mean": float(np.mean(v))}
               for k,v in self.lat.items()}
        return {"latency": lat, "counters": self.counters, "samples": self.samples}

def safety_utility(y_true, y_pred, fp_cost=1.0, fn_cost=5.0) -> float:
    y_true = np.asarray(y_true); y_pred = np.asarray(y_pred)
    return (- fp_cost * np.sum((y_pred != y_true) & (y_true == 0))
            - fn_cost * np.sum((y_pred != y_true) & (y_true != 0))) / len(y_true)
