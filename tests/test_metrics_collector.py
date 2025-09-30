#!/usr/bin/env python3
import importlib


def test_metrics_collector_errors_and_recent():
    core = importlib.import_module('src.core.renomeia_livro'.replace('/', '.'))
    mc = core.MetricsCollector()
    # simulate calls
    for i in range(5):
        mc.add_metric('openlibrary', 0.5, success=(i % 2 == 0))
    # add errors
    mc.add_error('openlibrary', 'HTTPError')
    mc.add_error('openlibrary', 'Timeout')
    stats = mc.get_api_stats('openlibrary')
    assert 'error_types' in stats
    assert stats['error_types'].get('HTTPError', 0) == 1
    assert stats['error_types'].get('Timeout', 0) == 1
    assert 'recent_errors' in stats
    assert len(stats['recent_errors']) >= 2

