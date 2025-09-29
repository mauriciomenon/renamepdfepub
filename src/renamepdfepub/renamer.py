"""Renamer that reads the JSON report produced by extractor_cli.py and renames files.
Supports --dry-run and --copy.
"""
import argparse
import json
import shutil
import re
import logging
from pathlib import Path
try:
    from .logging_config import configure_logging
except Exception:  # pragma: no cover - fallback for direct module import
    try:
        from logging_config import configure_logging  # type: ignore
    except Exception:
        def configure_logging():  # type: ignore
            pass

INVALID_CHARS_RE = re.compile(r'[^\w\-\._ ]')


def sanitize_name(s: str, max_len: int = 90) -> str:
    if not s:
        return ''
    s = s.strip()
    s = INVALID_CHARS_RE.sub('', s)
    return s[:max_len].strip()


def format_name(pattern: str, metadata: dict) -> str:
    # prepare fields
    title = metadata.get('title') or metadata.get('metadata', {}).get('title') or ''
    author = metadata.get('authors') or metadata.get('metadata', {}).get('authors') or ''
    publisher = metadata.get('publisher') or metadata.get('metadata', {}).get('publisher') or ''
    year = metadata.get('year') or metadata.get('metadata', {}).get('year') or ''
    isbn = metadata.get('isbn10') or metadata.get('metadata', {}).get('isbn10') or metadata.get('isbn13') or metadata.get('metadata', {}).get('isbn13') or ''
    # pattern placeholders
    name = pattern.format(title=title, author=author, publisher=publisher, year=year, isbn=isbn)
    return sanitize_name(name)


def dry_run(report_path: str, pattern: str):
    with open(report_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    proposals = []
    for entry in data:
        p = Path(entry['path'])
        meta = entry.get('metadata', {})
        newbase = format_name(pattern, {'metadata': meta})
        if not newbase:
            continue
        newname = newbase + p.suffix
        proposals.append((str(p), str(p.with_name(newname))))
    return proposals


def apply_changes(proposals, copy=False):
    results = []
    for src, dst in proposals:
        srcp = Path(src)
        dstp = Path(dst)
        if dstp.exists():
            results.append((src, dst, 'exists'))
            continue
        try:
            if copy:
                shutil.copy(src, dst)
                results.append((src, dst, 'copied'))
            else:
                srcp.rename(dstp)
                results.append((src, dst, 'renamed'))
        except Exception as e:
            results.append((src, dst, f'error: {e}'))
    return results


def main():
    parser = argparse.ArgumentParser(description='Rename files according to metadata report')
    parser.add_argument('report', help='JSON report produced by extractor_cli.py')
    parser.add_argument(
        '--pattern',
        default='{publisher}_{year}_{title}_{author}_{isbn}',
        help='Naming pattern',
    )
    parser.add_argument('--dry-run', action='store_true', default=False, help='Only show proposals (use --apply to perform)')
    parser.add_argument('--apply', action='store_true', help='Apply renaming')
    parser.add_argument('--copy', action='store_true', help='Copy files instead of rename')
    args = parser.parse_args()

    configure_logging()
    logger = logging.getLogger(__name__)

    proposals = dry_run(args.report, args.pattern)
    logger.info('Proposals: %d', len(proposals))
    for src, dst in proposals[:50]:
        logger.info('%s -> %s', src, dst)

    if args.apply:
        res = apply_changes(proposals, copy=args.copy)
        logger.info('Results:')
        for r in res:
            logger.info('%s', r)


if __name__ == '__main__':
    main()
