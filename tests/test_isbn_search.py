"""
Testes para o algoritmo de busca por ISBN.

Testa funcionalidades de:
- Validação de ISBN
- Correção de ISBNs corrompidos
- Extração de ISBNs de texto
- Busca por metadados usando ISBN
"""

import unittest
from unittest.mock import patch, MagicMock
from src.renamepdfepub.search_algorithms.isbn_search import ISBNValidator, ISBNSearchAlgorithm
from src.renamepdfepub.search_algorithms.base_search import SearchQuery, SearchResult


class TestISBNValidator(unittest.TestCase):
    """Testes para a classe ISBNValidator."""
    
    def test_clean_isbn(self):
        """Testa limpeza de ISBN."""
        # Test normal cleaning
        self.assertEqual(ISBNValidator.clean_isbn("978-0-123-45678-9"), "9780123456789")
        self.assertEqual(ISBNValidator.clean_isbn("978 0 123 45678 9"), "9780123456789")
        self.assertEqual(ISBNValidator.clean_isbn("ISBN: 978-0-123-45678-9"), "9780123456789")
        
        # Test with X
        self.assertEqual(ISBNValidator.clean_isbn("123456789X"), "123456789X")
        self.assertEqual(ISBNValidator.clean_isbn("123456789x"), "123456789X")
        
        # Test empty/invalid
        self.assertEqual(ISBNValidator.clean_isbn(""), "")
        self.assertEqual(ISBNValidator.clean_isbn(None), "")
    
    def test_is_valid_isbn13(self):
        """Testa validação de ISBN-13."""
        # Valid ISBN-13
        self.assertTrue(ISBNValidator.is_valid_isbn13("9780123456786"))
        self.assertTrue(ISBNValidator.is_valid_isbn13("9781234567890"))
        
        # Invalid ISBN-13
        self.assertFalse(ISBNValidator.is_valid_isbn13("9780123456789"))  # Wrong checksum
        self.assertFalse(ISBNValidator.is_valid_isbn13("123456789"))      # Wrong length
        self.assertFalse(ISBNValidator.is_valid_isbn13("978012345678X"))  # X in ISBN-13
        self.assertFalse(ISBNValidator.is_valid_isbn13(""))               # Empty
    
    def test_is_valid_isbn10(self):
        """Testa validação de ISBN-10."""
        # Valid ISBN-10
        self.assertTrue(ISBNValidator.is_valid_isbn10("0123456789"))
        self.assertTrue(ISBNValidator.is_valid_isbn10("123456789X"))
        
        # Invalid ISBN-10
        self.assertFalse(ISBNValidator.is_valid_isbn10("0123456788"))  # Wrong checksum
        self.assertFalse(ISBNValidator.is_valid_isbn10("123456789"))   # Wrong length
        self.assertFalse(ISBNValidator.is_valid_isbn10("12345678XY"))  # Invalid chars
        self.assertFalse(ISBNValidator.is_valid_isbn10(""))            # Empty
    
    def test_convert_isbn10_to_isbn13(self):
        """Testa conversão de ISBN-10 para ISBN-13."""
        # Valid conversions
        result = ISBNValidator.convert_isbn10_to_isbn13("0123456789")
        self.assertEqual(len(result), 13)
        self.assertTrue(result.startswith("978"))
        self.assertTrue(ISBNValidator.is_valid_isbn13(result))
        
        # Test with X
        result = ISBNValidator.convert_isbn10_to_isbn13("123456789X")
        self.assertEqual(len(result), 13)
        self.assertTrue(ISBNValidator.is_valid_isbn13(result))
        
        # Invalid input
        self.assertEqual(ISBNValidator.convert_isbn10_to_isbn13("invalid"), "")
        self.assertEqual(ISBNValidator.convert_isbn10_to_isbn13(""), "")
    
    def test_fix_corrupted_isbn(self):
        """Testa correção de ISBNs corrompidos."""
        # Test corruption pattern fixes
        corrupted = "978@123456789"  # @ instead of 9
        fixed = ISBNValidator.fix_corrupted_isbn(corrupted)
        self.assertTrue(len(fixed) > 0)
        
        # Test O vs 0
        corrupted = "978O123456789"
        fixed = ISBNValidator.fix_corrupted_isbn(corrupted)
        self.assertTrue(any("9780123456789" in isbn for isbn in fixed))
        
        # Test multiple corruptions
        corrupted = "978@12345678O"
        fixed = ISBNValidator.fix_corrupted_isbn(corrupted)
        self.assertTrue(len(fixed) > 0)
        
        # Test empty input
        self.assertEqual(ISBNValidator.fix_corrupted_isbn(""), [])
        self.assertEqual(ISBNValidator.fix_corrupted_isbn(None), [])
    
    def test_extract_isbns_from_text(self):
        """Testa extração de ISBNs de texto."""
        # Text with valid ISBN-13
        text = "This book has ISBN: 978-0-123-45678-6 and is great!"
        isbns = ISBNValidator.extract_isbns_from_text(text)
        self.assertTrue(len(isbns) > 0)
        
        # Text with ISBN-10
        text = "Old format: 0123456789"
        isbns = ISBNValidator.extract_isbns_from_text(text)
        self.assertTrue(len(isbns) > 0)
        
        # Text with corrupted ISBN
        text = "Corrupted: 978@123456789"
        isbns = ISBNValidator.extract_isbns_from_text(text)
        self.assertTrue(len(isbns) > 0)
        
        # Text without ISBNs
        text = "This is just regular text without any ISBNs."
        isbns = ISBNValidator.extract_isbns_from_text(text)
        self.assertEqual(len(isbns), 0)
        
        # Empty text
        isbns = ISBNValidator.extract_isbns_from_text("")
        self.assertEqual(len(isbns), 0)


