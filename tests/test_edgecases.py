import math
from pytoon import toon as toon_mod


def test_special_floats():
    obj = {"a": float("nan"), "b": float("inf"), "c": -float("inf")}
    s = toon_mod.dumps(obj)
    parsed = toon_mod.loads(s)
    assert math.isinf(parsed["b"]) and parsed["b"] > 0
    assert math.isinf(parsed["c"]) and parsed["c"] < 0
    assert math.isnan(parsed["a"])


def test_null_byte_and_control_chars():
    obj = {"x": "null\x00byte", "y": "line1\nline2", "z": "\tindented"}
    s = toon_mod.dumps(obj)
    parsed = toon_mod.loads(s)
    assert parsed["x"] == obj["x"]
    assert parsed["y"] == obj["y"]
    assert parsed["z"] == obj["z"]


def test_deeply_nested():
    depth = 60
    cur = {}
    root = cur
    for i in range(depth):
        new = {f"lvl{i}": {}}
        cur.update(new)
        cur = new[f"lvl{i}"]
    s = toon_mod.dumps(root)
    parsed = toon_mod.loads(s)
    assert isinstance(parsed, dict)
