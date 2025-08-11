
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Literal

@dataclass
class UnitCapacity:
    name: str
    total: int
    occupied: int = 0
    acuity: Literal["ICU","StepDown","Ward","EDObs"] = "Ward"

    def free(self) -> int:
        return max(0, self.total - self.occupied)

    def admit(self, k: int = 1) -> bool:
        if self.free() >= k:
            self.occupied += k
            return True
        return False

    def discharge(self, k: int = 1):
        self.occupied = max(0, self.occupied - k)

@dataclass
class Hospital:
    name: str
    distance_km: float
    ed_obs: UnitCapacity
    icu: UnitCapacity
    wards: Dict[str, UnitCapacity]

    def bed_snap(self):
        return {
            "EDObs": self.ed_obs.free(),
            "ICU": self.icu.free(),
            **{k: u.free() for k, u in self.wards.items()}
        }

def pick_hospital_by_capacity_and_eta(hospitals: List[Hospital], svc: str, need_icu: bool = False) -> Hospital:
    best, best_score = None, float("-inf")
    for h in hospitals:
        free = (h.icu.free() if need_icu else h.wards.get(svc, h.ed_obs).free())
        eta_penalty = 0.3 * h.distance_km
        score = free - eta_penalty
        if free > 0 and score > best_score:
            best, best_score = h, score
    return best or min(hospitals, key=lambda x: x.distance_km)

# Diagnostics orchestrator
from dataclasses import dataclass

@dataclass
class Order:
    kind: Literal["XR","CT","LABS","POCUS","ECG"]
    priority: Literal["STAT","ROUTINE"] = "STAT"
    status: Literal["ordered","in_progress","done"] = "ordered"
    eta_min: int = 20

class DiagnosticsOrchestrator:
    def __init__(self):
        self.queue: List[Order] = []

    def order(self, kind: Literal["XR","CT","LABS","POCUS","ECG"], priority: Literal["STAT","ROUTINE"] = "STAT", eta_min: int = 20) -> Order:
        o = Order(kind=kind, priority=priority, eta_min=eta_min)
        self.queue.append(o)
        return o

    def tick(self, minutes: int = 5):
        for o in self.queue:
            if o.status == "ordered":
                o.status = "in_progress"
            elif o.status == "in_progress":
                o.eta_min = max(0, o.eta_min - minutes)
                if o.eta_min == 0:
                    o.status = "done"

    def status(self) -> Dict[str, str]:
        return {f"{i}:{o.kind}": f"{o.status} ({o.eta_min}m)" for i,o in enumerate(self.queue)}

# Service routing
SPECIALTY_KEYS = ["IM","Cardiology","Nephrology","OBGYN"]

def route_service(cc: str, prob_acs: float, labs: Dict[str, float], pregnancy: bool) -> str:
    if pregnancy:
        return "OBGYN"
    if "creatinine" in labs and labs["creatinine"] > 2.5:
        return "Nephrology"
    if prob_acs >= 0.5 or cc.lower() in ("chest pain","sob","syncope"):
        return "Cardiology"
    return "IM"
