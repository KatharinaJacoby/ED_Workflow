
import math
import pytest
from hsctnt_roche_sex_adj import classify_hsctnt_0_1h, hsctnt_99th_url, TroponinValueError

def test_urls_by_sex():
    assert hsctnt_99th_url("female") == 9.0
    assert hsctnt_99th_url("male") == 16.8
    # non-binary and unknown => lower threshold for safety
    assert hsctnt_99th_url("non-binary") == 9.0
    assert hsctnt_99th_url("unknown") == 9.0

def test_single_draw_rule_out_requires_onset_ge_3h():
    # <5 ng/L only counts if onset >3h
    label, ctx = classify_hsctnt_0_1h(4.9, None, sex="female", onset_ge_3h=False)
    assert label == "observe" and ctx["trigger"] == "needs_1h"
    label, ctx = classify_hsctnt_0_1h(4.9, None, sex="female", onset_ge_3h=True)
    assert label == "rule_out" and ctx["trigger"].startswith("single_0h_valid")

def test_rule_in_abs_and_delta():
    # absolute
    label, ctx = classify_hsctnt_0_1h(52.0, 52.0, sex="male")
    assert label == "rule_in" and ctx["trigger"] == "abs_0h"
    # delta
    label, ctx = classify_hsctnt_0_1h(10.0, 15.0, sex="male")
    assert label == "rule_in" and ctx["trigger"] == "delta_1h"

def test_rule_out_band_plus_delta():
    label, ctx = classify_hsctnt_0_1h(11.9, 13.5, sex="female")  # delta 1.6 < 3.0 and t0 < 12
    assert label == "rule_out" and ctx["trigger"] == "band+delta"

def test_observe_zone_mid_values():
    label, ctx = classify_hsctnt_0_1h(20.0, 21.0, sex="non-binary")
    assert label == "observe" and ctx["trigger"] == "observe_zone"

def test_input_validation():
    with pytest.raises(TroponinValueError):
        classify_hsctnt_0_1h(-1.0, 0.0)
    with pytest.raises(TroponinValueError):
        classify_hsctnt_0_1h(math.nan, 0.0)
