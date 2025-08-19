"""
ED Pipeline v7 (consolidated, domain-tuned)

Changes vs v6 according to domain input:
- Troponin: no age adjustment. Use generic delta; if CKD (or low eGFR) present, emit an advisory:
  "Patient has CKD or other conditions that can elevate baseline troponin (e.g., pulmonary embolism) — check troponin baseline if available".
- D-dimer: age-adjusted threshold = 0.5 mg/L FEU + 0.1 mg/L per decade above age 50. (Age <= 50 -> 0.5)
  Always remind to compute Wells-PE and Wells-DVT when handling D-dimer results.
- Scores included: Marburg Heart Score, HEART, GRACE (points model), Wells-PE, Wells-DVT.
- SOFA: guarded minimal implementation. Computes domains only if inputs are available and reports missing domains.
- Lingering Patient Monitor: emits time-based alerts for ED boarding patients.
- ResultsNotifier: simple event bus that handles OBX-like lab results for D-dimer and Troponin.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union
import math

# --- Contract flags / bootstrap interop --------------------------------------------
try:
    CONFIG  # type: ignore
    RUN_PIPELINE = bool(CONFIG.get("RUN_PIPELINE", False))  # v6 pattern
except Exception:
    RUN_PIPELINE = False

pandas shim for timestamps -------------------------------------------------
try:
    import pandas as pd  # type: ignore
except Exception:  # pragma: no cover
    class _PDShim:
        @staticmethod
        def Timestamp(ts: Optional[Union[str, float]] = None):
            import datetime as _dt
            if ts is None:
                return _dt.datetime.utcnow()
            try:
                # Accept ISO8601-ish strings
                return _dt.datetime.fromisoformat(str(ts))
            except Exception:
                return _dt.datetime.utcnow()
        @staticmethod
        def Timedelta(**kw):
            import datetime as _dt
            return _dt.timedelta(**kw)
        @staticmethod
        def to_datetime(x):
            return _PDShim.Timestamp(x)
        @staticmethod
        def isna(x):
            return x is None
    pd = _PDShim()  # type: ignore

# ==============================================================================
# Patient context
# ==============================================================================

@dataclass
class PatientContext:
    patient_id: str
    age_years: Optional[int] = None
    sex: Optional[str] = None  # "M" / "F" / None
    comorbidities: List[str] = field(default_factory=list)  # include "CKD" if present
    egfr_ml_min_1_73m2: Optional[float] = None
    baseline_troponin_ng_L: Optional[float] = None

    def has_ckd(self) -> bool:
        """Return True if context indicates chronic kidney disease or low eGFR (<60)."""
        try:
            if any((c or "").strip().upper() == "CKD" for c in self.comorbidities):
                return True
            if self.egfr_ml_min_1_73m2 is not None and float(self.egfr_ml_min_1_73m2) < 60.0:
                return True
            return False
        except Exception:
            return False

# ==============================================================================
# D-dimer and Troponin helpers
# ==============================================================================

class Units:
    MG_L = "mg/L"
    UG_ML = "ug/mL"  # numerically equal to mg/L
    NG_ML = "ng/mL"
    UG_L = "ug/L"
    NG_L = "ng/L"


def _to_mg_per_L(value: float, unit: str) -> float:
    """Convert a value to mg/L (FEU) based on unit string."""
    u = (unit or "").strip().lower()
    if u in {"mg/l", "ug/ml"}:
        return float(value)
    if u in {"ng/ml"}:
        return float(value) / 1000.0
    if u in {"ug/l"}:
        return float(value) / 1000.0
    if u in {"ng/l"}:
        return float(value) / 1_000_000.0
    # Unknown unit: assume mg/L
    return float(value)


def compute_age_adjusted_ddimer_threshold(age_years: Optional[int],
                                          base_mg_L: float = 0.5,
                                          per_decade_add: float = 0.1) -> float:
    """
    Age-adjusted D-dimer threshold (mg/L FEU):
      threshold = 0.5 + 0.1 * N, where N is the number of decades above 50.
      Age <= 50 -> 0.5
      51-59 -> 0.6, 60-69 -> 0.7, 70-79 -> 0.8, 80-89 -> 0.9, etc.
    """
    if age_years is None or age_years <= 50:
        return base_mg_L
    # For ages 51-59, N should be 1; for 60-69, N=2, etc.
    increments = 1 + (int(age_years) - 50) // 10
    return round(base_mg_L + per_decade_add * increments, 3)


def interpret_ddimer(value: float, unit: str, *, age_years: Optional[int]) -> Dict[str, Any]:
    """
    Interpret D-dimer value against the age-adjusted threshold.
    Returns a dict with normalized value (mg/L), threshold, positivity, and reminders.
    """
    val_mg_L = _to_mg_per_L(float(value), unit)
    thr = compute_age_adjusted_ddimer_threshold(age_years)
    positive = val_mg_L >= thr
    return {
        "value_mg_L": round(val_mg_L, 4),
        "threshold_mg_L": thr,
        "is_positive": bool(positive),
        "reminders": ["Compute Wells-PE", "Compute Wells-DVT"],
        "advice": (
            "D-dimer positive vs age-adjusted threshold; follow PE/DVT diagnostic pathway"
            if positive else
            "D-dimer below age-adjusted threshold; in low/intermediate pretest probability, VTE may be excluded"
        ),
    }


def compute_troponin_delta(curr: float,
                           prev: Optional[float],
                           rel_pct_threshold: float = 20.0,
                           abs_ng_L_threshold: Optional[float] = None) -> Dict[str, Any]:
    """
    Generic troponin delta logic without age adjustment.
    Inputs are ng/L (high-sensitivity assays).
    Returns keys: can_compute, rel_change_pct, abs_delta, exceeds_relative, exceeds_absolute, delta_flag.
    """
    if prev is None or prev <= 0:
        return {
            "can_compute": False,
            "rel_change_pct": None,
            "abs_delta": None,
            "exceeds_relative": None,
            "exceeds_absolute": None,
            "delta_flag": False,
        }
    abs_delta = float(curr) - float(prev)
    rel_change_pct = (abs_delta / float(prev)) * 100.0
    exceeds_rel = abs(rel_change_pct) >= float(rel_pct_threshold)
    exceeds_abs = None
    if abs_ng_L_threshold is not None:
        exceeds_abs = abs(abs_delta) >= float(abs_ng_L_threshold)
    delta_flag = bool(exceeds_rel or (exceeds_abs is True))
    return {
        "can_compute": True,
        "rel_change_pct": round(rel_change_pct, 2),
        "abs_delta": round(abs_delta, 2),
        "exceeds_relative": bool(exceeds_rel),
        "exceeds_absolute": exceeds_abs,
        "delta_flag": delta_flag,
    }

# ==============================================================================
# Scores
# ==============================================================================

@dataclass
class ScoreResult:
    name: str
    score: float
    category: Optional[str]
    details: Dict[str, Any] = field(default_factory=dict)

# --- Marburg Heart Score ------------------------------------------------------

def marburg_heart_score(*,
                        male_ge_55_or_female_ge_65: bool,
                        known_vascular_disease: bool,
                        pain_worse_with_exercise: bool,
                        patient_assumes_cardiac: bool,
                        pain_not_reproducible_by_palpation: bool) -> ScoreResult:
    items = [
        male_ge_55_or_female_ge_65,
        known_vascular_disease,
        pain_worse_with_exercise,
        patient_assumes_cardiac,
        pain_not_reproducible_by_palpation,
    ]
    score = sum(1 for x in items if bool(x))
    if score <= 1:
        cat = "CAD very unlikely"
    elif score <= 2:
        cat = "CAD unlikely"
    elif score <= 3:
        cat = "Intermediate"
    else:
        cat = "High"
    return ScoreResult(
        name="Marburg Heart Score",
        score=float(score),
        category=cat,
        details={"items_true": score}
    )

# --- HEART score --------------------------------------------------------------

def heart_score(*, history: int, ecg: int, age: int, risk_factors: int, troponin: int) -> ScoreResult:
    """
    HEART components are supplied as integers in {0,1,2} by the caller.
    Bands: 0-3 Low, 4-6 Moderate, 7-10 High.
    """
    for k, v in {"history": history, "ecg": ecg, "age": age, "risk_factors": risk_factors, "troponin": troponin}.items():
        if v not in (0, 1, 2):
            raise ValueError(f"{k} must be 0, 1, or 2")
    score = history + ecg + age + risk_factors + troponin
    if score <= 3:
        cat = "Low"
    elif score <= 6:
        cat = "Moderate"
    else:
        cat = "High"
    return ScoreResult(
        name="HEART",
        score=float(score),
        category=cat,
        details={"components": {"history": history, "ecg": ecg, "age": age, "risk_factors": risk_factors, "troponin": troponin}}
    )

# --- GRACE (points model) -----------------------------------------------------

def _grace_points_age(age: int) -> int:
    if age < 30: return 0
    if age < 40: return 8
    if age < 50: return 25
    if age < 60: return 41
    if age < 70: return 58
    if age < 80: return 75
    if age < 90: return 91
    return 100

def _grace_points_hr(hr: int) -> int:
    if hr < 50: return 0
    if hr < 70: return 3
    if hr < 90: return 9
    if hr < 110: return 15
    if hr < 150: return 24
    if hr < 200: return 38
    return 46

def _grace_points_sbp(sbp: int) -> int:
    if sbp < 80: return 58
    if sbp < 100: return 53
    if sbp < 120: return 43
    if sbp < 140: return 34
    if sbp < 160: return 24
    if sbp < 200: return 10
    return 0

def _grace_points_creat_mgdl(creat: float) -> int:
    if creat < 0.4: return 1
    if creat < 0.8: return 4
    if creat < 1.2: return 7
    if creat < 1.6: return 10
    if creat < 2.0: return 13
    if creat < 4.0: return 21
    return 28

def grace_points(*,
                 age: int, hr: int, sbp: int, creat_mgdl: float,
                 killip_class: int,
                 cardiac_arrest_at_admission: bool,
                 st_deviation_present: bool,
                 elevated_enzymes: bool) -> ScoreResult:
    pts = 0
    pts += _grace_points_age(int(age))
    pts += _grace_points_hr(int(hr))
    pts += _grace_points_sbp(int(sbp))
    pts += _grace_points_creat_mgdl(float(creat_mgdl))
    killip_pts = {1: 0, 2: 20, 3: 39, 4: 59}.get(int(killip_class), 0)
    pts += killip_pts
    if cardiac_arrest_at_admission:
        pts += 39
    if st_deviation_present:
        pts += 28
    if elevated_enzymes:
        pts += 14
    if pts < 109:
        cat = "Low"
    elif pts <= 140:
        cat = "Intermediate"
    else:
        cat = "High"
    return ScoreResult(
        name="GRACE (points)",
        score=float(pts),
        category=cat,
        details={
            "components_points": {
                "age": _grace_points_age(int(age)),
                "hr": _grace_points_hr(int(hr)),
                "sbp": _grace_points_sbp(int(sbp)),
                "creatinine": _grace_points_creat_mgdl(float(creat_mgdl)),
                "killip": killip_pts,
                "cardiac_arrest": 39 if cardiac_arrest_at_admission else 0,
                "st_deviation": 28 if st_deviation_present else 0,
                "enzymes": 14 if elevated_enzymes else 0,
            }
        }
    )

# --- Wells scores -------------------------------------------------------------

def wells_pe(*,
             clinical_signs_dvt: bool,
             pe_more_likely_than_alt: bool,
             hr_gt_100: bool,
             immobilization_or_surgery_recent: bool,
             previous_dvt_pe: bool,
             hemoptysis: bool,
             cancer: bool) -> ScoreResult:
    pts = 0.0
    pts += 3.0 if clinical_signs_dvt else 0.0
    pts += 3.0 if pe_more_likely_than_alt else 0.0
    pts += 1.5 if hr_gt_100 else 0.0
    pts += 1.5 if immobilization_or_surgery_recent else 0.0
    pts += 1.5 if previous_dvt_pe else 0.0
    pts += 1.0 if hemoptysis else 0.0
    pts += 1.0 if cancer else 0.0
    two_tier = "PE likely" if pts > 4.0 else "PE unlikely"
    if pts <= 1.5:
        three_tier = "Low"
    elif pts <= 6.0:
        three_tier = "Intermediate"
    else:
        three_tier = "High"
    return ScoreResult(name="Wells-PE", score=float(pts), category=two_tier, details={"three_tier": three_tier})

def wells_dvt(*,
              active_cancer: bool,
              paralysis_or_immobilization: bool,
              bedridden_3days_or_surgery_12w: bool,
              localized_tenderness_deep_veins: bool,
              entire_leg_swollen: bool,
              calf_swelling_ge_3cm: bool,
              pitting_edema: bool,
              collateral_superficial_veins: bool,
              previous_dvt: bool,
              alternative_dx_as_likely: bool) -> ScoreResult:
    pts = 0
    pts += 1 if active_cancer else 0
    pts += 1 if paralysis_or_immobilization else 0
    pts += 1 if bedridden_3days_or_surgery_12w else 0
    pts += 1 if localized_tenderness_deep_veins else 0
    pts += 1 if entire_leg_swollen else 0
    pts += 1 if calf_swelling_ge_3cm else 0
    pts += 1 if pitting_edema else 0
    pts += 1 if collateral_superficial_veins else 0
    pts += 1 if previous_dvt else 0
    pts += -2 if alternative_dx_as_likely else 0
    category = "DVT likely" if pts >= 2 else "DVT unlikely"
    return ScoreResult(name="Wells-DVT", score=float(pts), category=category, details={})

# ==============================================================================
# SOFA (guarded minimal implementation)
# ==============================================================================

def sofa_score(*,
               pao2_fio2: Optional[float] = None,
               platelets_x10e9_L: Optional[float] = None,
               bilirubin_mg_dL: Optional[float] = None,
               map_mmHg: Optional[float] = None,
               vasopressors: Optional[Dict[str, float]] = None,  # mcg/kg/min for keys: dopamine, dobutamine, norepinephrine, epinephrine
               gcs: Optional[int] = None,
               creatinine_mg_dL: Optional[float] = None,
               urine_ml_per_day: Optional[float] = None) -> ScoreResult:
    details: Dict[str, Any] = {}
    missing: List[str] = []
    total = 0

    # Respiratory (PaO2/FiO2)
    if pao2_fio2 is None:
        missing.append("respiratory")
    else:
        if pao2_fio2 >= 400: resp = 0
        elif pao2_fio2 >= 300: resp = 1
        elif pao2_fio2 >= 200: resp = 2
        elif pao2_fio2 >= 100: resp = 3
        else: resp = 4
        details["respiratory"] = resp
        total += resp

    # Coagulation (platelets x10^9/L)
    if platelets_x10e9_L is None:
        missing.append("coagulation")
    else:
        pl = platelets_x10e9_L
        if pl >= 150: coag = 0
        elif pl >= 100: coag = 1
        elif pl >= 50: coag = 2
        elif pl >= 20: coag = 3
        else: coag = 4
        details["coagulation"] = coag
        total += coag

    # Liver (bilirubin mg/dL)
    if bilirubin_mg_dL is None:
        missing.append("liver")
    else:
        b = bilirubin_mg_dL
        if b < 1.2: liv = 0
        elif b < 2.0: liv = 1
        elif b < 6.0: liv = 2
        elif b < 12.0: liv = 3
        else: liv = 4
        details["liver"] = liv
        total += liv

    # Cardiovascular (MAP and vasopressors)
    if map_mmHg is None and not vasopressors:
        missing.append("cardiovascular")
    else:
        cv = 0
        if map_mmHg is not None and map_mmHg < 70:
            cv = max(cv, 1)
        if vasopressors:
            dopa = float(vasopressors.get("dopamine", 0.0)) if isinstance(vasopressors, dict) else 0.0
            dobut = float(vasopressors.get("dobutamine", 0.0)) if isinstance(vasopressors, dict) else 0.0
            ne = float(vasopressors.get("norepinephrine", 0.0)) if isinstance(vasopressors, dict) else 0.0
            epi = float(vasopressors.get("epinephrine", 0.0)) if isinstance(vasopressors, dict) else 0.0
            if dobut > 0 or (dopa > 0 and dopa <= 5): cv = max(cv, 2)
            if (5 < dopa <= 15) or (0.05 <= ne <= 0.1) or (0.05 <= epi <= 0.1): cv = max(cv, 3)
            if (dopa > 15) or (ne > 0.1) or (epi > 0.1): cv = max(cv, 4)
        details["cardiovascular"] = cv
        total += cv

    # CNS (GCS)
    if gcs is None:
        missing.append("cns")
    else:
        if gcs >= 15: cns = 0
        elif gcs >= 13: cns = 1
        elif gcs >= 10: cns = 2
        elif gcs >= 6: cns = 3
        else: cns = 4
        details["cns"] = cns
        total += cns

    # Renal (creatinine and/or urine)
    if creatinine_mg_dL is None and urine_ml_per_day is None:
        missing.append("renal")
    else:
        ren = 0
        if creatinine_mg_dL is not None:
            cr = creatinine_mg_dL
            if cr < 1.2: ren = max(ren, 0)
            elif cr < 2.0: ren = max(ren, 1)
            elif cr < 3.5: ren = max(ren, 2)
            elif cr < 5.0: ren = max(ren, 3)
            else: ren = max(ren, 4)
        if urine_ml_per_day is not None:
            u = urine_ml_per_day
            if u < 200: ren = max(ren, 4)
            elif u < 500: ren = max(ren, 3)
        details["renal"] = ren
        total += ren

    cat = f"Total={total}" if not missing else None
    return ScoreResult(name="SOFA", score=float(total), category=cat, details={"domains": details, "missing": missing})

# ==============================================================================
# Results Notifier (lab result handler)
# ==============================================================================

class ResultsNotifier:
    """
    Simplified results event emitter. Integrate with your HL7/feeds.
    Use handle_lab_result(patient, test_code, value, unit, obx_abnormal_flag=None, ts=None).
    """
    def __init__(self):
        # prior_values[patient_id][test_code] = (value, ts)
        self.prior_values: Dict[str, Dict[str, Tuple[float, Any]]] = {}
        # Troponin delta rule (no age dependency)
        self.trop_rel_pct: float = 20.0
        self.trop_abs_ng_L: Optional[float] = None  # set if lab wants absolute delta too
        self.listeners: List[Any] = []  # callables(event_type, payload)

    def on(self, callback):
        self.listeners.append(callback)

    def emit(self, event_type: str, payload: Dict[str, Any]):
        for cb in list(self.listeners):
            try:
                cb(event_type, payload)
            except Exception:
                pass

    def _remember(self, patient_id: str, test_code: str, value: float, ts: Any):
        self.prior_values.setdefault(patient_id, {})[test_code] = (float(value), ts)

    def handle_lab_result(self, patient: PatientContext, test_code: str, value: float, unit: str,
                          *, obx_abnormal_flag: Optional[str] = None, ts: Optional[Any] = None) -> Dict[str, Any]:
        test_code_u = (test_code or "").strip().upper()
        payload: Dict[str, Any] = {
        # Contract guard: clinical pipeline disabled -> return payload without emitting
        if not RUN_PIPELINE:
            return payload

            "patient_id": patient.patient_id,
            "test_code": test_code_u,
            "value": float(value),
            "unit": unit,
            "ts": str(ts) if ts is not None else str(pd.Timestamp()),
        }

        # D-dimer
        if test_code_u in {"D-DIMER", "DDIMER", "D DIMER"}:
            interp = interpret_ddimer(value, unit, age_years=patient.age_years)
            payload.update({"ddimer": interp})
            payload.setdefault("reminders", []).extend(interp.get("reminders", []))
            self.emit("lab_result_ddimer", payload)
            self._remember(patient.patient_id, test_code_u, float(value), ts)
            return payload

        # Troponin
        if test_code_u in {"TROPONIN", "TROPHS", "TNI", "TROP"}:
            prev = self.prior_values.get(patient.patient_id, {}).get(test_code_u, (None, None))[0]
            delta = compute_troponin_delta(curr=float(value), prev=prev,
                                           rel_pct_threshold=self.trop_rel_pct,
                                           abs_ng_L_threshold=self.trop_abs_ng_L)
            payload.update({"troponin_delta": delta, "abnormal_flag": obx_abnormal_flag})

            # CKD advisory (baseline elevation)
            if patient.has_ckd():
                payload.setdefault("advisories", []).append(
                    "Patient has CKD or other conditions that can elevate baseline troponin (e.g., pulmonary embolism) — check troponin baseline if available"
                )

            # Critical abnormal flag pass-through (site-specific tokens may vary)
            if (obx_abnormal_flag or "").strip().upper() in {"CRIT", "AA", "AAAA", "!"}:
                self.emit("lab_result_critical", payload)

            self.emit("lab_result_troponin", payload)
            if delta.get("delta_flag"):
                self.emit("lab_result_troponin_delta", payload)
            self._remember(patient.patient_id, test_code_u, float(value), ts)
            return payload

        # Generic
        self.emit("lab_result_generic", payload)
        self._remember(patient.patient_id, test_code_u, float(value), ts)
        return payload

# ==============================================================================
# Lingering Patient Monitor
# ==============================================================================

@dataclass
class LingeringAlert:
    patient_id: str
    level: str                 # "info" | "warning" | "critical"
    reason: str
    metrics: Dict[str, Any]
    suggested_action: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "patient_id": self.patient_id,
            "type": "lingering_patient",
            "level": self.level,
            "reason": self.reason,
            "metrics": self.metrics,
            "suggested_action": self.suggested_action,
            "ts_utc": str(pd.Timestamp()),
        }

class LingeringPatientMonitor:
    def __init__(self, *, thresholds: Optional[Dict[str, int]] = None):
        self.patients: Dict[str, Dict[str, Any]] = {}
        self.alert_thresholds = thresholds or {
            "assessment_overdue_min": 240,  # >4h without vitals
            "basic_needs_min":        360,  # >6h without nutrition/comfort
            "global_flag_min":        180,  # >3h since any touch
        }

    def _to_ts(self, maybe_ts) -> Optional[Any]:
        if maybe_ts is None:
            return None
        try:
            if isinstance(maybe_ts, pd.Timestamp):
                return maybe_ts
            return pd.Timestamp(maybe_ts)
        except Exception:
            return None

    def _minutes_since(self, ts: Optional[Any]) -> Optional[float]:
        if ts is None:
            return None
        try:
            delta = pd.Timestamp() - ts
        except Exception:
            return None
        try:
            total_seconds = delta.total_seconds()  # pandas Timedelta or datetime.timedelta
        except Exception:
            # Fallback for naive datetime
            import datetime as _dt
            if isinstance(delta, _dt.timedelta):
                total_seconds = delta.total_seconds()
            else:
                return None
        return max(total_seconds / 60.0, 0.0)

    def register_patient(self, patient_id: str, workflow_state) -> None:
        now = pd.Timestamp()
        self.patients[patient_id] = {
            "workflow_state": workflow_state,
            "registered_at": now,
            "last_check": now,
            "red_flags": []
        }

    def update_patient(self, patient_id: str, workflow_state) -> None:
        if patient_id not in self.patients:
            self.register_patient(patient_id, workflow_state)
            return
        self.patients[patient_id]["workflow_state"] = workflow_state
        self.patients[patient_id]["last_check"] = pd.Timestamp()

    def _extract_features(self, state) -> Dict[str, Any]:
        # Prefer an app-defined feature_dict()
        if hasattr(state, "feature_dict"):
            try:
                feat = state.feature_dict()
                return {
                    "since_vitals_min":      feat.get("since_vitals_min"),
                    "since_food_min":        feat.get("since_food_min"),
                    "since_any_touch_min":   feat.get("since_any_touch_min"),
                    "triage_acuity":         feat.get("triage_acuity"),
                    "room":                  feat.get("room"),
                }
            except Exception:
                pass
        # Fallback: derive from timestamps
        last_v = self._to_ts(getattr(state, "last_vital_ts_utc", None))
        last_f = self._to_ts(getattr(state, "last_food_ts_utc", None))
        last_m = self._to_ts(getattr(state, "last_med_ts_utc", None))
        last_touch = None
        for t in (last_v, last_f, last_m):
            if t is None:
                continue
            if last_touch is None or t > last_touch:
                last_touch = t
        return {
            "since_vitals_min":      self._minutes_since(last_v),
            "since_food_min":        self._minutes_since(last_f),
            "since_any_touch_min":   self._minutes_since(last_touch),
            "triage_acuity":         getattr(state, "triage_acuity", None),
            "room":                  getattr(state, "room", None),
        }

    def _grade(self, feat: Dict[str, Any]) -> Optional[LingeringAlert]:
        sv = feat.get("since_vitals_min")
        sf = feat.get("since_food_min")
        st = feat.get("since_any_touch_min")
        acuity = feat.get("triage_acuity")

        breaches = []
        if st is not None and st >= self.alert_thresholds["global_flag_min"]:
            breaches.append(("warning", "No contact in >=3h", st, "since_any_touch_min"))
        if sv is not None and sv >= self.alert_thresholds["assessment_overdue_min"]:
            breaches.append(("critical", "No vitals in >=4h", sv, "since_vitals_min"))
        if sf is not None and sf >= self.alert_thresholds["basic_needs_min"]:
            breaches.append(("warning", "No nutrition/comfort in >=6h", sf, "since_food_min"))

        if not breaches:
            return None

        level_rank = {"critical": 2, "warning": 1, "info": 0}
        breaches.sort(key=lambda x: (level_rank[x[0]], x[2]), reverse=True)
        top_level, reason, _value, key = breaches[0]

        suggested = "Nurse to room for reassessment and vitals now."
        if key == "since_food_min":
            suggested = "Offer nutrition/fluids; reassess comfort; document."

        metrics = {
            "since_vitals_min": sv,
            "since_food_min": sf,
            "since_any_touch_min": st,
            "triage_acuity": acuity,
        }

        # Escalate if high-acuity
        try:
            if acuity is not None and int(acuity) <= 2 and top_level != "critical":
                top_level = "critical"
                reason = reason + " (high-acuity patient)"
        except Exception:
            pass

        return LingeringAlert(
            patient_id="",
            level=top_level,
            reason=reason,
            metrics=metrics,
            suggested_action=suggested,
        )

    def check(self) -> List[Dict[str, Any]]:
        alerts: List[Dict[str, Any]] = []
        for pid, pdata in list(self.patients.items()):
            state = pdata.get("workflow_state")
            if state is None:
                continue
            feats = self._extract_features(state)
            alert = self._grade(feats)
            if alert:
                alert.patient_id = pid
                alerts.append(alert.as_dict())
        return alerts

def emit_lingering_alerts(monitor: LingeringPatientMonitor, notifier: Optional[ResultsNotifier] = None) -> List[Dict[str, Any]]:
    results = monitor.check()
    if notifier is not None:
        for a in results:
            try:
                notifier.emit("lingering_patient", a)
            except Exception:
                pass
    return results

# ==============================================================================
# Convenience: listener to attach Wells reminders on D-dimer events
# ==============================================================================

def attach_wells_reminder(notifier: ResultsNotifier):
    def _cb(evt: str, payload: Dict[str, Any]):
        if evt == "lab_result_ddimer":
            payload.setdefault("reminders", []).extend(["Compute Wells-PE", "Compute Wells-DVT"])
    notifier.on(_cb)

# Public API -------------------------------------------------------------------

__all__ = [
    "PatientContext",
    "compute_age_adjusted_ddimer_threshold",
    "interpret_ddimer",
    "compute_troponin_delta",
    "marburg_heart_score",
    "heart_score",
    "grace_points",
    "wells_pe",
    "wells_dvt",
    "sofa_score",
    "ResultsNotifier",
    "LingeringPatientMonitor",
    "LingeringAlert",
    "emit_lingering_alerts",
    "attach_wells_reminder",
]
