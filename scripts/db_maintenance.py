#!/usr/bin/env python3
"""
Lightweight DB maintenance for metadata_cache.db

Usage examples:
  - Stats: rows and last timestamp
      python3 scripts/db_maintenance.py --stats

  - Vacuum (compact) and backup
      python3 scripts/db_maintenance.py --vacuum --backup

Options:
  --db <path>    Path to DB (default: metadata_cache.db)
  --backup       Create timestamped copy alongside DB
  --vacuum       Run VACUUM
  --stats        Print summary (tables/rows/last timestamp)
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import time
from pathlib import Path


def do_backup(db: Path) -> Path:
    ts = time.strftime('%Y%m%d_%H%M%S')
    bkp = db.with_suffix(f".db.bak_{ts}")
    shutil.copy2(db, bkp)
    print(f"Backup: {bkp}")
    return bkp


def do_vacuum(conn: sqlite3.Connection) -> None:
    conn.execute('VACUUM')
    print("VACUUM done")


def do_stats(conn: sqlite3.Connection) -> None:
    try:
        cur = conn.cursor()
        total = cur.execute('SELECT COUNT(*) FROM metadata_cache').fetchone()[0]
        last = cur.execute('SELECT MAX(timestamp) FROM metadata_cache').fetchone()[0]
        print(f"Rows: {total}")
        print(f"Last timestamp: {last}")
    except Exception as e:
        print(f"[WARN] Stats failed: {e}")


def main() -> int:
    p = argparse.ArgumentParser(description='DB maintenance for metadata_cache.db')
    p.add_argument('--db', default='metadata_cache.db')
    p.add_argument('--backup', action='store_true')
    p.add_argument('--vacuum', action='store_true')
    p.add_argument('--stats', action='store_true')
    args = p.parse_args()

    db = Path(args.db)
    if not db.exists():
        print(f"[ERROR] DB not found: {db}")
        return 1
    if args.backup:
        do_backup(db)
    with sqlite3.connect(str(db)) as conn:
        if args.vacuum:
            do_vacuum(conn)
        if args.stats:
            do_stats(conn)
    if not (args.backup or args.vacuum or args.stats):
        print("No operation. Use --stats/--vacuum/--backup.")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

