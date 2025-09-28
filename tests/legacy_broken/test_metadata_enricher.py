import importlib
import types

metadata_enricher = importlib.import_module('renamepdfepub.metadata_enricher')


class DummyResp:
    def __init__(self, json_data):
        self._json = json_data

    def raise_for_status(self):
        return None

    def json(self):
        return self._json


def test_enrich_by_isbn_monkeypatch(monkeypatch):
    sample = {
        'ISBN:1234567890': {
            'title': 'Mock Title',
            'subtitle': 'Mock Subtitle',
            'authors': [{'name': 'X Y'}],
            'publishers': [{'name': 'MockPub'}],
            'publish_date': '2021',
            'identifiers': {'isbn_10': ['1234567890'], 'isbn_13': ['9781234567897']}
        }
    }

    def fake_get(url, params=None, timeout=None):
        return DummyResp(sample)

    monkeypatch.setattr(metadata_enricher, 'requests', types.SimpleNamespace(get=fake_get))

    out = metadata_enricher.enrich_by_isbn('1234567890')
    assert out is not None
    assert out.get('title') == 'Mock Title'
    assert out.get('isbn10') == '1234567890'
    assert out.get('isbn13') == '9781234567897'
