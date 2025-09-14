
import pandas as pd
import numpy as np
from carefirst.orchestrator_core import UnitCapacity, Hospital, pick_hospital_by_capacity_and_eta, DiagnosticsOrchestrator, route_service
from carefirst.pd_utils import clamp_series_or_frame, safe_assign, assert_no_na

def test_capacity_pick_prefers_free_beds_over_distance():
    h1 = Hospital("Near", 2.0, UnitCapacity("EDObs", 5, occupied=5), UnitCapacity("ICU", 5, occupied=5), {"IM": UnitCapacity("IM", 10, occupied=10)})
    h2 = Hospital("FarButFree", 10.0, UnitCapacity("EDObs", 5, occupied=0), UnitCapacity("ICU", 5, occupied=0), {"IM": UnitCapacity("IM", 10, occupied=0)})
    chosen = pick_hospital_by_capacity_and_eta([h1, h2], svc="IM", need_icu=False)
    assert chosen.name == "FarButFree"

def test_diagnostics_tick_advances_status():
    dx = DiagnosticsOrchestrator()
    o = dx.order("LABS", "STAT", eta_min=10)
    assert "ordered" in dx.status()["0:LABS"]
    dx.tick(5); assert "in_progress" in dx.status()["0:LABS"]
    dx.tick(5); assert "done" in dx.status()["0:LABS"]

def test_route_service_rules():
    assert route_service("chest pain", 0.1, {}, False) == "Cardiology"
    assert route_service("syncope", 0.4, {}, True) == "OBGYN"
    assert route_service("other", 0.9, {}, False) == "Cardiology"
    assert route_service("other", 0.1, {"creatinine": 3.0}, False) == "Nephrology"

def test_pd_clamp_replacement_and_assign():
    df = pd.DataFrame({"a": [-1, 0, 10]})
    df2 = clamp_series_or_frame(df, lower=0, upper=5)
    assert df2["a"].tolist() == [0, 0, 5]
    df = safe_assign(df, "b", [1,2,3])
    assert list(df["b"]) == [1,2,3]

def test_assert_no_na_detects_missing():
    df = pd.DataFrame({"a": [1, None, 3]})
    try:
        assert_no_na(df, ["a"])
        raise AssertionError("Should have raised")
    except ValueError as e:
        assert "NA values" in str(e)
