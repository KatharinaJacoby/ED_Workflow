import pytest

def test_kernelspec_is_python3(snapshot):
    ks = snapshot.get("kernelspec", {})
    if ks:
        assert ks.get("name") == "python3"

def test_notebook_has_code(snapshot):
    assert snapshot["n_cells"] > 0
    assert snapshot["code_text_len"] > 0

def test_has_some_imports(snapshot):
    assert len(snapshot["imports"]) >= 1
