#!/usr/bin/env python3
import csv
import subprocess
import sys
from pathlib import Path


def test_apply_renames_from_csv(tmp_path: Path):
    # Create files
    f1 = tmp_path / 'a.pdf'
    f2 = tmp_path / 'x.pdf'
    f1.write_bytes(b'%PDF-1.4\n%EOF\n')
    f2.write_bytes(b'%PDF-1.4\n%EOF\n')
    # CSV mapping
    csv_path = tmp_path / 'map.csv'
    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Arquivo', 'Proposto'])
        w.writerow([str(f1), 'b.pdf'])
        w.writerow([str(f2), 'x.pdf'])  # identical => skip/no error

    script = Path(__file__).parent.parent / 'scripts' / 'apply_renames_from_csv.py'
    # Dry-run
    res = subprocess.run([sys.executable, str(script), '--csv', str(csv_path)], capture_output=True, text=True)
    assert res.returncode == 0
    assert '[PREVIEW]' in (res.stdout + res.stderr)
    # Apply
    res2 = subprocess.run([sys.executable, str(script), '--csv', str(csv_path), '--apply'], capture_output=True, text=True)
    assert res2.returncode == 0
    # Verify rename happened
    assert not f1.exists()
    assert (tmp_path / 'b.pdf').exists()

