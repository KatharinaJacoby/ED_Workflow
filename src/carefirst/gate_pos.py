
# gate_pos.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Tuple, Optional
import math, time, hashlib, json, random
from pathlib import Path
import pandas as pd
import numpy as np

# --- WorkflowState MUST be defined before TinyCritics (per invariant) ---
@dataclass
class WorkflowState:
    role: str = "nurse"
    now_utc: Optional[pd.Timestamp] = None
    timers: Dict[str, float] = field(default_factory=dict)         # e.g., timers["since_vitals_min"]
    backlog: List[Dict[str,Any]] = field(default_factory=list)     # list of tasks
    alerts: List[str] = field(default_factory=list)                 # active alerts
    event_log_path: str = "/mnt/data/event_log.csv"

    def __post_init__(self):
        if self.now_utc is None:
            self.now_utc = pd.Timestamp.utcnow()
        # Ensure event log file exists
        p = Path(self.event_log_path)
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("ts,event,type,payload\n")

    def touch_now(self, ts: Optional[pd.Timestamp] = None):
        self.now_utc = ts or pd.Timestamp.utcnow()

    def feature_dict(self) -> Dict[str, Any]:
        # Extendable — we may add keys but cannot remove/rename (per invariant).
        f = {
            "role": self.role,
            "ts_unix": float(self.now_utc.timestamp()),
            "backlog_size": int(len(self.backlog)),
            "n_alerts": int(len(self.alerts)),
        }
        # timers flattened with default 0.0
        for k,v in self.timers.items():
            f[f"timer__{k}"] = float(v)
        # explicit missing indicators
        for key in ["since_vitals_min","since_ecg_min"]:
            f.setdefault(f"timer__{key}", float(self.timers.get(key, 0.0)))
            f[f"missing__{key}"] = (key not in self.timers)
        return f

    def update_state_from_event(self, event: Dict[str,Any]):
        """Update timers/backlog/alerts based on a single event."""
        etype = event.get("type","")
        payload = event.get("payload",{})
        if etype == "vitals":
            # reset since_vitals_min
            self.timers["since_vitals_min"] = 0.0
        elif etype == "tick":
            # advance timers by dt (min)
            dt = float(payload.get("dt_min", 1.0))
            for k in list(self.timers.keys()):
                self.timers[k] = float(self.timers[k]) + dt
        elif etype == "task_add":
            self.backlog.append({"id": payload.get("id","unknown"), "label": payload.get("label","")})
        elif etype == "task_done":
            tid = payload.get("id")
            self.backlog = [t for t in self.backlog if t.get("id") != tid]
        elif etype == "alert_add":
            msg = payload.get("msg","")
            if msg:
                self.alerts.append(msg)
        elif etype == "alert_clear":
            msg = payload.get("msg","")
            self.alerts = [a for a in self.alerts if a != msg]
        # append to event log
        with open(self.event_log_path, "a") as f:
            f.write(f"{pd.Timestamp.utcnow().isoformat()},{self.now_utc.isoformat()},{etype},{json.dumps(payload)}\n")

    def apply_event_log(self, events: List[Dict[str,Any]]):
        for e in events:
            self.update_state_from_event(e)

# --- TinyCritics uses WorkflowState.feature_dict(); cold-start safe (no transform before fit) ---
class TinyCritics:
    def __init__(self, seed: int = 0):
        self.seed = seed

    def _score_one(self, features: Dict[str,Any], action_id: str) -> float:
        # Deterministic, bounded [0,1]; depends on a few features to be meaningful
        v = 0.0
        v += 0.2 * min(1.0, features.get("backlog_size",0)/5.0)
        v += 0.2 * min(1.0, features.get("n_alerts",0)/3.0)
        v += 0.3 * min(1.0, features.get("timer__since_vitals_min",0)/60.0)
        # hash-based salt to differentiate actions deterministically
        h = int(hashlib.md5(action_id.encode("utf-8")).hexdigest(), 16) % 1000
        v += (h / 1000.0) * 0.1
        return max(0.0, min(1.0, v))

    def score(self, state: WorkflowState, actions: List[Dict[str,Any]]):
        f = state.feature_dict()
        p = np.array([self._score_one(f, a["id"]) for a in actions], dtype=float)
        # b: simple baseline (mean), u: uncertainty band (conformal-ish width from n_alerts)
        b = np.full_like(p, p.mean())
        u = np.full_like(p, 0.1 + 0.05*min(3, f.get("n_alerts",0)))
        return p, b, u

