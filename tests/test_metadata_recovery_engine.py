import logging
from collections import defaultdict
from dataclasses import asdict
from typing import Optional

import pytest

from renomeia_livro import (
    BookMetadata,
    MetadataRecoveryEngine,
    NORMALIZED_PUBLISHERS,
)


class DummyPDFProcessor:
    def __init__(self, text):
        self.text = text

    def extract_text_from_pdf(self, file_path: str, max_pages: int = 10):
        return self.text, ["dummy_pdf"]


class DummyEbookProcessor:
    def extract_text_from_epub(self, file_path: str):
        return "", []

    def extract_text_from_mobi(self, file_path: str):
        return "", []


class DummyISBNExtractor:
    def __init__(self, isbns):
        self._isbns = set(isbns)

    def extract_from_text(self, text: str, source_path: str = ""):
        return set(self._isbns)


class DummyMetadataFetcher:
    def __init__(self, metadata: Optional[BookMetadata]):
        self._metadata = metadata

    def fetch_metadata(self, isbn: str):
        if self._metadata is None:
            return None
        # Return a fresh copy to simulate real fetcher behaviour
        return BookMetadata(**asdict(self._metadata))


def _normalize_publisher(publisher: str) -> str:
    if not publisher:
        return "Unknown"
    upper = publisher.upper()
    for variant, normalized in NORMALIZED_PUBLISHERS.items():
        if variant in upper:
            return normalized
    return publisher.strip() or "Unknown"


def _add_publisher_stats(metadata_dict, runtime_stats):
    runtime_stats.setdefault("publisher_stats", defaultdict(lambda: {"total": 0, "success": 0}))
    pub = metadata_dict.get("publisher", "Unknown")
    stats = runtime_stats["publisher_stats"][pub]
    stats["total"] += 1
    stats["success"] += 1


@pytest.fixture
def base_runtime_stats():
    stats = {
        "processed_files": [],
        "successful_files": [],
        "successful_results": [],
        "failure_details": {},
        "api_errors": defaultdict(list),
        "processing_times": {},
        "format_stats": defaultdict(lambda: {"total": 0, "success": 0, "failed": 0}),
        "recovery_stats": {"attempted": 0, "recovered": 0},
    }
    return stats


def test_recovery_engine_recovers_metadata_via_isbn(base_runtime_stats):
    file_path = "dummy_book.pdf"
    base_runtime_stats["processed_files"].append(file_path)
    base_runtime_stats["failure_details"][file_path] = {"error": "no_isbn_found"}
    base_runtime_stats["format_stats"]["pdf"]["total"] = 1
    base_runtime_stats["format_stats"]["pdf"]["failed"] = 1

    metadata = BookMetadata(
        title="Clean Architecture",
        authors=["Robert C. Martin"],
        publisher="Pearson",
        published_date="2017",
        isbn_13="9780134494166",
        confidence_score=0.8,
        source="unit-test",
    )

    engine = MetadataRecoveryEngine(
        pdf_processor=DummyPDFProcessor("ISBN 9780134494166"),
        ebook_processor=DummyEbookProcessor(),
        isbn_extractor=DummyISBNExtractor({"9780134494166"}),
        metadata_fetcher=DummyMetadataFetcher(metadata),
        normalize_publisher=_normalize_publisher,
        add_publisher_stats=_add_publisher_stats,
        logger=logging.getLogger("test.recovery"),
    )

    recovered = engine.recover_missing_metadata(base_runtime_stats)

    assert len(recovered) == 1
    assert base_runtime_stats["recovery_stats"]["recovered"] == 1
    assert base_runtime_stats["format_stats"]["pdf"]["success"] == 1
    assert base_runtime_stats["format_stats"]["pdf"]["failed"] == 0
    assert recovered[0].isbn_13 == "9780134494166"
    assert recovered[0].source.startswith("recovery:")


def test_recovery_engine_falls_back_to_text_analysis(base_runtime_stats):
    file_path = "analysis_book.pdf"
    base_runtime_stats["processed_files"].append(file_path)
    base_runtime_stats["failure_details"][file_path] = {"error": "metadata_fetch_failed"}
    base_runtime_stats["format_stats"]["pdf"]["total"] = 1
    base_runtime_stats["format_stats"]["pdf"]["failed"] = 1

    sample_text = (
        "Fluent Python\n"
        "By Luciano Ramalho\n"
        "© 2015 O’Reilly Media, Inc.\n"
        "Practical programming for writing idiomatic Python."
    )

    engine = MetadataRecoveryEngine(
        pdf_processor=DummyPDFProcessor(sample_text),
        ebook_processor=DummyEbookProcessor(),
        isbn_extractor=DummyISBNExtractor(set()),
        metadata_fetcher=DummyMetadataFetcher(None),
        normalize_publisher=_normalize_publisher,
        add_publisher_stats=_add_publisher_stats,
        logger=logging.getLogger("test.recovery"),
    )

    recovered = engine.recover_missing_metadata(base_runtime_stats)

    assert len(recovered) == 1
    book = recovered[0]
    assert "Fluent Python" in book.title
    assert "Luciano Ramalho" in book.authors[0]
    assert book.publisher == "OReilly"
    assert book.published_date == "2015"
    assert book.isbn_13 is None
    assert book.source == "secondary_text_analysis"
    assert book.confidence_score >= 0.6
    assert base_runtime_stats["recovery_stats"]["recovered"] == 1
    assert file_path not in base_runtime_stats["failure_details"]