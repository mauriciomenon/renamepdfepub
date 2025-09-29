#!/usr/bin/env python3
"""
Basic performance sanity checks.

Keeps thresholds generous to avoid flakiness but ensures we do not regress
into very slow single-file processing on fallback path.
"""

import time
from pathlib import Path
import sys


def test_single_extraction_under_reasonable_time(tmp_path: Path):
    root = Path(__file__).parent.parent
    sys.path.insert(0, str(root / "src"))
    from renamepdfepub.metadata_extractor import extract_from_pdf  # type: ignore

    p = tmp_path / "Quick Check - Minimal (2019).pdf"
    p.write_bytes(b"%PDF-1.4\n%EOF\n")
    t0 = time.time()
    md = extract_from_pdf(str(p))
    dt = time.time() - t0
    assert dt < 1.5, f"single extraction too slow: {dt:.3f}s"
    assert md.get("title") == "Minimal"

