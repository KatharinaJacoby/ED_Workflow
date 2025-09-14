
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable

class ReminderEngine:
    """
    Minimal event-driven reminder engine for ED workflows.
    - Maintain per-patient timers for required actions (e.g., 'order troponin', 'repeat troponin in 60m').
    - Trigger callbacks when timers expire and conditions remain unmet.
    - Completely generic: any lab/test can be represented via config.
    """
    def __init__(self, now_fn: Callable[[], datetime] = None):
        self.now_fn = now_fn or (lambda: datetime.utcnow())
        self.patients: Dict[str, Dict[str, Any]] = {}
        self.callbacks: List[Callable[[str, str, Dict[str, Any]], None]] = []

    def on_notify(self, fn: Callable[[str, str, Dict[str, Any]], None]):
        self.callbacks.append(fn)

    def _emit(self, patient_id: str, key: str, payload: Dict[str, Any]):
        for cb in self.callbacks:
            cb(patient_id, key, payload)

    def ensure_patient(self, patient_id: str):
        self.patients.setdefault(patient_id, {"events": {}, "timers": []})

    def ingest_event(self, patient_id: str, event_type: str, payload: Dict[str, Any] = None):
        payload = payload or {}
        self.ensure_patient(patient_id)
        now = self.now_fn()
        self.patients[patient_id]["events"].setdefault(event_type, []).append({"t": now, **payload})
        self._evaluate(patient_id)

    def add_timer(self, patient_id: str, key: str, due_in: timedelta, condition: Dict[str, Any]):
        self.ensure_patient(patient_id)
        due_at = self.now_fn() + due_in
        self.patients[patient_id]["timers"].append({"key": key, "due_at": due_at, "condition": condition, "fired": False})

    def _has_event(self, patient_id: str, event_type: str, where: Optional[Dict[str, Any]] = None) -> bool:
        evs = self.patients.get(patient_id, {}).get("events", {}).get(event_type, [])
        if where is None:
            return bool(evs)
        for e in evs:
            if all(e.get(k) == v for k, v in where.items()):
                return True
        return False

    def _get_last_event_time(self, patient_id: str, event_type: str, where: Optional[Dict[str, Any]] = None):
        evs = self.patients.get(patient_id, {}).get("events", {}).get(event_type, [])
        if where:
            evs = [e for e in evs if all(e.get(k) == v for k, v in where.items())]
        if not evs:
            return None
        return max(e["t"] for e in evs)

    def _evaluate(self, patient_id: str):
        now = self.now_fn()
        timers = self.patients[patient_id]["timers"]
        for t in timers:
            if t["fired"]:
                continue
            if now >= t["due_at"]:
                cond = t["condition"]
                ok = True
                if "require_event" in cond:
                    ok = self._has_event(patient_id, cond["require_event"], cond.get("where"))
                if not ok:
                    t["fired"] = True
                    self._emit(patient_id, t["key"], {"due_at": t["due_at"], "condition": cond})

    def apply_lab_protocol(self, patient_id: str, protocol):
        self.ensure_patient(patient_id)
        self.add_timer(
            patient_id,
            key=f"{protocol['test_name']}_initial_order_due",
            due_in=timedelta(minutes=protocol.get("initial_order_due_min", 10)),
            condition={"require_event": "order_placed", "where": {"test": protocol["test_name"]}}
        )
        self.patients[patient_id].setdefault("lab_protocols", {})[protocol["test_name"]] = protocol

    def on_sample_collected(self, patient_id: str, test_name: str):
        proto = self.patients.get(patient_id, {}).get("lab_protocols", {}).get(test_name)
        if not proto:
            return
        for mins in proto.get("repeat_schedule_min", []):
            self.add_timer(
                patient_id,
                key=f"{test_name}_repeat_due_{mins}m",
                due_in=timedelta(minutes=mins),
                condition={"require_event": "sample_collected", "where": {"test": test_name, "offset_min": mins}}
            )
