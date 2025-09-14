# Tests & Tooling (non-intrusive)
Place `tests/` and `pyproject.toml` at the repository root (same folder as your notebook).
They are safe: tests skip unless `tracker_core` / `refresh_sop_registry` are importable.

Run locally (optional):
    pip install pytest ruff mypy
    pytest -q
    ruff check .
    mypy .

Future packaging:
- ed_tracker.tracker_core: TrackerService, EquipmentRepository, MovesLogRepository, QRService, SOPRegistry
- ed_tracker.sop: refresh_sop_registry
