#!/usr/bin/env python3
'''
RenamePDFEPUB - CLI Interface
============================

Ponto de entrada principal para interface de linha de comando.
'''

import sys
from pathlib import Path

# Adiciona src ao path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.core.advanced_algorithm_comparison import main as run_algorithms
from src.cli.launch_system import main as launch_system

def main():
    '''Interface CLI principal'''
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == 'algorithms':
            run_algorithms()
        elif command == 'launch':
            launch_system()
        else:
            print_help()
    else:
        print_help()

def print_help():
    '''Mostra ajuda'''
    print("RenamePDFEPUB - Sistema de Renomeação de PDFs/EPUBs")
    print()
    print("Uso:")
    print("  python3 cli.py algorithms  # Executar algoritmos")
    print("  python3 cli.py launch      # Launcher sistema")
    print("  python3 web.py             # Interface web")
    print("  python3 gui.py             # Interface gráfica")

if __name__ == '__main__':
    main()
