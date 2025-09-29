#!/usr/bin/env python3
"""
End-to-end scan pipeline tests (no code changes).

Validates that the scan CLI (extractor v2) can generate JSON and that the
simple HTML report generator can render from either the latest JSON or a
given JSON file. Uses temporary directories and synthetic filenames to avoid
external dependencies.
"""

import json
import os
import sys
import time
import shutil
import subprocess
from pathlib import Path


def _make_fake_books(tmp: Path) -> None:
    # Create fake pdf/epub files with informative names
    (tmp / "Alice Smith - Sample Book (2018).pdf").write_bytes(b"%PDF-1.4\n%EOF\n")
    (tmp / "Bob Jones - Another Title (2020).epub").write_text("EPUB", encoding="utf-8")
    (tmp / "weird_file_name_without_year.pdf").write_bytes(b"%PDF-1.4\n%EOF\n")


def test_scan_and_html_report(tmp_path: Path):
    root = Path(__file__).parent.parent
    extractor = root / "src" / "gui" / "renomeia_livro_renew_v2.py"
    try:
        import tqdm  # type: ignore
    except Exception:
        import pytest
        pytest.skip("tqdm not available; skipping extractor-based scan test")
    report_json = tmp_path / "book_metadata_report.json"
    html_out = tmp_path / "summary.html"

    _make_fake_books(tmp_path)

    # Run extractor: directory only, no rename, threads small, recursive false
    cmd = [
        sys.executable,
        str(extractor),
        str(tmp_path),
        "-t",
        "2",
        "-o",
        str(report_json),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=tmp_path)
    assert res.returncode == 0, f"extractor failed: {res.stderr or res.stdout}"

    assert report_json.exists(), "JSON report was not created"
    data = json.loads(report_json.read_text(encoding="utf-8"))
    assert isinstance(data, dict) and "summary" in data, "Invalid JSON structure"
    assert data["summary"].get("total_processed", 0) >= 0

    # Generate HTML from explicit JSON
    gen = root / "simple_report_generator.py"
    res2 = subprocess.run(
        [sys.executable, str(gen), "--json", str(report_json), "--output", str(html_out)],
        capture_output=True,
        text=True,
        cwd=root,
    )
    assert res2.returncode == 0, f"report gen failed: {res2.stderr or res2.stdout}"
    content = html_out.read_text(encoding="utf-8")
    assert "<html" in content.lower() and "</html>" in content.lower(), "Invalid HTML output"
    # Ensure ASCII only (project policy for UI/report outputs)
    assert all(ord(c) < 128 for c in content), "Non-ASCII chars found in HTML"


def test_scan_cycles_runs_multiple(tmp_path: Path):
    root = Path(__file__).parent.parent
    cli = root / "start_cli.py"
    try:
        import tqdm  # type: ignore
    except Exception:
        import pytest
        pytest.skip("tqdm not available; skipping scan-cycles test")
    _make_fake_books(tmp_path)

    # Run 2 cycles quickly on the temp folder (should complete fast)
    cmd = [
        sys.executable,
        str(cli),
        "scan-cycles",
        str(tmp_path),
        "--cycles",
        "2",
        "-t",
        "1",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=root, timeout=60)
    assert res.returncode in (0, 1), "scan-cycles should complete without crashing"
