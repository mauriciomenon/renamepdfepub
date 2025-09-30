#!/usr/bin/env python3
"""
Apply batch renames from a CSV produced by preview (Arquivo,Proposto).

Usage:
  Dry-run (default):
    python3 scripts/apply_renames_from_csv.py --csv preview_renome.csv

  Apply renames:
    python3 scripts/apply_renames_from_csv.py --csv preview_renome.csv --apply

Behavior:
  - Validates that source file exists and proposed name is non-empty.
  - Applies conflict-safe renames (adds incremental suffix if target exists).
  - Skips rows with identical names (no-op).
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path


def _safe_rename(src: Path, dst: Path) -> Path:
    if not dst.exists():
        os.rename(str(src), str(dst))
        return dst
    base = dst.stem
    ext = dst.suffix
    i = 2
    while True:
        candidate = dst.with_name(f"{base} ({i}){ext}")
        if not candidate.exists():
            os.rename(str(src), str(candidate))
            return candidate
        i += 1


def main() -> int:
    p = argparse.ArgumentParser(description='Apply batch renames from CSV (Arquivo,Proposto)')
    p.add_argument('--csv', required=True, help='Path to CSV with columns Arquivo,Proposto')
    p.add_argument('--apply', action='store_true', help='Apply renames (otherwise dry-run)')
    args = p.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"[ERROR] CSV not found: {csv_path}")
        return 1

    rows = []
    with open(csv_path, 'r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        headers = [h.lower() for h in (reader.fieldnames or [])]
        # Accept both Portuguese and English headers fallback
        col_src = 'arquivo' if 'arquivo' in headers else 'file'
        col_dst = 'proposto' if 'proposto' in headers else 'proposed'
        if col_src not in headers or col_dst not in headers:
            print("[ERROR] CSV must contain columns: Arquivo,Proposto (or File,Proposed)")
            return 1
        for r in reader:
            rows.append({'src': r.get('Arquivo') or r.get('File') or '',
                         'dst': r.get('Proposto') or r.get('Proposed') or ''})

    changed = 0
    skipped = 0
    errors = 0
    for row in rows:
        src = Path(row['src'])
        dst_name = (row['dst'] or '').strip()
        if not src.exists() or not dst_name:
            skipped += 1
            continue
        dst = src.with_name(dst_name)
        if dst == src:
            skipped += 1
            continue
        if not args.apply:
            print(f"[PREVIEW] {src.name} -> {dst.name}")
            continue
        try:
            final_dst = _safe_rename(src, dst)
            print(f"[RENAMED] {src.name} -> {final_dst.name}")
            changed += 1
        except Exception as e:
            print(f"[ERROR] Failed to rename {src} -> {dst}: {e}")
            errors += 1

    if args.apply:
        print(f"Done. Renamed: {changed}, Skipped: {skipped}, Errors: {errors}")
    else:
        print(f"Dry-run. Candidates: {len(rows)}, Skipped: {skipped}")
    return 0 if errors == 0 else 1


if __name__ == '__main__':
    sys.exit(main())

