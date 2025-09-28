#!/usr/bin/env python3
"""
RenamePDFEPUB - Web Interface
============================

Ponto de entrada para interface web Streamlit.
"""

import sys
import argparse
from pathlib import Path

VERSION = "1.4.0"

# Adiciona src ao path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

def main():
    """Interface Web principal"""
    parser = argparse.ArgumentParser(
        description='RenamePDFEPUB - Interface Web Streamlit',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Opcoes da interface:
  1. Iniciar Interface Streamlit (Recomendado)  
  2. Gerar Relatorio HTML
  3. Executar Teste de Algoritmos
  4. Gerar Dados de Exemplo
  0. Sair
        """
    )
    
    parser.add_argument('--version', '-v', action='version', 
                       version=f'RenamePDFEPUB Web v{VERSION}')
    
    parser.add_argument('--auto-start', action='store_true',
                       help='Iniciar automaticamente interface Streamlit')
    
    args = parser.parse_args()
    
    if args.auto_start:
        print("Iniciando interface Streamlit automaticamente...")
        try:
            from src.gui.web_launcher import launch_streamlit, install_streamlit, generate_sample_data
            if install_streamlit():
                generate_sample_data()
                launch_streamlit()
            else:
                print("[ERROR] Nao foi possível instalar Streamlit")
        except ImportError as e:
            print(f"[ERROR] Erro ao importar modulos web: {e}")
    else:
        try:
            from src.gui.web_launcher import main as web_main
            web_main()
        except ImportError as e:
            print(f"[ERROR] Erro ao importar web launcher: {e}")
            print("Verifique se o arquivo src/gui/web_launcher.py existe")

if __name__ == '__main__':
    main()
