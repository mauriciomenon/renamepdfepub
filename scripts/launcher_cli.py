#!/usr/bin/env python3
"""
Unified CLI launcher for RenamePDFEPUB (does not replace start_*.py).

Commands (wraps the canonical core + helpers):

  scan <dir> [options]                -> start_cli.py scan
  scan-cycles <dir> --cycles N [...]   -> start_cli.py scan-cycles
  rename-existing ...                  -> start_cli.py rename-existing
  rename-search <dir> [--rename]       -> start_cli.py rename-search
  rescan-cache                         -> start_cli.py scan --rescan-cache
  update-cache --confidence-threshold  -> start_cli.py scan --update-cache --confidence-threshold X
  normalize-publishers [--db DB] [--apply|--dry-run]
  web                                  -> start_web.py
  gui                                  -> start_gui.py
  streamlit                            -> streamlit run src/gui/streamlit_interface.py
  algorithms                           -> start_cli.py algorithms
  report-html --json FILE [--output OUT]

Examples:
  python3 scripts/launcher_cli.py scan books -r -t 8 -o out.json
  python3 scripts/launcher_cli.py scan-cycles books --cycles 3 -t 2
  python3 scripts/launcher_cli.py rescan-cache
  python3 scripts/launcher_cli.py update-cache --confidence-threshold 0.7
  python3 scripts/launcher_cli.py normalize-publishers --dry-run
  python3 scripts/launcher_cli.py streamlit
"""

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(args_list, cwd=None):
    return subprocess.call(args_list, cwd=cwd or ROOT)


