#!/usr/bin/env python3
import sqlite3
import subprocess
import sys
from pathlib import Path


def test_launcher_rename_from_db_dry(tmp_path: Path):
    # Prepare DB row and file
    f = tmp_path / 'abc.pdf'
    f.write_bytes(b'%PDF-1.4\n%EOF\n')
    db = tmp_path / 'metadata_cache.db'
    with sqlite3.connect(str(db)) as conn:
        conn.execute(
            """CREATE TABLE metadata_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                isbn_10 TEXT, isbn_13 TEXT, title TEXT, authors TEXT,
                publisher TEXT, published_date TEXT, confidence_score REAL,
                source TEXT, file_path TEXT, raw_json TEXT, timestamp INTEGER
            )"""
        )
        conn.execute(
            "INSERT INTO metadata_cache (isbn_13, title, authors, publisher, published_date, confidence_score, source, file_path, timestamp) VALUES (?,?,?,?,?,?,?,?,?)",
            ('9789999999999', 'X', 'A, B', 'NOVATEC', '2019', 0.8, 'openlibrary', str(f), 0)
        )
        conn.commit()

    root = Path(__file__).parent.parent
    res = subprocess.run([
        sys.executable, str(root / 'scripts' / 'launcher_cli.py'),
        'rename-from-db', '--db', str(db), '--file', str(f)
    ], capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    assert '[PREVIEW]' in (res.stdout + res.stderr)

