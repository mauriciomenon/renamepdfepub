"""Compatibility wrapper forwarding to src.gui.web_launcher without emojis."""
from __future__ import annotations

from pathlib import Path
import sys as _sys

_src_path = Path(__file__).resolve().parent / "src"
if str(_src_path) not in _sys.path:
    _sys.path.insert(0, str(_src_path))

from gui.web_launcher import *  # type: ignore  # noqa: F401,F403
