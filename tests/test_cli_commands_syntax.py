#!/usr/bin/env python3
"""
CLI syntax smoke tests to guard README examples.

These tests do not require heavy deps; they only assert that commands are
accepted and do not fail due to unrecognized arguments.
"""

import subprocess
import sys
from pathlib import Path


def _run(cmd, cwd=None):
    return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=60)


def _ok(result):
    out = (result.stdout or "") + (result.stderr or "")
    assert "unrecognized arguments" not in out.lower()


def test_cli_algorithms_help_ok():
    root = Path(__file__).parent.parent
    cmd = [sys.executable, str(root / 'start_cli.py'), 'algorithms']
    res = _run(cmd, cwd=root)
    assert res.returncode in (0, 1)
    _ok(res)


def test_cli_scan_variants_ok():
    root = Path(__file__).parent.parent
    books = root / 'books'
    cmd1 = [sys.executable, str(root / 'start_cli.py'), 'scan', str(books)]
    res1 = _run(cmd1, cwd=root)
    assert res1.returncode in (0, 1)
    _ok(res1)

    cmd2 = [sys.executable, str(root / 'start_cli.py'), 'scan', str(books), '-r']
    res2 = _run(cmd2, cwd=root)
    assert res2.returncode in (0, 1)
    _ok(res2)

    cmd3 = [sys.executable, str(root / 'start_cli.py'), 'scan', str(books), '-t', '2', '-o', 'out.json']
    res3 = _run(cmd3, cwd=root)
    assert res3.returncode in (0, 1)
    _ok(res3)


def test_cli_scan_cycles_ok():
    root = Path(__file__).parent.parent
    books = root / 'books'
    # Ensure wrapper strips --cycles before delegating to extractor
    cmd = [sys.executable, str(root / 'start_cli.py'), 'scan-cycles', str(books), '--cycles', '1']
    res = _run(cmd, cwd=root)
    assert res.returncode in (0, 1)
    _ok(res)


def test_cli_rename_existing_usage_ok():
    root = Path(__file__).parent.parent
    # Just invoke usage path (no report provided)
    cmd = [sys.executable, str(root / 'start_cli.py'), 'rename-existing']
    res = _run(cmd, cwd=root)
    assert res.returncode in (0, 1)
    _ok(res)


def test_cli_rename_search_ok():
    root = Path(__file__).parent.parent
    books = root / 'books'
    cmd = [sys.executable, str(root / 'start_cli.py'), 'rename-search', str(books), '--rename']
    res = _run(cmd, cwd=root)
    assert res.returncode in (0, 1)
    _ok(res)

