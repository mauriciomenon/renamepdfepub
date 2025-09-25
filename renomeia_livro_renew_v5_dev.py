"""Refactored (dev) version of renomeia_livro_renew_v5.py.
This file mirrors the main CLI behavior but is modular and safer for iterative refactors.
It intentionally avoids heavy top-level imports and delegates work to helper modules.
"""
import argparse
import logging
from pathlib import Path
from logging_config import configure_logging

from metadata_extractor import extract_from_pdf, extract_from_epub, extract_from_amazon_html
from metadata_enricher import enrich_by_isbn
from renamer import dry_run, apply_changes
from metadata_cache import MetadataCache


def process_path(p: Path):
    ext = p.suffix.lower()
    if ext == '.pdf':
        return {'path': str(p), 'metadata': extract_from_pdf(str(p))}
    if ext == '.epub':
        return {'path': str(p), 'metadata': extract_from_epub(str(p))}
    if ext in ('.html', '.htm'):
        return {'path': str(p), 'metadata': extract_from_amazon_html(str(p))}
    return {'path': str(p), 'metadata': {}}


def scan_directory(root: Path, recursive: bool = False):
    out = []
    for entry in sorted(root.iterdir()):
        if entry.is_dir() and recursive:
            out.extend(scan_directory(entry, recursive))
        elif entry.is_file() and entry.suffix.lower() in ('.pdf', '.epub', '.html', '.htm'):
            out.append(process_path(entry))
    return out


def main():
    parser = argparse.ArgumentParser(description='(dev) Extract and propose renames')
    parser.add_argument('directory', nargs='?', default='.', help='Directory to scan')
    parser.add_argument('-r', '--recursive', action='store_true', help='Recurse into subdirectories')
    parser.add_argument('--apply', action='store_true', help='Apply renames')
    parser.add_argument('--copy', action='store_true', help='Copy instead of rename')
    parser.add_argument('--pattern', default='{publisher}_{year}_{title}_{author}_{isbn}', help='Naming pattern')
    args = parser.parse_args()

    configure_logging()
    logger = logging.getLogger(__name__)

    root = Path(args.directory)
    logger.info('Scanning %s (recursive=%s)', root, args.recursive)
    cache = MetadataCache('metadata_cache.db')
    report = scan_directory(root, recursive=args.recursive)
    # upsert into cache and consult cache when extraction is empty
    for entry in report:
        md = entry.get('metadata') or {}
        # if no useful metadata, try cache
        if not any(md.get(k) for k in ('isbn10', 'isbn13', 'title')):
            # try lookup by filename in cache
            cached = cache.get_by_path(entry['path'])
            if cached:
                entry['metadata'] = cached
                continue
        # otherwise, upsert what we have
        cache.upsert(entry['path'], md)

    logger.info('Found %d files', len(report))

    # try to enrich where possible
    for entry in report:
        meta = entry.get('metadata') or {}
        if not meta.get('isbn10') and not meta.get('isbn13'):
            # nothing to enrich
            continue
        isbn = meta.get('isbn10') or meta.get('isbn13')
        enrich = enrich_by_isbn(isbn)
        if enrich:
            # merge fields conservatively
            for k, v in enrich.items():
                if not meta.get(k):
                    meta[k] = v

    # write proposals
    import json
    report_file = root / 'metadata_report_dev.json'
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    logger.info('Wrote report to %s', report_file)

    proposals = dry_run(str(report_file), args.pattern)
    logger.info('Proposals: %d', len(proposals))
    for s, d in proposals[:20]:
        logger.info('%s -> %s', s, d)

    if args.apply:
        res = apply_changes(proposals, copy=args.copy)
        for r in res:
            logger.info('%s', r)
    cache.close()


if __name__ == '__main__':
    main()
