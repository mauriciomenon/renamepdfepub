"""Compatibility wrapper for legacy tests expecting gui_RenameBook at repo root.

Exposes RenamePDFGUI pointing to the Qt FileRenamer implementation.
"""

from src.gui.gui_RenameBook import FileRenamer as RenamePDFGUI  # noqa: F401

