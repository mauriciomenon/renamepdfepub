#!/usr/bin/env python3
'''
RenamePDFEPUB - GUI Interface
============================

Ponto de entrada para interface gráfica.
'''

import sys
from pathlib import Path

# Adiciona src ao path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

try:
    from src.gui.gui_modern import main
    main()
except ImportError:
    print("[ERROR] Interface gráfica requer dependências adicionais")
    print("Execute: pip install tkinter")
