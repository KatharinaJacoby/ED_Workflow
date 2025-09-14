# ED Pipeline: Advice‑only UI Gate (MLP/CatBoost) + SPC Monitoring

> **Tagline:** *Clinician‑engineer: FastAPI, SQLite, scikit‑learn; advice‑only orchestration for ED workflows.*

---

## Why
A small, auditable pipeline that surfaces **non‑binding suggestions** to ED staff. No autonomous actions. Built for transparency, reproducibility, and easy rollback.

## Highlights
- **Advice‑only UI gate** with calibrated probability threshold (τ) set by **recall floor + FP/hour budget**.
- **Models:** MLP (64→32, ReLU, dropout 0.1) and **CatBoost** as a strong tabular baseline.
- **Status:** Labels for the target KPI are being finalized → **MLP/CatBoost heads are wired but not trained on final labels yet**.
- **Evaluation (once labels land):** 5× CV; metrics: **AUPRC/AUROC/ECE**, confusion at operating point; **isotonic calibration**.
- **Monitoring:** **SPC** (Shewhart for proposal rate; **EWMA** for fatigue/acceptance drift). Alerts are review prompts, not actions.
- **Local‑first & auditable:** Runs on local machine; **JSONL audit logs**; artifacts saved (bundle, features, calibration, report).
- **Separation of concerns:** Staff/patient **LLM assistant** is a **separate service** to keep this prediction pipeline clean.

## Architecture (simplified)
```
[Data source (public demo)] → [Feature builder] → [Model head: MLP | CatBoost]
         ↓                                        |
     JSONL logs  ←  [Calibration + Threshold τ] ←  |
         ↓                                        ↓
    [SPC monitors: Shewhart/EWMA] ——→ [UI Gate (advice‑only)] ——→ User
```

## Quickstart
```bash
# 1) create env
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2) run preflight / smoke tests
python scripts/preflight.py  # checks data path, config, seeds

# 3) run the UI gate (dry‑run until labels are ready)
python app.py --run-ui --dry-run  # emits audit logs + SPC charts

# 4) train once labels.csv is available
python pipeline/train.py --labels data/labels.csv --config configs/pipeline.yml
python pipeline/eval.py   --bundle artifacts/run_YYYYMMDDHHMM
```

## Config snippet (`configs/pipeline.yml`)
```yaml
seed: 1
features: [age, sex, triage_acuity, vitals_last, meds_flags, dx_flags]
thresholds:
  tau: 0.42          # operating point
  recall_floor: 0.85 # used to select tau during CV
  fp_per_hour: 0.8   # budget for UI proposals
model:
  head: catboost     # or mlp
  mlp: {hidden: [64, 32], dropout: 0.1, lr: 1e-3, epochs: 40}
  catboost: {depth: 6, learning_rate: 0.05, iterations: 500, class_weights: auto}
calibration: isotonic
spc:
  shewhart: {window: 200, k: 3}
  ewma:     {alpha: 0.2, l: 2.7}
logging:
  jsonl_path: logs/events.jsonl
  artifacts_dir: artifacts/
flags:
  RUN_UI: true
  RUN_PIPELINE: false
```

## A/B protocol (once labels land)
1) Fix seeds/deps; freeze feature set.  
2) 5× CV to select τ under **recall_floor + FP/hour**.  
3) Compare **CatBoost vs MLP** at the selected τ on a held‑out fold.  
4) Save: metrics.json, calibration curves, confusion tables, SPC baselines.  
5) Roll forward the winner behind the **UI gate** only.

## Monitoring & Ops
- SPC baselines recomputed monthly; drift triggers review PRs.  
- Audit logs are append‑only JSONL; include inputs, version, τ, scores, UI outcome.  
- Preflight blocks start if config/schema mismatch.

## Data & Privacy
- Uses **public, de‑identified demo data** for development; no PHI leaves the machine.  
- For real deployments, wire hospital sources in a separate, private repo/environment.

## Repo layout (suggested)
```
notebooks/  # pipeline-activated-ui-gate-mlp-spc.ipynb, ed-pipeline-demo-ui-patched.ipynb
pipeline/   # train.py, eval.py, calibrate.py, features.py
app/        # app.py, routers/ui_gate.py
monitoring/ # spc.py, charts/
configs/    # pipeline.yml, thresholds.yml
scripts/    # preflight.py, smoke_test.py
artifacts/  # saved bundles
logs/       # JSONL audit logs
```

## Status
- Labels: in progress  
- Gate: active in dry‑run  
- SPC: wired  
- Next: label finalization → CV+calibration → **A/B MLP vs CatBoost**

## License & Citation
Choose a permissive license (e.g., MIT/Apache‑2.0).  
If you use this work, please cite: *Jacoby K. "ED Pipeline: Advice‑only UI Gate with SPC" (2025).*

