
import pytest
from carefirst.flow_troponin_fixed import classify_troponin_0_1h, DEFAULT_ASSAY, TroponinValueError

def test_single_draw_rule_out():
    label, ctx = classify_troponin_0_1h(DEFAULT_ASSAY, 1.9, None)
    assert label == "rule_out"
    assert ctx["trigger"] == "single_0h"
    assert ctx["t1"] is None

def test_single_draw_observe_band():
    label, ctx = classify_troponin_0_1h(DEFAULT_ASSAY, 4.9, None)
    assert label == "observe"
    assert ctx["trigger"] == "needs_1h"

def test_single_draw_rule_in_abs():
    label, ctx = classify_troponin_0_1h(DEFAULT_ASSAY, 64.0, None)
    assert label == "rule_in"
    assert ctx["trigger"] == "abs_0h"

def test_delta_rule_in():
    label, ctx = classify_troponin_0_1h(DEFAULT_ASSAY, 10.0, 17.0)
    assert label == "rule_in"
    assert ctx["trigger"] == "delta_1h"

def test_band_plus_delta_rule_out():
    label, ctx = classify_troponin_0_1h(DEFAULT_ASSAY, 4.9, 6.5)  # delta 1.6 < 2.0
    assert label == "rule_out"
    assert ctx["trigger"] == "band+delta"

def test_observe_zone():
    label, ctx = classify_troponin_0_1h(DEFAULT_ASSAY, 10.0, 11.0)  # delta 1.0 < 2.0; but t0 >= band_upper
    assert label == "observe"
    assert ctx["trigger"] == "observe_zone"

def test_reject_negative():
    with pytest.raises(TroponinValueError):
        classify_troponin_0_1h(DEFAULT_ASSAY, -1.0, 0.0)

def test_reject_nan():
    import math
    with pytest.raises(TroponinValueError):
        classify_troponin_0_1h(DEFAULT_ASSAY, math.nan, 0.0)

def test_unknown_assay():
    import pytest
    with pytest.raises(KeyError):
        classify_troponin_0_1h("Nope", 0.0, 0.0)
