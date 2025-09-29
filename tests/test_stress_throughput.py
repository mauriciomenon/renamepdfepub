#!/usr/bin/env python3
"""
Stress test for throughput (marked slow).

Generates N synthetic PDFs and measures total extraction time. Thresholds are
generous to avoid flakiness and to serve as regression guardrails.
"""

from pathlib import Path
import time
import sys
import pytest


@pytest.mark.slow
def test_throughput_synthetic_batch(tmp_path: Path):
    root = Path(__file__).parent.parent
    sys.path.insert(0, str(root / "src"))
    from renamepdfepub.metadata_extractor import extract_from_pdf  # type: ignore

    N = 120
    for i in range(N):
        (tmp_path / f"User {i} - Book {i} (2019).pdf").write_bytes(b"%PDF-1.4\n%EOF\n")

    t0 = time.time()
    cnt = 0
    for p in tmp_path.glob("*.pdf"):
        _ = extract_from_pdf(str(p))
        cnt += 1
    dt = time.time() - t0

    assert cnt == N
    # Total time upper bound (very generous)
    assert dt < 25.0, f"batch extraction too slow: {dt:.2f}s for {N} files"

