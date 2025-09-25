from metadata_extractor import extract_from_amazon_html


def test_extract_from_report_html():
    # use one of the example reports in reports/ as a fixture
    path = 'reports/metadata_report_20241125_165155.html'
    res = extract_from_amazon_html(path)
    # this report contains an ISBN in previous runs; assert keys exist
    assert 'title' in res
    # we expect isbn10 or isbn13 possibly present
    assert 'isbn10' in res or 'isbn13' in res


def test_extract_from_pdf_missing_file_returns_structure():
    from metadata_extractor import extract_from_pdf

    # calling with a non-existing path should return the metadata dict structure
    res = extract_from_pdf('/path/does/not/exist.pdf')
    assert isinstance(res, dict)
    # keys should match expected schema
    for k in ['title', 'subtitle', 'authors', 'publisher', 'year', 'isbn10', 'isbn13']:
        assert k in res
