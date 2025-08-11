
from typing import Callable, Dict, Any, List, Optional, Tuple
from datetime import datetime

class ResultsNotifier:
    def __init__(self):
        self.callbacks: List[Callable[[str, str, Dict[str, Any]], None]] = []
        self.last_values: Dict[str, Dict[str, Tuple[float, datetime]]] = {}
        self.delta_rules = {
            "TROPONIN": {"abs_ng_per_l": 5.0, "rel_pct": 20.0}
        }

    def on_notify(self, fn: Callable[[str, str, Dict[str, Any]], None]):
        self.callbacks.append(fn)

    def _emit(self, patient_id: str, event: str, payload: Dict[str, Any]):
        for cb in self.callbacks:
            cb(patient_id, event, payload)

    @staticmethod
    def _split_segments(msg: str):
        segs = msg.strip().split("\r")
        return [s.split("|") for s in segs if s]

    @staticmethod
    def _field(component: str, idx: int) -> str:
        parts = component.split("^")
        return parts[idx] if idx < len(parts) else ""

    @staticmethod
    def _parse_ts(ts: str):
        for fmt in ("%Y%m%d%H%M%S", "%Y%m%d%H%M", "%Y%m%d"):
            try:
                return datetime.strptime(ts, fmt)
            except Exception:
                continue
        return None

    def _get_pid(self, segments):
        for s in segments:
            if s[0] == "PID":
                return s[3].split("^")[0] if len(s) > 3 else ""
        return ""

    def handle_hl7(self, message: str):
        segs = self._split_segments(message)
        if not segs or segs[0][0] != "MSH":
            return
        msg_type = segs[0][8] if len(segs[0]) > 8 else ""
        pid = self._get_pid(segs) or "UNKNOWN"

        if "ORU^R01" in msg_type:
            self._handle_oru(pid, segs)
        elif "MDM^T02" in msg_type or ("ORU^R01" in msg_type and any(s[0]=="OBX" and s[2] in ("TX","FT","ED") for s in segs)):
            self._handle_report(pid, segs)

    def _handle_oru(self, pid, segs):
        obr_accession = None
        obr_ts = None
        for s in segs:
            if s[0] == "OBR":
                obr_accession = s[3] if len(s) > 3 else None
                obr_ts = self._parse_ts(s[7]) if len(s) > 7 else None
            if s[0] == "OBX":
                id_comp = s[3] if len(s) > 3 else ""
                code = self._field(id_comp, 0) or self._field(id_comp, 1) or "UNKNOWN_TEST"
                value_raw = s[5] if len(s) > 5 else ""
                units = s[6] if len(s) > 6 else ""
                status = s[11] if len(s) > 11 else ""
                ts = self._parse_ts(s[14]) if len(s) > 14 else obr_ts
                try:
                    value = float(value_raw)
                except Exception:
                    value = None
                payload = {
                    "test_code": code.upper(),
                    "value_raw": value_raw,
                    "value": value,
                    "units": units,
                    "status": status,
                    "ts": ts,
                    "accession": obr_accession,
                }
                self._emit(pid, "lab_result_ready", payload)
                if status and status.upper().startswith("C"):
                    self._emit(pid, "lab_result_critical", payload)
                if value is not None:
                    self._maybe_emit_delta(pid, payload)

    def _maybe_emit_delta(self, pid, payload):
        code = payload["test_code"]
        value = payload["value"]
        ts = payload["ts"] or datetime.utcnow()
        rules = self.delta_rules.get(code)
        if not rules:
            self.last_values.setdefault(pid, {})[code] = (value, ts)
            return
        last = self.last_values.get(pid, {}).get(code)
        if last:
            prev, _ = last
            abs_delta = abs(value - prev)
            rel_pct = (abs_delta / prev * 100.0) if prev else 0.0
            triggered = (abs_delta >= rules.get("abs_ng_per_l", 1e9)) or (rel_pct >= rules.get("rel_pct", 1e9))
            delta_payload = {**payload, "prev_value": prev, "abs_delta": abs_delta, "rel_pct": rel_pct}
            if triggered:
                self._emit(pid, "lab_delta_positive", delta_payload)
        self.last_values.setdefault(pid, {})[code] = (value, ts)

    def _handle_report(self, pid, segs):
        text_blocks = []
        study_id = None
        ts = None
        for s in segs:
            if s[0] == "OBR":
                study_id = s[3] if len(s) > 3 else study_id
                ts = self._parse_ts(s[7]) if len(s) > 7 else ts
            if s[0] == "OBX" and len(s) > 2 and s[2] in ("TX", "FT", "ED"):
                text_blocks.append(s[5] if len(s) > 5 else "")
        if text_blocks:
            payload = {"study_id": study_id, "report_text": "\n".join(text_blocks), "ts": ts}
            self._emit(pid, "imaging_report_ready", payload)
