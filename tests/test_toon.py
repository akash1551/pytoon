# test_toon.py
import pytest
from collections import namedtuple
from dataclasses import dataclass, is_dataclass
import inspect

# Import your toon module
from pytoon import toon as toon_mod


# -----------------------------
# Helper normalization for comparisons
# -----------------------------
def _is_namedtuple_instance(x):
    return isinstance(x, tuple) and hasattr(x, "_fields")


def normalize(obj):
    """
    Convert Python object into a canonical comparable form.
    Ensures round-trip comparison works for dataclasses, namedtuples, sets, tuples, custom objects.
    """
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj

    # dataclass → dict
    try:
        from dataclasses import asdict
        if is_dataclass(obj):
            return normalize(asdict(obj))
    except Exception:
        pass

    # namedtuple → dict
    if _is_namedtuple_instance(obj):
        return normalize(obj._asdict())

    # dict
    if isinstance(obj, dict):
        return {k: normalize(v) for k, v in obj.items()}

    # list or tuple
    if isinstance(obj, (list, tuple)):
        return [normalize(v) for v in obj]

    # set → sorted list
    if isinstance(obj, set):
        try:
            return sorted(normalize(v) for v in obj)
        except Exception:
            return sorted(str(normalize(v)) for v in obj)

    # custom object → public attributes dict
    if hasattr(obj, "__dict__"):
        public = {k: v for k, v in vars(obj).items()
                  if not k.startswith("_") and not inspect.isroutine(v)}
        return normalize(public)

    # fallback
    return str(obj)


# -----------------------------
# Fixtures
# -----------------------------
Item = namedtuple("Item", ["id", "label"])
i1 = Item(1, "A")
i2 = Item(2, "B")


@dataclass
class Book:
    title: str
    pages: int
    tags: list


class Device:
    def __init__(self, model, version, status):
        self.model = model
        self.version = version
        self.status = status
        self._internal = "hidden"


# Test objects
PYTHON_OBJECTS = [

    # 1. Primitives
    ({"a": 1, "b": 2.2, "c": True, "d": None, "e": "hello"}, "primitives"),

    # 2. Strings needing quoting
    ({"s1": "hello,world", "s2": "line\nbreak", "s3": "  padded", "s4": "null"}, "quoted_strings"),

    # 3. Nested object
    ({
        "user": {
            "id": 123,
            "config": {"x": 10, "y": 20, "z": {"enabled": True}}
        },
        "roles": ["a", "b", "c"]
    }, "nested"),

    # 4. Uniform table
    ({
        "items": [
            {"a": 1, "b": 2},
            {"a": 3, "b": 4},
        ]
    }, "uniform_table"),

    # 5. Non-uniform list
    ({
        "mixed": [
            {"x": 1},
            {"x": 2, "y": True},
            100,
            "test"
        ]
    }, "non_uniform_list"),

    # 6. Tuples & Sets
    ({
        "tuple": (1, 2, 3),
        "set": {"x", "y", "z"}
    }, "tuple_set"),

    # 7. Dataclass
    (Book("Sample", 100, ["t1", "t2"]), "dataclass"),

    # 8. Namedtuple list
    ([i1, i2], "namedtuple_list"),

    # 9. Custom object
    (Device("X100", "v1.0", "active"), "custom_object"),

    # 10. Deeply nested data
    ({
        "system": {
            "config": {
                "levels": {
                    "one": {"a": 1},
                    "two": {"b": 2},
                    "three": {"c": 3},
                }
            },
            "modes": ["on", "off"]
        }
    }, "deep_nested"),

    # 11. Mixed complex list
    ([
        {"k": "v"},
        [10, 20],
        {"coords": (5, 6)},
        None,
        True,
        {"nested": [{"m": 1}, {"n": 2}]}
    ], "complex_list"),

    # 12. Unicode
    ({
        "u1": "こんにちは",
        "u2": "你好",
        "u3": "🙂🔥"
    }, "unicode"),

    # 13. Multiline text
    ({
        "note": "line1\nline2\nline3"
    }, "multiline"),
]


# -----------------------------
# Round-trip tests: loads(dumps(obj)) == normalize(obj)
# -----------------------------
@pytest.mark.parametrize("obj,label", PYTHON_OBJECTS)
def test_roundtrip(obj, label):
    s = toon_mod.dumps(obj)
    parsed = toon_mod.loads(s)
    assert normalize(parsed) == normalize(obj), (
        f"Roundtrip mismatch for {label}\n"
        f"TOON:\n{s}\n"
        f"Parsed: {parsed}\n"
        f"Expected normalized: {normalize(obj)}"
    )


# -----------------------------
# Hand-made TOON loads tests
# -----------------------------
@pytest.mark.parametrize("toon_str,expected", [

    # Simple
    ("a: 10\nb: true\n", {"a": 10, "b": True}),

    # Nested
    ("root:\n  x: 1\n  y:\n    z: 2\n", {"root": {"x": 1, "y": {"z": 2}}}),

    # Primitive list
    ("nums[3]: 1,2,3\n", {"nums": [1, 2, 3]}),

    # Table
    ("tbl[2]{id,val}:\n  1,A\n  2,B\n",
     {"tbl": [{"id": 1, "val": "A"}, {"id": 2, "val": "B"}]}),

    # Mixed list
    ("""items[4]:
  - 10
  - test
  -
    x: 1
  - false
""",
     {"items": [10, "test", {"x": 1}, False]}),

    # Unicode
    ("greet:\n  hi: \"你好\"\n", {"greet": {"hi": "你好"}}),

    # Quoted
    ("strs:\n  a: \"hello,world\"\n  b: \"line1\\nline2\"\n",
     {"strs": {"a": "hello,world", "b": "line1\nline2"}}),

])
def test_loads_examples(toon_str, expected):
    parsed = toon_mod.loads(toon_str)
    assert normalize(parsed) == normalize(expected)


# -----------------------------
# Edge cases
# -----------------------------
def test_empty_structs():
    obj = {"empty_list": [], "empty_dict": {}, "nested": {"x": []}}
    s = toon_mod.dumps(obj)
    parsed = toon_mod.loads(s)
    assert normalize(parsed) == normalize(obj)


def test_table_with_commas_in_values():
    obj = {
        "records": [
            {"id": 1, "name": "A,B"},
            {"id": 2, "name": "C,D"},
        ]
    }
    s = toon_mod.dumps(obj)
    parsed = toon_mod.loads(s)
    assert normalize(parsed) == normalize(obj)


def test_custom_object_ignores_private_attrs():
    d = Device("M1", "v2", "ready")
    s = toon_mod.dumps(d)
    parsed = toon_mod.loads(s)
    np = normalize(parsed)

    assert "model" in np
    assert "version" in np
    assert "status" in np

    assert "_internal" not in np
    assert "internal" not in np


def test_dumps_produces_string():
    s = toon_mod.dumps({"a": 1})
    assert isinstance(s, str) and len(s) > 0
