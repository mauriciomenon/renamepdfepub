#!/usr/bin/env python3
"""
RenamePDFEPUB - CLI Interface
============================

Ponto de entrada principal para interface de linha de comando.
"""

import sys
import argparse
from pathlib import Path

# Adiciona src ao path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

VERSION = "1.4.0"

def main():
    """Interface CLI principal"""
    parser = argparse.ArgumentParser(
        description='RenamePDFEPUB - Sistema de Renomeacao de PDFs/EPUBs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python start_cli.py algorithms    # Executar algoritmos
  python start_cli.py launch        # Launcher sistema
  python start_cli.py --version     # Mostrar versao
  python start_cli.py --help        # Mostrar esta ajuda
        """
    )
    
    parser.add_argument('command', nargs='?', default='help',
                       choices=['algorithms', 'launch', 'help'],
                       help='Comando a executar (default: help)')
    
    parser.add_argument('--version', '-v', action='version', 
                       version=f'RenamePDFEPUB v{VERSION}')
    
    args = parser.parse_args()
    
    if args.command == 'algorithms':
        try:
            from src.core.advanced_algorithm_comparison import main as run_algorithms
            run_algorithms()
        except ImportError as e:
            print(f"Erro ao importar algoritmos: {e}")
            print("Verifique se os arquivos estao na estrutura correta")
    
    elif args.command == 'launch':
        try:
            from src.cli.launch_system import main as launch_system
            launch_system()
        except ImportError as e:
            print(f"Erro ao importar launcher: {e}")
            print("Verifique se os arquivos estao na estrutura correta")
    
    elif args.command == 'help':
        parser.print_help()
        print_usage_examples()

def print_usage_examples():
    """Mostra exemplos de uso adicionais"""
    print("\nOutros pontos de entrada:")
    print("  python start_web.py       # Interface web Streamlit")
    print("  python start_gui.py       # Interface grafica")
    print("  python start_html.py      # Visualizador de relatorios HTML")

if __name__ == '__main__':
    main()
