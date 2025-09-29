#!/usr/bin/env python3
"""
Golden-set accuracy tests using tiny synthetic PDFs with realistic filenames.

Checks that extractor returns minimal expected fields (title/author/year)
and that years are coherent when present.
"""

from pathlib import Path
import sys
from datetime import datetime


GOLDEN = [
    {
        "filename": "Shannon Bradshaw et al - MongoDB The Definitive Guide (2019).pdf",
        "title": "MongoDB The Definitive Guide",
        "author": "Shannon Bradshaw et al",
        "year": "2019",
    },
    {
        "filename": "Paul McFedries - Build a Website with CSS and HTML (2018).pdf",
        "title": "Build a Website with CSS and HTML",
        "author": "Paul McFedries",
        "year": "2018",
    },
    {
        "filename": "Jane Smith - Practical Python (2021).pdf",
        "title": "Practical Python",
        "author": "Jane Smith",
        "year": "2021",
    },
]


def _write_min_pdf(path: Path) -> None:
    path.write_bytes(b"%PDF-1.4\n%EOF\n")


def test_golden_minimal_fields(tmp_path: Path):
    root = Path(__file__).parent.parent
    sys.path.insert(0, str(root / "src"))
    from renamepdfepub.metadata_extractor import extract_from_pdf  # type: ignore

    current_year = datetime.now().year
    for item in GOLDEN:
        p = tmp_path / item["filename"]
        _write_min_pdf(p)
        md = extract_from_pdf(str(p))
        assert md.get("title") == item["title"]
        assert md.get("authors") in (item["author"], item["author"].replace(" et al", ""))
        y = md.get("year")
        assert y is not None and y.isdigit()
        yi = int(y)
        assert 1900 <= yi <= current_year

