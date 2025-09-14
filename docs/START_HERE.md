# ED Ops Pipeline — v6 (Stable PoC)

**Generated:** 2025-08-17T12:38:11.790937 UTC

This is the stable, runnable Proof‑of‑Concept with the tracker in the **core architecture**.
It keeps your real `WorkflowState`, patched `TinyCritics` (using `feature_dict()`), and adds
first‑class tracker core + a guarded UI. Phase‑2/3 hooks are present but inert by default.

## Files

- `ED_Pipeline_v6.ipynb` — start here.
- `tracker_core.py` — repositories (equipment, moves, SOP), QR service, `TrackerService`.
- `tracker_ui.py` — Streamlit tracker UI that drives the core.
- `phase2_bridge.py` — optional ICU/agent‑mesh/trainer hooks (only active with `RUN_PIPELINE=True`).

## Quick start

1. Open `ED_Pipeline_v6.ipynb` and run all cells.
2. To launch the UI (Streamlit inside the notebook env), set:
   ```python
   CONFIG["RUN_UI"] = True
   ```
3. To enable Phase‑2/3 hooks (only if/imports exist), set:
   ```python
   CONFIG["RUN_PIPELINE"] = True
   ```
4. QR output will be written to `CONFIG["QR_OUTPUT_DIR"]`.
5. Equipment status/moves live at:
   - `CONFIG["EQUIPMENT_STATUS_PATH"]`
   - `CONFIG["EQUIPMENT_MOVES_LOG_PATH"]`
6. SOP registry CSV at `CONFIG["SOP_REGISTRY_PATH"]` (empty is fine).

## Sanity checklist (what passes now)

- `WorkflowState` defined before use, annotation‑safe.
- `TinyCritics` uses `feature_dict()`; cold‑start returns neutral scores safely.
- Tracker core wired: equipment table read/write, moves logging, SOP read, QR generation.
- UI launches behind `RUN_UI`; no side‑effects at import.
- Phase‑2/3 bridge present; inert unless `RUN_PIPELINE=True` **and** modules exist.

## Notes

- The v6 notebook was executed end‑to‑end here with `RUN_UI=False`, `RUN_PIPELINE=False`.
- If you later promote ICU/mesh/trainer code into modules (e.g., `icu_constraints.py`),
  the v6 bridge will use them automatically when `RUN_PIPELINE=True`.
