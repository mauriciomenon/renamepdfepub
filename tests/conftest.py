"""Test configuration to ensure project modules are importable."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the repository root is on sys.path so tests can import modules
ROOT_DIR = Path(__file__).resolve().parents[1]
root_str = str(ROOT_DIR)
if root_str not in sys.path:
    sys.path.insert(0, root_str)
