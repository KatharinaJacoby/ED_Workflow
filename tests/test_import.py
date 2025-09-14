def test_import():
    import sys
    sys.path.append("src")
    import carefirst
    assert carefirst is not None
