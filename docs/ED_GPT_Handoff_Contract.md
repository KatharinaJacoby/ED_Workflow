
# ED Workflow Assistant — Handoff for GPT
**Author:** Dr. med. Katharina Jacoby ("Katharina")  
**Date:** 30 August 2025  
**Document type:** Engineer-facing handoff & collaboration **contract** (Markdown)

---

## TL;DR
You are an LLM collaborator working under a **strict contract** to help extend an **advice-only** ED workflow assistant. Your job is to **implement small, testable changes**, ask when uncertain, and provide evidence (code + smoke checks) for every claim. Respect protected surfaces and **never** ship destructive or unverifiable edits.

**Scope:** coordination + safety tooling (timers, follow-ups, calculators, SPC monitoring, advice-only hints).  
**Non-goals:** diagnosis, autonomous clinical decisions, uncontrolled network calls, PHI handling.

---

## System Snapshot (context)
- **Architecture:** Skills/Agent Mesh under a **Safety Governor**; transparent calculators (e.g., hs-cTnT 0/1-h, qSOFA/MEWS/HEART), **SPC monitoring** (Shewhart/EWMA) for operational drift.  
- **Data (current):** **MIMIC-IV ED Demo** (public, de-identified). Synthetic generator retired due to unrealistic scenarios.  
- **Policy:** Advice-only prompts; **human approval required**. JSONL event logging for auditability.  
- **Upcoming:** Append-only integration of an **MLP classifier** for a single operational KPI label (e.g., `y_ecg_repeat_60m`).

---

## Collaboration Contract (MUST follow exactly)

### Invariants (MUST NOT CHANGE/REMOVE)
- `WorkflowState` unchanged, defined before use; exposes `.feature_dict()`, `.update_state_from_event(...)`, `.apply_event_log(...)`; timers/backlogs/alerts intact.
- `TinyCritics` uses `WorkflowState.feature_dict()`; **cold-start safe** (no transform before fit).
- `CONFIG` bootstrap with defaults; flags `RUN_UI=False`, `RUN_PIPELINE=False`. Paths exist and keep CSV/dir semantics:  
  `EQUIPMENT_STATUS_PATH`, `EQUIPMENT_MOVES_LOG_PATH`, `SOP_REGISTRY_PATH`, `QR_OUTPUT_DIR`, `EVENT_LOG_PATH`.
- Tracker core first-class (`tracker_core.TrackerService` + `tracker_ui.run_ui(...)` or inlined equivalents). **No import-time side effects**.
- SOP auto-pull present & **offline-safe**: `refresh_sop_registry(CONFIG, base_url)`; lazy imports; returns summary on failure.
- QR: **generate + scan-to-update**; manual payload fallback **must** update moves when decode libs absent.
- Overdue/alerts: equipment overdue (by `last_seen`) + **lingering patient** indicator (by `since_vitals_min`) with adjustable thresholds in UI.
- Notebook metadata includes kernelspec: `python3`.

### No-hallucinations / verification rules (MANDATORY)
- **No claims without evidence.** Do not say “implemented/wired/working” unless:
  1) you added/modified code in this notebook or wrote a file **and**  
  2) a **local smoke check** for that feature runs **now** and passes.
- **Provenance required:** If you reuse code, name the source file/notebook and the cell/module superseded.
- **State uncertainty explicitly:** If an external dependency/network is required, say so and describe fallback behavior. Don’t imply success without verification.
- **No virtual resources:** Don’t reference files/URLs/data that weren’t created now or already present. Create them or mark TODO—don’t claim they exist.
- **Exact diffs or full cells:** For any modification, provide a **line-precise diff** or the **full replacement** cell/module.
- **No silent renames/moves:** If a symbol/path changes, declare it and update all call sites in the same patch—otherwise, don’t change it.
- **Ask before destructive edits:** Never delete code/data without explicit instruction.

### Allowed changes
- New features **only behind guards**: `if RUN_PIPELINE:` (Phase-2/3) and/or `if RUN_UI:`.
- **Append** after core definitions; do **not** reorder `WorkflowState`/`TinyCritics`.
- Optional deps (`requests`, `bs4`, `Pillow`, `pyzbar`) **lazy-imported** inside guarded code.
- You may **extend** `.feature_dict()` by **adding keys** (no renames/removals).

### Forbidden changes
- No placeholders for `WorkflowState`. No renames of core classes/functions/paths.
- **No top-level execution** (no jobs at import; no undefined symbol instantiation).
- **No order fragility** (no references before definition).
- Do **not** touch PDFs/data except via tracker/SOP services.

