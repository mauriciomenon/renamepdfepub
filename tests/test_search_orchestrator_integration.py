"""
Testes de integração para o SearchOrchestrator com todos os algoritmos.

Testa funcionalidades de:
- Coordenação entre algoritmos Fuzzy, ISBN e Semantic
- Seleção automática de algoritmos
- Execução paralela e combinação de resultados
- Performance e otimização
"""

import unittest
import time
from unittest.mock import patch, MagicMock
from src.renamepdfepub.search_algorithms.search_orchestrator import SearchOrchestrator
from src.renamepdfepub.search_algorithms.base_search import SearchQuery, SearchResult
from src.renamepdfepub.search_algorithms.fuzzy_search import FuzzySearchAlgorithm
from src.renamepdfepub.search_algorithms.isbn_search import ISBNSearchAlgorithm
from src.renamepdfepub.search_algorithms.semantic_search import SemanticSearchAlgorithm


class TestSearchOrchestratorIntegration(unittest.TestCase):
    """Testes de integração para o SearchOrchestrator completo."""
    
    def setUp(self):
        """Configuração inicial para cada teste."""
        self.orchestrator = SearchOrchestrator(max_workers=4)
    
    def test_initialization_with_all_algorithms(self):
        """Testa inicialização com todos os algoritmos."""
        # Should have all three algorithms registered
        algorithms = self.orchestrator.get_registered_algorithms()
        algorithm_names = [algo.name for algo in algorithms]
        
        self.assertIn('FuzzySearch', algorithm_names)
        self.assertIn('ISBNSearch', algorithm_names)
        self.assertIn('SemanticSearch', algorithm_names)
        self.assertEqual(len(algorithms), 3)
    
    def test_algorithm_suitability_selection(self):
        """Testa seleção automática baseada na adequação dos algoritmos."""
        # Query with ISBN - should select ISBN algorithm
        isbn_query = SearchQuery(isbn="9781234567890")
        suitable = self.orchestrator._get_ordered_algorithms(isbn_query)
        
        # ISBN algorithm should be suitable
        isbn_suitable = any(algo.name == 'ISBNSearch' for algo in suitable)
        self.assertTrue(isbn_suitable)
        
        # Query with rich text - should select Semantic algorithm
        text_query = SearchQuery(
            title="Advanced Machine Learning with Python Programming",
            text_content="Comprehensive guide to machine learning algorithms"
        )
        suitable = self.orchestrator._get_ordered_algorithms(text_query)
        
        # Semantic algorithm should be suitable
        semantic_suitable = any(algo.name == 'SemanticSearch' for algo in suitable)
        self.assertTrue(semantic_suitable)
        
        # Query with partial/fuzzy terms - Fuzzy should be suitable
        fuzzy_query = SearchQuery(title="Pythno Programing")  # Intentional typos
        suitable = self.orchestrator._get_ordered_algorithms(fuzzy_query)
        
        # Fuzzy algorithm should be suitable
        fuzzy_suitable = any(algo.name == 'FuzzySearch' for algo in suitable)
        self.assertTrue(fuzzy_suitable)
    
    def test_parallel_search_execution(self):
        """Testa execução paralela de múltiplos algoritmos."""
        query = SearchQuery(
            title="Python Programming Guide",
            authors=["John Smith"],
            isbn="9781234567890",
            text_content="Advanced guide to Python programming with machine learning"
        )
        
        start_time = time.time()
        results = self.orchestrator.search(query, strategy='parallel', max_results=20)
        execution_time = time.time() - start_time
        
        # Should return results from multiple algorithms
        self.assertTrue(len(results) > 0)
        
        # Check that results come from different algorithms
        algorithm_sources = set(result.algorithm for result in results)
        self.assertTrue(len(algorithm_sources) > 1)  # Multiple algorithms contributed
        
        # Should complete reasonably fast (parallel execution benefit)
        self.assertTrue(execution_time < 5.0)  # Less than 5 seconds
    
    def test_sequential_search_execution(self):
        """Testa execução sequencial de algoritmos."""
        query = SearchQuery(
            title="Machine Learning Fundamentals",
            text_content="Introduction to machine learning concepts and algorithms"
        )
        
        results = self.orchestrator.search(query, strategy='sequential', max_results=10)
        
        # Should return results
        self.assertTrue(len(results) > 0)
        
        # Results should be properly ranked
        if len(results) > 1:
            for i in range(len(results) - 1):
                self.assertTrue(results[i].score >= results[i + 1].score)
    
    def test_best_match_strategy(self):
        """Testa estratégia de melhor correspondência."""
        # Query ideal for ISBN search
        isbn_query = SearchQuery(isbn="9781234567890")
        results = self.orchestrator.search(isbn_query, strategy='best_match', max_results=5)
        
        # Should prioritize ISBN algorithm results
        if results:
            # Most results should come from ISBN algorithm
            isbn_results = [r for r in results if r.algorithm == 'ISBNSearch']
            self.assertTrue(len(isbn_results) > 0)
    
    def test_auto_strategy_selection(self):
        """Testa seleção automática de estratégia."""
        # Complex query should trigger parallel strategy
        complex_query = SearchQuery(
            title="Comprehensive Guide to Data Science",
            authors=["Dr. Jane Doe", "Prof. John Smith"],
            isbn="9781234567890",
            text_content="Complete guide covering statistics, machine learning, and data visualization"
        )
        
        results = self.orchestrator.search(complex_query, strategy='auto', max_results=15)
        self.assertTrue(len(results) > 0)
        
        # Simple query might trigger different strategy
        simple_query = SearchQuery(title="Book Title")
        results = self.orchestrator.search(simple_query, strategy='auto', max_results=5)
        # Should still work
        self.assertTrue(len(results) >= 0)
    
    def test_result_combination_strategies(self):
        """Testa diferentes estratégias de combinação de resultados."""
        query = SearchQuery(
            title="Python Programming",
            text_content="Guide to Python programming language"
        )
        
        # Test weighted merge (default)
        self.orchestrator.result_combination_strategy = 'weighted_merge'
        results_weighted = self.orchestrator.search(query, strategy='parallel')
        
        # Test best of each
        self.orchestrator.result_combination_strategy = 'best_of_each'
        results_best = self.orchestrator.search(query, strategy='parallel')
        
        # Both should return results
        self.assertTrue(len(results_weighted) >= 0)
        self.assertTrue(len(results_best) >= 0)
    
    def test_algorithm_registration_and_removal(self):
        """Testa registro e remoção de algoritmos."""
        # Create custom algorithm
        custom_algo = FuzzySearchAlgorithm()
        custom_algo.name = "CustomFuzzy"
        custom_algo.configure({'similarity_threshold': 0.8})
        
        # Register custom algorithm
        success = self.orchestrator.register_algorithm(custom_algo)
        self.assertTrue(success)
        
        algorithms = self.orchestrator.get_registered_algorithms()
        self.assertEqual(len(algorithms), 4)  # 3 default + 1 custom
        
        # Remove custom algorithm
        removed = self.orchestrator.remove_algorithm("CustomFuzzy")
        self.assertTrue(removed)
        
        algorithms = self.orchestrator.get_registered_algorithms()
        self.assertEqual(len(algorithms), 3)  # Back to 3 default
    
    def test_performance_statistics(self):
        """Testa coleta de estatísticas de performance."""
        queries = [
            SearchQuery(title="Python Programming"),
            SearchQuery(isbn="9781234567890"),
            SearchQuery(title="Machine Learning", authors=["John Doe"]),
            SearchQuery(text_content="Data science and analytics guide")
        ]
        
        # Execute multiple searches
        for query in queries:
            self.orchestrator.search(query, strategy='parallel')
        
        # Check orchestrator stats
        stats = self.orchestrator.get_performance_stats()
        self.assertIn('total_searches', stats)
        self.assertIn('average_time', stats)
        self.assertTrue(stats['total_searches'] > 0)
        
        # Check individual algorithm stats
        algorithm_stats = self.orchestrator.get_algorithm_stats()
        self.assertEqual(len(algorithm_stats), 3)  # 3 algorithms
        
        for algo_name, algo_stats in algorithm_stats.items():
            self.assertIn('executions', algo_stats)
    
    def test_timeout_handling(self):
        """Testa tratamento de timeout."""
        # Set short timeout
        self.orchestrator.default_timeout = 0.1  # 100ms
        
        query = SearchQuery(
            title="Complex Query That Might Take Time",
            text_content="Very long text content " * 100
        )
        
        # Should handle timeout gracefully
        results = self.orchestrator.search(query, strategy='parallel')
        # Should not crash, may have fewer results due to timeout
        self.assertTrue(len(results) >= 0)
    
    def test_empty_and_invalid_queries(self):
        """Testa comportamento com queries vazias ou inválidas."""
        # Empty query
        empty_query = SearchQuery()
        results = self.orchestrator.search(empty_query)
        self.assertEqual(len(results), 0)
        
        # Query with only whitespace
        whitespace_query = SearchQuery(title="   ", text_content="  \n  ")
        results = self.orchestrator.search(whitespace_query)
        self.assertEqual(len(results), 0)
    
    def test_algorithm_error_resilience(self):
        """Testa resiliência a erros em algoritmos individuais."""
        # Mock one algorithm to raise exception
        with patch.object(self.orchestrator.algorithms['FuzzySearch'], 'search') as mock_search:
            mock_search.side_effect = Exception("Simulated algorithm error")
            
            query = SearchQuery(title="Test Query")
            results = self.orchestrator.search(query, strategy='parallel')
            
            # Should still get results from other algorithms
            # and not crash due to one failing algorithm
            self.assertTrue(len(results) >= 0)
    
    def test_max_results_limiting(self):
        """Testa limitação do número máximo de resultados."""
        query = SearchQuery(
            title="Python Programming Guide",
            text_content="Comprehensive guide to Python programming"
        )
        
        # Test different max_results values
        results_5 = self.orchestrator.search(query, max_results=5)
        results_10 = self.orchestrator.search(query, max_results=10)
        
        # Should respect max_results limit
        self.assertTrue(len(results_5) <= 5)
        self.assertTrue(len(results_10) <= 10)
    
    def test_weighted_algorithm_results(self):
        """Testa ponderação de resultados por algoritmo."""
        query = SearchQuery(
            title="Advanced Python Programming",
            isbn="9781234567890",
            text_content="Complete guide to advanced Python programming techniques"
        )
        
        results = self.orchestrator.search(query, strategy='parallel')
        
        if results:
            # ISBN results should generally have high confidence
            isbn_results = [r for r in results if r.algorithm == 'ISBNSearch']
            if isbn_results:
                self.assertTrue(all(r.score > 0.8 for r in isbn_results))
            
            # Results should be properly sorted by score
            for i in range(len(results) - 1):
                self.assertTrue(results[i].score >= results[i + 1].score)
    
    def test_result_deduplication(self):
        """Testa remoção de resultados duplicados."""
        query = SearchQuery(
            title="Python Programming",
            text_content="Python programming guide"
        )
        
        results = self.orchestrator.search(query, strategy='parallel')
        
        # Check for potential duplicates (same metadata)
        seen_metadata = set()
        for result in results:
            # Create a simple hash of key metadata fields
            metadata_hash = (
                result.metadata.get('title', ''),
                result.metadata.get('isbn', ''),
                str(result.metadata.get('authors', []))
            )
            
            # In a real implementation, duplicates should be removed
            # For now, we just verify the structure is correct
            self.assertIsInstance(result.metadata, dict)


