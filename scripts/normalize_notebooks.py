#!/usr/bin/env python3
"""Normalize all notebooks under the repository to ensure cells have 'id' fields.

This script will rewrite notebooks in-place when it makes changes.
"""
import nbformat
import pathlib
import uuid
import sys


def ensure_cell_ids(nb):
    changed = False
    for cell in nb.get("cells", []):
        # Newer nbformat uses 'id' in cell metadata; some notebooks lack it.
        if "id" not in cell:
            cell["id"] = uuid.uuid4().hex[:8]
            changed = True
    return changed


def normalize_notebook(path: pathlib.Path):
    try:
        text = path.read_text(encoding="utf-8")
        nb = nbformat.reads(text, as_version=4)
    except Exception as e:
        print(f"Skipping {path}: not a valid notebook ({e})")
        return False

    changed = False
    try:
        # If nbformat provides a normalize function, use it
        if hasattr(nbformat, "normalize"):
            norm = nbformat.normalize(nb)
            if norm != nb:
                nb = norm
                changed = True
    except Exception:
        pass

    if ensure_cell_ids(nb):
        changed = True

    if changed:
        path.write_text(nbformat.writes(nb), encoding="utf-8")
        print(f"Normalized: {path}")
    return changed


def main(root="."):
    root = pathlib.Path(root)
    any_changed = False
    for p in root.rglob("*.ipynb"):
        # skip .ipynb_checkpoints
        if ".ipynb_checkpoints" in p.as_posix():
            continue
        if normalize_notebook(p):
            any_changed = True

    if any_changed:
        print("Normalization complete: some notebooks updated.")
        return 0
    print("Normalization complete: no changes needed.")
    return 0


if __name__ == "__main__":
    sys.exit(main("."))
