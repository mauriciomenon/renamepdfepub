# minor: keep imports minimal for test clarity

from renamepdfepub.metadata_cache import MetadataCache


def test_cache_upsert_and_get(tmp_path):
    db = tmp_path / 'cache.db'
    c = MetadataCache(str(db))
    try:
        path = 'books/book1.pdf'
        md = {'title': 'X', 'isbn10': '1111111111', 'isbn13': '9781111111117'}
        c.upsert(path, md)

        got = c.get_by_path(path)
        assert got['title'] == 'X'

        found = c.find_by_isbn('1111111111')
        assert found['title'] == 'X'
    finally:
        c.close()
