
from typing import Dict, Any, List, Optional

# ---------- helpers ----------
def _num(fd: Dict[str,Any], *keys, default: Optional[float]=None) -> Optional[float]:
    for k in keys:
        if k in fd and fd[k] is not None:
            try:
                return float(fd[k])
            except Exception:
                pass
    return default

def _parse_rr_string(rr: str) -> Optional[float]:
    # Accept formats like '120/80', '120/80 mmHg', 'RR 120/80'
    try:
        import re
        m = re.search(r"(\d{2,3})\s*/\s*(\d{2,3})", str(rr))
        if m:
            return float(m.group(1))
    except Exception:
        pass
    return None

def _sbp(fd: Dict[str,Any]) -> Optional[float]:
    # Common keys: SBP, RR_sys, BP_sys, systolic, Systolic, or parse 'RR' like '120/80'
    sbp = _num(fd, "SBP", "RR_sys", "BP_sys", "systolic", "Systolic")
    if sbp is not None:
        return sbp
    rr = fd.get("RR") or fd.get("RR_mmHg") or fd.get("RR_str")
    if rr is not None:
        return _parse_rr_string(str(rr))
    return None

def _cfg(cfg: Dict[str,Any], key: str, default):
    try:
        return type(default)(cfg.get(key, default))
    except Exception:
        return default

