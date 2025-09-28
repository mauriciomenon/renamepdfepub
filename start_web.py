#!/usr/bin/env python3
'''
RenamePDFEPUB - Web Interface
============================

Ponto de entrada para interface web Streamlit.
'''

import sys
from pathlib import Path

# Adiciona src ao path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.gui.web_launcher import main

if __name__ == '__main__':
    main()
