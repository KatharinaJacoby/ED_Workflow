
from __future__ import annotations
import importlib.util, sys, json
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

EVENT_LOG = Path("/mnt/data/ml_events.jsonl")

def _load_module_from_path(path: str):
    spec = importlib.util.spec_from_file_location("user_pipeline_mod", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["user_pipeline_mod"] = mod
    assert spec and spec.loader, "Failed to load spec"
    spec.loader.exec_module(mod)  # type: ignore
    return mod

def _detect_id_col(df):
    # Prefer meta.json if present, else try common ID names
    meta = Path("/mnt/data/meta.json")
    if meta.exists():
        try:
            js = json.loads(meta.read_text())
            for c in js.get("validated_id_cols", []):
                if c in df.columns:
                    return c
        except Exception:
            pass
    # Fallbacks
    for c in ["Fall-ID", "fall_id", "PatientID", "patient_id", "VISIT_ID", "visit_id", "ID", "id"]:
        if c in df.columns:
            return c
    # Else: first object-like column
    for c in df.columns:
        if df[c].dtype == "object":
            return c
    # Last resort
    return df.columns[0]

def _append_event(ev: Dict[str, Any]):
    EVENT_LOG.parent.mkdir(parents=True, exist_ok=True)
    EVENT_LOG.touch(exist_ok=True)
    ev = {"ts": datetime.now(timezone.utc).isoformat(), **ev}
    with EVENT_LOG.open("a") as fp:
        fp.write(json.dumps(ev, ensure_ascii=False) + "\n")

def emit_ml_events(pipeline_path: Optional[str]=None) -> Dict[str, Any]:
    """
    Execute the user's pipeline script (top-level), extract test probabilities and threshold,
    then append JSONL events per row for operational consumption.
    Returns a summary {n_events, tau, id_col}.
    """
    # Locate pipeline
    cand = pipeline_path or "/mnt/data/real_data_overlap_prevalence_isotonic(1).py"
    mp = Path(cand)
    if not mp.exists():
        # fallback to alternate name
        mp = Path("/mnt/data/real_data_overlap_prevalence_isotonic.py")
    if not mp.exists():
        raise FileNotFoundError("Pipeline script not found.")
    import os
    _cwd = os.getcwd()
    try:
        os.chdir('/mnt/data')
        mod = _load_module_from_path(str(mp))
    finally:
        os.chdir(_cwd)

    # Required globals we expect from the script
    missing = [k for k in ["test", "probs_te", "tau"] if not hasattr(mod, k)]
    if missing:
        raise RuntimeError(f"Pipeline did not expose expected globals: {missing}")
    test = getattr(mod, "test")
    probs_te = getattr(mod, "probs_te")
    tau = float(getattr(mod, "tau"))

    id_col = _detect_id_col(test)

    n = len(test)
    n_events = 0
    for i in range(n):
        pid = test.iloc[i][id_col] if id_col in test.columns else i
        prob = float(probs_te[i])
        decision = "POS" if prob >= tau else "NEG"
        ev = {
            "type": "ml_risk",
            "id_col": id_col,
            "patient_id": pid,
            "prob_cal": round(prob, 6),
            "tau": round(tau, 6),
            "decision": decision,
            "source": mp.name,
        }
        _append_event(ev)
        n_events += 1

    # Emit one summary event
    _append_event({
        "type": "ml_risk_summary",
        "tau": round(tau, 6),
        "n_rows": n,
        "id_col": id_col,
        "source": mp.name,
    })
    return {"ok": True, "n_events": n_events, "tau": tau, "id_col": id_col, "source": mp.name}
