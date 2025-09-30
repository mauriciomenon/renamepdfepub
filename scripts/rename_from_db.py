#!/usr/bin/env python3
"""
Rename a single file based on metadata stored in metadata_cache.db.

Usage:
  Dry-run (preview):
    python3 scripts/rename_from_db.py --file "/path/to/file.pdf"

  Apply rename with custom pattern:
    python3 scripts/rename_from_db.py --file "/path/to/file.pdf" --apply --pattern "{publisher}_{year}_{title}"

Placeholders in pattern: {title}, {author}, {year}, {publisher}, {isbn}
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import unicodedata
from pathlib import Path


def _clean_string(s: str, underscore: bool = False) -> str:
    s = unicodedata.normalize('NFKD', s)
    s = s.encode('ASCII', 'ignore').decode('ASCII')
    # allow alnum, space, dash and underscore
    out = ''.join(ch if (ch.isalnum() or ch in (' ', '-', '_')) else ' ' for ch in s)
    out = ' '.join(out.split())
    if underscore:
        out = out.replace(' ', '_')
    return out.strip()


def _first_two_authors(authors: str) -> str:
    parts = [a.strip() for a in (authors or '').split(',') if a.strip()]
    return ', '.join(parts[:2]) if parts else ''


def main() -> int:
    p = argparse.ArgumentParser(description='Rename a single file from DB metadata')
    p.add_argument('--db', default='metadata_cache.db', help='Path to SQLite DB')
    p.add_argument('--file', required=True, help='Path to the file to rename')
    p.add_argument('--pattern', default='{title} - {author} - {year}', help='Filename pattern')
    p.add_argument('--apply', action='store_true', help='Apply rename (otherwise preview)')
    p.add_argument('--underscore', action='store_true', help='Replace spaces with underscores')
    args = p.parse_args()

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"[ERROR] File not found: {file_path}")
        return 1

    db = Path(args.db)
    if not db.exists():
        print(f"[ERROR] DB not found: {db}")
        return 1

    with sqlite3.connect(str(db)) as conn:
        row = conn.execute(
            """
            SELECT title, authors, publisher, published_date, COALESCE(isbn_13, isbn_10) AS isbn
            FROM metadata_cache
            WHERE file_path = ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (str(file_path),)
        ).fetchone()

    if not row:
        print("[ERROR] No metadata found for file in DB. Run scan first.")
        return 1

    title, authors, publisher, published, isbn = row
    title = '' if not title or str(title).lower() == 'unknown' else str(title)
    authors = '' if not authors or str(authors).lower() == 'unknown' else str(authors)
    publisher = '' if not publisher or str(publisher).lower() == 'unknown' else str(publisher)
    year = ''
    if published:
        published = str(published)
        year = published.split('-')[0] if '-' in published else published
    author_display = _first_two_authors(authors)

    # Build new base name
    new_base = args.pattern.format(
        title=_clean_string(title, underscore=args.underscore),
        author=_clean_string(author_display, underscore=args.underscore),
        year=_clean_string(year, underscore=args.underscore),
        publisher=_clean_string(publisher, underscore=args.underscore),
        isbn=_clean_string(isbn or '', underscore=args.underscore),
    ).strip()
    if not new_base:
        print("[ERROR] Pattern produced empty name.")
        return 1

    # Assemble target path
    ext = file_path.suffix
    target = file_path.with_name(new_base + ext)

    if target == file_path:
        print("[INFO] Filename already matches pattern; nothing to do.")
        return 0

    if not args.apply:
        print(f"[PREVIEW] {file_path.name} -> {target.name}")
        return 0

    # Apply rename safely
    if target.exists():
        # append incremental suffix
        i = 2
        while True:
            candidate = file_path.with_name(f"{new_base} ({i}){ext}")
            if not candidate.exists():
                target = candidate
                break
            i += 1
    try:
        os.rename(str(file_path), str(target))
        print(f"[RENAMED] {file_path.name} -> {target.name}")
        return 0
    except Exception as e:
        print(f"[ERROR] Rename failed: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())

