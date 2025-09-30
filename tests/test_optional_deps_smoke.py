#!/usr/bin/env python3
"""
Smoke tests for optional dependencies (Streamlit, PyQt6).
Skip when the dependency is not installed.
"""

import importlib
import pytest


def _has(mod: str) -> bool:
    try:
        importlib.import_module(mod)
        return True
    except Exception:
        return False


@pytest.mark.integration
def test_streamlit_imports_skip_if_missing():
    if not _has('streamlit'):
        pytest.skip('streamlit not installed')
    # if present, ensure our module can be imported without executing app
    import src.gui.streamlit_interface as si  # noqa: F401


@pytest.mark.integration
def test_pyqt6_imports_skip_if_missing():
    if not _has('PyQt6'):
        pytest.skip('PyQt6 not installed')
    import src.gui.gui_RenameBook as gui  # noqa: F401

