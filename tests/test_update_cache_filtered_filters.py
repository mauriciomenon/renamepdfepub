#!/usr/bin/env python3
from pathlib import Path
import sqlite3
import importlib.util


def _import_update_script(mod_path: Path):
    spec = importlib.util.spec_from_file_location('update_cache_filtered', str(mod_path))
    mod = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


def test_select_rows_filters(tmp_path: Path):
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
        # Two incomplete rows with different publishers/years
        conn.execute("INSERT INTO metadata_cache (isbn_13, title, authors, publisher, published_date, confidence_score, source, file_path, timestamp) VALUES (?,?,?,?,?,?,?,?,?)",
                     ('9781111111111', '', '', 'MANNING', '', 0.1, 'openlibrary', '/tmp/a.pdf', 1))
        conn.execute("INSERT INTO metadata_cache (isbn_13, title, authors, publisher, published_date, confidence_score, source, file_path, timestamp) VALUES (?,?,?,?,?,?,?,?,?)",
                     ('9782222222222', '', '', 'O\'REILLY', '2020', 0.1, 'openlibrary', '/tmp/b.pdf', 2))
        conn.commit()

    mod = _import_update_script(Path(__file__).parent.parent / 'scripts' / 'update_cache_filtered.py')
    with sqlite3.connect(str(db)) as conn:
        rows_all = mod._select_rows(conn, True, False, 0.0, 100, None, None, None, None)
        assert len(rows_all) == 2
        rows_manning = mod._select_rows(conn, True, False, 0.0, 100, 'MANNING', None, None, None)
        assert len(rows_manning) == 1
        rows_year = mod._select_rows(conn, True, False, 0.0, 100, None, '2020', None, None)
        assert len(rows_year) == 1

