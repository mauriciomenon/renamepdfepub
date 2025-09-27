"""
Testes para o algoritmo de busca semântica.

Testa funcionalidades de:
- Normalização de texto
- Cálculos TF-IDF
- Similaridade semântica
- Correspondência de autores com N-gramas
"""

import unittest
from unittest.mock import patch, MagicMock
from src.renamepdfepub.search_algorithms.semantic_search import (
    TextNormalizer, TFIDFCalculator, SemanticSearchAlgorithm
)
from src.renamepdfepub.search_algorithms.base_search import SearchQuery, SearchResult


class TestTextNormalizer(unittest.TestCase):
    """Testes para a classe TextNormalizer."""
    
    def test_normalize_text_english(self):
        """Testa normalização de texto em inglês."""
        text = "The Advanced Python Programming Guide for Machine Learning"
        tokens = TextNormalizer.normalize_text(text, 'english')
        
        # Should remove stop words
        self.assertNotIn('the', tokens)
        self.assertNotIn('for', tokens)
        
        # Should keep meaningful words
        self.assertIn('advanced', tokens)
        self.assertIn('python', tokens)
        self.assertIn('programming', tokens)
        self.assertIn('machine', tokens)
        self.assertIn('learning', tokens)
    
    def test_normalize_text_portuguese(self):
        """Testa normalização de texto em português."""
        text = "O Guia Avançado de Programação Python para Aprendizado de Máquina"
        tokens = TextNormalizer.normalize_text(text, 'portuguese')
        
        # Should remove Portuguese stop words
        self.assertNotIn('o', tokens)
        self.assertNotIn('de', tokens)
        self.assertNotIn('para', tokens)
        
        # Should keep meaningful words
        self.assertIn('guia', tokens)
        self.assertIn('avançado', tokens)
        self.assertIn('programação', tokens)
        self.assertIn('python', tokens)
    
    def test_preserve_technical_terms(self):
        """Testa preservação de termos técnicos."""
        text = "API SDK JSON XML SQL NoSQL React.js Node.js C++ C#"
        tokens = TextNormalizer.normalize_text(text)
        
        # Technical terms should be preserved and normalized
        self.assertIn('api', tokens)
        self.assertIn('sdk', tokens)
        self.assertIn('json', tokens)
        self.assertIn('xml', tokens)
        self.assertIn('sql', tokens)
        self.assertIn('nosql', tokens)
        self.assertIn('react', tokens)  # .js should be normalized
        self.assertIn('nodejs', tokens)  # node.js should become nodejs
        self.assertIn('cpp', tokens)     # c++ should become cpp
        self.assertIn('csharp', tokens)  # c# should become csharp
    
    def test_generate_ngrams(self):
        """Testa geração de N-gramas."""
        tokens = ['john', 'doe', 'smith']
        
        # Test bigrams
        bigrams = TextNormalizer.generate_ngrams(tokens, 2)
        expected = ['john doe', 'doe smith']
        self.assertEqual(bigrams, expected)
        
        # Test trigrams
        trigrams = TextNormalizer.generate_ngrams(tokens, 3)
        expected = ['john doe smith']
        self.assertEqual(trigrams, expected)
        
        # Test with insufficient tokens
        short_tokens = ['john']
        bigrams = TextNormalizer.generate_ngrams(short_tokens, 2)
        self.assertEqual(bigrams, [])
    
    def test_extract_author_variants(self):
        """Testa extração de variantes de nome de autor."""
        author = "John Doe Smith"
        variants = TextNormalizer.extract_author_variants(author)
        
        # Should contain multiple variants
        self.assertIn('john doe smith', variants)      # Original
        self.assertIn('john smith', variants)          # First + Last
        self.assertIn('smith, john', variants)         # Last, First
        self.assertIn('jd. smith', variants)           # Initials + Last
        self.assertIn('smith', variants)               # Just last name
    
    def test_extract_author_variants_edge_cases(self):
        """Testa casos extremos na extração de variantes."""
        # Single name
        variants = TextNormalizer.extract_author_variants("Madonna")
        self.assertIn('madonna', variants)
        
        # Empty/None
        variants = TextNormalizer.extract_author_variants("")
        self.assertEqual(len(variants), 0)
        
        variants = TextNormalizer.extract_author_variants(None)
        self.assertEqual(len(variants), 0)
        
        # Multiple middle names
        variants = TextNormalizer.extract_author_variants("John William Doe Smith")
        self.assertIn('john smith', variants)
        self.assertIn('jwd. smith', variants)


