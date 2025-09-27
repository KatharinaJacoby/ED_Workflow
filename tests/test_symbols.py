import pytest

def test_has_functions(snapshot):
    assert len(snapshot["functions"]) >= 1

def test_has_or_skips_classes(snapshot):
    # Some notebooks are function-only; don't fail if no classes exist.
    if not snapshot["classes"]:
        pytest.skip("No classes declared in this notebook")
