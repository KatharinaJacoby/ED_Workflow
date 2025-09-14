
"""
operational_icu_bridge
- Aggregates unit-level ICU capacity into global ICU features.
- Provides an overlay wrapper so we can pass ICU fields to the existing builder
  without modifying WorkflowState or the gate engine.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import json

ICU_JSON_PATH_DEFAULT = "/mnt/data/icu_status.json"

def rollup_icu_units(units: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate ICU unit-level data into totals/ratios + simple ETAs."""
    if not units:
        return {
            "icu_capacity_total": 0,
            "icu_occupied_beds": 0,
            "icu_free_beds": 0,
            "icu_occupancy": 0.0,
            "icu_free_ratio": 0.0,
            "icu_units_total": 0,
            "icu_units_full": 0,
            "icu_next_bed_eta_min": None,
        }
    cap = 0
    occ = 0
    free_list = []
    eta_candidates = []
    full_count = 0
    for u in units:
        c = int(u.get("capacity", 0) or 0)
        o = int(u.get("occupied", 0) or 0)
        cap += c
        occ += o
        free = max(0, c - o)
        free_list.append(free)
        if o >= c:
            # next-bed ETA given only when full; may be missing
            etas = u.get("discharge_eta_minutes") or []
            etas = [int(x) for x in etas if str(x).strip().isdigit()]
            if etas:
                eta_candidates.append(min(etas))
            full_count += 1

    free_total = sum(free_list)
    free_ratio = float(free_total) / float(cap) if cap else 0.0
    occ_ratio = float(occ) / float(cap) if cap else 0.0
    eta_min = (min(eta_candidates) if eta_candidates else (0 if free_total > 0 else None))

    return {
        "icu_capacity_total": int(cap),
        "icu_occupied_beds": int(occ),
        "icu_free_beds": int(free_total),
        "icu_occupancy": float(occ_ratio),
        "icu_free_ratio": float(free_ratio),
        "icu_units_total": int(len(units)),
        "icu_units_full": int(full_count),
        "icu_next_bed_eta_min": eta_min,
    }

def load_icu_units_from_json(path: str = ICU_JSON_PATH_DEFAULT) -> Optional[List[Dict[str, Any]]]:
    """Load ICU units from the persisted status JSON written by your UI code."""
    p = Path(path)
    if not p.exists():
        return None
    try:
        js = json.loads(p.read_text())
        units = js.get("units")
        if isinstance(units, list):
            return units
    except Exception:
        pass
    return None

class _WSOverlay:
    """Tiny wrapper to inject overlay fields into WorkflowState.feature_dict() results."""
    def __init__(self, ws: Any, overlay: Dict[str, Any]):
        self._ws = ws
        self._overlay = dict(overlay)

    def feature_dict(self) -> Dict[str, Any]:
        base = dict(self._ws.feature_dict())
        base.update(self._overlay)
        return base

def extended_feature_dict_with_icu(ws: Any, builder_module, *, baselines=None, history=None, context=None, icu_units=None, icu_json_path: str = ICU_JSON_PATH_DEFAULT, now=None) -> Dict[str, Any]:
    """
    Build extended features while overlaying ICU rollup fields.
    - builder_module must expose build_operational_features() or extended_feature_dict()
    - icu_units: optional already-loaded units; if None, tries to load from icu_json_path
    """
    units = icu_units
    if units is None:
        units = load_icu_units_from_json(icu_json_path) or []
    icu_roll = rollup_icu_units(units)
    # Prefer builder_module.extended_feature_dict if present; otherwise call builder then merge
    if hasattr(builder_module, "extended_feature_dict"):
        overlay_ws = _WSOverlay(ws, icu_roll)
        return builder_module.extended_feature_dict(overlay_ws, baselines=baselines, history=history, context=context, now=now)
    else:
        # Build only add-on features and append to ws dict
        feats = builder_module.build_operational_features(ws, baselines=baselines, history=history, context=context, now=now)
        base = dict(ws.feature_dict()); base.update(icu_roll); base.update(feats)
        return base
