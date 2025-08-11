
from __future__ import annotations
from typing import Optional, Tuple, Dict, Literal

Sex = Literal["female", "male", "non-binary", "unknown"]

# Roche Elecsys hs‑cTnT (cTnT‑hs) 0/1‑h algorithm thresholds (ESC‑validated):
# Rule‑out: 0h < 5 ng/L (only if symptom onset >3 h) OR 0h < 12 ng/L AND Δ0‑1h < 3 ng/L
# Rule‑in : 0h ≥ 52 ng/L OR Δ0‑1h ≥ 5 ng/L
# Source: Roche Elecsys Troponin T hs STAT method sheet v3.0 (Feb 2024), pp. 3–5.
# Sex‑specific 99th percentile URLs for hs‑cTnT:
#   females: 9.0 ng/L; males: 16.8 ng/L (overall 14 ng/L)
# Same source: Roche Elecsys method sheet v7.0 (Aug 2022) / STAT v3.0 (Feb 2024).
ASSAY = {
    "name": "Roche_Elecsys_hs_cTnT",
    "units": "ng/L",
    "algorithm": {
        "rule_in":  {"abs_0h": 52.0, "delta_1h": 5.0},
        "rule_out": {"single_0h": 5.0,  "band_upper": 12.0, "delta_1h": 3.0}
    },
    "urls_99th": {"female": 9.0, "male": 16.8, "overall": 14.0}
}

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

def hsctnt_99th_url(sex: Sex = "unknown") -> float:
    """Return the sex-specific 99th percentile URL for hs‑cTnT.
    If sex is 'non-binary' or 'unknown', return the *lower* threshold (female)."""
    if sex == "male":
        return ASSAY["urls_99th"]["male"]
    # choose lower threshold by default for inclusivity/safety
    return ASSAY["urls_99th"]["female"]

def classify_hsctnt_0_1h(
    t0: float,
    t1: Optional[float] = None,
    *,
    sex: Sex = "unknown",
    onset_ge_3h: bool = False
) -> Tuple[str, Dict[str, float]]:
    """
    Classify 0/1‑h hs‑cTnT per ESC algorithm with sex‑aware context.
    Returns (label, context) where label in {'rule_in','rule_out','observe'}.
    Context includes: t0, t1 (may be None), delta, trigger, units, url_99th.
    Notes:
      • Single‑sample rule‑out (0h < 5 ng/L) is only valid if symptom onset >3 h.
      • Sex parameter *does not* change the algorithm cutoffs; it sets the URL shown
        in context and downstream pathways that rely on the 99th percentile.
      • For non‑binary / unknown, we use the lower (female) URL by default.
    """
    t0 = _coerce(t0)
    t1 = _coerce(t1) if t1 is not None else None

    ri_abs   = ASSAY["algorithm"]["rule_in"]["abs_0h"]
    ri_d1    = ASSAY["algorithm"]["rule_in"]["delta_1h"]
    ro_single= ASSAY["algorithm"]["rule_out"]["single_0h"]
    ro_band  = ASSAY["algorithm"]["rule_out"]["band_upper"]
    ro_d1    = ASSAY["algorithm"]["rule_out"]["delta_1h"]

    url = hsctnt_99th_url(sex)

    # Single draw logic
    if t1 is None:
        if t0 >= ri_abs:
            return "rule_in", {"t0": t0, "t1": None, "delta": 0.0, "trigger": "abs_0h", "units": ASSAY["units"], "url_99th": url}
        if onset_ge_3h and t0 < ro_single:
            return "rule_out", {"t0": t0, "t1": None, "delta": 0.0, "trigger": "single_0h_valid_>3h", "units": ASSAY["units"], "url_99th": url}
        # no decision possible without 1h sample
        return "observe", {"t0": t0, "t1": None, "delta": 0.0, "trigger": "needs_1h", "units": ASSAY["units"], "url_99th": url}

    delta = t1 - t0

    # Rule-in checks
    if t0 >= ri_abs or delta >= ri_d1:
        return "rule_in", {
            "t0": t0, "t1": t1, "delta": delta,
            "trigger": "abs_0h" if t0 >= ri_abs else "delta_1h",
            "units": ASSAY["units"], "url_99th": url
        }

    # Rule-out checks
    if t0 < ro_single and onset_ge_3h:
        return "rule_out", {"t0": t0, "t1": t1, "delta": delta, "trigger": "single_0h_valid_>3h", "units": ASSAY["units"], "url_99th": url}
    if t0 < ro_band and delta < ro_d1:
        return "rule_out", {"t0": t0, "t1": t1, "delta": delta, "trigger": "band+delta", "units": ASSAY["units"], "url_99th": url}

    # Observe zone
    return "observe", {"t0": t0, "t1": t1, "delta": delta, "trigger": "observe_zone", "units": ASSAY["units"], "url_99th": url}
