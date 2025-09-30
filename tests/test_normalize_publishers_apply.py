#!/usr/bin/env python3
import sqlite3
import subprocess
import sys
from pathlib import Path


def test_normalize_publishers_apply(tmp_path: Path):
    # Create temp DB with variants
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
        conn.execute("INSERT INTO metadata_cache (publisher) VALUES ('MANNING PUBLICATIONS')")
        conn.execute("INSERT INTO metadata_cache (publisher) VALUES ('unknown')")
        conn.commit()

    # Apply normalization
    script = Path(__file__).parent.parent / 'scripts' / 'normalize_publishers.py'
    res = subprocess.run([sys.executable, str(script), '--apply', '--db', str(db)], capture_output=True, text=True)
    assert res.returncode == 0

    # Validate
    with sqlite3.connect(str(db)) as conn:
        pubs = [r[0] for r in conn.execute("SELECT publisher FROM metadata_cache ORDER BY id").fetchall()]
        assert pubs[0] == 'Manning'
        assert pubs[1] == ''

