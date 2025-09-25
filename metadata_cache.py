"""Simple SQLite-backed metadata cache used by the pipeline.
Provides upsert/get/find_by_isbn utilities. Lightweight and safe for unit tests.
"""
import sqlite3
import json
from typing import Optional, Dict


class MetadataCache:
    def __init__(self, db_path: str = 'metadata_cache.db'):
        self.db_path = db_path
        self._conn = sqlite3.connect(self.db_path)
        self._ensure_table()

    def _ensure_table(self):
        cur = self._conn.cursor()
        cur.execute('''
        CREATE TABLE IF NOT EXISTS metadata (
            path TEXT PRIMARY KEY,
            isbn10 TEXT,
            isbn13 TEXT,
            metadata_json TEXT
        )
        ''')
        self._conn.commit()

    def upsert(self, path: str, metadata: Dict) -> None:
        isbn10 = metadata.get('isbn10') or None
        isbn13 = metadata.get('isbn13') or None
        md = json.dumps(metadata, ensure_ascii=False)
        cur = self._conn.cursor()
        cur.execute('''
            INSERT INTO metadata(path, isbn10, isbn13, metadata_json)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                isbn10=excluded.isbn10,
                isbn13=excluded.isbn13,
                metadata_json=excluded.metadata_json
        ''', (path, isbn10, isbn13, md))
        self._conn.commit()

    def get_by_path(self, path: str) -> Optional[Dict]:
        cur = self._conn.cursor()
        cur.execute('SELECT metadata_json FROM metadata WHERE path = ?', (path,))
        row = cur.fetchone()
        if not row:
            return None
        return json.loads(row[0])

    def find_by_isbn(self, isbn: str) -> Optional[Dict]:
        if not isbn:
            return None
        isbn_clean = isbn.replace('-', '').strip()
        cur = self._conn.cursor()
        cur.execute('SELECT metadata_json FROM metadata WHERE isbn10 = ? OR isbn13 = ? LIMIT 1', (isbn_clean, isbn_clean))
        row = cur.fetchone()
        if not row:
            return None
        return json.loads(row[0])

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass


__all__ = ['MetadataCache']