class TestTFIDFCalculator(unittest.TestCase):
    """Testes para a classe TFIDFCalculator."""
    
    def setUp(self):
        """Configuração inicial para cada teste."""
        self.calculator = TFIDFCalculator()
    
    def test_add_document_and_vocabulary(self):
        """Testa adição de documentos e construção do vocabulário."""
        # Add first document
        doc1_tokens = ['python', 'programming', 'guide']
        self.calculator.add_document(doc1_tokens)
        
        self.assertEqual(self.calculator.total_documents, 1)
        self.assertEqual(len(self.calculator.vocabulary), 3)
        self.assertIn('python', self.calculator.vocabulary)
        
        # Add second document
        doc2_tokens = ['python', 'machine', 'learning']
        self.calculator.add_document(doc2_tokens)
        
        self.assertEqual(self.calculator.total_documents, 2)
        self.assertEqual(len(self.calculator.vocabulary), 5)  # 3 + 2 new terms
    
    def test_calculate_tf(self):
        """Testa cálculo de Term Frequency."""
        tokens = ['python', 'python', 'programming', 'guide']
        tf_scores = self.calculator.calculate_tf(tokens)
        
        # python appears 2/4 = 0.5
        self.assertEqual(tf_scores['python'], 0.5)
        
        # programming and guide appear 1/4 = 0.25 each
        self.assertEqual(tf_scores['programming'], 0.25)
        self.assertEqual(tf_scores['guide'], 0.25)
    
    def test_calculate_idf(self):
        """Testa cálculo de Inverse Document Frequency."""
        # Add documents to build corpus
        self.calculator.add_document(['python', 'programming'])
        self.calculator.add_document(['python', 'data'])
        self.calculator.add_document(['java', 'programming'])
        
        # python appears in 2/3 documents
        python_idf = self.calculator.calculate_idf('python')
        expected_idf = 0.4054651081081644  # log(3/2)
        self.assertAlmostEqual(python_idf, expected_idf, places=5)
        
        # programming appears in 2/3 documents
        programming_idf = self.calculator.calculate_idf('programming')
        self.assertAlmostEqual(programming_idf, expected_idf, places=5)
        
        # data appears in 1/3 documents
        data_idf = self.calculator.calculate_idf('data')
        expected_idf = 1.0986122886681098  # log(3/1)
        self.assertAlmostEqual(data_idf, expected_idf, places=5)
    
    def test_calculate_tfidf_vector(self):
        """Testa cálculo de vetor TF-IDF."""
        # Build corpus
        self.calculator.add_document(['python', 'programming'])
        self.calculator.add_document(['python', 'data'])
        
        # Calculate TF-IDF for new document
        tokens = ['python', 'programming']
        tfidf_vector = self.calculator.calculate_tfidf_vector(tokens)
        
        # Should have TF-IDF scores for both terms
        self.assertIn('python', tfidf_vector)
        self.assertIn('programming', tfidf_vector)
        self.assertTrue(all(score > 0 for score in tfidf_vector.values()))
    
    def test_cosine_similarity(self):
        """Testa cálculo de similaridade coseno."""
        vector1 = {'python': 0.5, 'programming': 0.3, 'guide': 0.2}
        vector2 = {'python': 0.4, 'programming': 0.6, 'data': 0.3}
        
        similarity = self.calculator.cosine_similarity(vector1, vector2)
        
        # Should be between 0 and 1
        self.assertTrue(0 <= similarity <= 1)
        self.assertTrue(similarity > 0)  # Should have some similarity
    
    def test_cosine_similarity_edge_cases(self):
        """Testa casos extremos na similaridade coseno."""
        # Identical vectors
        vector1 = {'python': 0.5, 'programming': 0.5}
        similarity = self.calculator.cosine_similarity(vector1, vector1)
        self.assertAlmostEqual(similarity, 1.0, places=5)
        
        # Completely different vectors
        vector1 = {'python': 1.0}
        vector2 = {'java': 1.0}
        similarity = self.calculator.cosine_similarity(vector1, vector2)
        self.assertEqual(similarity, 0.0)
        
        # Empty vectors
        similarity = self.calculator.cosine_similarity({}, {})
        self.assertEqual(similarity, 0.0)


