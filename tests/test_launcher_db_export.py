#!/usr/bin/env python3
import csv
import sqlite3
import subprocess
import sys
from pathlib import Path


def test_db_export_creates_csv(tmp_path: Path):
    # Prepare temp DB
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
                     ('9781234567890', 'Example', 'Author', 'MANNING PUBLICATIONS', '2020', 0.9, 'openlibrary', '/tmp/example.pdf', 0))
        conn.commit()

    # Run launcher_cli db-export
    root = Path(__file__).parent.parent
    out_csv = tmp_path / 'export.csv'
    res = subprocess.run([
        sys.executable,
        str(root / 'scripts' / 'launcher_cli.py'),
        'db-export', '--db', str(db), '--limit', '10', '--output', str(out_csv)
    ], capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    assert out_csv.exists()
    # Validate CSV has at least header and one row
    rows = list(csv.reader(out_csv.read_text(encoding='utf-8').splitlines()))
    assert len(rows) >= 2

