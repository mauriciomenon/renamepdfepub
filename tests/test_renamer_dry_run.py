#!/usr/bin/env python3
"""
Covers renamer dry-run proposals using a synthetic report structure.
"""

from pathlib import Path
import json
import sys


def test_renamer_dry_run_proposals(tmp_path: Path):
    root = Path(__file__).parent.parent
    sys.path.insert(0, str(root / "src" / "renamepdfepub"))
    import renamer  # type: ignore

    # Create fake files
    f1 = tmp_path / "Alice - Data Science (2020).pdf"
    f2 = tmp_path / "Bob - Systems (2018).epub"
    f1.write_bytes(b"%PDF-1.4\n%EOF\n")
    f2.write_text("EPUB", encoding="utf-8")

    # Synthetic report compatible with renamer.dry_run expectations
    report = [
        {
            "path": str(f1),
            "metadata": {
                "title": "Data Science",
                "authors": "Alice",
                "publisher": "TestPub",
                "year": "2020",
                "isbn13": "9780000000000",
            },
        },
        {
            "path": str(f2),
            "metadata": {
                "title": "Systems",
                "authors": "Bob",
                "publisher": "Demo",
                "year": "2018",
            },
        },
    ]
    report_path = tmp_path / "synthetic_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    pattern = "{publisher}_{year}_{title}_{author}_{isbn}"
    proposals = renamer.dry_run(str(report_path), pattern)
    assert isinstance(proposals, list) and len(proposals) == 2
    # Ensure resulting names contain meaningful parts and the same suffix
    src0, dst0 = proposals[0]
    assert dst0.endswith(".pdf") and "Data Science" in dst0
    src1, dst1 = proposals[1]
    assert dst1.endswith(".epub") and "Systems" in dst1

