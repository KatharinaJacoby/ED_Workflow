import json, pathlib

SNAPSHOT = json.loads(pathlib.Path("notebook_snapshot.json").read_text(encoding="utf-8"))

def test_catboost_declared_if_used():
    joined = "\n".join(SNAPSHOT["imports"])
    # This assertion is conditional on presence in the notebook content
    assert ("catboost" in joined) or (not "catboost" in joined and not "catboost" in "\n".join(SNAPSHOT.get("functions",[]) + SNAPSHOT.get("classes",[])))
