import os, json, re, pathlib, nbformat, pytest

def _discover_notebook():
    # 1) Respect NOTEBOOK_PATH if provided
    nb_env = os.environ.get("NOTEBOOK_PATH", "").strip()
    if nb_env:
        p = pathlib.Path(nb_env)
        assert p.exists(), f"Notebook not found at NOTEBOOK_PATH={p}"
        return p

    # 2) Otherwise find .ipynb files in the repo (skip checkpoints)
    cands = [
        p for p in pathlib.Path(".").rglob("*.ipynb")
        if ".ipynb_checkpoints" not in p.as_posix()
    ]
    assert cands, "No .ipynb files found. Set NOTEBOOK_PATH or add a notebook."

    # 3) If exactly one notebook, use it
    if len(cands) == 1:
        return cands[0]

    # 4) Prefer names likely to be your main pipeline notebook
    preferred = [p for p in cands if re.search(r"(pipeline|catboost|mlp)", p.name, re.I)]
    if len(preferred) == 1:
        return preferred[0]

    # 5) Otherwise pick the one with the most code cells; if tie, require NOTEBOOK_PATH
    def code_cells_count(path):
        nb = nbformat.read(path.as_posix(), as_version=4)
        return sum(1 for c in nb["cells"] if c.get("cell_type") == "code")

    cands.sort(key=code_cells_count, reverse=True)
    top = cands[0]
    top_count = code_cells_count(top)
    ties = [p for p in cands if code_cells_count(p) == top_count]
    if len(ties) > 1:
        raise AssertionError(
            "Multiple notebooks found with the same number of code cells:\n"
            + "\n".join(f"- {p}" for p in ties)
            + "\nSet NOTEBOOK_PATH to the one you want."
        )
    return top

@pytest.fixture(scope="session")
def snapshot():
    nb_path = _discover_notebook()
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
        "nb_path": nb_path.as_posix(),
    }
    # Optional: write a snapshot file for debugging (tests don’t rely on it)
    pathlib.Path("notebook_snapshot.json").write_text(
        json.dumps(snap, indent=2), encoding="utf-8"
    )
    return snap
