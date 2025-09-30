#!/usr/bin/env python3
import sqlite3
import subprocess
import sys
from pathlib import Path


def test_update_cache_filtered_dry_runs(tmp_path: Path):
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
        # No ISBN row (should be skipped safely)
        conn.execute("INSERT INTO metadata_cache (title, authors, publisher, published_date, confidence_score, source, file_path, timestamp) VALUES (?,?,?,?,?,?,?,?)",
                     ('', '', 'unknown', '', 0.1, 'openlibrary', '/tmp/none.pdf', 0))
        # With ISBN row
        conn.execute("INSERT INTO metadata_cache (isbn_13, title, authors, publisher, published_date, confidence_score, source, file_path, timestamp) VALUES (?,?,?,?,?,?,?,?,?)",
                     ('9781234567890', 'T', 'A', 'MANNING', '2021', 0.2, 'openlibrary', '/tmp/x.pdf', 0))
        conn.commit()

    script = Path(__file__).parent.parent / 'scripts' / 'update_cache_filtered.py'
    res = subprocess.run([sys.executable, str(script), '--db', str(db), '--only-incomplete', '--dry-run', '--limit', '10'], capture_output=True, text=True)
    assert res.returncode == 0, res.stderr

