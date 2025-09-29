"""Compatibility wrapper for legacy imports.

Re-exports the advanced algorithm comparison utilities from the new
`src/core` package so legacy scripts and tests can continue to import the
module from the project root.
"""
from __future__ import annotations

from pathlib import Path
import sys

_src_path = Path(__file__).resolve().parent / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

from core.advanced_algorithm_comparison import *  # noqa: F401,F403
