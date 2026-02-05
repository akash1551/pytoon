"""
toon.py

A self-contained, practical Python implementation of TOON (Token-Oriented Object Notation)
with a JSON-like API: `dumps(obj)` and `loads(toon_str)`.

- dumps(obj) -> str : Serialize common Python objects into TOON.
- loads(toon_str) -> Any : Parse TOON produced by dumps back into Python types.

This is a best-effort, usable implementation focused on round-tripping dumps -> loads for
typical Python objects: primitives, dicts, lists/tuples/sets, dataclasses/namedtuples and
uniform-table arrays. It is not a complete spec implementation, but is practical and easy
to extend.

Usage:
    from toon import dumps, loads
    s = dumps(my_obj)
    obj = loads(s)
"""

from dataclasses import is_dataclass, asdict
import json
import inspect
from typing import Any, List, Tuple, Dict

INDENT_STR = "  "  # two spaces per level (modifiable if desired)


# -------------------- Helpers for serialization --------------------


def _is_primitive(x):
    return x is None or isinstance(x, (bool, int, float, str))


def _to_toon_primitive(x):
    """Return a TOON-safe string for a primitive."""
    if x is None:
        return "null"
    if isinstance(x, bool):
        return "true" if x else "false"
    if isinstance(x, (int, float)):
        return str(x)
    s = str(x)
    if s == "":
        return '""'
    needs_quote = (
        any(ch in s for ch in [",", "\n", "\r"])
        or s[0].isspace()
        or s[-1].isspace()
        or s.startswith(('"', "'"))
        or s.lower() in ("null", "true", "false")
    )
    if needs_quote:
        return json.dumps(s, ensure_ascii=False)
    return s


def _escape_header_key(k: str) -> str:
    """Make a key safe for header usage; quote if it's not a simple identifier."""
    if isinstance(k, str) and k.isidentifier():
        return k
    return json.dumps(str(k), ensure_ascii=False)


def _is_namedtuple_instance(x):
    return isinstance(x, tuple) and hasattr(x, "_fields")


def _object_to_dict(obj):
    """Convert dataclass/namedtuple/object to dict for serialization."""
    if is_dataclass(obj):
        return asdict(obj)
    if _is_namedtuple_instance(obj):
        return obj._asdict()
    if hasattr(obj, "__dict__"):
        return {
            k: v
            for k, v in vars(obj).items()
            if not k.startswith("_") and not inspect.isroutine(v)
        }
    # fallback
    return {"value": repr(obj)}


def _all_dicts_uniform(list_of_dicts: List[dict]) -> Tuple[bool, List[str] or None]:
    """
    Return (is_uniform, keys_order).
    Uniform means every element is a dict and they all have the same set of keys.
    If insertion order is consistent across elements, return that order; otherwise return sorted keys.
    """
    if not list_of_dicts:
        return False, None
    if not all(isinstance(item, dict) for item in list_of_dicts):
        return False, None
    sets = [set(d.keys()) for d in list_of_dicts]
    first_set = sets[0]
    if all(s == first_set for s in sets):
        first_keys = list(list_of_dicts[0].keys())
        if all(tuple(d.keys()) == tuple(first_keys) for d in list_of_dicts):
            return True, first_keys
        return True, sorted(first_set)
    return False, None


# -------------------- Serialization: dumps --------------------