# --- Gate_Pos: multi-task trunk with heads, deterministic gate integration, stability controls ---
@dataclass
class GatePos:
    gate_floor: float = 0.2
    ttl_min: int = 30
    hysteresis: float = 0.05
    reorder_rate_limit_min: int = 15
    calibrators: Dict[str, Dict[str, List[float]]] = field(default_factory=dict)  # e.g. {"day_weekday":{"T2":[30,60,120]}}
    last_ranking: Dict[str, Dict[str,Any]] = field(default_factory=dict)  # id -> {"priority": float, "ts": pd.Timestamp}

    # helpers
    def _day_key(self, ts: pd.Timestamp) -> str:
        dow = ts.dayofweek
        weekday = "weekday" if dow < 5 else "weekend"
        hour = ts.hour
        daynight = "day" if 7 <= hour < 19 else "night"
        return f"{daynight}_{weekday}"

    # heads — simple deterministic models using monotone binned features
    def _complexity(self, f: Dict[str,Any]) -> float:
        return max(0.0, min(1.0, 0.3 + 0.1*f.get("backlog_size",0) + 0.05*f.get("n_alerts",0)))

    def _resource_need(self, f: Dict[str,Any]) -> float:
        # ordinal proxy 0..1
        bins = [0.0, 0.33, 0.66, 1.0]
        score = min(1.0, (f.get("timer__since_vitals_min",0)/180.0))
        # soft calibration step
        return np.interp(score, [0,1], [0.2,0.8])

    def _deterioration_4h(self, f: Dict[str,Any]) -> float:
        # risk rises with alerts and time since vitals
        base = 0.15 + 0.1*f.get("n_alerts",0)
        base += 0.4 * min(1.0, f.get("timer__since_vitals_min",0)/240.0)
        return max(0.0, min(1.0, base))

    def _ordinal_T2_readiness(self, ts: pd.Timestamp, f: Dict[str,Any]) -> Tuple[List[str], List[float]]:
        # buckets and calibrated cutpoints by regime
        key = self._day_key(ts)
        default_cuts = [30, 60, 120]
        cuts = self.calibrators.get(key, {}).get("T2", default_cuts)
        # simple logits then cumulative probs (monotone)
        x = 0.5 + 0.5*min(1.0, f.get("timer__since_vitals_min",0)/120.0) - 0.1*f.get("n_alerts",0)
        logits = [x - 0.2, x, x + 0.2]
        cp = [1/(1+math.exp(-z)) for z in logits]
        # convert to bin probs
        p = [max(0.0, min(1.0, cp[0])),
             max(0.0, min(1.0, cp[1]-cp[0])),
             max(0.0, min(1.0, cp[2]-cp[1])),
             1.0 - max(0.0, min(1.0, cp[2]))]
        # normalize
        s = sum(p); p = [pi/s for pi in p]
        labels = [f"<= {cuts[0]}m", f"{cuts[0]}-{cuts[1]}m", f"{cuts[1]}-{cuts[2]}m", f">{cuts[2]}m"]
        return labels, p

    def _hazard_T3_completion(self, f: Dict[str,Any]) -> Dict[int,float]:
        # discrete-time hazards at minutes [30, 60, 120, 240]
        base = 0.2 + 0.2*min(1.0, f.get("timer__since_vitals_min",0)/60.0)
        hazards = {30: min(0.6, base),
                   60: min(0.7, base+0.05),
                   120: min(0.8, base+0.1),
                   240: min(0.9, base+0.15)}
        return hazards

    def _ordinal_T4_ready_time(self, ts: pd.Timestamp, f: Dict[str,Any]) -> Tuple[List[str], List[float]]:
        # mirror T2 but broader horizon (quantile-ish)
        key = self._day_key(ts)
        default_cuts = [60, 120, 240]
        cuts = self.calibrators.get(key, {}).get("T4", default_cuts)
        x = 0.4 + 0.6*min(1.0, f.get("timer__since_vitals_min",0)/240.0) - 0.1*f.get("n_alerts",0)
        logits = [x - 0.2, x, x + 0.2]
        cp = [1/(1+math.exp(-z)) for z in logits]
        p = [max(0.0, min(1.0, cp[0])),
             max(0.0, min(1.0, cp[1]-cp[0])),
             max(0.0, min(1.0, cp[2]-cp[1])),
             1.0 - max(0.0, min(1.0, cp[2]))]
        s = sum(p); p = [pi/s for pi in p]
        labels = [f"<= {cuts[0]}m", f"{cuts[0]}-{cuts[1]}m", f"{cuts[1]}-{cuts[2]}m", f">{cuts[2]}m"]
        return labels, p

    def _priority(self, f: Dict[str,Any]) -> Tuple[float, Dict[str,Any]]:
        d4 = self._deterioration_4h(f)
        res = self._resource_need(f)
        raw = 0.6*d4 + 0.4*res
        prio = max(self.gate_floor, raw)
        reasons = {
            "deterioration4h": round(d4,3),
            "resource_need": round(res,3),
            "gate_floor": round(self.gate_floor,3),
            "raw": round(raw,3),
        }
        return prio, reasons

    def score(self, states: List[Tuple[str, WorkflowState]]) -> Dict[str,Any]:
        """Compute multi-head outputs per id and stabilized ordering."""
        outputs = {}
        for sid, s in states:
            f = s.feature_dict()
            ts = s.now_utc
            labels_T2, p_T2 = self._ordinal_T2_readiness(ts, f)
            labels_T4, p_T4 = self._ordinal_T4_ready_time(ts, f)
            hazards = self._hazard_T3_completion(f)
            prio, reasons = self._priority(f)
            outputs[sid] = {
                "complexity": self._complexity(f),
                "resource": self._resource_need(f),
                "det4h": self._deterioration_4h(f),
                "T2_labels": labels_T2, "T2_probs": p_T2,
                "T3_hazards": hazards,
                "T4_labels": labels_T4, "T4_probs": p_T4,
                "priority": prio, "reasons": reasons,
            }
        ranking = self._stabilize_rank(outputs, states)
        return {"per_id": outputs, "ranking": ranking}

    def _stabilize_rank(self, outputs: Dict[str,Any], states: List[Tuple[str,WorkflowState]]):
        """TTL/hysteresis & rate-limit stable ordering."""
        now = pd.Timestamp.utcnow()
        scored = []
        for sid, s in states:
            pr = outputs[sid]["priority"]
            last = self.last_ranking.get(sid, {})
            last_pr = last.get("priority", pr)
            last_ts = last.get("ts", now - pd.Timedelta(minutes=60))
            # hysteresis
            if abs(pr - last_pr) < self.hysteresis:
                pr_use = last_pr
            else:
                pr_use = pr
            # rate limit
            if (now - last_ts) < pd.Timedelta(minutes=self.reorder_rate_limit_min):
                pr_use = last_pr
            self.last_ranking[sid] = {"priority": pr_use, "ts": now}
            scored.append((sid, pr_use))
        # order by descending priority
        scored.sort(key=lambda x: x[1], reverse=True)
        # apply TTL: stickiness (keep prior order if within TTL for ties)
        return [sid for sid,_ in scored]

