import os
import nbformat
import pathlib
import tempfile
import json
import re

from conftest import _discover_notebook


def _write_nb(path, cells):
    nb = nbformat.v4.new_notebook()
    nb['cells'] = cells
    path.write_text(nbformat.writes(nb), encoding='utf-8')


def test_discover_with_notebook_path_env(tmp_path, monkeypatch):
    nb_path = tmp_path / "my_notebook.ipynb"
    cells = [nbformat.v4.new_code_cell("print('hi')")]
    _write_nb(nb_path, cells)

    monkeypatch.setenv("NOTEBOOK_PATH", str(nb_path))
    found = _discover_notebook()
    assert pathlib.Path(found).resolve() == nb_path.resolve()


def test_discover_prefers_preferred_name(tmp_path, monkeypatch, tmp_path_factory):
    # Create multiple notebooks and ensure preference for names matching pipeline/catboost/mlp
    nb1 = tmp_path / "random.ipynb"
    nb2 = tmp_path / "pipeline_main.ipynb"
    _write_nb(nb1, [nbformat.v4.new_code_cell("a=1")])
    _write_nb(nb2, [nbformat.v4.new_code_cell("b=2")])

    # monkeypatch cwd to tmp_path so _discover_notebook scans it
    monkeypatch.chdir(tmp_path)
    found = _discover_notebook()
    assert pathlib.Path(found).name == "pipeline_main.ipynb"
