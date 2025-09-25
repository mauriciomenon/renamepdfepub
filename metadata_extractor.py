"""Simple metadata extractor for PDF, EPUB and HTML pages (Amazon). 
Focus: title, subtitle, authors, publisher, year, isbn10, isbn13

This is a small, robust implementation intended to be used by the project's CLI.
"""
from __future__ import annotations

import re
import os
import json
from typing import Dict, Optional

# PDF handling
try:
    import pdfplumber
except Exception:
    pdfplumber = None

# Prefer modern 'pypdf' package (replacement for PyPDF2). Fall back to PyPDF2 if
# pypdf isn't available. We expose a PdfReader symbol compatible with both.
PdfReader = None
try:
    # pypdf uses the same API name PdfReader
    from pypdf import PdfReader as _PdfReader  # type: ignore
    PdfReader = _PdfReader
except Exception:
    try:
        import PyPDF2  # type: ignore
        PdfReader = PyPDF2.PdfReader
    except Exception:
        PdfReader = None

# EPUB handling
try:
    from ebooklib import epub
except Exception:
    epub = None

# HTML parsing
try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None

ISBN13_RE = re.compile(r'(97[89][\d\- ]{10,17}[\dXx])')
ISBN10_RE = re.compile(r'(?<!\d)(\d{9}[\dXx])(?!\d)')

def normalize_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def extract_from_epub(path: str) -> Dict[str, Optional[str]]:
    result = {k: None for k in ['title', 'subtitle', 'authors', 'publisher', 'year', 'isbn10', 'isbn13']}
    if epub is None:
        return result
    try:
        book = epub.read_epub(path)
        md = book.get_metadata('DC', 'title')
        if md:
            title = str(md[0][0])
            if ':' in title:
                parts = title.split(':', 1)
                result['title'] = normalize_spaces(parts[0])
                result['subtitle'] = normalize_spaces(parts[1])
            else:
                result['title'] = normalize_spaces(title)
        creators = book.get_metadata('DC', 'creator')
        if creators:
            result['authors'] = ', '.join([str(c[0]) for c in creators])
        pub = book.get_metadata('DC', 'publisher')
        if pub:
            result['publisher'] = str(pub[0][0])
        dates = book.get_metadata('DC', 'date')
        if dates:
            result['year'] = str(dates[0][0])[:4]
        ids = book.get_metadata('DC', 'identifier')
        if ids:
            # try to find ISBN within identifier
            for ident in ids:
                txt = str(ident[0])
                m13 = ISBN13_RE.search(txt)
                if m13:
                    result['isbn13'] = re.sub(r'[^0-9Xx]', '', m13.group(1))
                m10 = ISBN10_RE.search(txt)
                if m10:
                    result['isbn10'] = m10.group(1)
    except Exception:
        pass
    return result


def extract_from_pdf(path: str, pages_to_scan: int = 7) -> Dict[str, Optional[str]]:
    result = {k: None for k in ['title', 'subtitle', 'authors', 'publisher', 'year', 'isbn10', 'isbn13']}
    text = ''
    # prefer pdfplumber if available
    try:
        if pdfplumber:
            with pdfplumber.open(path) as pdf:
                for p in pdf.pages[:pages_to_scan]:
                    t = p.extract_text() or ''
                    text += '\n' + t
        elif PdfReader:
            with open(path, 'rb') as f:
                reader = PdfReader(f)
                for p in reader.pages[:pages_to_scan]:
                    # pypdf and PyPDF2 expose extract_text on page objects
                    t = p.extract_text() or ''
                    text += '\n' + t
        else:
            return result
    except Exception:
        # fallback: try PyPDF2 if pdfplumber failed
        try:
            if PdfReader:
                with open(path, 'rb') as f:
                    reader = PdfReader(f)
                    for p in reader.pages[:pages_to_scan]:
                        t = p.extract_text() or ''
                        text += '\n' + t
        except Exception:
            return result

    # Normalize
    cleaned = normalize_spaces(text)

    # ISBN
    m13 = ISBN13_RE.search(cleaned)
    if m13:
        result['isbn13'] = re.sub(r'[^0-9Xx]', '', m13.group(1))
    else:
        m10 = ISBN10_RE.search(cleaned)
        if m10:
            result['isbn10'] = m10.group(1)

    # Title heuristics: first line with >4 chars
    lines = [ln.strip() for ln in cleaned.split('\n') if ln.strip()]
    if lines:
        if len(lines[0]) > 5:
            # try split title/subtitle by ':' or ' - '
            first = lines[0]
            if ':' in first:
                parts = first.split(':', 1)
                result['title'] = normalize_spaces(parts[0])
                result['subtitle'] = normalize_spaces(parts[1])
            elif ' - ' in first:
                parts = first.split(' - ', 1)
                result['title'] = normalize_spaces(parts[0])
                result['subtitle'] = normalize_spaces(parts[1])
            else:
                result['title'] = normalize_spaces(first)
        # try to find author after title (line that contains 'by ')
        for line in lines[:10]:
            m = re.search(r'by\s+([A-Za-z0-9\,\.\-\s]+)', line, re.I)
            if m:
                result['authors'] = normalize_spaces(m.group(1))
                break

    # Publisher and year
    m = re.search(r'Published by\s+([^\n,]+)', cleaned, re.I)
    if m:
        result['publisher'] = normalize_spaces(m.group(1))
    m = re.search(r'(\b\d{4}\b)', cleaned)
    if m:
        result['year'] = m.group(1)

    return result


