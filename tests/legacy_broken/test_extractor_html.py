from renamepdfepub.metadata_extractor import extract_from_amazon_html
from pathlib import Path


def test_extract_from_existing_report_html():
    html_path = Path('reports/metadata_report_20241125_165155.html')
    assert html_path.exists(), "Sample HTML report must exist for this test"
    out = extract_from_amazon_html(str(html_path))
    # At minimum, we expect a title (heuristic)
    assert out is not None
    assert out.get('title') is not None
