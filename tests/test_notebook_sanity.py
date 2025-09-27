import json, pathlib, re

SNAPSHOT = json.loads(pathlib.Path("/mnt/data/repo_v2/notebook_snapshot.json").read_text(encoding="utf-8"))

def test_kernelspec_is_python3():
    ks = SNAPSHOT.get("kernelspec", {})
    assert ks.get("name") == "python3"
    assert "Python" in ks.get("display_name", "") or ks.get("display_name") == "Python 3"

def test_notebook_has_code_cells():
    assert SNAPSHOT["n_cells"] > 0
    assert SNAPSHOT["code_text_len"] > 0

def test_declares_core_imports_present_in_this_notebook():
    joined = "\n".join(SNAPSHOT["imports"])
    # Assert the imports actually present, observed from the notebook
    for token in ['IPython', 'PIL', '__future__', 'catboost', 'collections', 'csv,', 'dataclasses', 'datetime', 'duckdb,', 'hashlib', 'importlib', 'importlib,', 'inspect', 'inspect,', 'ipywidgets', 'joblib', 'json', 'json,', 'math', 'matplotlib', 'numpy', 'os', 'os,', 'pandas', 'pathlib', 'pdf2image', 'pyzbar', 'qrcode', 'random,', 're', 're,', 're;', 'requests;', 'scipy', 'sklearn', 'streamlit', 'sys,', 'time;', 'types', 'typing', 'warnings']:
        assert token in joined
