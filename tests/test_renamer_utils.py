from renamer import sanitize_name, format_name


def test_sanitize_name_basic():
    assert sanitize_name('This is / a ? title:') == 'This is  a  title'
    long = 'x' * 200
    assert len(sanitize_name(long)) <= 120


def test_format_name_pattern():
    meta = {'metadata': {'title': 'T', 'authors': 'A', 'publisher': 'P', 'year': '2022', 'isbn10': '123'}}
    name = format_name('{publisher}_{year}_{title}_{author}_{isbn}', meta)
    assert 'P_2022_T_A_123' in name