### Delivery checklist (MUST PASS)
```python
# 1 Set:
CONFIG["RUN_UI"] = True; CONFIG["RUN_PIPELINE"] = True

# 2–6 TinyCritics cold-start
s = WorkflowState(role="nurse"); getattr(s,"touch_now",lambda *_:None)(pd.Timestamp.utcnow())
tc = TinyCritics(); p,b,u = tc.score(s,[
    {"id":"reassess_vitals","label":"Reassess vitals"},
    {"id":"order_ecg","label":"Order ECG"}
])
assert len(p)==2 and (0<=p).all() and (p<=1).all()

# 7–15 Tracker core basic IO
from pathlib import Path
from tracker_core import TrackerService, QRService, EquipmentRepository, MovesLogRepository, SOPRegistry
t = TrackerService.from_config(CONFIG)
_ = t.equipment_status(); t.log_move("pump-001","A1","B2"); assert Path(CONFIG["EQUIPMENT_MOVES_LOG_PATH"]).exists()
q = QRService(CONFIG["QR_OUTPUT_DIR"]).make("poctest"); assert isinstance(q,str) and len(q)>0
sop = SOPRegistry(CONFIG["SOP_REGISTRY_PATH"]).read(); assert sop is not None
print("SMOKE_OK")

# 16–20 Surfaces and metadata
# SOP auto-pull surface present; offline or missing libs returns a non-throwing summary.
# QR scan fallback present: manual payload (e.g., id=pump-001) updates location and appends to moves log if decode fails.
# Overdue/alerts visible in UI with adjustable thresholds (minutes).
# Notebook metadata contains: {"kernelspec":{"name":"python3","display_name":"Python 3","language":"python"}}
```

---

## Tasks for GPT (current focus)
1) **MLP classifier (append-only integration):**  
   - Choose **one** operational label (e.g., `y_ecg_repeat_60m`).  
   - Implement a guarded trainer (sklearn MLP, 64→32 ReLU, dropout 0.1; LogisticRegression baseline).  
   - 5× stratified CV → report **AUPRC/AUROC/ECE** + **FP/hour at recall τ**.  
   - Calibrate (isotonic) on held-out fold. Save artifacts: `mlp_v1.joblib`, `features.json`, `calibration.json`, `training_report.json`.
2) **MLPGate (advice-only):** read bundle under `RUN_PIPELINE`; if `yhat ≥ τ`, emit an **advice-only** suggestion + JSONL event (`"type":"ml_score"`). No automatic actions.
3) **SPC wiring:** add Shewhart/EWMA monitoring of positive rate (no auto-tuning). Trigger only a review note.
4) **Preflight notebook cell:** load bundle → score 3 rows → assert 0≤p≤1 → print KPI summary.

**Important:** Do not rename existing keys/paths. Add a new config node only:
```python
CONFIG["MLP"] = {
  "TARGET": "y_ecg_repeat_60m",
  "FEATURES_VERSION": "feat_v1",
  "BUNDLE_PATH": ".../mlp_v1.joblib",
  "THRESHOLD": 0.62,
  "CALIBRATION": "isotonic",
  "SEED": 17
}
```

---

## Ask-When-Uncertain Prompts (use verbatim)
- “I’m unsure which label to prioritize. Options I see are X/Y/Z. Which should I implement first?”  
- “Feature K requires field Z; I don’t see it in `feature_dict()`. May I add `Z_missing` and proceed?”  
- “External dependency A is unavailable; fallback B will mark TODO and print a non-throwing summary. Proceed?”  
- “Changing symbol/path Q would break invariant R. I propose an appended function `Q2(...)`. Approve?”

---

## Evidence & Outputs
- **Code:** provide exact diffs or full cells.  
- **Tests:** include smoke/asserts inline; for larger changes, add a tiny `tests/test_*.py` or a Sanity Pack cell.  
- **Artifacts:** write to new paths; never overwrite existing bundles unless explicitly instructed.  
- **Logs:** append JSONL to `EVENT_LOG_PATH` for new events (`ml_score`, `spc_flag`, etc.).

---

## Review Loop (A → B → C)
1) Implement with LLM **A** under this contract; **ask** when uncertain.  
2) Human validation: run smoke tests; adjust; answer A’s domain questions.  
3) Critical review with LLM **B** (catch overblown code, placeholders, hallucinations, brittle design).  
4) Iterate with **B** until clear; validate again.  
5) Independent pass with LLM **C**; validate again.  
6) New session: hand back updated notebook + contract to **A/B** for divergence testing; pick stronger path.

---

## Safety, Ethics, and Scope
- **Advice-only** outputs; never issue orders or auto-actions.  
- **No PHI**; stick to MIMIC-IV ED Demo for examples.  
- **SPC > Isolation Forest:** SPC selected for auditability and reduced model conflict.  
- **Bias:** do not use age/sex as features; allowed for subgroup reporting/calibration only.

---

## Definitions of Done (per patch)
- Invariants untouched; guards respected.  
- Code + smoke checks present and passing.  
- Artifacts saved with versioned filenames.  
- JSONL events emitted when relevant; no schema breakage.  
- Short note of **assumptions/uncertainties** included.

---

## Appendix: Label & Feature Stubs (to fill during work)
- **Target label (choose one):** `y_ecg_repeat_60m` | `y_trop_pair_0_1h` | `y_result_to_page_10m`  
  *Definition:* … (time window, inclusion/exclusion, leakage guard).  
- **Feature keys (append-only):** timers (`mins_since_first_trop`, `mins_since_last_ecg`, …), context flags (`is_chest_pain_route`, `has_ckd_flag`, `on_anticoagulant`), calculator outputs (`trop_curr`, `trop_delta`, `d_dimer_thr_hit`), ops snapshots (`ct_queue_len`, `icu_eta_min`), **missingness** bits.

---

_This document is the authoritative contract for GPT sessions on this project. If any requested change conflicts with the contract, GPT must stop and ask._