def main():
    p = argparse.ArgumentParser(prog='launcher_cli', description='Unified CLI launcher for RenamePDFEPUB')
    sub = p.add_subparsers(dest='cmd', required=True)

    # scan
    sp = sub.add_parser('scan', help='Run scan via core pipeline')
    sp.add_argument('directory')
    sp.add_argument('-r', '--recursive', action='store_true')
    sp.add_argument('--subdirs', help='Comma-separated list of subdirectories to process')
    sp.add_argument('-t', '--threads', type=int, default=4)
    sp.add_argument('-o', '--output')
    sp.add_argument('--rename', action='store_true')

    # scan-cycles
    sc = sub.add_parser('scan-cycles', help='Run repeated scans')
    sc.add_argument('directory')
    sc.add_argument('--cycles', type=int, default=1)
    sc.add_argument('--time-seconds', type=int, default=0)
    sc.add_argument('-r', '--recursive', action='store_true')
    sc.add_argument('--subdirs', help='Comma-separated list of subdirectories to process')
    sc.add_argument('-t', '--threads', type=int, default=2)

    # rename-existing
    rexp = sub.add_parser('rename-existing', help='Rename using an existing JSON report')
    rexp.add_argument('--report', required=True)
    rexp.add_argument('--apply', action='store_true')
    rexp.add_argument('--copy', action='store_true')
    rexp.add_argument('--pattern')

    # rename-search
    rs = sub.add_parser('rename-search', help='Search + rename')
    rs.add_argument('directory')
    rs.add_argument('--rename', action='store_true', default=True)
    rs.add_argument('-r', '--recursive', action='store_true')
    rs.add_argument('-t', '--threads', type=int, default=4)

    # db-gaps (quick summary)
    dbg = sub.add_parser('db-gaps', help='Show counts of missing fields in DB')
    dbg.add_argument('--db', default='metadata_cache.db')
    # db-export
    dbe = sub.add_parser('db-export', help='Export filtered rows to CSV (stdout or file)')
    dbe.add_argument('--db', default='metadata_cache.db')
    dbe.add_argument('--title')
    dbe.add_argument('--author')
    dbe.add_argument('--publisher')
    dbe.add_argument('--year')
    dbe.add_argument('--only-isbn', action='store_true')
    dbe.add_argument('--only-incomplete', action='store_true')
    dbe.add_argument('--limit', type=int, default=1000)
    dbe.add_argument('--output', help='Write CSV to file instead of stdout')

    # maintenance
    sub.add_parser('rescan-cache', help='Reprocess entire cache (core)')
    uc = sub.add_parser('update-cache', help='Update low-confidence cache entries (core)')
    uc.add_argument('--confidence-threshold', type=float, default=0.7)

    # normalize publishers
    npb = sub.add_parser('normalize-publishers', help='Normalize publisher names in DB')
    mode = npb.add_mutually_exclusive_group(required=True)
    mode.add_argument('--apply', action='store_true')
    mode.add_argument('--dry-run', action='store_true')
    npb.add_argument('--db', default='metadata_cache.db')

    # web/gui/streamlit
    sub.add_parser('web', help='Launch web interface (menu)')
    sub.add_parser('gui', help='Launch desktop GUI')
    sub.add_parser('streamlit', help='Launch Streamlit interface directly')

    # algorithms
    sub.add_parser('algorithms', help='Run algorithm comparison suite')

    # report-html
    rh = sub.add_parser('report-html', help='Generate HTML from JSON report')
    rh.add_argument('--json', required=True)
    rh.add_argument('--output')

    args, extra = p.parse_known_args()
    start_cli = ROOT / 'start_cli.py'

    if args.cmd == 'scan':
        cmd = [sys.executable, str(start_cli), 'scan', args.directory]
        if args.recursive:
            cmd.append('-r')
        if args.subdirs:
            cmd += ['--subdirs', args.subdirs]
        cmd += ['-t', str(args.threads)]
        if args.output:
            cmd += ['-o', args.output]
        if args.rename:
            cmd.append('--rename')
        sys.exit(run(cmd + extra))

    if args.cmd == 'scan-cycles':
        cmd = [sys.executable, str(start_cli), 'scan-cycles', args.directory, '--cycles', str(args.cycles), '-t', str(args.threads)]
        if args.time_seconds and args.time_seconds > 0:
            cmd += ['--time-seconds', str(args.time_seconds)]
        if args.recursive:
            cmd.append('-r')
        if args.subdirs:
            cmd += ['--subdirs', args.subdirs]
        sys.exit(run(cmd + extra))

    if args.cmd == 'rename-existing':
        cmd = [sys.executable, str(start_cli), 'rename-existing', '--report', args.report]
        if args.apply:
            cmd.append('--apply')
        if args.copy:
            cmd.append('--copy')
        if args.pattern:
            cmd += ['--pattern', args.pattern]
        sys.exit(run(cmd + extra))

    if args.cmd == 'rename-search':
        cmd = [sys.executable, str(start_cli), 'rename-search', args.directory]
        if args.rename:
            cmd.append('--rename')
        if args.recursive:
            cmd.append('-r')
        if args.threads:
            cmd += ['-t', str(args.threads)]
        sys.exit(run(cmd + extra))

    if args.cmd == 'rescan-cache':
        cmd = [sys.executable, str(start_cli), 'scan', '--rescan-cache']
        sys.exit(run(cmd + extra))

    if args.cmd == 'update-cache':
        cmd = [sys.executable, str(start_cli), 'scan', '--update-cache', '--confidence-threshold', str(args.confidence_threshold)]
        sys.exit(run(cmd + extra))

    if args.cmd == 'normalize-publishers':
        script = ROOT / 'scripts' / 'normalize_publishers.py'
        cmd = [sys.executable, str(script), '--db', args.db]
        cmd.append('--apply' if args.apply else '--dry-run')
        sys.exit(run(cmd + extra))

    if args.cmd == 'web':
        sys.exit(run([sys.executable, str(ROOT / 'start_web.py')]))
    if args.cmd == 'gui':
        sys.exit(run([sys.executable, str(ROOT / 'start_gui.py')]))
    if args.cmd == 'streamlit':
        app = ROOT / 'src' / 'gui' / 'streamlit_interface.py'
        sys.exit(run([sys.executable, '-m', 'streamlit', 'run', str(app), '--server.address=localhost', '--browser.gatherUsageStats=false']))

    if args.cmd == 'algorithms':
        sys.exit(run([sys.executable, str(start_cli), 'algorithms']))

    if args.cmd == 'report-html':
        gen = ROOT / 'simple_report_generator.py'
        cmd = [sys.executable, str(gen), '--json', args.json]
        if args.output:
            cmd += ['--output', args.output]
        sys.exit(run(cmd + extra))

    if args.cmd == 'db-gaps':
        import sqlite3
        db = Path(args.db)
        if not db.exists():
            print(f"[ERROR] DB not found: {db}")
            return 1
        try:
            with sqlite3.connect(str(db)) as conn:
                cur = conn.cursor()
                def _count(sql: str) -> int:
                    cur.execute(sql)
                    return cur.fetchone()[0]
                total = _count("SELECT COUNT(*) FROM metadata_cache")
                missing_title = _count("SELECT COUNT(*) FROM metadata_cache WHERE title IS NULL OR title='' OR title='Unknown'")
                missing_auth = _count("SELECT COUNT(*) FROM metadata_cache WHERE authors IS NULL OR authors='' OR authors='Unknown'")
                missing_pub = _count("SELECT COUNT(*) FROM metadata_cache WHERE publisher IS NULL OR publisher='' OR publisher='Unknown'")
                missing_year = _count("SELECT COUNT(*) FROM metadata_cache WHERE published_date IS NULL OR published_date='' OR published_date='Unknown'")
                missing_isbn = _count("SELECT COUNT(*) FROM metadata_cache WHERE (COALESCE(isbn_13,'')='' AND COALESCE(isbn_10,'')='')")
            print("DB Gaps Summary:\n" \
                  f"  Total:        {total}\n" \
                  f"  No Title:     {missing_title}\n" \
                  f"  No Authors:   {missing_auth}\n" \
                  f"  No Publisher: {missing_pub}\n" \
                  f"  No Year:      {missing_year}\n" \
                  f"  No ISBN:      {missing_isbn}")
            return 0
        except Exception as e:
            print(f"[ERROR] Failed to query DB: {e}")
            return 1

    if args.cmd == 'db-export':
        import csv
        import sqlite3
        db = Path(args.db)
        if not db.exists():
            print(f"[ERROR] DB not found: {db}")
            return 1
        where = []
        params = []
        def like(field, value):
            where.append(f"{field} LIKE ?")
            params.append(f"%{value}%")
        if args.title:
            like('title', args.title)
        if args.author:
            like('authors', args.author)
        if args.publisher:
            like('publisher', args.publisher)
        if args.year:
            like('published_date', args.year)
        if args.only_isbn:
            where.append("(COALESCE(isbn_13,'') <> '' OR COALESCE(isbn_10,'') <> '')")
        if args.only_incomplete:
            where.append("(title IS NULL OR title='' OR publisher IS NULL OR publisher='' OR publisher='Unknown' OR authors IS NULL OR authors='' OR published_date IS NULL OR published_date='' OR published_date='Unknown')")
        sql = "SELECT isbn_13, isbn_10, title, authors, publisher, published_date, confidence_score, source, file_path, timestamp FROM metadata_cache"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY timestamp DESC LIMIT ?"
        params.append(int(args.limit))
        rows = []
        try:
            with sqlite3.connect(str(db)) as conn:
                rows = conn.execute(sql, params).fetchall()
        except Exception as e:
            print(f"[ERROR] DB query failed: {e}")
            return 1
        headers = ['ISBN-13', 'ISBN-10', 'Title', 'Authors', 'Publisher', 'Published', 'Confidence', 'Source', 'File', 'Timestamp']
        if args.output:
            with open(args.output, 'w', newline='', encoding='utf-8') as f:
                cw = csv.writer(f)
                cw.writerow(headers)
                cw.writerows(rows)
            print(f"Wrote {len(rows)} rows to {args.output}")
        else:
            cw = csv.writer(sys.stdout)
            cw.writerow(headers)
            cw.writerows(rows)
        return 0

    p.error('Unrecognized command')


if __name__ == '__main__':
    main()
