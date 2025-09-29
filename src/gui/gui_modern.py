#!/usr/bin/env python3
"""Compatibilidade com a antiga interface Tkinter.

Esta versão mantém o nome `gui_modern.py`, mas redireciona para a
interface oficial baseada em PyQt6 (`gui_RenameBook`).
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


def _check_pyqt6() -> Tuple[bool, str]:
    try:
        import PyQt6  # noqa: F401
        return True, "PyQt6 disponível"
    except ImportError:
        return False, "PyQt6 não encontrado. Instale com: pip install PyQt6"


def _launch_pyqt_gui() -> None:
    from PyQt6.QtWidgets import QApplication
    from gui.gui_RenameBook import FileRenamer

    app = QApplication(sys.argv)
    window = FileRenamer()
    window.show()
    app.exec()


def main() -> None:
    available, message = _check_pyqt6()
    if not available:
        print("[ERRO] Interface gráfica requer PyQt6")
        print("NOTA: tkinter não é mais utilizado. Instale PyQt6.")
        print(message)
        return

    try:
        _launch_pyqt_gui()
    except ImportError as exc:  # pragma: no cover - feedback interativo
        print(f"[ERRO] Não foi possível carregar a interface: {exc}")
        print("Execute a partir da raiz do projeto: python start_gui.py")
    except Exception as exc:  # pragma: no cover - feedback interativo
        print(f"[ERRO] Falha inesperada na interface PyQt6: {exc}")


if __name__ == "__main__":
    main()