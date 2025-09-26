"""Enrich metadata using OpenLibrary APIs (by ISBN) and simple fallbacks.
"""
import requests
import time
from typing import Dict, Optional

OPENLIB_URL_ISBN = 'https://openlibrary.org/api/books'


def enrich_by_isbn(isbn: str) -> Optional[Dict]:
    """Query OpenLibrary by ISBN (isbn may be 10 or 13). Returns dict with possible keys.
    Minimal retries and basic normalization.
    """
    if not isbn:
        return None
    isbn_clean = isbn.replace('-', '').strip()
    params = {
        'bibkeys': f'ISBN:{isbn_clean}',
        'format': 'json',
        'jscmd': 'data'
    }
    try:
        resp = requests.get(OPENLIB_URL_ISBN, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        key = f'ISBN:{isbn_clean}'
        if key not in data:
            return None
        rec = data[key]
        out = {}
        out['title'] = rec.get('title')
        # subtitle
        if 'subtitle' in rec:
            out['subtitle'] = rec.get('subtitle')
        # authors
        if 'authors' in rec:
            out['authors'] = ', '.join(a.get('name') for a in rec.get('authors', []) if a.get('name'))
        # publishers
        if 'publishers' in rec:
            out['publisher'] = ', '.join(p.get('name') for p in rec.get('publishers', []) if p.get('name'))
        # published date/year
        if 'publish_date' in rec:
            out['published_date'] = rec.get('publish_date')
            # try extract year
            import re
            m = re.search(r'(\d{4})', out['published_date'])
            if m:
                out['year'] = m.group(1)
        # isbn lists
        if 'identifiers' in rec:
            ids = rec.get('identifiers')
            # isbn_10 / isbn_13
            if 'isbn_10' in ids:
                out['isbn10'] = ids.get('isbn_10')[0]
            if 'isbn_13' in ids:
                out['isbn13'] = ids.get('isbn_13')[0]
        return out
    except Exception:
        # simple retry backoff
        try:
            time.sleep(1)
            resp = requests.get(OPENLIB_URL_ISBN, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            key = f'ISBN:{isbn_clean}'
            if key not in data:
                return None
            rec = data[key]
            out = {
                'title': rec.get('title')
            }
            return out
        except Exception:
            return None


if __name__ == '__main__':
    import sys
    import logging
    from .logging_config import configure_logging

    configure_logging()
    logger = logging.getLogger(__name__)

    if len(sys.argv) < 2:
        logger.error('usage: metadata_enricher.py <ISBN>')
        sys.exit(1)
    logger.info('%s', enrich_by_isbn(sys.argv[1]))
