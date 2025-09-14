
from __future__ import annotations
from typing import List, Dict, Any
import numpy as np

def apply_policy(pred_idx: np.ndarray,
                 probs: np.ndarray,
                 context: Dict[str,Any],
                 actions: List[Dict[str,Any]]) -> List[Dict[str,Any]]:
    out = []
    for i, a_idx in enumerate(pred_idx.tolist()):
        spec = actions[a_idx]
        msg = {"action_code": spec["code"], "params": spec.get("params", {}), "proba": float(probs[i, a_idx])}
        if spec["code"] == "ORDER_CT":
            approved = context.get("approval", {}).get("ORDER_CT", False)
            if not approved or context.get("cap_stale", False):
                msg["requires_approval"] = True
                msg["blocked_reason"] = "CT needs approval and fresh capacity"
        if spec["code"] == "REQUEST_BED" and context.get("cap_stale", False):
            msg["action_code"] = "VERIFY_CAPACITY"
            msg["note"] = "Capacity stale -> repoll before bed request"
        unc = context.get("uncertainty", None)
        if unc is not None:
            msg["needs_check"] = bool(unc[i] > np.quantile(unc, 0.75))
        out.append(msg)
    return out
