
# tests/test_core.py
import os, json, math
from carefirst.core_services_sop_registry import SOPRegistry
from troponin_rules import roche_hstnt_delta

def test_roche_rule_core():
    assert roche_hstnt_delta(20,25).significant is True
    assert roche_hstnt_delta(20,22).significant is False
    assert roche_hstnt_delta(60,84).significant is False
    assert roche_hstnt_delta(60,90).significant is True
    assert roche_hstnt_delta(10,18).applied_rule == "<14:N/A>"

def test_sop_registry_demo_seed(tmp_path):
    path = tmp_path / "sop_registry.json"
    reg = SOPRegistry(str(path))
    n = reg.refresh_offline_demo()
    assert n >= 3
    assert reg.items[0].source.startswith("SOP-Notaufnahme")
    reg2 = SOPRegistry(str(path))
    assert reg2.load() == n

def test_audit_like_flags(tmp_path):
    # Simulate the audit checks you run in the notebook
    path = tmp_path / "sop_registry.json"
    reg = SOPRegistry(str(path))
    reg.refresh_offline_demo()
    ok_registry = os.path.exists(path)
    assert ok_registry
