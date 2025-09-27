import re, pytest

def test_imports_well_formed(snapshot):
    # Every recorded import line should be a valid 'import X' or 'from X import Y'
    assert isinstance(snapshot["imports"], list)
    for line in snapshot["imports"]:
        assert re.match(r'^(import\s+[A-Za-z0-9_.]+|from\s+[A-Za-z0-9_.]+\s+import\b)', line), f"Bad import line: {line}"

def test_used_common_libs_are_declared(snapshot):
    # Only require an import if the token is actually used in code
    common = ["numpy", "pandas", "sklearn", "matplotlib", "joblib", "streamlit"]
    joined = "\n".join(snapshot["imports"])
    for token in common:
        if token in snapshot["code"]:
            assert token in joined, f"Notebook uses {token} but no import was found"
