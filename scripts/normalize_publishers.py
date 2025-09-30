#!/usr/bin/env python3
"""
Normalize publisher names in metadata_cache.db.

Usage:
  python3 scripts/normalize_publishers.py --apply [--db metadata_cache.db]
  python3 scripts/normalize_publishers.py --dry-run [--db metadata_cache.db]

Behavior:
- Standardizes common variants (Casa do Código, Manning, O'Reilly, Novatec, Alta Books, Packt, etc.).
- Replaces case-insensitive 'unknown' with empty string.
- Creates a timestamped backup of the DB before applying changes.
"""

import argparse
import shutil
import sqlite3
import sys
import time
from pathlib import Path
try:
    from src.core.normalization import canonical_publisher as _canon
except Exception:
    # Fallback when executed from project root
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from core.normalization import canonical_publisher as _canon


def normalize_name(name: str) -> str:
    return _canon(name)


def main() -> int:
    p = argparse.ArgumentParser(description='Normalize publishers in metadata_cache.db')
    p.add_argument('--db', default='metadata_cache.db', help='Path to SQLite DB (default: metadata_cache.db)')
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--apply', action='store_true', help='Apply changes to the database')
    mode.add_argument('--dry-run', action='store_true', help='Show what would change and exit')
    args = p.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"[ERROR] DB not found: {db_path}")
        return 1

    # Read current rows
    with sqlite3.connect(str(db_path)) as conn:
        cur = conn.execute("SELECT rowid, publisher FROM metadata_cache")
        rows = cur.fetchall()

    total = len(rows)
    to_update = []
    for rowid, pub in rows:
        current = pub or ''
        canon = normalize_name(current)
        if canon != current:
            to_update.append((rowid, current, canon))

    print(f"Total rows: {total}")
    print(f"To update: {len(to_update)}")

    # Show a brief sample of planned changes
    for rowid, old, new in to_update[:20]:
        print(f" - rowid={rowid}: '{old}' -> '{new}'")
    if len(to_update) > 20:
        print(f" ... and {len(to_update) - 20} more")

    if args.dry_run:
        return 0

    # Backup DB
    backup = db_path.with_suffix(f".db.bak_{time.strftime('%Y%m%d_%H%M%S')}")
    shutil.copy2(db_path, backup)
    print(f"Backup created: {backup}")

    # Apply updates
    changed = 0
    with sqlite3.connect(str(db_path)) as conn:
        for rowid, old, new in to_update:
            conn.execute("UPDATE metadata_cache SET publisher=? WHERE rowid=?", (new, rowid))
            changed += 1
        conn.commit()

    print(f"Updated rows: {changed}")
    print("Done.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
