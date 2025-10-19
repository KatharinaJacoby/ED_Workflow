# Notebook normalization

This repository includes a small helper script to normalize Jupyter notebooks and ensure each cell has an `id` field. This helps avoid warnings from `nbformat` and future hard errors when validating notebooks.

Files
- `scripts/normalize_notebooks.py` — scans the repository for `.ipynb` files (skips `.ipynb_checkpoints`) and rewrites notebooks in-place when it adds missing cell ids.

Why normalize
- Newer nbformat versions expect a stable `id` field on each cell. Some older or hand-edited notebooks lack this field and cause `MissingIDFieldWarning` during validation.

How to run

From the repository root run:

```bash
python3 scripts/normalize_notebooks.py
```

This will print which notebooks were updated. If you want to target a subfolder, pass the path as the first argument:

```bash
python3 scripts/normalize_notebooks.py notebooks/
```

After normalizing, re-run the test suite:

```bash
pytest -q
```

Notes
- The script writes files in-place — consider committing changes on a feature branch and reviewing them before merging.
- The normalization performed is conservative: it adds short UUIDs to any cell missing an `id` and ensures `metadata` exists.
