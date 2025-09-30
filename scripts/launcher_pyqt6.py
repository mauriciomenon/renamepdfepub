#!/usr/bin/env python3
"""
Basic PyQt6 launcher exposing core operations via buttons/forms.
Note: Focused on wiring; not a full redesign of GUI. Does not replace start_gui.py.
"""

import sys
import subprocess
from pathlib import Path

try:
    from PyQt6.QtWidgets import (
        QApplication, QWidget, QPushButton, QLabel, QLineEdit, QCheckBox,
        QSpinBox, QHBoxLayout, QVBoxLayout, QFileDialog, QMessageBox, QTabWidget
    )
except Exception:
    print('[ERROR] PyQt6 not installed. Install with: pip install PyQt6')
    sys.exit(1)


ROOT = Path(__file__).resolve().parents[1]


def run_cmd(cmd):
    try:
        subprocess.Popen(cmd, cwd=ROOT)
        return True
    except Exception as e:
        QMessageBox.critical(None, 'Erro', str(e))
        return False


class Launcher(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('RenamePDFEPUB - Launcher (PyQt6)')

        tabs = QTabWidget(self)
        tabs.addTab(self._build_scan_tab(), 'Scan')
        tabs.addTab(self._build_maintenance_tab(), 'Maintenance')
        tabs.addTab(self._build_tools_tab(), 'Tools')

        layout = QVBoxLayout()
        layout.addWidget(tabs)
        self.setLayout(layout)

    def _build_scan_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)

        h_dir = QHBoxLayout()
        self.dir_edit = QLineEdit(str((ROOT / 'books').resolve()))
        btn_browse = QPushButton('...')
        btn_browse.clicked.connect(self._choose_dir)
        h_dir.addWidget(QLabel('Directory:'))
        h_dir.addWidget(self.dir_edit)
        h_dir.addWidget(btn_browse)

        h_opts = QHBoxLayout()
        self.chk_recursive = QCheckBox('Recursive')
        self.spin_threads = QSpinBox()
        self.spin_threads.setRange(1, 32)
        self.spin_threads.setValue(4)
        h_opts.addWidget(self.chk_recursive)
        h_opts.addWidget(QLabel('Threads:'))
        h_opts.addWidget(self.spin_threads)

        btn_scan = QPushButton('Run scan')
        btn_scan.clicked.connect(self._run_scan)
        btn_cycles = QPushButton('Run scan-cycles (3)')
        btn_cycles.clicked.connect(self._run_cycles)

        v.addLayout(h_dir)
        v.addLayout(h_opts)
        v.addWidget(btn_scan)
        v.addWidget(btn_cycles)
        v.addStretch(1)
        return w

    def _build_maintenance_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)

        # Cache ops
        btn_rescan = QPushButton('Rescan cache (core)')
        btn_rescan.clicked.connect(lambda: run_cmd([sys.executable, str(ROOT / 'start_cli.py'), 'scan', '--rescan-cache']))

        h_upd = QHBoxLayout()
        self.spin_thr = QLineEdit('0.7')
        h_upd.addWidget(QLabel('Confidence <'))
        h_upd.addWidget(self.spin_thr)
        btn_update = QPushButton('Update cache (core)')
        def _do_update():
            thr = self.spin_thr.text().strip() or '0.7'
            run_cmd([sys.executable, str(ROOT / 'start_cli.py'), 'scan', '--update-cache', '--confidence-threshold', thr])
        btn_update.clicked.connect(_do_update)

        # Normalize publishers
        btn_norm_dry = QPushButton('Normalize publishers (dry-run)')
        btn_norm_dry.clicked.connect(lambda: run_cmd([sys.executable, str(ROOT / 'scripts' / 'normalize_publishers.py'), '--dry-run']))
        btn_norm_apply = QPushButton('Normalize publishers (apply)')
        btn_norm_apply.clicked.connect(lambda: run_cmd([sys.executable, str(ROOT / 'scripts' / 'normalize_publishers.py'), '--apply']))

        v.addWidget(btn_rescan)
        v.addLayout(h_upd)
        v.addWidget(btn_update)
        v.addSpacing(12)
        v.addWidget(btn_norm_dry)
        v.addWidget(btn_norm_apply)
        v.addStretch(1)
        return w

    def _build_tools_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)

        btn_streamlit = QPushButton('Open Streamlit UI')
        btn_streamlit.clicked.connect(lambda: run_cmd([sys.executable, str(ROOT / 'scripts' / 'launcher_streamlit.py')]))
        btn_web = QPushButton('Open Web Launcher')
        btn_web.clicked.connect(lambda: run_cmd([sys.executable, str(ROOT / 'start_web.py')]))
        btn_alg = QPushButton('Run Algorithms Suite')
        btn_alg.clicked.connect(lambda: run_cmd([sys.executable, str(ROOT / 'start_cli.py'), 'algorithms']))

        v.addWidget(btn_streamlit)
        v.addWidget(btn_web)
        v.addWidget(btn_alg)
        v.addStretch(1)
        return w

    def _choose_dir(self):
        d = QFileDialog.getExistingDirectory(self, 'Select Directory', self.dir_edit.text())
        if d:
            self.dir_edit.setText(d)

    def _run_scan(self):
        cmd = [
            sys.executable, str(ROOT / 'start_cli.py'), 'scan', self.dir_edit.text()
        ]
        if self.chk_recursive.isChecked():
            cmd.append('-r')
        cmd += ['-t', str(self.spin_threads.value())]
        run_cmd(cmd)

    def _run_cycles(self):
        cmd = [
            sys.executable, str(ROOT / 'start_cli.py'), 'scan-cycles', self.dir_edit.text(), '--cycles', '3', '-t', str(max(1, self.spin_threads.value()//2))
        ]
        run_cmd(cmd)


def main():
    app = QApplication(sys.argv)
    w = Launcher()
    w.resize(720, 420)
    w.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()