class TestSemanticSearchAlgorithm(unittest.TestCase):
    """Testes para a classe SemanticSearchAlgorithm."""
    
    def setUp(self):
        """Configuração inicial para cada teste."""
        self.algorithm = SemanticSearchAlgorithm()
    
    def test_configure(self):
        """Testa configuração do algoritmo."""
        config = {
            'min_similarity_threshold': 0.2,
            'author_ngram_size': 3,
            'title_weight': 0.7,
            'author_weight': 0.2,
            'content_weight': 0.1
        }
        
        result = self.algorithm.configure(config)
        self.assertTrue(result)
        self.assertTrue(self.algorithm.is_configured)
        self.assertEqual(self.algorithm.min_similarity_threshold, 0.2)
        self.assertEqual(self.algorithm.author_ngram_size, 3)
        self.assertEqual(self.algorithm.title_weight, 0.7)
    
    def test_configure_weight_normalization(self):
        """Testa normalização automática de pesos."""
        config = {
            'title_weight': 0.8,
            'author_weight': 0.4,
            'content_weight': 0.2
        }
        
        self.algorithm.configure(config)
        
        # Weights should be normalized to sum to 1.0
        total = self.algorithm.title_weight + self.algorithm.author_weight + self.algorithm.content_weight
        self.assertAlmostEqual(total, 1.0, places=5)
    
    def test_is_suitable_for_query(self):
        """Testa adequação do algoritmo para diferentes queries."""
        # Query with meaningful text
        query = SearchQuery(title="Advanced Python Programming")
        self.assertTrue(self.algorithm.is_suitable_for_query(query))
        
        # Query with authors
        query = SearchQuery(authors=["John Doe", "Jane Smith"])
        self.assertTrue(self.algorithm.is_suitable_for_query(query))
        
        # Query with text content
        query = SearchQuery(text_content="This is a comprehensive guide to machine learning")
        self.assertTrue(self.algorithm.is_suitable_for_query(query))
        
        # Query with insufficient text
        query = SearchQuery(title="Book", isbn="123")
        self.assertFalse(self.algorithm.is_suitable_for_query(query))
        
        # Empty query
        query = SearchQuery()
        self.assertFalse(self.algorithm.is_suitable_for_query(query))
    
    def test_search_basic(self):
        """Testa busca semântica básica."""
        self.algorithm.configure({})
        
        query = SearchQuery(
            title="Python Programming Machine Learning",
            authors=["John Smith"],
            text_content="Advanced guide to Python programming for machine learning applications"
        )
        
        results = self.algorithm.search(query)
        
        # Should return some results
        self.assertTrue(len(results) > 0)
        self.assertTrue(all(isinstance(r, SearchResult) for r in results))
        self.assertTrue(all(r.algorithm == "SemanticSearch" for r in results))
        
        # Results should be sorted by score
        if len(results) > 1:
            for i in range(len(results) - 1):
                self.assertTrue(results[i].score >= results[i + 1].score)
    
    def test_search_with_title_only(self):
        """Testa busca apenas com título."""
        self.algorithm.configure({})
        
        query = SearchQuery(title="Advanced Python Programming Techniques")
        results = self.algorithm.search(query)
        
        self.assertTrue(len(results) > 0)
    
    def test_search_with_authors_only(self):
        """Testa busca apenas com autores."""
        self.algorithm.configure({})
        
        query = SearchQuery(authors=["John Smith", "Maria Garcia"])
        results = self.algorithm.search(query)
        
        self.assertTrue(len(results) > 0)
    
    def test_search_threshold_filtering(self):
        """Testa filtragem por threshold de similaridade."""
        # Set high threshold
        self.algorithm.configure({'min_similarity_threshold': 0.9})
        
        query = SearchQuery(title="Completely Different Topic Biology")
        results = self.algorithm.search(query)
        
        # Should return few or no results due to high threshold
        self.assertTrue(all(r.score >= 0.9 for r in results))
    
    def test_get_capabilities(self):
        """Testa retorno de capacidades."""
        capabilities = self.algorithm.get_capabilities()
        
        expected_capabilities = [
            'tfidf_similarity',
            'ngram_matching',
            'semantic_analysis',
            'author_name_variants',
            'contextual_scoring',
            'multilingual_support',
            'technical_term_preservation'
        ]
        
        for capability in expected_capabilities:
            self.assertIn(capability, capabilities)
    
    def test_reset_corpus(self):
        """Testa reset do corpus."""
        # Initialize and use corpus
        query = SearchQuery(title="Test Query")
        self.algorithm.search(query)
        self.assertTrue(self.algorithm.corpus_initialized)
        
        # Reset corpus
        self.algorithm.reset_corpus()
        self.assertFalse(self.algorithm.corpus_initialized)
    
    def test_get_corpus_stats(self):
        """Testa estatísticas do corpus."""
        # Initialize corpus
        query = SearchQuery(title="Python Programming")
        self.algorithm.search(query)
        
        stats = self.algorithm.get_corpus_stats()
        
        self.assertIn('total_documents', stats)
        self.assertIn('vocabulary_size', stats)
        self.assertIn('top_terms', stats)
        self.assertTrue(stats['total_documents'] > 0)
        self.assertTrue(stats['vocabulary_size'] > 0)
    
    def test_author_similarity_calculation(self):
        """Testa cálculo de similaridade de autores."""
        # Exact match
        query_variants = ['john smith', 'j. smith']
        candidate_variants = ['john smith', 'smith, john']
        
        similarity = self.algorithm._calculate_author_similarity(query_variants, candidate_variants)
        self.assertEqual(similarity, 1.0)  # Should be exact match
        
        # Partial match
        query_variants = ['john doe']
        candidate_variants = ['jane doe']
        
        similarity = self.algorithm._calculate_author_similarity(query_variants, candidate_variants)
        self.assertTrue(0 < similarity < 1.0)  # Should have partial similarity
        
        # No match
        query_variants = ['john smith']
        candidate_variants = ['jane williams']
        
        similarity = self.algorithm._calculate_author_similarity(query_variants, candidate_variants)
        self.assertTrue(similarity >= 0.0)  # Should be low but not necessarily 0
    
    def test_word_overlap_similarity(self):
        """Testa similaridade por sobreposição de palavras."""
        # Identical texts
        similarity = self.algorithm._word_overlap_similarity("python programming", "python programming")
        self.assertEqual(similarity, 1.0)
        
        # Partial overlap
        similarity = self.algorithm._word_overlap_similarity("python programming", "programming guide")
        self.assertTrue(0 < similarity < 1.0)
        
        # No overlap
        similarity = self.algorithm._word_overlap_similarity("python programming", "java development")
        self.assertEqual(similarity, 0.0)
        
        # Empty strings
        similarity = self.algorithm._word_overlap_similarity("", "")
        self.assertEqual(similarity, 0.0)


