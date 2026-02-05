# pytoon

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Version](https://img.shields.io/badge/pypi-v0.1.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)

`pytoon` — **TOON** (**T**oken-**O**riented **O**bject **N**otation) serializer and parser for Python.

## Installation

```bash
pip install pytoon
```

## Features

- **Human-Readable**: Minimal syntax, similar to YAML but distinct.
- **Round-Trip**: `dumps(obj)` -> `loads(text)` preserves structure.
- **Compact Tables**: Automatically detects lists of uniform objects and formats them as compact tables.
- **Broad Support**: Handles `dict`, `list`, `tuple`, `set`, `dataclasses`, `namedtuples`, and simple objects.

## Quickstart

```python
from pytoon import dumps, loads

data = {"items": [{"id":1,"name":"A"}, {"id":2,"name":"B"}]}

# Serialize
s = dumps(data)
print(s)

# Parse back
obj = loads(s)
print(obj)
```

**Output:**
```yaml
items[2]{id,name}:
  1,A
  2,B
```

## API Reference

### `dumps(obj, name=None, indent=0) -> str`
Serializes a Python object to a TOON string.
- `obj`: The object to serialize.
- `name`: (Optional) Root key name for the object.
- `indent`: (Optional) Starting indentation level (default 0).

### `loads(toon_str) -> Any`
Parses a TOON string back into Python objects.
- Returns `dict`, `list`, or primitive depending on the input.
