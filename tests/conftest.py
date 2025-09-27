import os, json, re, pathlib, nbformat, pytest
DEFAULT_NOTEBOOK_PATH = os.environ.get(
    "NOTEBOOK_PATH",
    "notebooks/pipeline-ui-gate-mlp-catboost-spc.ipynb",
)
@pytest.fixture(scope="session")
def snapshot():
    nb_path = pathlib.Path(DEFAULT_NOTEBOOK_PATH)
    assert nb_path.exists(), f"Notebook not found at {nb_path}"
    nb = nbformat.read(nb_path.as_posix(), as_version=4)
    code = "\n\n".join(
        c.get("source", "") for c in nb["cells"] if c.get("cell_type") == "code"
    )
    classes = re.findall(r'^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)\b', code, re.M)
    funcs = re.findall(r'^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\b', code, re.M)
    imports = [
        l.strip()
        for l in code.splitlines()
        if re.match(r'^\s*(import\s+[A-Za-z0-9_\.]+|from\s+[A-Za-z0-9_\.]+\s+import)\b', l.strip())
    ]
    snap = {
        "kernelspec": nb.get("metadata", {}).get("kernelspec", {}),
        "n_cells": len(nb.get("cells", [])),
        "classes": classes,
        "functions": funcs,
        "imports": imports,
        "code_text_len": len(code),
        "code": code,
    }
    pathlib.Path("notebook_snapshot.json").write_text(
        json.dumps(snap, indent=2), encoding="utf-8"
    )
    return snap