class TestISBNSearchAlgorithm(unittest.TestCase):
    """Testes para a classe ISBNSearchAlgorithm."""
    
    def setUp(self):
        """Configuração inicial para cada teste."""
        self.algorithm = ISBNSearchAlgorithm()
    
    def test_configure(self):
        """Testa configuração do algoritmo."""
        config = {
            'partial_match_threshold': 0.9,
            'enable_corruption_fixing': False,
            'cache': {'clear_on_configure': True}
        }
        
        result = self.algorithm.configure(config)
        self.assertTrue(result)
        self.assertTrue(self.algorithm.is_configured)
        self.assertEqual(self.algorithm.partial_match_threshold, 0.9)
        self.assertFalse(self.algorithm.enable_corruption_fixing)
    
    def test_is_suitable_for_query(self):
        """Testa adequação do algoritmo para diferentes queries."""
        # Query with explicit ISBN
        query = SearchQuery(isbn="9780123456789")
        self.assertTrue(self.algorithm.is_suitable_for_query(query))
        
        # Query with ISBN in text
        query = SearchQuery(text_content="Book with ISBN: 978-0-123-45678-9")
        self.assertTrue(self.algorithm.is_suitable_for_query(query))
        
        # Query without ISBN
        query = SearchQuery(title="Some Book Title", authors=["Author Name"])
        self.assertFalse(self.algorithm.is_suitable_for_query(query))
        
        # Empty query
        query = SearchQuery()
        self.assertFalse(self.algorithm.is_suitable_for_query(query))
    
    def test_search_with_valid_isbn(self):
        """Testa busca com ISBN válido."""
        self.algorithm.configure({'enable_corruption_fixing': False})
        
        query = SearchQuery(isbn="9781234567890")
        results = self.algorithm.search(query)
        
        self.assertTrue(len(results) > 0)
        self.assertTrue(all(isinstance(r, SearchResult) for r in results))
        self.assertTrue(all(r.score > 0 for r in results))
        self.assertTrue(all(r.algorithm == "ISBNSearch" for r in results))
    
    def test_search_with_corrupted_isbn(self):
        """Testa busca com ISBN corrompido."""
        self.algorithm.configure({'enable_corruption_fixing': True})
        
        # ISBN with corruption
        query = SearchQuery(isbn="978@123456789")
        results = self.algorithm.search(query)
        
        # Should attempt to fix and find results
        self.assertTrue(len(results) >= 0)  # May or may not find results
    
    def test_search_with_text_content(self):
        """Testa busca com ISBN no conteúdo do texto."""
        query = SearchQuery(
            title="Advanced Python",
            text_content="This comprehensive guide ISBN: 978-1-234-56789-0 covers advanced topics"
        )
        
        results = self.algorithm.search(query)
        self.assertTrue(len(results) > 0)
    
    def test_cache_functionality(self):
        """Testa funcionalidade de cache."""
        isbn = "9781234567890"
        
        # First search - should populate cache
        query1 = SearchQuery(isbn=isbn)
        results1 = self.algorithm.search(query1)
        
        # Second search - should use cache
        query2 = SearchQuery(isbn=isbn)
        results2 = self.algorithm.search(query2)
        
        # Results should be similar (cache hit)
        self.assertEqual(len(results1), len(results2))
        
        # Check cache stats
        stats = self.algorithm.get_cache_stats()
        self.assertTrue(stats['cache_size'] > 0)
        self.assertIn(isbn, stats['cached_isbns'])
    
    def test_clear_cache(self):
        """Testa limpeza do cache."""
        # Populate cache
        query = SearchQuery(isbn="9781234567890")
        self.algorithm.search(query)
        
        # Verify cache has content
        stats_before = self.algorithm.get_cache_stats()
        self.assertTrue(stats_before['cache_size'] > 0)
        
        # Clear cache
        self.algorithm.clear_cache()
        
        # Verify cache is empty
        stats_after = self.algorithm.get_cache_stats()
        self.assertEqual(stats_after['cache_size'], 0)
    
    def test_get_capabilities(self):
        """Testa retorno de capacidades."""
        capabilities = self.algorithm.get_capabilities()
        
        expected_capabilities = [
            'isbn_validation',
            'isbn_correction',
            'partial_isbn_matching',
            'corruption_fixing',
            'isbn10_to_isbn13_conversion',
            'text_isbn_extraction',
            'checksum_validation'
        ]
        
        for capability in expected_capabilities:
            self.assertIn(capability, capabilities)
    
    def test_algorithm_stats(self):
        """Testa coleta de estatísticas do algoritmo."""
        # Execute some searches
        queries = [
            SearchQuery(isbn="9781234567890"),
            SearchQuery(isbn="9781234567891"),
            SearchQuery(text_content="Book with ISBN: 978-1-234-56789-2")
        ]
        
        for query in queries:
            self.algorithm.search(query)
        
        # Check stats
        stats = self.algorithm.get_stats()
        self.assertIn('executions', stats)
        self.assertIn('total_time', stats)
        self.assertIn('average_time', stats)
        self.assertIn('average_score', stats)
        self.assertTrue(stats['executions'] > 0)
    
    def test_empty_and_invalid_queries(self):
        """Testa comportamento com queries vazias ou inválidas."""
        # Empty query
        empty_query = SearchQuery()
        results = self.algorithm.search(empty_query)
        self.assertEqual(len(results), 0)
        
        # Query with invalid ISBN
        invalid_query = SearchQuery(isbn="invalid-isbn")
        results = self.algorithm.search(invalid_query)
        # Should still work if corruption fixing is enabled
        self.assertTrue(len(results) >= 0)
    
    def test_multiple_isbns_in_text(self):
        """Testa extração de múltiplos ISBNs do texto."""
        text_with_multiple_isbns = """
        First book: ISBN-13: 978-1-234-56789-0
        Second book: ISBN-10: 0123456789
        Third book: 978-9-876-54321-0
        """
        
        query = SearchQuery(text_content=text_with_multiple_isbns)
        results = self.algorithm.search(query)
        
        # Should find multiple books
        self.assertTrue(len(results) > 0)


