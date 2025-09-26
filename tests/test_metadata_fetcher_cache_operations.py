import logging
from copy import deepcopy

import pytest

from renomeia_livro import BookMetadata, MetadataFetcher


class FakeCache:
    def __init__(self, records):
        self.records = [deepcopy(record) for record in records]
        self.set_calls = []

    def get_all(self):
        return [deepcopy(record) for record in self.records]

    def set(self, metadata):
        payload = deepcopy(metadata)
        self.set_calls.append(payload)
        isbn = payload.get("isbn_13") or payload.get("isbn_10")
        for idx, record in enumerate(self.records):
            current_isbn = record.get("isbn_13") or record.get("isbn_10")
            if current_isbn == isbn:
                self.records[idx] = payload
                break
        else:
            self.records.append(payload)

    def get(self, isbn):
        for record in self.records:
            if record.get("isbn_13") == isbn or record.get("isbn_10") == isbn:
                return deepcopy(record)
        return None


@pytest.fixture
def base_record():
    return {
        "isbn_13": "9781234567890",
        "isbn_10": None,
        "title": "Original Title",
        "authors": ["Original Author"],
        "publisher": "Original Publisher",
        "published_date": "2024",
        "confidence_score": 0.5,
        "source": "cache",
        "file_path": "/tmp/original.pdf",
    }


@pytest.fixture
def fetcher(base_record):
    fetcher = MetadataFetcher()
    fetcher.logger = logging.getLogger("test_metadata_fetcher")
    fetcher.logger.propagate = False
    fetcher.cache = FakeCache([base_record])
    return fetcher


def test_update_low_confidence_records_improves_metadata(fetcher, monkeypatch):
    def fake_fetch(isbn, force_refresh=False):
        assert force_refresh is True
        return BookMetadata(
            title="Improved Title",
            authors=["Original Author"],
            publisher="Original Publisher",
            published_date="2024",
            isbn_13=isbn,
            isbn_10=None,
            confidence_score=0.95,
            source="test_api",
        )

    monkeypatch.setattr(fetcher, "fetch_metadata", fake_fetch)

    updated = fetcher.update_low_confidence_records(confidence_threshold=0.8)

    assert updated == 1
    stored = fetcher.cache.records[0]
    assert stored["title"] == "Improved Title"
    assert stored["confidence_score"] == 0.95
    assert stored["source"] == "test_api"


def test_update_low_confidence_records_preserves_when_no_gain(fetcher, base_record, monkeypatch):
    def fake_fetch(isbn, force_refresh=False):
        return BookMetadata(
            title="No Gain Title",
            authors=["Original Author"],
            publisher="Original Publisher",
            published_date="2024",
            isbn_13=isbn,
            isbn_10=None,
            confidence_score=0.5,
            source="test_api",
        )

    monkeypatch.setattr(fetcher, "fetch_metadata", fake_fetch)

    updated = fetcher.update_low_confidence_records(confidence_threshold=0.8)

    assert updated == 0
    stored = fetcher.cache.records[0]
    assert stored["title"] == base_record["title"]
    assert stored["confidence_score"] == base_record["confidence_score"]


def test_rescan_cache_updates_when_new_information(fetcher, base_record, monkeypatch):
    fetcher.cache.records[0]["confidence_score"] = 0.85

    def fake_fetch(isbn, force_refresh=False):
        return BookMetadata(
            title=base_record["title"],
            authors=["Original Author", "Second Author"],
            publisher="New Publisher",
            published_date="2024",
            isbn_13=isbn,
            isbn_10=None,
            confidence_score=0.85,
            source="test_api",
        )

    monkeypatch.setattr(fetcher, "fetch_metadata", fake_fetch)

    updated = fetcher.rescan_cache()

    assert updated == 1
    stored = fetcher.cache.records[0]
    assert stored["publisher"] == "New Publisher"
    assert stored["authors"] == ["Original Author", "Second Author"]