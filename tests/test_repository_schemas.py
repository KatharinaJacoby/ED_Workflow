import re, pytest

def test_detect_explicit_dataframe_schemas_if_any(snapshot):
    # Look for explicit pd.DataFrame(columns=[...]) patterns; if none, skip.
    code = snapshot["code"]
    matches = list(re.finditer(r'pd\.DataFrame\(\s*columns\s*=\s*\[([^\]]+)\]\s*\)', code))
    if not matches:
        pytest.skip("No explicit DataFrame schema blocks found")
    # If found, ensure at least one non-empty column name exists in each hit
    for m in matches:
        raw = m.group(1)
        cols = [x.strip().strip("\"'") for x in raw.split(",") if x.strip().strip("\"'")]
        assert cols, "Found an empty DataFrame(columns=[...]) declaration"
