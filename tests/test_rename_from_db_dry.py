#!/usr/bin/env python3
import sqlite3
import subprocess
import sys
from pathlib import Path


def test_rename_from_db_dry(tmp_path: Path):
    # Create sample file and DB row
    f = tmp_path / 'orig.pdf'
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
            ('9781234567890', 'Sample Title', 'John Doe, Jane Roe', 'MANNING', '2022', 0.9, 'openlibrary', str(f), 0)
        )
        conn.commit()

    script = Path(__file__).parent.parent / 'scripts' / 'rename_from_db.py'
    res = subprocess.run([sys.executable, str(script), '--db', str(db), '--file', str(f)], capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    assert '[PREVIEW]' in (res.stdout + res.stderr)

