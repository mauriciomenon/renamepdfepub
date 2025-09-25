import json
from pathlib import Path

from renamer import dry_run, apply_changes


def test_dry_run_and_apply_copy(tmp_path):
    # create two dummy files
    f1 = tmp_path / "book1.pdf"
    f2 = tmp_path / "book2.epub"
    f1.write_text("x")
    f2.write_text("y")

    report = [
        {
            "path": str(f1),
            "metadata": {
                "title": "Title One",
                "authors": "A. Author",
                "publisher": "Pub",
                "year": "2020",
                "isbn10": "1234567890",
            },
        },
        {
            "path": str(f2),
            "metadata": {
                "title": "Second Book",
                "authors": "B. Writer",
                "publisher": "Pub2",
                "year": "2019",
                "isbn10": "0987654321",
            },
        },
    ]

    report_file = tmp_path / "report.json"
    report_file.write_text(json.dumps(report, ensure_ascii=False))

    proposals = dry_run(str(report_file), pattern="{publisher}_{year}_{title}_{author}_{isbn}")
    assert len(proposals) == 2

    # use copy to avoid moving actual test files
    res = apply_changes(proposals, copy=True)
    # check all files copied
    assert all(r[2] in ('copied',) for r in res)
    # destination files should exist
    for _, dst, _ in res:
        assert Path(dst).exists()
