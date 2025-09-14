# Pure-Python sanity test for the guard, no external packages.
from app.model_client import guard_no_fake_labs

def _run():
    assert guard_no_fake_labs("Bitte CRP nennen.", None) is True  # no numeric value -> OK
    assert guard_no_fake_labs("CRP: 42", None) is False           # numeric without tool -> NOT OK
    assert guard_no_fake_labs("CRP: 12.3", "lab json ... 12.3 ...") is True  # numeric present in tool -> OK
    assert guard_no_fake_labs("Alles gut.", None) is True

if __name__ == "__main__":
    _run()
    print("sanity_ok")
