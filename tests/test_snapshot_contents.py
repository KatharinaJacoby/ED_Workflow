import nbformat
import pathlib
import json

def test_snapshot_has_expected_keys(snapshot):
    keys = {"kernelspec", "n_cells", "classes", "functions", "imports", "code_text_len", "code", "nb_path"}
    assert keys.issubset(set(snapshot.keys()))


def test_snapshot_n_cells_matches_code_cells(snapshot):
    # n_cells should be the total cells count in the notebook
    nb = nbformat.read(snapshot["nb_path"], as_version=4)
    assert snapshot["n_cells"] == len(nb.get("cells", []))


def test_snapshot_imports_are_list(snapshot):
    assert isinstance(snapshot["imports"], list)
    for imp in snapshot["imports"]:
        assert isinstance(imp, str)


def test_code_text_len_matches_length(snapshot):
    assert snapshot["code_text_len"] == len(snapshot["code"])
