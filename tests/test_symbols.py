import json, pathlib

SNAPSHOT = json.loads(pathlib.Path("/mnt/data/repo_v2/notebook_snapshot.json").read_text(encoding="utf-8"))

def test_key_classes_present():
    required = ['EquipmentRepository', 'MovesLogRepository', 'SPCProcessControl', 'EquipmentRecord', 'TrackerService', '_SimpleTracker', 'BaselineStats', 'WorkflowState', 'SOPRegistry', 'TinyCritics']
    missing = [c for c in required if c not in SNAPSHOT["classes"]]
    assert not missing, f"Missing classes: {missing}"

def test_key_functions_present():
    required = ['calculate_operational_stress', '_best_relevant_icu_capacity', '_update_all_context_widgets', 'run_ui_actions_and_critic', 'run_ui_movement_analytics', 'equipment_moves_log_path', '_derive_state_from_data', 'calculate_control_score']
    missing = [f for f in required if f not in SNAPSHOT["functions"]]
    assert not missing, f"Missing functions: {missing}"
