
from typing import Tuple, Dict, Optional

ASSAYS = {
    "Abbott_Architect_hs_cTnI": {
        "units": "ng/L",
        "rule_in":  {"abs_0h": 64.0, "delta_1h": 6.0},
        "rule_out": {"single_0h": 2.0, "band_upper": 5.0, "delta_1h": 2.0},
        "imprecision_note": "Caution near LoD; Δ<2 ng/L relies on tight QC."
    },
    "Roche_hs_cTnT": {
        "units": "ng/L",
        "rule_in":  {"abs_0h": 52.0, "delta_1h": 5.0},
        "rule_out": {"single_0h": 5.0, "band_upper": 12.0, "delta_1h": 3.0}
    }
}

DEFAULT_ASSAY = "Abbott_Architect_hs_cTnI"

class TroponinValueError(ValueError):
    pass

def _coerce(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    try:
        v = float(value)
    except Exception as e:
        raise TroponinValueError(f"Non-numeric troponin value: {value!r}") from e
    if v < 0 or not (v == v) or v in (float('inf'), float('-inf')):
        raise TroponinValueError(f"Invalid troponin value: {value!r}")
    return v

def classify_troponin_0_1h(assay_key: str, t0: float, t1: Optional[float]) -> Tuple[str, Dict[str, float]]:
    """
    Robust 0/1h hs-cTn classifier with proper single-draw handling.
    Returns (label, context) where label in {'rule_in','rule_out','observe'}.
    Context contains t0, t1 (possibly None), delta (0 if t1 is None), and trigger.
    """
    if assay_key not in ASSAYS:
        raise KeyError(f"Unknown assay: {assay_key}")
    t0 = _coerce(t0)
    t1 = _coerce(t1) if t1 is not None else None

    spec = ASSAYS[assay_key]
    ri_abs   = spec["rule_in"]["abs_0h"]
    ri_d1    = spec["rule_in"]["delta_1h"]
    ro_single= spec["rule_out"]["single_0h"]
    ro_band  = spec["rule_out"]["band_upper"]
    ro_d1    = spec["rule_out"]["delta_1h"]

    # Single draw logic
    if t1 is None:
        if t0 >= ri_abs:
            return "rule_in", {"t0": t0, "t1": None, "delta": 0.0, "trigger": "abs_0h"}
        if t0 < ro_single:
            return "rule_out", {"t0": t0, "t1": None, "delta": 0.0, "trigger": "single_0h"}
        return "observe", {"t0": t0, "t1": None, "delta": 0.0, "trigger": "needs_1h"}

    delta = t1 - t0

    if t0 >= ri_abs or delta >= ri_d1:
        return "rule_in", {"t0": t0, "t1": t1, "delta": delta, "trigger": "abs_0h" if t0 >= ri_abs else "delta_1h"}
    if t0 < ro_single:
        return "rule_out", {"t0": t0, "t1": t1, "delta": delta, "trigger": "single_0h"}
    if t0 < ro_band and delta < ro_d1:
        return "rule_out", {"t0": t0, "t1": t1, "delta": delta, "trigger": "band+delta"}

    return "observe", {"t0": t0, "t1": t1, "delta": delta, "trigger": "observe_zone"}
