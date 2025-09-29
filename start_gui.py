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
        import PyQt6
        return True, "PyQt6 available"
    except ImportError:
        return False, "PyQt6 nao disponivel - instale com: pip install PyQt6"

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
    
    parser.add_argument('--dir', dest='initial_dir', help='Diretorio inicial para seleção de arquivos')

    args = parser.parse_args()
    
    if args.check_deps:
        available, msg = check_gui_dependencies()
        print(f"Dependencias GUI: {msg}")
        return
    
    # Verifica dependencias
    available, msg = check_gui_dependencies()
    if not available:
        print("[ERROR] Interface grafica requer PyQt6")
        print("NOTA: PyQt6 precisa ser instalado separadamente")
        print("Execute: pip install PyQt6")
        print("Ou: conda install pyqt")
        return
    
    try:
        from PyQt6.QtWidgets import QApplication
        from src.gui.gui_RenameBook import FileRenamer
        
        app = QApplication(sys.argv)
        window = FileRenamer(initial_directory=args.initial_dir)
        window.show()
        app.exec()
        
    except ImportError as e:
        print(f"[ERROR] Erro ao importar interface grafica: {e}")
        print("Verifique se PyQt6 esta instalado: pip install PyQt6")
    except Exception as e:
        print(f"[ERROR] Erro na interface grafica: {e}")

if __name__ == '__main__':
    main()
