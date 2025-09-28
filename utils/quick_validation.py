#!/usr/bin/env python3
"""
Validacao Rapida de Referencias
==============================
"""

import sys
from pathlib import Path

def test_imports():
    """Testa imports principais"""
    print("TESTANDO IMPORTS PRINCIPAIS")
    print("-" * 40)
    
    # Entry points
    entry_points = [
        'start_cli.py',
        'start_web.py', 
        'start_gui.py'
    ]
    
    for entry in entry_points:
        path = Path(entry)
        if path.exists():
            print(f"[OK] {entry} - existe")
        else:
            print(f"[X] {entry} - AUSENTE")

def test_core_files():
    """Testa arquivos principais"""
    print("\nTESTANDO ARQUIVOS PRINCIPAIS")
    print("-" * 40)
    
    core_files = [
        'src/core/advanced_algorithm_comparison.py',
        'src/gui/streamlit_interface.py',
        'src/gui/web_launcher.py',
        'src/cli/launch_system.py',
        'reports/simple_report_generator.py'
    ]
    
    for file_path in core_files:
        path = Path(file_path)
        if path.exists():
            print(f"[OK] {file_path} - existe")
        else:
            print(f"[X] {file_path} - AUSENTE")

def test_structure():
    """Testa estrutura de diretorios"""
    print("\nTESTANDO ESTRUTURA")
    print("-" * 40)
    
    dirs = ['src/core', 'src/gui', 'src/cli', 'reports', 'utils', 'tests']
    
    for dir_path in dirs:
        path = Path(dir_path)
        if path.exists() and path.is_dir():
            py_files = len(list(path.glob('*.py')))
            print(f"[OK] {dir_path} - {py_files} arquivos Python")
        else:
            print(f"[X] {dir_path} - AUSENTE")

def main():
    """Validacao principal"""
    print("VALIDACAO RAPIDA DE REFERENCIAS")
    print("=" * 50)
    
    test_imports()
    test_core_files() 
    test_structure()
    
    print("\n" + "=" * 50)
    print("VALIDACAO CONCLUIDA")

if __name__ == '__main__':
    main()