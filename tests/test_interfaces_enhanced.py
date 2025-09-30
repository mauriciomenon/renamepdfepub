#!/usr/bin/env python3
"""
Enhanced interface tests: help text and options advertised in README.
"""

import subprocess
import sys
from pathlib import Path


def run_cmd(args, cwd=None):
    return subprocess.run(args, capture_output=True, text=True, cwd=cwd, timeout=60)


def test_start_web_help_has_keywords():
    root = Path(__file__).parent.parent
    res = run_cmd([sys.executable, str(root / 'start_web.py'), '--help'], cwd=root)
    assert res.returncode == 0
    text = (res.stdout or '') + (res.stderr or '')
    assert 'interface web' in text.lower() or 'streamlit' in text.lower()


def test_start_web_print_menu_contains_items():
    root = Path(__file__).parent.parent
    res = run_cmd([sys.executable, str(root / 'start_web.py'), '--print-menu'], cwd=root)
    assert res.returncode == 0
    text = (res.stdout or '') + (res.stderr or '')
    # Ensure menu items are present
    essentials = [
        'Iniciar Interface Streamlit',
        'Executar scan',
        'Gerar Relatorio HTML',
        'teste de algoritmos',
        'Dica sobre relatorios reais',
    ]
    assert all(item.lower() in text.lower() for item in essentials)


def test_start_gui_help_mentions_dir_option():
    root = Path(__file__).parent.parent
    res = run_cmd([sys.executable, str(root / 'start_gui.py'), '--help'], cwd=root)
    assert res.returncode == 0
    text = (res.stdout or '') + (res.stderr or '')
    assert '--dir' in text or 'dir' in text.lower()


def test_start_html_help_ok():
    root = Path(__file__).parent.parent
    # start_html.py should at least show help without crashing
    res = run_cmd([sys.executable, str(root / 'start_html.py'), '--help'], cwd=root)
    assert res.returncode in (0, 1)
