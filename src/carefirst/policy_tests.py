
from __future__ import annotations
from typing import List, Dict, Any

def detect_duplicate_orders(actions: List[Dict[str,Any]]) -> int:
    seen = set(); dup = 0
    for a in actions:
        key = (a.get("type"), a.get("modality") or a.get("op"), str(a.get("params",{})))
        if key in seen: dup += 1
        else: seen.add(key)
    return dup

def detect_contradictions(actions: List[Dict[str,Any]]) -> int:
    has_ct = any(a.get("type") == "ORDER" and a.get("modality") == "CT" for a in actions)
    has_noop = any(a.get("type") == "INFO" and a.get("code") == "NO_OP" for a in actions)
    return int(has_ct and has_noop)

def stale_capacity_violation(actions: List[Dict[str,Any]], cap_stale: bool) -> int:
    if not cap_stale: return 0
    return sum(1 for a in actions if (a.get("type") == "ORDER" and a.get("modality") == "CT") or (a.get("type")=="BED_OP" and a.get("op")=="REQUEST_BED"))