def extract_from_amazon_html(path_or_html: str, is_html: bool = False) -> Dict[str, Optional[str]]:
    """If is_html True, path_or_html is an HTML string; otherwise treat as file path and read file."""
    result = {k: None for k in ['title', 'subtitle', 'authors', 'publisher', 'year', 'isbn10', 'isbn13']}
    if BeautifulSoup is None:
        return result
    try:
        if is_html:
            html = path_or_html
        else:
            with open(path_or_html, 'r', encoding='utf-8', errors='ignore') as f:
                html = f.read()
        soup = BeautifulSoup(html, 'lxml')
        # Title
        title_tag = soup.find(id='productTitle') or soup.find('h1')
        if title_tag:
            title_text = normalize_spaces(title_tag.get_text())
            # Split title/subtitle
            if ':' in title_text:
                parts = title_text.split(':', 1)
                result['title'] = normalize_spaces(parts[0])
                result['subtitle'] = normalize_spaces(parts[1])
            else:
                result['title'] = title_text
        # Authors
        authors = soup.select('#bylineInfo span.author') or soup.select('.contributors a')
        if authors:
            names = [normalize_spaces(a.get_text()) for a in authors]
            result['authors'] = ', '.join(names)
        # Product details area for ISBN and publisher/year
        detail = soup.find(id='detailBullets_feature_div') or soup.find(id='productDetailsTable') or soup
        txt = normalize_spaces(detail.get_text()) if detail else ''
        m13 = ISBN13_RE.search(txt)
        if m13:
            result['isbn13'] = re.sub(r'[^0-9Xx]', '', m13.group(1))
        m10 = ISBN10_RE.search(txt)
        if m10:
            result['isbn10'] = m10.group(1)
        # publisher/year
        m = re.search(r'Publisher:\s*([^;\n\(]+)\s*\(?\s*(\d{4})?', txt, re.I)
        if m:
            result['publisher'] = normalize_spaces(m.group(1))
            if m.group(2):
                result['year'] = m.group(2)
    except Exception:
        pass
    return result


if __name__ == '__main__':
    # Quick smoke test
    import sys
    import logging
    from logging_config import configure_logging

    configure_logging()
    logger = logging.getLogger(__name__)

    p = sys.argv[1] if len(sys.argv) > 1 else None
    if not p:
        logger.info('metadata_extractor: pass path to pdf/epub/html to test')
        sys.exit(0)
    ext = os.path.splitext(p)[1].lower()
    if ext == '.epub':
        logger.info(json.dumps(extract_from_epub(p), indent=2, ensure_ascii=False))
    elif ext == '.pdf':
        logger.info(json.dumps(extract_from_pdf(p), indent=2, ensure_ascii=False))
    elif ext in ('.html', '.htm'):
        logger.info(json.dumps(extract_from_amazon_html(p), indent=2, ensure_ascii=False))
    else:
        # try as HTML content
        logger.info(json.dumps(extract_from_amazon_html(p, is_html=True), indent=2, ensure_ascii=False))