def dumps(obj: Any, name: str = None, indent: int = 0) -> str:
    """
    Serialize Python object into TOON. `name` is optional and produces a top-level key.
    indent counts indentation levels (0 == top).
    """
    pad = INDENT_STR * indent

    # primitives
    if _is_primitive(obj):
        val = _to_toon_primitive(obj)
        if name:
            return f"{pad}{name}: {val}\n"
        return f"{pad}{val}\n"

    # dataclass / namedtuple => dict
    if _is_namedtuple_instance(obj) or is_dataclass(obj):
        obj = _object_to_dict(obj)

    # dict
    if isinstance(obj, dict):
        lines = []
        if name:
            lines.append(f"{pad}{name}:")
            child_pad = INDENT_STR * (indent + 1)
        else:
            child_pad = pad
        # explicit empty dict representation: return a '{}' line so parser can detect it
        if not obj:
            if name:
                return f"{pad}{name}:\n{child_pad}{{}}\n"
            return f"{pad}{{}}\n"
        for k, v in obj.items():
            key = _escape_header_key(k)
            if _is_primitive(v):
                lines.append(f"{child_pad}{key}: {_to_toon_primitive(v)}")
            else:
                lines.append(f"{child_pad}{key}:")
                # use one-level deeper indentation for nested content
                lines.append(dumps(v, name=None, indent=indent + 1).rstrip("\n"))
        return "\n".join(lines) + ("\n" if lines else "")

    # list / tuple / set
    if isinstance(obj, (list, tuple, set)):
        if isinstance(obj, set):
            try:
                lst = sorted(list(obj))
            except Exception:
                lst = list(obj)
        else:
            lst = list(obj)
        n = len(lst)
        if n == 0:
            return f"{pad}{name}[0]:\n" if name else f"{pad}[]\n"

        uniform, keys = _all_dicts_uniform(lst)
        # compact table if uniform dicts and all primitive values
        if (
            uniform
            and keys
            and all(
                _is_primitive(v)
                for d in lst
                for v in (d.values() if isinstance(d, dict) else [])
            )
        ):
            keys_escaped = ",".join(_escape_header_key(k) for k in keys)
            header = (
                f"{pad}{name}[{n}]{{{keys_escaped}}}:"
                if name
                else f"{pad}[{n}]{{{keys_escaped}}}:"
            )
            lines = [header]
            for d in lst:
                row = ",".join(_to_toon_primitive(d.get(k)) for k in keys)
                lines.append(f"{pad}{INDENT_STR}{row}")
            return "\n".join(lines) + "\n"

        # all primitives => single-line comma list (if named) or a simple "- ..." block
        if all(_is_primitive(x) for x in lst):
            vals = ",".join(_to_toon_primitive(x) for x in lst)
            if name:
                return f"{pad}{name}[{n}]: {vals}\n"
            # unnamed list of primitives as a single "- ..." line (useful for readability)
            return f"{pad}- " + ", ".join(_to_toon_primitive(x) for x in lst) + "\n"

        # mixed/complex items => list block with '-' markers; nested items are indented one level deeper
        lines = []
        if name:
            lines.append(f"{pad}{name}[{n}]:")
            item_indent_str = pad + INDENT_STR
            nested_indent = indent + 2
        else:
            item_indent_str = pad
            nested_indent = indent + 1

        for item in lst:
            if _is_primitive(item):
                lines.append(f"{item_indent_str}- {_to_toon_primitive(item)}")
            else:
                # migrate dataclass/namedtuple -> dict first
                if _is_namedtuple_instance(item) or is_dataclass(item):
                    item = _object_to_dict(item)
                # list item header
                lines.append(f"{item_indent_str}-")
                # nested item content at indent+2 (one level deeper than the '-' line)
                lines.append(dumps(item, name=None, indent=nested_indent).rstrip("\n"))
        return "\n".join(lines) + "\n"

    # fallback for objects: try to convert to dict and include class name
    try:
        obj_dict = _object_to_dict(obj)
        return dumps(obj_dict, name=name, indent=indent)
    except Exception:
        val = _to_toon_primitive(repr(obj))
        if name:
            return f"{pad}{name}: {val}\n"
        return f"{pad}{val}\n"


# -------------------- Parsing: loads --------------------


def _parse_primitive_token(tok: str):
    tok = tok.strip()
    if tok == "":
        return ""
    if tok == "null":
        return None
    if tok == "true":
        return True
    if tok == "false":
        return False
    # JSON quoted string
    if (tok.startswith('"') and tok.endswith('"')) or (
        tok.startswith("'") and tok.endswith("'")
    ):
        try:
            return json.loads(tok)
        except Exception:
            return tok[1:-1]
    # try int then float (float handles nan/inf and exponent forms)
    try:
        # attempt exact int parsing first
        try:
            return int(tok)
        except Exception:
            # fall back to float parsing (accepts 'nan', 'inf', '1e3', etc.)
            return float(tok)
    except Exception:
        return tok


