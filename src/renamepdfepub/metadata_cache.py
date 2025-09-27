"""SQLite-backed metadata cache with performance optimizations.
Provides upsert/get/find_by_isbn utilities. Lightweight and safe for unit tests.
Performance features: connection pooling, optimized PRAGMAs, batch operations.
"""
import sqlite3
import json
from typing import Optional, Dict, List
import threading


class MetadataCache:
    def __init__(self, db_path: str = 'metadata_cache.db'):
        self.db_path = db_path
        self._local = threading.local()
        self._ensure_table()

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local connection with optimized PRAGMAs."""
        if not hasattr(self._local, 'conn'):
            self._local.conn = sqlite3.connect(self.db_path)
            # Performance optimizations
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA synchronous=NORMAL")
            self._local.conn.execute("PRAGMA cache_size=10000")
            self._local.conn.execute("PRAGMA temp_store=memory")
            self._local.conn.execute("PRAGMA mmap_size=268435456")  # 256MB
        return self._local.conn

    def _ensure_table(self):
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute('''
        CREATE TABLE IF NOT EXISTS metadata (
            path TEXT PRIMARY KEY,
            isbn10 TEXT,
            isbn13 TEXT,
            metadata_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        # Create indexes for performance
        cur.execute('CREATE INDEX IF NOT EXISTS idx_isbn10 ON metadata(isbn10)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_isbn13 ON metadata(isbn13)')
        cur.execute('CREATE INDEX IF NOT EXISTS idx_updated_at ON metadata(updated_at)')
        conn.commit()

    def upsert(self, path: str, metadata: Dict) -> None:
        """Insert or update metadata for a file path."""
        isbn10 = metadata.get('isbn10') or None
        isbn13 = metadata.get('isbn13') or None
        md = json.dumps(metadata, ensure_ascii=False)
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO metadata(path, isbn10, isbn13, metadata_json, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(path) DO UPDATE SET
                isbn10=excluded.isbn10,
                isbn13=excluded.isbn13,
                metadata_json=excluded.metadata_json,
                updated_at=CURRENT_TIMESTAMP
        ''', (path, isbn10, isbn13, md))
        conn.commit()

    def batch_upsert(self, items: List[tuple]) -> None:
        """Batch insert/update for better performance with many records."""
        if not items:
            return
        conn = self._get_connection()
        cur = conn.cursor()
        cur.executemany('''
            INSERT INTO metadata(path, isbn10, isbn13, metadata_json, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(path) DO UPDATE SET
                isbn10=excluded.isbn10,
                isbn13=excluded.isbn13,
                metadata_json=excluded.metadata_json,
                updated_at=CURRENT_TIMESTAMP
        ''', items)
        conn.commit()

    def get_by_path(self, path: str) -> Optional[Dict]:
        """Get metadata by file path."""
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute('SELECT metadata_json FROM metadata WHERE path = ?', (path,))
        row = cur.fetchone()
        if not row:
            return None
        return json.loads(row[0])

    def find_by_isbn(self, isbn: str) -> Optional[Dict]:
        """Find metadata by ISBN (10 or 13 digit)."""
        if not isbn:
            return None
        isbn_clean = isbn.replace('-', '').strip()
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute(
            'SELECT metadata_json FROM metadata WHERE isbn10 = ? OR isbn13 = ? LIMIT 1',
            (isbn_clean, isbn_clean),
        )
        row = cur.fetchone()
        if not row:
            return None
        return json.loads(row[0])

    def cleanup_old_entries(self, days: int = 30) -> int:
        """Remove entries older than specified days. Returns count of deleted rows."""
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute('''
            DELETE FROM metadata 
            WHERE updated_at < datetime('now', '-{} days')
        '''.format(days))
        deleted = cur.rowcount
        conn.commit()
        return deleted

    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM metadata')
        total = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM metadata WHERE isbn10 IS NOT NULL OR isbn13 IS NOT NULL')
        with_isbn = cur.fetchone()[0]
        return {'total_entries': total, 'entries_with_isbn': with_isbn}

    def close(self):
        """Close thread-local connections."""
        if hasattr(self._local, 'conn'):
            try:
                self._local.conn.close()
            except Exception:
                pass


__all__ = ['MetadataCache']
