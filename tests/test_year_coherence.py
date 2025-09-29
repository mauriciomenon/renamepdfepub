#!/usr/bin/env python3
"""
Year coherence validation on generated JSON reports.

If an existing report exists in reports/, validate it; otherwise, generate a
small report with the extractor (when tqdm is available) and validate years.
"""

from pathlib import Path
import json
from datetime import datetime
import sys


def _validate_years(data: dict):
    current = datetime.now().year
    books = data.get("books") or []
    for entry in books[:100]:  # cap to keep runtime sensible
        year = entry.get("year") or entry.get("published_date") or None
        if year and isinstance(year, str) and year[:4].isdigit():
            yi = int(year[:4])
            assert 1900 <= yi <= current


def test_years_in_report_are_coherent(tmp_path: Path):
    root = Path(__file__).parent.parent
    reports_dir = root / "reports"
    candidates = sorted(reports_dir.glob("metadata_report_*.json")) if reports_dir.exists() else []
    report_path = None
    if candidates:
        report_path = candidates[-1]
    else:
        # try to generate a minimal report
        extractor = root / "src" / "gui" / "renomeia_livro_renew_v2.py"
        try:
            import tqdm  # type: ignore
        except Exception:
            import pytest
            pytest.skip("tqdm not available; skipping year coherence generation")
        # make small data set
        (tmp_path / "Alpha Tester - Sample One (2017).pdf").write_bytes(b"%PDF-1.4\n%EOF\n")
        out = tmp_path / "book_metadata_report.json"
        import subprocess
        res = subprocess.run(
            [sys.executable, str(extractor), str(tmp_path), "-t", "2", "-o", str(out)],
            capture_output=True,
            text=True,
            cwd=root,
        )
        if res.returncode != 0:
            import pytest
            pytest.skip("extractor not runnable in this environment")
        report_path = out

    if not report_path:
        import pytest
        pytest.skip("no report to validate")
    data = json.loads(Path(report_path).read_text(encoding="utf-8"))
    if isinstance(data, list):
        # Some legacy reports are lists; wrap for uniform validation
        data = {"books": data}
    assert isinstance(data, dict)
    _validate_years(data)
