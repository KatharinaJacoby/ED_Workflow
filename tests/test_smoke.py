def test_notebook_loads_and_has_code(snapshot):
    assert snapshot["n_cells"] > 0
    assert snapshot["code_text_len"] > 0

def test_has_imports(snapshot):
    assert isinstance(snapshot["imports"], list)
    assert len(snapshot["imports"]) >= 1