class TestSemanticSearchIntegration(unittest.TestCase):
    """Testes de integração para o algoritmo semântico."""
    
    def test_full_search_workflow(self):
        """Testa fluxo completo de busca semântica."""
        algorithm = SemanticSearchAlgorithm()
        algorithm.configure({
            'min_similarity_threshold': 0.1,
            'title_weight': 0.6,
            'author_weight': 0.3,
            'content_weight': 0.1
        })
        
        query = SearchQuery(
            title="Machine Learning with Python",
            authors=["John Smith"],
            text_content="Comprehensive guide to machine learning algorithms using Python programming language"
        )
        
        results = algorithm.search(query)
        
        # Verify results structure
        self.assertTrue(len(results) > 0)
        for result in results:
            self.assertIsInstance(result, SearchResult)
            self.assertTrue(result.score >= 0.1)  # Above threshold
            self.assertEqual(result.algorithm, "SemanticSearch")
            self.assertIn('similarity_components', result.details)
            self.assertIn('semantic_method', result.details)
    
    def test_multilingual_support(self):
        """Testa suporte a múltiplos idiomas."""
        algorithm = SemanticSearchAlgorithm()
        algorithm.configure({})
        
        # Portuguese query
        query = SearchQuery(
            title="Programação Avançada em Python",
            text_content="Guia completo para programação avançada usando a linguagem Python"
        )
        
        results = algorithm.search(query)
        self.assertTrue(len(results) > 0)
    
    def test_performance_with_complex_query(self):
        """Testa performance com query complexa."""
        algorithm = SemanticSearchAlgorithm()
        algorithm.configure({})
        
        # Complex query with lots of text
        complex_text = " ".join([
            "machine learning", "artificial intelligence", "deep learning",
            "neural networks", "python programming", "data science",
            "statistics", "algorithms", "computer vision", "natural language processing"
        ] * 10)  # Repeat to make it larger
        
        query = SearchQuery(
            title="Comprehensive AI and Machine Learning Guide",
            authors=["Dr. Jane Smith", "Prof. John Doe"],
            text_content=complex_text
        )
        
        import time
        start_time = time.time()
        results = algorithm.search(query)
        execution_time = time.time() - start_time
        
        # Should complete in reasonable time
        self.assertTrue(execution_time < 2.0)  # Less than 2 seconds
        self.assertTrue(len(results) > 0)


if __name__ == '__main__':
    unittest.main()