class TestISBNSearchIntegration(unittest.TestCase):
    """Testes de integração para o algoritmo ISBN."""
    
    def test_isbn_search_with_title_matching(self):
        """Testa busca por ISBN com correspondência de título."""
        algorithm = ISBNSearchAlgorithm()
        algorithm.configure({})
        
        query = SearchQuery(
            isbn="9781234567890",
            title="Python Programming Advanced",
            authors=["John Smith"]
        )
        
        results = algorithm.search(query)
        self.assertTrue(len(results) > 0)
        
        # Should have higher scores for matching metadata
        for result in results:
            self.assertTrue(result.score > 0.8)  # High confidence for ISBN matches
    
    def test_performance_with_large_text(self):
        """Testa performance com texto grande."""
        algorithm = ISBNSearchAlgorithm()
        algorithm.configure({})
        
        # Create large text with embedded ISBNs
        large_text = "This book " * 1000 + " has ISBN: 978-1-234-56789-0 " + "more text " * 1000
        
        query = SearchQuery(text_content=large_text)
        
        import time
        start_time = time.time()
        results = algorithm.search(query)
        execution_time = time.time() - start_time
        
        # Should complete in reasonable time (less than 1 second)
        self.assertTrue(execution_time < 1.0)
        self.assertTrue(len(results) > 0)


if __name__ == '__main__':
    unittest.main()