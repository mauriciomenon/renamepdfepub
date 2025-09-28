#!/usr/bin/env python3
"""
RenamePDFEPUB - GUI Interface
============================

Ponto de entrada para interface grafica.
"""

import sys
import argparse
from pathlib import Path

VERSION = "1.4.0"

# Adiciona src ao path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

def check_gui_dependencies():
    """Verifica se as dependencias da GUI estao disponíveis"""
    try:
        import tkinter
        return True, "tkinter available"
    except ImportError:
        try:
            import Tkinter  # Python 2 fallback
            return True, "Tkinter available"
        except ImportError:
            return False, "tkinter nao disponivel - e um modulo built-in do Python"

def main():
    """Interface GUI principal"""
    parser = argparse.ArgumentParser(
        description='RenamePDFEPUB - Interface Grafica',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--version', '-v', action='version', 
                       version=f'RenamePDFEPUB GUI v{VERSION}')
    
    parser.add_argument('--check-deps', action='store_true',
                       help='Verificar dependencias')
    
    args = parser.parse_args()
    
    if args.check_deps:
        available, msg = check_gui_dependencies()
        print(f"Dependencias GUI: {msg}")
        return
    
    # Verifica dependencias
    available, msg = check_gui_dependencies()
    if not available:
        print("[ERROR] Interface grafica requer tkinter")
        print("NOTA: tkinter e um modulo built-in do Python")
        print("Se nao esta disponivel, verifique sua instalacao do Python")
        print("Em sistemas Ubuntu/Debian: sudo apt-get install python3-tk")
        print("Em sistemas macOS: tkinter deve estar incluído")
        return
    
    try:
        from src.gui.gui_modern import main as gui_main
        gui_main()
    except ImportError as e:
        print(f"[ERROR] Erro ao importar interface grafica: {e}")
        print("Verifique se o arquivo src/gui/gui_modern.py existe")
    except Exception as e:
        print(f"[ERROR] Erro na interface grafica: {e}")

if __name__ == '__main__':
    main()
