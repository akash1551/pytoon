"""
pytoon package - TOON (Token-Oriented Object Notation) for Python.
Expose dumps / loads API and package version.
"""

from .toon import dumps, loads

try:
    # populated by setuptools_scm at build time
    from __version__ import __version__
except Exception:
    __version__ = "0.0.0"

__all__ = ["dumps", "loads", "__version__"]