# ---------- main ----------
def compute_gates_from_features(fd: Dict[str,Any], cfg: Dict[str,Any]) -> Dict[str,Any]:
    """Ops rules (fallback): SBP-centric resus + abdomen guardrails + venous BGA flags.
    Adds notification gates for nurse/doc, and attending for critical.
    Returns gatepack: {'gates','priority','next_action','explain','ttl'}.
    """
    gates: List[str] = []
    prio = 0
    action = ""
    explain: List[str] = []
    ttl = {}

    # --- Immediate resus via triage or SBP context (no MAP dependence) ---
    triage = str(fd.get("Triage", "")).title()
    if triage == "Red":
        gates.append("RESUS_NOW")
        prio = max(prio, 5); action = action or "Move to resus + call senior."
        explain.append("triage Red")
    else:
        sbp = _sbp(fd)
        hr = _num(fd, "HF", "HR", "heart_rate")
        spo2 = _num(fd, "SpO2", "SpO₂", "SpO2_pct")
        gcs = _num(fd, "GCS")
        if sbp is not None and sbp < 90:
            gates.append("RESUS_NOW")
            prio = max(prio, 5); action = action or "Move to resus + call senior."
            explain.append("SBP<90 mmHg")
        elif sbp is not None and sbp < 100 and (
            (hr is not None and hr > 130) or
            (spo2 is not None and spo2 < 90) or
            (gcs is not None and gcs < 15)
        ):
            gates.append("RESUS_NOW")
            prio = max(prio, 5); action = action or "Move to resus + call senior."
            explain.append("SBP<100 with shock features (HR>130 or SpO2<90 or GCS<15)")
        else:
            # Last fallback only: MAP if explicitly present
            map_v = _num(fd, "MAP")
            if map_v is not None and map_v < 65:
                gates.append("RESUS_NOW")
                prio = max(prio, 5); action = action or "Move to resus + call senior."
                explain.append("MAP<65 (fallback only)")

    # --- Venous BGA (VBG) flags ---
    # Config thresholds (override in CONFIG as needed)
    PH_CRIT_LOW     = _cfg(cfg, "TH_BGA_PH_CRIT_LOW", 7.10)
    PH_ALK_HIGH     = _cfg(cfg, "TH_BGA_PH_ALK_HIGH", 7.50)  # HIGH if pH >= 7.50
    PH_ALK_CRIT     = _cfg(cfg, "TH_BGA_PH_ALK_CRIT", 7.55)  # CRITICAL if pH > 7.55
    LACT_CRIT       = _cfg(cfg, "TH_BGA_LACTATE_CRIT", 4.0)  # mmol/L
    LACT_HIGH       = _cfg(cfg, "TH_BGA_LACTATE_HIGH", 2.0)  # mmol/L
    PCO2_CRIT       = _cfg(cfg, "TH_BGA_PCO2_CRIT", 60.0)    # mmHg (venous)
    HCO3_LOW        = _cfg(cfg, "TH_BGA_HCO3_LOW", 15.0)     # mmol/L
    BE_LOW          = _cfg(cfg, "TH_BGA_BE_LOW", -10.0)      # mEq/L
    K_CRIT_HIGH     = _cfg(cfg, "TH_BGA_K_CRIT_HIGH", 6.5)   # mmol/L
    K_HIGH          = _cfg(cfg, "TH_BGA_K_HIGH", 6.0)        # mmol/L
    K_CRIT_LOW      = _cfg(cfg, "TH_BGA_K_CRIT_LOW", 2.5)    # mmol/L
    K_LOW           = _cfg(cfg, "TH_BGA_K_LOW", 2.8)         # mmol/L
    NA_LOW          = _cfg(cfg, "TH_BGA_NA_LOW", 129.0)      # mmol/L
    NA_CRIT_LOW     = _cfg(cfg, "TH_BGA_NA_CRIT_LOW", 125.0) # mmol/L
    NA_HIGH         = _cfg(cfg, "TH_BGA_NA_HIGH", 145.0)     # mmol/L
    AG_LOW          = _cfg(cfg, "TH_BGA_AG_LOW", 8.0)        # mmol/L
    AG_HIGH         = _cfg(cfg, "TH_BGA_AG_HIGH", 16.0)      # mmol/L

    # Read typical VBG keys (presence-guarded; accept variants)
    ph   = _num(fd, "vbg_pH", "BGA_pH", "pH_ven", "pH")
    pco2 = _num(fd, "vbg_pCO2_mmHg", "vbg_pco2_mmHg", "BGA_pCO2", "pCO2_ven", "pCO2")
    lact = _num(fd, "vbg_lactate", "Lactate", "lactate")
    hco3 = _num(fd, "vbg_HCO3", "HCO3", "bicarbonate")
    be   = _num(fd, "vbg_BE", "base_excess", "BE")
    k    = _num(fd, "vbg_K", "K", "Potassium")
    na   = _num(fd, "vbg_Na", "Na", "Sodium")
    cl   = _num(fd, "vbg_Cl", "Cl", "Chloride")

    # pH tiers (order matters: CRITICAL first so we don't emit both)
    if ph is not None:
        if ph > PH_ALK_CRIT:
            gates.append("BGA_ALKALOSIS_CRITICAL"); explain.append(f"VBG pH>{PH_ALK_CRIT}")
            prio = max(prio, 5)
            action = action or "Critical alkalosis on VBG — escalate care."
        elif ph >= PH_ALK_HIGH:
            gates.append("BGA_ALKALOSIS_HIGH"); explain.append(f"VBG pH≥{PH_ALK_HIGH}")
            prio = max(prio, 4)
            action = action or "Severe alkalosis on VBG — escalate care."
        elif ph < PH_CRIT_LOW:
            gates.append("BGA_ACIDOSIS_CRITICAL"); explain.append(f"VBG pH<{PH_CRIT_LOW}")
            prio = max(prio, 5)
            action = action or "Critical acidosis on VBG — escalate care."

    # Lactate
    if lact is not None:
        if lact >= LACT_CRIT:
            gates.append("BGA_LACTATE_CRITICAL"); explain.append(f"Lactate≥{LACT_CRIT} mmol/L")
            prio = max(prio, 5)
            action = action or "High lactate — treat shock/sepsis causes."
        elif lact >= LACT_HIGH:
            gates.append("BGA_LACTATE_HIGH"); explain.append(f"Lactate≥{LACT_HIGH} mmol/L")
            prio = max(prio, 3)
            action = action or "Elevated lactate — reassess perfusion."

    # CO2
    if pco2 is not None and pco2 >= PCO2_CRIT:
        gates.append("BGA_HYPERCAPNIA"); explain.append(f"pCO2≥{PCO2_CRIT} mmHg (venous)")
        prio = max(prio, 4)
        action = action or "Severe hypercapnia — evaluate ventilation."

    # HCO3 / BE
    if hco3 is not None and hco3 < HCO3_LOW:
        gates.append("BGA_BICARB_LOW"); explain.append(f"HCO3<{HCO3_LOW} mmol/L")
        prio = max(prio, 3); action = action or "Metabolic acidosis — investigate cause."
    if be is not None and be <= BE_LOW:
        gates.append("BGA_BASE_EXCESS_LOW"); explain.append(f"BE≤{BE_LOW}")
        prio = max(prio, 3); action = action or "Base deficit — assess acidosis severity."

    # Electrolytes — Potassium
    if k is not None:
        if k >= K_CRIT_HIGH:
            gates.append("BGA_HYPERKALAEMIA_CRITICAL"); explain.append(f"K≥{K_CRIT_HIGH} mmol/L")
            prio = max(prio, 5)
            action = action or "Hyperkalaemia — follow protocol now."
        elif k >= K_HIGH:
            gates.append("BGA_HYPERKALAEMIA_HIGH"); explain.append(f"K≥{K_HIGH} mmol/L")
            prio = max(prio, 4)
            action = action or "Hyperkalaemia — treat per protocol."
        if k < K_CRIT_LOW:
            gates.append("BGA_HYPOKALAEMIA_CRITICAL"); explain.append(f"K<{K_CRIT_LOW} mmol/L")
            prio = max(prio, 5)
            action = action or "Severe hypokalaemia — correct urgently."
        elif k <= K_LOW:
            gates.append("BGA_HYPOKALAEMIA"); explain.append(f"K≤{K_LOW} mmol/L")
            prio = max(prio, 4); action = action or "Hypokalaemia — correct carefully."

    # Electrolytes — Sodium (general vs critical low)
    if na is not None:
        if na <= NA_CRIT_LOW:
            gates.append("BGA_DYSNATRAEMIA_CRITICAL"); explain.append(f"Na≤{NA_CRIT_LOW} mmol/L")
            prio = max(prio, 5)
            action = action or "Severe hyponatraemia — manage safely."
        elif na <= NA_LOW or na >= NA_HIGH:
            gates.append("BGA_DYSNATRAEMIA"); explain.append(f"Na out of range (≤{NA_LOW} or ≥{NA_HIGH})")
            prio = max(prio, 3); action = action or "Dysnatremia — address underlying cause."

    # Anion gap (requires Na, Cl, HCO3; include K if available)
    if na is not None and cl is not None and hco3 is not None:
        ag = na + (k if k is not None else 0.0) - cl - hco3
        if ag < AG_LOW:
            gates.append("BGA_ANION_GAP_LOW"); explain.append(f"Anion gap<{AG_LOW} mmol/L")
            prio = max(prio, 2)
        elif ag > AG_HIGH:
            gates.append("BGA_ANION_GAP_HIGH"); explain.append(f"Anion gap>{AG_HIGH} mmol/L")
            prio = max(prio, 3)

    # Summary critical flag for BGA + notifications
    any_bga_gate = any(g.startswith("BGA_") for g in gates)
    any_critical = any(g.endswith("_CRITICAL") for g in gates)
    if any_critical and "BGA_CRITICAL" not in gates:
        gates.append("BGA_CRITICAL")
    if any_bga_gate:
        gates.append("ALERT_NURSE"); ttl["ALERT_NURSE"] = 300
        gates.append("ALERT_DOC"); ttl["ALERT_DOC"] = 300
        if any_critical:
            gates.append("ALERT_ATTENDING"); ttl["ALERT_ATTENDING"] = 300

    # --- Abdominal pain guardrails ---
    lt = str(fd.get("Leitsymptom", "")).lower()
    if any(kword in lt for kword in ["abd", "bauch", "abdominal"]):
        if not (fd.get("US_done") or fd.get("CT_done")):
            gates.append("CT_OVERDUE")
            explain.append("Abdominal pain: US/CT required")
            prio = max(prio, 3)
            action = action or "Order Ultrasound ± CT."
        labs_cycles = int(fd.get("labs_cycles_done", fd.get("labs_count", 0)) or 0)
        if labs_cycles < 2:
            gates.append("LABS_OVERDUE")
            explain.append("Abdominal pain: labs cycle <2")
            prio = max(prio, 3)
            action = action or "Repeat labs (≥2 cycles)."
        gates.append("ABDOMEN_GUARDRAILS")
        prio = max(prio, 4)
        action = action or "Keep in Obs; no discharge <24h."

    # de-dup preserve order
    seen = set()
    gates = [g for g in gates if (g not in seen and not seen.add(g))]

    return {"gates": gates, "priority": prio, "next_action": action, "explain": explain, "ttl": ttl}
