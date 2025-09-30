#!/usr/bin/env python3
"""
Update cache selectively (filtered) using the core MetadataFetcher.

Usage examples:
  - Dry-run on incomplete rows (no writes):
      python3 scripts/update_cache_filtered.py --only-incomplete --dry-run

  - Apply on low-confidence rows (< 0.7), up to 200 rows:
      python3 scripts/update_cache_filtered.py --low-confidence --confidence-threshold 0.7 --limit 200

Notes:
  - Only rows with ISBN-13/ISBN-10 are processed (others are skipped).
  - Requires core module to be importable from project root.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path


def _import_core():
    try:
        # If executed from project root with src/ available on sys.path
        from src.core.renomeia_livro import MetadataFetcher  # type: ignore
        from src.core.metadata_utils import normalize_authors  # type: ignore
        from src.core.normalization import canonical_publisher  # type: ignore
        return MetadataFetcher, normalize_authors, canonical_publisher
    except Exception:
        # Fallback: add src to path
        root = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(root / 'src'))
        from core.renomeia_livro import MetadataFetcher  # type: ignore
        from core.metadata_utils import normalize_authors  # type: ignore
        from core.normalization import canonical_publisher  # type: ignore
        return MetadataFetcher, normalize_authors, canonical_publisher


def _select_rows(conn: sqlite3.Connection, only_incomplete: bool, low_conf: bool, thr: float, limit: int):
    where = []
    if only_incomplete:
        where.append(
            "(title IS NULL OR title='' OR title='Unknown' "
            "OR authors IS NULL OR authors='' OR authors='Unknown' "
            "OR publisher IS NULL OR publisher='' OR publisher='Unknown' "
            "OR published_date IS NULL OR published_date='' OR published_date='Unknown')"
        )
    if low_conf:
        where.append("(confidence_score IS NULL OR confidence_score < ?)")
    sql = (
        "SELECT rowid, isbn_10, isbn_13, confidence_score "
        "FROM metadata_cache"
    )
    params = []
    if where:
        sql += " WHERE " + " AND ".join(where)
        if low_conf:
            params.append(float(thr))
    sql += " ORDER BY timestamp DESC LIMIT ?"
    params.append(int(limit))
    return conn.execute(sql, params).fetchall()


def main() -> int:
    p = argparse.ArgumentParser(description='Update cache selectively (filtered) using core MetadataFetcher')
    p.add_argument('--db', default='metadata_cache.db', help='Path to SQLite DB (default: metadata_cache.db)')
    grp = p.add_mutually_exclusive_group(required=True)
    grp.add_argument('--only-incomplete', action='store_true', help='Process rows with missing fields')
    grp.add_argument('--low-confidence', action='store_true', help='Process low-confidence rows')
    p.add_argument('--confidence-threshold', type=float, default=0.7, help='Threshold for low-confidence')
    p.add_argument('--limit', type=int, default=500, help='Max rows to process (default: 500)')
    p.add_argument('--dry-run', action='store_true', help='Show what would be updated without writing')
    args = p.parse_args()

    db = Path(args.db)
    if not db.exists():
        print(f"[ERROR] DB not found: {db}")
        return 1

    MetadataFetcher, normalize_authors, canonical_publisher = _import_core()

    with sqlite3.connect(str(db)) as conn:
        rows = _select_rows(conn, args.only_incomplete, args.low_confidence, args.confidence_threshold, args.limit)
        if not rows:
            print("No rows matched filters.")
            return 0
        print(f"Matched rows: {len(rows)}")

        if args.dry_run:
            to_show = rows[:10]
            for r in to_show:
                rid, isbn10, isbn13, conf = r
                print(f" rowid={rid} isbn13={isbn13} isbn10={isbn10} conf={conf}")
            if len(rows) > 10:
                print(f" ... and {len(rows)-10} more")
            return 0

        fetcher = MetadataFetcher()
        updated = 0
        for rid, isbn10, isbn13, conf in rows:
            isbn = isbn13 or isbn10
            if not isbn:
                continue  # skip rows without ISBN
            try:
                m = fetcher.fetch_metadata(isbn)
                if not m:
                    continue
                # Update only if improvement
                if conf is None or (m.confidence_score or 0) > float(conf or 0):
                    conn.execute(
                        """
                        UPDATE metadata_cache
                        SET title=?, authors=?, publisher=?, published_date=?, confidence_score=?, source=?, raw_json=?, timestamp=strftime('%s','now')
                        WHERE rowid=?
                        """,
                        (
                            m.title,
                            ', '.join(normalize_authors(m.authors)),
                            canonical_publisher(m.publisher),
                            m.published_date,
                            m.confidence_score,
                            m.source,
                            __import__('json').dumps(m.__dict__),
                            rid,
                        )
                    )
                    updated += 1
            except Exception as e:
                print(f"[WARN] Failed to update rowid={rid} ({isbn}): {e}")
                continue
        conn.commit()
        print(f"Updated: {updated}")
        return 0


if __name__ == '__main__':
    sys.exit(main())

