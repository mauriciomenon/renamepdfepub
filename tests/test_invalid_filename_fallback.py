#!/usr/bin/env python3
"""
Tests for filename-based fallback and guardrails against absurd data.

These tests create synthetic files and run the metadata extractor in a way
that exercises filename fallback without requiring PDF parsing libraries.
"""

from pathlib import Path
from typing import Dict, Optional
import sys


def test_fallback_from_filename_sanity(tmp_path: Path):
    root = Path(__file__).parent.parent
    sys.path.insert(0, str(root / "src"))
    from renamepdfepub.metadata_extractor import extract_from_pdf  # type: ignore

    # Absurd year like 8400 should not be used; no (19|20) pattern -> year None
    p1 = tmp_path / "Jane Doe - Fictional Book (8400).pdf"
    p1.write_bytes(b"%PDF-1.4\n%EOF\n")
    md1 = extract_from_pdf(str(p1))
    # Titulo deve conter o nome base, sem exigir remocao do sufixo fora do padrao
    assert md1.get("title") and "Fictional Book" in md1.get("title")
    assert md1.get("authors") in ("Jane Doe", None)
    # Ano absurdo nao deve ser aceito como ano valido
    assert md1.get("year") in (None, "2019", "2020", "2021")  # tolerante ao evoluir

    # Reasonable year should be captured
    p2 = tmp_path / "John Roe - Practical Guide (2017).pdf"
    p2.write_bytes(b"%PDF-1.4\n%EOF\n")
    md2 = extract_from_pdf(str(p2))
    assert md2.get("title") == "Practical Guide"
    assert md2.get("year") == "2017"

    # No year -> still get title
    p3 = tmp_path / "Alex Poe - Another Sample.pdf"
    p3.write_bytes(b"%PDF-1.4\n%EOF\n")
    md3 = extract_from_pdf(str(p3))
    assert md3.get("title") == "Another Sample"
    # authors optional depending on heuristic
