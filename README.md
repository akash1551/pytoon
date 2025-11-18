# pytoon

`pytoon` — TOON (Token-Oriented Object Notation) serializer and parser for Python.

## Features
- `dumps(obj)` — serialize Python objects to TOON.
- `loads(text)` — parse TOON back to Python objects.
- Supports dicts, lists, tuples, sets, dataclasses, namedtuples and simple custom objects.
- Compact table-style arrays for uniform lists of objects.

## Quickstart
```py
from pytoon import dumps, loads

data = {"items": [{"id":1,"name":"A"}, {"id":2,"name":"B"}]}
s = dumps(data)
print(s)

obj = loads(s)
print(obj)
