
from dataclasses import dataclass
from typing import Dict, List
import pandas as pd

# This version uses exactly your 16 feature names (as seen in the model bundle)
# ['Tag','t_min','Triage','Leitsymptom','HF','MAP','ICU_Kap','Kap_veraltet',
#  't_norm','hat_Labor','Labor_ausstehend','hat_Roentgen','Roentgen_ausstehend',
#  'hat_CT','CT_ausstehend','naechste_Aktion']

@dataclass(frozen=True)
class GateMeta:
    priority: int
    next_action: str
    ttl_sec: int

def _bool(s: pd.Series) -> pd.Series:
    return s.fillna(False).astype(bool) if isinstance(s, pd.Series) else bool(s)

def compute_gates(df: pd.DataFrame) -> pd.DataFrame:
    # Ensure required columns exist; create safe defaults if not present
    col_defaults = {
        "Tag": "",
        "t_min": 0,
        "Triage": "",
        "Leitsymptom": "",
        "HF": 0,
        "MAP": 80,
        "ICU_Kap": 0,
        "Kap_veraltet": False,
        "t_norm": 0.0,
        "hat_Labor": False,
        "Labor_ausstehend": False,
        "hat_Roentgen": False,
        "Roentgen_ausstehend": False,
        "hat_CT": False,
        "CT_ausstehend": False,
        "naechste_Aktion": "",
    }
    for k,v in col_defaults.items():
        if k not in df.columns:
            df[k] = v

    # Extract/derive predicates
    triage = df["Triage"].astype(str).str.title()
    chest_pain = df["Leitsymptom"].astype(str).str.contains("chest|thorax|brust", case=False, na=False)
    t_min = df["t_min"].fillna(0)

    resus_now = (df["MAP"] < 65) | (df["HF"] > 130) | (triage == "Red")
    triage_overdue = ((triage == "Yellow") & (t_min > 10)) | ((triage == "Green") & (t_min > 60))

    # Imaging / lab overdue gates based on your booleans
    labs_due = _bool(df["hat_Labor"]) & _bool(df["Labor_ausstehend"]) & (t_min > 45)
    xray_due = _bool(df["hat_Roentgen"]) & _bool(df["Roentgen_ausstehend"]) & (t_min > 40)
    ct_due   = _bool(df["hat_CT"]) & _bool(df["CT_ausstehend"]) & (t_min > 30)

    # Bed / capacity signal
    bed_escalate = (df["ICU_Kap"].fillna(0) <= 0) & (triage.isin(["Orange","Red"]))

    # Meta ops gate if capacity numbers are stale
    refresh_capacity = _bool(df["Kap_veraltet"])

    # Optional ECG rule from symptom text
    ecg_due = chest_pain & (t_min > 10)

    G: Dict[str, tuple] = {
        "RESUS_NOW":            (resus_now,        GateMeta(5, "Move to resus + call senior.", 60)),
        "TRIAGE_OVERDUE":       (triage_overdue,   GateMeta(3, "Pull patient to triage.", 300)),
        "LABS_OVERDUE":         (labs_due,         GateMeta(2, "Chase labs / call lab.", 600)),
        "XRAY_OVERDUE":         (xray_due,         GateMeta(2, "Call X-ray to expedite.", 600)),
        "CT_OVERDUE":           (ct_due,           GateMeta(3, "Page CT to clear pathway.", 600)),
        "BED_ESCALATE":         (bed_escalate,     GateMeta(4, "Page bed manager for placement.", 600)),
        "REFRESH_CAPACITY":     (refresh_capacity, GateMeta(1, "Refresh ICU/ward capacity.", 900)),
        "ECG_DUE":              (ecg_due,          GateMeta(4, "Do ECG now (10-min rule).", 120)),
    }

    all_active: List[List[str]] = []
    priority: List[int] = []
    next_action: List[str] = []

    for idx in df.index:
        active = [name for name,(mask,_) in G.items() if bool(mask.loc[idx])]
        all_active.append(active)
        if active:
            best = max(active, key=lambda n: G[n][1].priority)
            priority.append(G[best][1].priority)
            next_action.append(G[best][1].next_action)
        else:
            priority.append(0)
            next_action.append("")

    res = df.copy()
    res["gates"] = all_active
    res["priority"] = priority
    res["next_action"] = next_action
    return res
