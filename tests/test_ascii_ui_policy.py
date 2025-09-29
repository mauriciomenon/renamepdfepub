#!/usr/bin/env python3
"""
UI ASCII-only policy tests.

Ensures Streamlit, GUI, web launcher and HTML generator source files contain
only ASCII in user-facing strings to keep output clean across environments.
"""

from pathlib import Path


FILES = [
    Path("src/gui/streamlit_interface.py"),
    Path("src/gui/gui_RenameBook.py"),
    Path("src/gui/web_launcher.py"),
    Path("simple_report_generator.py"),
]


def test_ui_files_ascii_only():
    for p in FILES:
        assert p.exists(), f"Missing file: {p}"
        s = p.read_text(encoding="utf-8")
        non_ascii = {c for c in s if ord(c) > 127}
        # Allow newline and tabs; check only offending characters
        assert not non_ascii, f"Non-ASCII chars found in {p}: {sorted(non_ascii)}"

