"""CLI to walk a directory and extract metadata using metadata_extractor.py
Generates a JSON report with one entry per file.
"""
import argparse
import json
import logging
from pathlib import Path
from metadata_extractor import extract_from_pdf, extract_from_epub, extract_from_amazon_html
from logging_config import configure_logging


def process_file(path: str) -> dict:
    ext = Path(path).suffix.lower()
    if ext == '.pdf':
        return {'path': path, 'metadata': extract_from_pdf(path)}
    if ext == '.epub':
        return {'path': path, 'metadata': extract_from_epub(path)}
    if ext in ('.html', '.htm'):
        return {'path': path, 'metadata': extract_from_amazon_html(path)}
    # fallback: no extraction
    return {'path': path, 'metadata': {}}


def walk_and_extract(root: str, recursive: bool = False):
    results = []
    for entry in sorted(Path(root).iterdir()):
        if entry.is_dir() and recursive:
            results.extend(walk_and_extract(str(entry), recursive))
        elif entry.is_file():
            if entry.suffix.lower() in ('.pdf', '.epub', '.html', '.htm'):
                results.append(process_file(str(entry)))
    return results


def main():
    parser = argparse.ArgumentParser(description='Extract metadata from PDFs/EPUBs/HTML')
    parser.add_argument('directory', nargs='?', default='.', help='Directory to scan')
    parser.add_argument('-r', '--recursive', action='store_true', help='Recurse into subdirectories')
    parser.add_argument('-o', '--output', default='metadata_report.json', help='Output JSON file')
    args = parser.parse_args()

    configure_logging()
    logger = logging.getLogger(__name__)

    results = walk_and_extract(args.directory, recursive=args.recursive)
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    logger.info('Wrote %d entries to %s', len(results), args.output)


if __name__ == '__main__':
    main()
