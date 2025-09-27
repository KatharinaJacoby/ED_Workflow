import json, pathlib, re
CODE = "\n\n".join(c.get("source","") for c in json.loads(pathlib.Path("/mnt/data/pipeline-ui-gate-mlp-catboost-spc.ipynb").read_text(encoding="utf-8")).get("cells",[]) if c.get("cell_type")=="code")

def test_schema_equipmentrepository():
    m = re.search(r"class\s+EquipmentRepository\b.*?:\n(.*?)(?=\nclass\s|\Z)", CODE, flags=re.S)
    assert m, "Class block for EquipmentRepository not found"
    cols = []
    for m2 in re.finditer(r'pd\.DataFrame\(\s*columns\s*=\s*\[([^\]]+)\]\s*\)', m.group(1)):
        raw = m2.group(1)
        cols += [x.strip().strip("\"'") for x in raw.split(",")]
    assert cols, "No explicit pd.DataFrame(columns=[...]) found in EquipmentRepository"
    assert "equip_id" in cols and "name" in cols and "location" in cols, "Expected subset of columns in EquipmentRepository not found"


def test_schema_moveslogrepository():
    m = re.search(r"class\s+MovesLogRepository\b.*?:\n(.*?)(?=\nclass\s|\Z)", CODE, flags=re.S)
    assert m, "Class block for MovesLogRepository not found"
    cols = []
    for m2 in re.finditer(r'pd\.DataFrame\(\s*columns\s*=\s*\[([^\]]+)\]\s*\)', m.group(1)):
        raw = m2.group(1)
        cols += [x.strip().strip("\"'") for x in raw.split(",")]
    assert cols, "No explicit pd.DataFrame(columns=[...]) found in MovesLogRepository"
    assert "equip_id" in cols and "from" in cols and "to" in cols, "Expected subset of columns in MovesLogRepository not found"


def test_schema_sopregistry():
    m = re.search(r"class\s+SOPRegistry\b.*?:\n(.*?)(?=\nclass\s|\Z)", CODE, flags=re.S)
    assert m, "Class block for SOPRegistry not found"
    cols = []
    for m2 in re.finditer(r'pd\.DataFrame\(\s*columns\s*=\s*\[([^\]]+)\]\s*\)', m.group(1)):
        raw = m2.group(1)
        cols += [x.strip().strip("\"'") for x in raw.split(",")]
    assert cols, "No explicit pd.DataFrame(columns=[...]) found in SOPRegistry"
    assert "sop_id" in cols and "title" in cols and "pdf_path" in cols, "Expected subset of columns in SOPRegistry not found"


def test_schema_equipmentrepository():
    m = re.search(r"class\s+EquipmentRepository\b.*?:\n(.*?)(?=\nclass\s|\Z)", CODE, flags=re.S)
    assert m, "Class block for EquipmentRepository not found"
    cols = []
    for m2 in re.finditer(r'pd\.DataFrame\(\s*columns\s*=\s*\[([^\]]+)\]\s*\)', m.group(1)):
        raw = m2.group(1)
        cols += [x.strip().strip("\"'") for x in raw.split(",")]
    assert cols, "No explicit pd.DataFrame(columns=[...]) found in EquipmentRepository"
    assert "equip_id" in cols and "name" in cols and "location" in cols, "Expected subset of columns in EquipmentRepository not found"
