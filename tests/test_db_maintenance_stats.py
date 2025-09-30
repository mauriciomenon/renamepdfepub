#!/usr/bin/env python3
import sqlite3
import subprocess
import sys
from pathlib import Path


def test_db_maintenance_stats(tmp_path: Path):
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
        conn.execute("INSERT INTO metadata_cache (isbn_13, title, authors, publisher, published_date, confidence_score, source, file_path, timestamp) VALUES (?,?,?,?,?,?,?,?,?)",
                     ('9781111111111', 'T', 'A', 'P', '2020', 0.1, 'openlibrary', '/tmp/a.pdf', 123))
        conn.commit()

    root = Path(__file__).parent.parent
    res = subprocess.run([sys.executable, str(root / 'scripts' / 'db_maintenance.py'), '--db', str(db), '--stats'], capture_output=True, text=True)
    assert res.returncode == 0
    assert 'Rows:' in (res.stdout + res.stderr)