def _count_leading_indent(s: str) -> int:
    """Count how many INDENT_STR are at the start of s."""
    count = 0
    while s.startswith(INDENT_STR):
        count += 1
        s = s[len(INDENT_STR) :]
    return count


def _split_csv_like(s: str) -> List[str]:
    """
    Split comma-separated tokens but respect quoted substrings.
    Returns list of tokens (whitespace preserved trimmed).
    """
    parts = []
    cur = ""
    in_q = False
    qchar = None
    i = 0
    while i < len(s):
        ch = s[i]
        if ch in ('"', "'"):
            if not in_q:
                in_q = True
                qchar = ch
                cur += ch
            elif qchar == ch:
                in_q = False
                cur += ch
            else:
                cur += ch
        elif ch == "," and not in_q:
            parts.append(cur.strip())
            cur = ""
        else:
            cur += ch
        i += 1
    if cur.strip() != "":
        parts.append(cur.strip())
    return parts


def loads(toon_str: str) -> Any:
    """
    Parse a TOON string (created by dumps) back into Python objects (dict/list/primitives).
    This parser is intentionally aligned to the dumps() format above for reliable round-trips.
    """
    # Split and filter out blank lines but preserve structural indentation
    raw_lines = toon_str.splitlines()
    lines = []
    for ln in raw_lines:
        # keep lines that are not empty after stripping spaces (but preserve indentation)
        if ln.strip() == "":
            continue
        lines.append(ln.rstrip("\n"))

    # Preprocess into (indent_level, content) tuples
    processed: List[Tuple[int, str]] = []
    for ln in lines:
        indent = _count_leading_indent(ln)
        content = ln[indent * len(INDENT_STR) :]
        processed.append((indent, content))

    idx = 0
    N = len(processed)

    def parse_block(expected_indent: int):
        nonlocal idx
        result: Dict[str, Any] = {}
        arr_mode = None  # if we encounter '-' list items, we build a list

        while idx < N:
            indent, content = processed[idx]
            if indent < expected_indent:
                break
            if indent > expected_indent:
                # Deeper indentation than expected: this should be consumed by caller.
                break

            # Handle explicit empty list "[]"
            if content.strip() == "[]":
                idx += 1
                if arr_mode is None and not result:
                    return []
                continue
            # Handle explicit empty dict "{}"
            if content.strip() == "{}":
                idx += 1
                if arr_mode is None and not result:
                    return {}
                continue

            # Handle list item lines: "- value" or "-" (then nested)
            if content.startswith("- ") or content == "-":
                if arr_mode is None:
                    arr_mode = []
                # consume the line
                idx += 1
                if content == "-":
                    # nested block follows with indent > current indent
                    if idx < N and processed[idx][0] > indent:
                        item = parse_block(indent + 1)
                        arr_mode.append(item)
                    else:
                        arr_mode.append(None)
                else:
                    val_tok = content[2:].strip()
                    # if comma-separated tokens (e.g. "- a, b, c") we append each as separate primitives
                    if "," in val_tok and not (
                        val_tok.startswith('"') or val_tok.startswith("'")
                    ):
                        parts = _split_csv_like(val_tok)
                        for p in parts:
                            arr_mode.append(_parse_primitive_token(p))
                    else:
                        arr_mode.append(_parse_primitive_token(val_tok))
                continue

            # otherwise handle "key: value" or "key:" or "name[N]{...}:" or "name[N]: v1,v2" forms
            # find colon not inside quotes
            colon_pos = None
            in_q = False
            qch = None
            for i, ch in enumerate(content):
                if ch in ('"', "'"):
                    if not in_q:
                        in_q = True
                        qch = ch
                    elif qch == ch:
                        in_q = False
                if ch == ":" and not in_q:
                    colon_pos = i
                    break

            if colon_pos is None:
                # No key: treat as a primitive-only line (top-level primitive or inline primitive)
                val = _parse_primitive_token(content)
                idx += 1
                if arr_mode is None and not result:
                    return val
                if arr_mode is not None:
                    arr_mode.append(val)
                    continue
                # otherwise skip stray primitive
                continue

            key_part = content[:colon_pos].strip()
            val_part = content[colon_pos + 1 :].strip()
            idx += 1

            # If val_part is empty -> either table header like name[N]{...}:  OR nested block key:
            if val_part == "":
                # Table-style header?
                if (
                    "[" in key_part
                    and "]" in key_part
                    and "{" in key_part
                    and "}" in key_part
                ):
                    # parse header: name[NN]{k1,k2}  (name may be empty if not provided)
                    name_section = key_part.split("[", 1)[0].strip()
                    # extract keys inside {}
                    try:
                        br_start = key_part.index("[")
                        br_end = key_part.index("]", br_start)
                        keys_start = key_part.index("{", br_end)
                        keys_end = key_part.index("}", keys_start)
                        n_section = key_part[br_start + 1 : br_end]
                        keys_str = key_part[keys_start + 1 : keys_end]
                        keys = [
                            k.strip().strip('"').strip("'")
                            for k in keys_str.split(",")
                            if k.strip() != ""
                        ]
                    except Exception:
                        keys = []
                    # collect rows at indent == expected_indent + 1
                    rows = []
                    while idx < N and processed[idx][0] == expected_indent + 1:
                        _, row_content = processed[idx]
                        parts = _split_csv_like(row_content.strip())
                        row = {}
                        for k, vtok in zip(keys, parts):
                            row[k] = _parse_primitive_token(vtok)
                        rows.append(row)
                        idx += 1
                    if name_section == "":
                        # anonymous table -> return as list? put under special key
                        # but to be consistent, put under "_table" with rows
                        result_key = "_table"
                    else:
                        result_key = name_section
                    result[result_key] = rows
                    continue
                else:
                    # Check for list header: name[N]
                    real_key = key_part
                    is_list_header = False
                    if "[" in key_part and key_part.endswith("]"):
                        try:
                            name_part, rest = key_part.split("[", 1)
                            if rest.endswith("]"):
                                real_key = name_part.strip()
                                is_list_header = True
                        except ValueError:
                            pass

                    # nested block "key:" -> parse a nested block at indent+1
                    nested = parse_block(expected_indent + 1)

                    if is_list_header and nested == {}:
                        nested = []

                    result[real_key] = nested
                    continue
            else:
                # inline value exists after colon.
                # handle name[N]: v1,v2  (array inline)
                if "[" in key_part and "]" in key_part:
                    name = key_part.split("[", 1)[0].strip()
                    parts = _split_csv_like(val_part)
                    vals = [_parse_primitive_token(p) for p in parts if p != ""]
                    result[name] = vals
                    continue
                # regular "key: value"
                result[key_part] = _parse_primitive_token(val_part)
                continue

        if arr_mode is not None:
            return arr_mode

        # Unwrap anonymous table if it's the only thing
        if len(result) == 1 and "_table" in result:
            return result["_table"]

        return result

    # Start parse from top-level indent 0
    idx = 0
    parsed = parse_block(0)
    return parsed


# -------------------- Quick demo when run as script --------------------
if __name__ == "__main__":
    from collections import namedtuple

    Person = namedtuple("Person", ["id", "name", "role"])
    p1 = Person(1, "Alice", "admin")
    p2 = Person(2, "Bob", "user")

    example = {
        "context": {"task": "Roundtrip demo", "season": "spring_2025"},
        "friends": ["ana", "luis", "sam"],
        "hikes": [
            {"id": 1, "name": "Blue Lake Trail", "distanceKm": 7.5},
            {"id": 2, "name": "Ridge, Overlook", "distanceKm": 9.2},
        ],
        "people": [p1, p2],
        "misc": (1, None, "two"),
        "empty_list": [],
    }

    s = dumps(example)
    print("=== TOON ===")
    print(s)
    print("=== PARSED BACK ===")
    parsed = loads(s)
    print(parsed)
