
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
import pandas as pd

ACTIONS = {
    "none": 0,
    "resus": 1,
    "rate_ctrl": 2,
    "ct": 3,
    "med_ward_path": 4,
    "abd_protocol": 5,
    "cath_lab": 6,
    "admit": 7
}

@dataclass
class OpsTask:
    fall_id: str
    kind: str
    priority: int
    details: Dict[str, Any]
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        for k,v in list(d.get("details", {}).items()):
            d[f"detail_{k}"] = v
        d.pop("details", None)
        return d

def _ultrasound_codes_from_maps(coding_maps: Optional[Dict[str, Any]]) -> Dict[str, int]:
    defaults = {"abd_pain": 0, "minor_trauma": 4, "polytrauma": 7}
    if not coding_maps or "complaint_to_code" not in coding_maps:
        return defaults
    m = coding_maps["complaint_to_code"]
    out = {}
    for k in defaults.keys():
        if k in m:
            out[k] = int(m[k])
    for k,v in defaults.items(): out.setdefault(k, v)
    return out

def _needs_ultrasound(row: pd.Series, us_codes: Dict[str,int]) -> bool:
    LS = int(row["Leitsymptom"])
    if LS in (us_codes.get("abd_pain", -1), us_codes.get("minor_trauma", -1)):
        return True
    if LS == us_codes.get("polytrauma", -2) and int(row.get("hat_CT",0)) == 0:
        return True
    return False

def imaging_tasks(df: pd.DataFrame, coding_maps: Optional[Dict[str,Any]] = None) -> List[OpsTask]:
    tasks: List[OpsTask] = []
    us_codes = _ultrasound_codes_from_maps(coding_maps)
    for _, r in df.iterrows():
        fid = r["Fall-ID"]
        if int(r["hat_CT"]) == 1 and int(r["CT_ausstehend"]) == 1:
            tasks.append(OpsTask(fid, "imaging_queue", 80, {"modality": "CT"}))
        if int(r["hat_Roentgen"]) == 1 and int(r["Roentgen_ausstehend"]) == 1:
            tasks.append(OpsTask(fid, "imaging_queue", 50, {"modality": "XRay"}))
        if _needs_ultrasound(r, us_codes):
            tasks.append(OpsTask(fid, "imaging_queue", 40, {"modality": "US"}))
    return tasks

def lab_subscriptions(df: pd.DataFrame) -> List[OpsTask]:
    tasks: List[OpsTask] = []
    for _, r in df.iterrows():
        if int(r["hat_Labor"]) == 1 and int(r["Labor_ausstehend"]) == 1:
            tasks.append(OpsTask(r["Fall-ID"], "lab_ready_sub", 90, {"panel": "core"}))
    return tasks

def bed_eta(df: pd.DataFrame) -> List[OpsTask]:
    tasks: List[OpsTask] = []
    for _, r in df.iterrows():
        if int(r["naechste_Aktion"]) == ACTIONS["admit"]:
            if int(r["ICU_Kap"]) > 0:
                tasks.append(OpsTask(r["Fall-ID"], "bed_eta", 95, {"unit": "ICU", "eta_min": 0}))
            else:
                tasks.append(OpsTask(r["Fall-ID"], "bed_eta", 70, {"unit": "ICU", "eta_min": 60, "eta_max": 240}))
    return tasks

def discharge_ready(df: pd.DataFrame) -> List[OpsTask]:
    tasks: List[OpsTask] = []
    pending = (df["Labor_ausstehend"].astype(int) | df["CT_ausstehend"].astype(int) | df["Roentgen_ausstehend"].astype(int)) > 0
    ready = (~pending) & (df["naechste_Aktion"].astype(int) != ACTIONS["admit"])
    for fid in df.loc[ready, "Fall-ID"].unique():
        tasks.append(OpsTask(fid, "discharge_ready", 60, {}))
    return tasks

def dedupe_latest(df: pd.DataFrame) -> pd.DataFrame:
    idx = df.sort_values(["Fall-ID","t_min"]).groupby("Fall-ID").tail(1).index
    return df.loc[idx].copy()

def build_ops_queue(df_events: pd.DataFrame, coding_maps: Optional[Dict[str,Any]] = None) -> List[OpsTask]:
    snap = dedupe_latest(df_events)
    tasks = imaging_tasks(snap, coding_maps) + lab_subscriptions(snap) + bed_eta(snap) + discharge_ready(snap)
    tasks.sort(key=lambda x: -x.priority)
    return tasks
