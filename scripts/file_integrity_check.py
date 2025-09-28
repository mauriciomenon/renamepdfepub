#!/usr/bin/env python3
"""
VERIFICADOR DE INTEGRIDADE DE ARQUIVOS
====================================

Script simples para verificar se os arquivos essenciais do sistema existem.
Util para diagnostico rapido de problemas de estrutura.

Uso: python3 scripts/file_integrity_check.py
"""

import os
from pathlib import Path

def main():
    print("=== VERIFICACAO DE INTEGRIDADE DE ARQUIVOS ===")
    
    # Lista de arquivos essenciais para verificar
    essential_files = [
        "start_cli.py",
        "start_web.py", 
        "start_gui.py",
        "start_iterative_cache.py",
        "src/core/advanced_algorithm_comparison.py",
        "src/gui/web_launcher.py",
        "README.md",
        "requirements.txt"
    ]
    
    missing_files = []
    
    for file_path in essential_files:
        if os.path.exists(file_path):
            print(f"[OK] {file_path}")
        else:
            print(f"[MISSING] {file_path}")
            missing_files.append(file_path)
    
    print("=" * 50)
    
    if missing_files:
        print(f"ENCONTRADOS {len(missing_files)} ARQUIVOS FALTANDO:")
        for f in missing_files:
            print(f"  - {f}")
        return 1
    else:
        print("TODOS OS ARQUIVOS ESSENCIAIS ESTAO PRESENTES!")
        return 0

if __name__ == "__main__":
    exit(main())