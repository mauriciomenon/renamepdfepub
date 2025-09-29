"""Compatibility bridge for the legacy `simple_report_generator` entrypoint."""
from __future__ import annotations

import importlib.util
from pathlib import Path

_project_root = Path(__file__).resolve().parent
_module_path = _project_root / "reports" / "simple_report_generator.py"

_spec = importlib.util.spec_from_file_location("reports.simple_report_generator", _module_path)
if _spec is None or _spec.loader is None:
    raise ImportError("Unable to load reports.simple_report_generator")
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)  # type: ignore[arg-type]

globals().update({name: getattr(_module, name) for name in dir(_module) if not name.startswith('_')})
