import pytest

def test_catboost_import_consistency(snapshot):
    # If the notebook uses 'catboost' anywhere, assert it is imported.
    uses = "catboost" in snapshot["code"]
    declared = any("catboost" in imp for imp in snapshot["imports"])
    if uses:
        assert declared, "Notebook uses catboost but no import was found"
    else:
        pytest.skip("Notebook does not use catboost")
