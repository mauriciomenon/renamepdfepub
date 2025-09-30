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
        tabs.addTab(self._build_dbgaps_tab(), 'DB Gaps')
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

    def _build_dbgaps_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)
        # Summary labels
        self.lbl_total = QLabel('Registros: —')
        self.lbl_title = QLabel('Sem título: —')
        self.lbl_auth = QLabel('Sem autores: —')
        self.lbl_pub = QLabel('Sem editora: —')
        self.lbl_year = QLabel('Sem ano: —')
        self.lbl_isbn = QLabel('Sem ISBN: —')
        btn_refresh = QPushButton('Atualizar contagem')
        btn_refresh.clicked.connect(self._refresh_dbgaps)

        v.addWidget(self.lbl_total)
        v.addWidget(self.lbl_title)
        v.addWidget(self.lbl_auth)
        v.addWidget(self.lbl_pub)
        v.addWidget(self.lbl_year)
        v.addWidget(self.lbl_isbn)
        v.addWidget(btn_refresh)

        # Export CSV
        btn_export = QPushButton('Exportar incompletos (CSV)')
        def _do_export():
            out, _ = QFileDialog.getSaveFileName(self, 'Salvar CSV', str(ROOT / 'incompletos.csv'))
            if out:
                cmd = [
                    sys.executable, str(ROOT / 'scripts' / 'launcher_cli.py'), 'db-export',
                    '--only-incomplete', '--limit', '20000', '--output', out
                ]
                run_cmd(cmd)
        btn_export.clicked.connect(_do_export)
        v.addWidget(btn_export)

        w.setLayout(v)
        return w

    def _refresh_dbgaps(self):
        import sqlite3
        db = ROOT / 'metadata_cache.db'
        if not db.exists():
            QMessageBox.information(self, 'Info', 'metadata_cache.db não encontrado')
            return
        try:
            with sqlite3.connect(str(db)) as conn:
                cur = conn.cursor()
                def _count(sql: str) -> int:
                    cur.execute(sql)
                    return cur.fetchone()[0]
                total = _count("SELECT COUNT(*) FROM metadata_cache")
                missing_title = _count("SELECT COUNT(*) FROM metadata_cache WHERE title IS NULL OR title='' OR title='Unknown'")
                missing_auth = _count("SELECT COUNT(*) FROM metadata_cache WHERE authors IS NULL OR authors='' OR authors='Unknown'")
                missing_pub = _count("SELECT COUNT(*) FROM metadata_cache WHERE publisher IS NULL OR publisher='' OR publisher='Unknown'")
                missing_year = _count("SELECT COUNT(*) FROM metadata_cache WHERE published_date IS NULL OR published_date='' OR published_date='Unknown'")
                missing_isbn = _count("SELECT COUNT(*) FROM metadata_cache WHERE (COALESCE(isbn_13,'')='' AND COALESCE(isbn_10,'')='')")
            self.lbl_total.setText(f'Registros: {total}')
            self.lbl_title.setText(f'Sem título: {missing_title}')
            self.lbl_auth.setText(f'Sem autores: {missing_auth}')
            self.lbl_pub.setText(f'Sem editora: {missing_pub}')
            self.lbl_year.setText(f'Sem ano: {missing_year}')
            self.lbl_isbn.setText(f'Sem ISBN: {missing_isbn}')
        except Exception as e:
            QMessageBox.critical(self, 'Erro', str(e))

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
