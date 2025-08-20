
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Iterable, Optional, List
import json

EVENT_LOG = Path("/mnt/data/event_log.jsonl")
ML_EVENT_LOG = Path("/mnt/data/ml_events.jsonl")

def read_events(event_type: Optional[str]=None, tail: Optional[int]=None) -> list[dict]:
    if not EVENT_LOG.exists():
        return []
    evs = []
    with EVENT_LOG.open() as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
                if (event_type is None) or (ev.get("type")==event_type):
                    evs.append(ev)
            except Exception:
                continue
    return evs[-tail:] if tail else evs



def read_ml_events(tail: Optional[int]=None) -> list[dict]:
    evs = []
    path = ML_EVENT_LOG
    if not path.exists():
        return evs
    with path.open() as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
                if ev.get("type") == "ml_risk":
                    evs.append(ev)
            except Exception:
                continue
    return evs[-tail:] if tail else evs

def append_event(ev: Dict[str, Any]):
    EVENT_LOG.parent.mkdir(parents=True, exist_ok=True)
    EVENT_LOG.touch(exist_ok=True)
    ev = {"ts": datetime.now(timezone.utc).isoformat(), **ev}
    with EVENT_LOG.open("a") as fp:
        fp.write(json.dumps(ev, ensure_ascii=False) + "\n")

class LingeringPatientMonitor:
    """
    Minimal monitor: if ML decision is POS, raise a 'lingering_alert' event.
    Threshold is already encoded in ML decision; we just translate to ops.
    """
    def on_ml_event(self, ev: Dict[str, Any]):
        if ev.get("type")!="ml_risk": 
            return
        if ev.get("decision")=="POS":
            append_event({
                "type": "lingering_alert",
                "patient_id": ev.get("patient_id"),
                "id_col": ev.get("id_col"),
                "prob_cal": ev.get("prob_cal"),
                "tau": ev.get("tau"),
                "reason": "ml_high_risk",
                "source": "LingeringPatientMonitor"
            })

class MLToOpsAdapter:
    """
    Wires ML events into operational monitors.
    """
    def __init__(self, monitors: Optional[list]=None):
        self.monitors = monitors or [LingeringPatientMonitor()]

    def fanout(self, events: Iterable[Dict[str, Any]]):
        for ev in events:
            for m in self.monitors:
                try:
                    m.on_ml_event(ev)
                except Exception:
                    pass

def pump_ml_events_into_ops():
    ml_events = read_ml_events()
    MLToOpsAdapter().fanout(ml_events)
    return {"ok": True, "n_in": len(ml_events)}