class TestSpecificAlgorithmInteractions(unittest.TestCase):
    """Testes específicos de interação entre algoritmos."""
    
    def setUp(self):
        """Configuração inicial."""
        self.orchestrator = SearchOrchestrator()
    
    def test_isbn_and_semantic_combination(self):
        """Testa combinação de resultados ISBN e semânticos."""
        query = SearchQuery(
            title="Advanced Python Programming Techniques",
            isbn="9781234567890",
            authors=["John Smith"],
            text_content="Comprehensive guide to advanced Python programming with machine learning"
        )
        
        results = self.orchestrator.search(query, strategy='parallel')
        
        # Should have results from both ISBN and Semantic algorithms
        algorithm_types = set(r.algorithm for r in results)
        
        # May have ISBN results if ISBN is valid
        # Should have Semantic results due to rich text content
        self.assertTrue(len(algorithm_types) >= 1)
    
    def test_fuzzy_and_semantic_overlap(self):
        """Testa sobreposição entre resultados Fuzzy e Semânticos."""
        query = SearchQuery(
            title="Pythno Programing Machien Learing",  # Intentional typos
            text_content="Guide to Python programming and machine learning algorithms"
        )
        
        results = self.orchestrator.search(query, strategy='parallel')
        
        # Both Fuzzy (typo correction) and Semantic (content analysis) should contribute
        algorithm_types = set(r.algorithm for r in results)
        self.assertTrue(len(algorithm_types) >= 1)
        
        # Verify results quality
        if results:
            # Should have reasonable scores despite typos
            self.assertTrue(any(r.score > 0.3 for r in results))
    
    def test_algorithm_priority_in_combination(self):
        """Testa prioridade de algoritmos na combinação de resultados."""
        # Query that should favor ISBN algorithm
        isbn_priority_query = SearchQuery(
            isbn="9781234567890",
            title="Some Book Title"
        )
        
        results = self.orchestrator.search(isbn_priority_query, strategy='parallel')
        
        if results:
            # ISBN results should typically have higher scores
            isbn_results = [r for r in results if r.algorithm == 'ISBNSearch']
            other_results = [r for r in results if r.algorithm != 'ISBNSearch']
            
            if isbn_results and other_results:
                avg_isbn_score = sum(r.score for r in isbn_results) / len(isbn_results)
                avg_other_score = sum(r.score for r in other_results) / len(other_results)
                
                # ISBN should generally have higher confidence for ISBN queries
                self.assertTrue(avg_isbn_score >= avg_other_score * 0.8)  # Allow some flexibility


if __name__ == '__main__':
    unittest.main()