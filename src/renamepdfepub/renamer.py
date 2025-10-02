"""Renamer that reads metadata reports and renames files.

Supports two JSON input formats:
- Legacy list format: a list of entries with fields: {
    'path': '/full/path/to/file.ext',
    'metadata': {'title': ..., 'authors': ..., 'publisher': ..., 'year': ..., 'isbn10': ..., 'isbn13': ...}
  }
- Scan combined report (dict) format: a dict with key 'successful_extractions',
  where each item contains fields like: title, authors, publisher, published_date,
  isbn_10, isbn_13, file_path. This is the report generated under reports/report_*.json.

The tool normalizes either format and generates rename proposals based on a pattern.
"""
import argparse
import json
import shutil
import re
import logging
from pathlib import Path
from typing import List, Tuple, Dict, Any
try:
    from .logging_config import configure_logging
except Exception:  # pragma: no cover - fallback for direct module import
    try:
        from logging_config import configure_logging  # type: ignore
    except Exception:
        def configure_logging():  # type: ignore
            pass

INVALID_CHARS_RE = re.compile(r'[^\w\-\._ ]')
WHITESPACE_RE = re.compile(r"\s+")


def sanitize_name(s: str, max_len: int = 90) -> str:
    """Sanitize a string for filesystem-safe names.

    Removes disallowed characters, normalizes whitespace, and trims length.
    """
    if not s:
        return ''
    s = WHITESPACE_RE.sub(' ', s.strip())
    s = INVALID_CHARS_RE.sub('', s)
    return s[:max_len].strip()


def format_name(pattern: str, metadata: dict) -> str:
    """Format a file base name using placeholders and metadata.

    Placeholders: {title}, {author}, {publisher}, {year}, {isbn}
    """
    md = metadata.get('metadata', metadata)
    title = md.get('title') or ''
    authors = md.get('authors') or ''
    if isinstance(authors, list):
        authors = ', '.join([str(a) for a in authors if a])
    author = authors
    publisher = md.get('publisher') or ''
    year = md.get('year') or ''
    isbn = md.get('isbn10') or md.get('isbn13') or ''
    name = pattern.format(title=title, author=author, publisher=publisher, year=year, isbn=isbn)
    return sanitize_name(name)


def _from_scan_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize one successful_extractions item from scan JSON to legacy metadata dict."""
    md = {
        'title': item.get('title') or '',
        'authors': item.get('authors') or '',
        'publisher': item.get('publisher') or '',
        'year': (item.get('published_date') or '').split('-')[0],
        'isbn10': item.get('isbn_10') or '',
        'isbn13': item.get('isbn_13') or '',
    }
    return md


def load_report(report_path: str) -> List[Tuple[str, Dict[str, Any]]]:
    """Load report file and return a list of (path, metadata_dict) pairs.

    Accepts legacy list format or scan combined dict format.
    """
    data = json.loads(Path(report_path).read_text(encoding='utf-8'))
    items: List[Tuple[str, Dict[str, Any]]] = []
    if isinstance(data, list):
        # Legacy format
        for entry in data:
            p = entry.get('path')
            md = entry.get('metadata', {})
            if not p:
                continue
            items.append((p, md))
        return items
    if isinstance(data, dict) and 'successful_extractions' in data:
        for entry in data.get('successful_extractions', []) or []:
            fp = entry.get('file_path')
            if not fp:
                # As fallback, try to resolve from filename in same directory
                fn = entry.get('filename')
                if fn:
                    # best-effort: search under project root (parent of reports)
                    try:
                        rp = Path(report_path).resolve().parent
                        root = rp.parent
                        cand = None
                        for p in root.rglob(fn):
                            cand = p
                            break
                        if cand is None:
                            continue
                        fp = str(cand)
                    except Exception:
                        continue
                else:
                    continue
            md = _from_scan_item(entry)
            items.append((fp, md))
        return items
    # Unknown format
    raise ValueError("Unsupported report format: expected list or dict with 'successful_extractions'.")


def dry_run(report_path: str, pattern: str) -> List[Tuple[str, str]]:
    """Create rename proposals from report without modifying files."""
    pairs = load_report(report_path)
    proposals: List[Tuple[str, str]] = []
    for src, md in pairs:
        p = Path(src)
        newbase = format_name(pattern, {'metadata': md})
        if not newbase:
            continue
        dst = str(p.with_name(newbase + p.suffix))
        proposals.append((str(p), dst))
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
