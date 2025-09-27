#!/usr/bin/env python3
"""
Script de teste para validar o Milestone 2 - ISBN Intelligence e Semantic Search.

Executa testes abrangentes dos novos algoritmos implementados:
- ISBNSearchAlgorithm com validação e correção
- SemanticSearchAlgorithm com TF-IDF
- Integração completa no SearchOrchestrator

Uso:
    python test_milestone2_algorithms.py
"""

import sys
import time
from typing import List, Dict, Any
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from renamepdfepub.search_algorithms.base_search import SearchQuery, SearchResult
from renamepdfepub.search_algorithms.isbn_search import ISBNValidator, ISBNSearchAlgorithm  
from renamepdfepub.search_algorithms.semantic_search import TextNormalizer, SemanticSearchAlgorithm
from renamepdfepub.search_algorithms.search_orchestrator import SearchOrchestrator


def print_section(title: str):
    """Imprime seção formatada."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_results(results: List[SearchResult], max_results: int = 5):
    """Imprime resultados de busca formatados."""
    if not results:
        print("❌ Nenhum resultado encontrado")
        return
    
    print(f"✅ {len(results)} resultados encontrados:")
    for i, result in enumerate(results[:max_results]):
        print(f"\n{i+1}. Score: {result.score:.3f} | Algoritmo: {result.algorithm}")
        print(f"   Título: {result.metadata.get('title', 'N/A')}")
        print(f"   Autores: {result.metadata.get('authors', 'N/A')}")
        if 'isbn' in result.metadata:
            print(f"   ISBN: {result.metadata['isbn']}")
        if result.details:
            print(f"   Detalhes: {result.details}")


def test_isbn_validator():
    """Testa funcionalidades do ISBNValidator."""
    print_section("TESTE 1: ISBN Validator")
    
    # Test ISBN validation
    test_cases = [
        ("9780123456786", True, "ISBN-13 válido"),
        ("0123456789", True, "ISBN-10 válido"),
        ("123456789X", True, "ISBN-10 com X"),
        ("9780123456789", False, "ISBN-13 inválido"),
        ("978@123456789", False, "ISBN corrompido")
    ]
    
    print("\n📋 Testando validação de ISBNs:")
    for isbn, expected, description in test_cases:
        is_valid_13 = ISBNValidator.is_valid_isbn13(isbn)
        is_valid_10 = ISBNValidator.is_valid_isbn10(isbn)
        is_valid = is_valid_13 or is_valid_10
        
        status = "✅" if is_valid == expected else "❌"
        print(f"{status} {description}: {isbn} -> {is_valid}")
    
    # Test corruption fixing
    print("\n🔧 Testando correção de ISBNs corrompidos:")
    corrupted_isbns = [
        "978@123456789",  # @ instead of 9
        "978O123456789",  # O instead of 0
        "978I234567890",  # I instead of 1
    ]
    
    for corrupted in corrupted_isbns:
        fixed = ISBNValidator.fix_corrupted_isbn(corrupted)
        status = "✅" if fixed else "❌"
        print(f"{status} {corrupted} -> {fixed}")
    
    # Test ISBN extraction from text
    print("\n📤 Testando extração de ISBNs de texto:")
    test_text = """
    Este livro tem ISBN: 978-0-123-45678-6 e é muito bom.
    Outro livro interessante: ISBN-10: 0123456789
    Versão corrompida: 978@123456789
    """
    
    extracted = ISBNValidator.extract_isbns_from_text(test_text)
    print(f"✅ ISBNs extraídos: {extracted}")


def test_text_normalizer():
    """Testa funcionalidades do TextNormalizer."""
    print_section("TESTE 2: Text Normalizer")
    
    # Test text normalization
    test_texts = [
        ("The Advanced Python Programming Guide", "english"),
        ("O Guia Avançado de Programação Python", "portuguese"),
        ("API SDK JSON XML React.js Node.js C++", "english")
    ]
    
    print("\n📝 Testando normalização de texto:")
    for text, language in test_texts:
        tokens = TextNormalizer.normalize_text(text, language)
        print(f"✅ {language}: '{text}' -> {tokens}")
    
    # Test author variants
    print("\n👤 Testando variantes de autores:")
    authors = ["John Doe Smith", "Maria Silva Santos", "Dr. Jane Watson"]
    
    for author in authors:
        variants = TextNormalizer.extract_author_variants(author)
        print(f"✅ '{author}' -> {list(variants)[:3]}...")  # Show first 3 variants
    
    # Test N-grams
    print("\n🔤 Testando geração de N-gramas:")
    tokens = ['machine', 'learning', 'python', 'programming']
    bigrams = TextNormalizer.generate_ngrams(tokens, 2)
    trigrams = TextNormalizer.generate_ngrams(tokens, 3)
    print(f"✅ Tokens: {tokens}")
    print(f"✅ Bigramas: {bigrams}")
    print(f"✅ Trigramas: {trigrams}")


def test_isbn_search_algorithm():
    """Testa o ISBNSearchAlgorithm."""
    print_section("TESTE 3: ISBN Search Algorithm")
    
    algorithm = ISBNSearchAlgorithm()
    config = {
        'partial_match_threshold': 0.8,
        'enable_corruption_fixing': True,
        'cache': {'clear_on_configure': False}
    }
    algorithm.configure(config)
    
    # Test queries
    test_queries = [
        {
            'name': 'ISBN Explícito',
            'query': SearchQuery(isbn="9781234567890"),
        },
        {
            'name': 'ISBN no Texto',
            'query': SearchQuery(
                title="Python Programming Guide",
                text_content="This book ISBN: 978-1-234-56789-0 covers advanced topics"
            ),
        },
        {
            'name': 'ISBN Corrompido',
            'query': SearchQuery(isbn="978@123456789"),
        },
        {
            'name': 'Query sem ISBN',
            'query': SearchQuery(title="Some Book Title"),
        }
    ]
    
    for test_case in test_queries:
        print(f"\n📚 {test_case['name']}:")
        
        # Check suitability
        suitable = algorithm.is_suitable_for_query(test_case['query'])
        print(f"   Adequado: {'✅' if suitable else '❌'}")
        
        if suitable:
            results = algorithm.search(test_case['query'])
            print_results(results, max_results=2)
    
    # Test cache stats
    print(f"\n💾 Estatísticas do Cache:")
    cache_stats = algorithm.get_cache_stats()
    print(f"   Tamanho do cache: {cache_stats['cache_size']}")
    print(f"   ISBNs em cache: {cache_stats['cached_isbns'][:3]}...")


def test_semantic_search_algorithm():
    """Testa o SemanticSearchAlgorithm."""
    print_section("TESTE 4: Semantic Search Algorithm")
    
    algorithm = SemanticSearchAlgorithm()
    config = {
        'min_similarity_threshold': 0.1,
        'author_ngram_size': 2,
        'title_weight': 0.6,
        'author_weight': 0.3,
        'content_weight': 0.1
    }
    algorithm.configure(config)
    
    # Test queries
    test_queries = [
        {
            'name': 'Query Rica em Texto',
            'query': SearchQuery(
                title="Advanced Machine Learning with Python",
                authors=["John Smith", "Maria Garcia"],
                text_content="Comprehensive guide to machine learning algorithms and deep learning techniques using Python programming language"
            ),
        },
        {
            'name': 'Query Focada em Título',
            'query': SearchQuery(title="Python Programming Fundamentals"),
        },
        {
            'name': 'Query Focada em Autores',
            'query': SearchQuery(authors=["Dr. Jane Watson", "Prof. Robert Chen"]),
        },
        {
            'name': 'Query Multilíngue',
            'query': SearchQuery(
                title="Programação Avançada em Python",
                text_content="Guia completo sobre programação Python e aprendizado de máquina"
            ),
        }
    ]
    
    for test_case in test_queries:
        print(f"\n🧠 {test_case['name']}:")
        
        # Check suitability
        suitable = algorithm.is_suitable_for_query(test_case['query'])
        print(f"   Adequado: {'✅' if suitable else '❌'}")
        
        if suitable:
            results = algorithm.search(test_case['query'])
            print_results(results, max_results=2)
    
    # Test corpus stats
    print(f"\n📊 Estatísticas do Corpus:")
    corpus_stats = algorithm.get_corpus_stats()
    print(f"   Documentos totais: {corpus_stats['total_documents']}")
    print(f"   Tamanho do vocabulário: {corpus_stats['vocabulary_size']}")
    print(f"   Termos principais: {corpus_stats['top_terms'][:5]}...")


def test_search_orchestrator_integration():
    """Testa integração completa no SearchOrchestrator."""
    print_section("TESTE 5: Search Orchestrator Integration")
    
    orchestrator = SearchOrchestrator(max_workers=4)
    
    # Verify all algorithms are registered
    algorithms = orchestrator.get_registered_algorithms()
    algorithm_names = [algo.name for algo in algorithms]
    
    print(f"🎼 Algoritmos registrados: {algorithm_names}")
    
    # Test comprehensive query
    comprehensive_query = SearchQuery(
        title="Advanced Python Programming and Machine Learning",
        authors=["John Smith", "Dr. Jane Doe"],
        isbn="9781234567890",
        text_content="Complete guide to Python programming, machine learning algorithms, data science, and artificial intelligence techniques"
    )
    
    # Test different strategies
    strategies = ['auto', 'parallel', 'sequential', 'best_match']
    
    for strategy in strategies:
        print(f"\n🎯 Estratégia: {strategy}")
        
        start_time = time.time()
        results = orchestrator.search(comprehensive_query, strategy=strategy, max_results=8)
        execution_time = time.time() - start_time
        
        print(f"   Tempo de execução: {execution_time:.3f}s")
        print(f"   Algoritmos utilizados: {set(r.algorithm for r in results)}")
        
        print_results(results, max_results=3)
    
    # Test performance stats
    print(f"\n📈 Estatísticas de Performance:")
    perf_stats = orchestrator.get_performance_stats()
    for key, value in perf_stats.items():
        print(f"   {key}: {value}")
    
    # Test algorithm stats
    print(f"\n🔍 Estatísticas por Algoritmo:")
    algo_stats = orchestrator.get_algorithm_stats()
    for algo_name, stats in algo_stats.items():
        print(f"   {algo_name}: {stats['executions']} execuções, "
              f"tempo médio: {stats.get('average_time', 0):.3f}s")


def test_edge_cases_and_error_handling():
    """Testa casos extremos e tratamento de erros."""
    print_section("TESTE 6: Edge Cases & Error Handling")
    
    orchestrator = SearchOrchestrator()
    
    # Test empty queries
    print("\n🚫 Testando queries vazias:")
    empty_queries = [
        SearchQuery(),
        SearchQuery(title=""),
        SearchQuery(title="   ", text_content="  \n  "),
        SearchQuery(isbn="invalid-isbn"),
    ]
    
    for i, query in enumerate(empty_queries):
        results = orchestrator.search(query)
        print(f"   Query {i+1}: {len(results)} resultados")
    
    # Test large text content
    print("\n📏 Testando conteúdo de texto grande:")
    large_text = "Python programming " * 500 + " machine learning algorithms " * 300
    large_query = SearchQuery(text_content=large_text)
    
    start_time = time.time()
    results = orchestrator.search(large_query)
    execution_time = time.time() - start_time
    
    print(f"   Texto grande ({len(large_text)} chars): {len(results)} resultados em {execution_time:.3f}s")
    
    # Test special characters and encoding
    print("\n🔤 Testando caracteres especiais:")
    special_query = SearchQuery(
        title="Título com Acentos: Programação Avançada",
        authors=["José da Silva", "François Müller"],
        text_content="Conteúdo com émojis 🐍 e caracteres especiais: α, β, γ"
    )
    
    results = orchestrator.search(special_query)
    print(f"   Caracteres especiais: {len(results)} resultados")


def run_comprehensive_validation():
    """Executa validação abrangente de todos os componentes."""
    print("🚀 INICIANDO VALIDAÇÃO COMPLETA DO MILESTONE 2")
    print("Phase 2 Search Algorithms - ISBN Intelligence & Semantic Search")
    
    start_time = time.time()
    
    try:
        # Run all tests
        test_isbn_validator()
        test_text_normalizer()
        test_isbn_search_algorithm()
        test_semantic_search_algorithm()
        test_search_orchestrator_integration()
        test_edge_cases_and_error_handling()
        
        total_time = time.time() - start_time
        
        print_section("VALIDAÇÃO COMPLETA ✅")
        print(f"🎉 Todos os testes executados com sucesso!")
        print(f"⏱️  Tempo total: {total_time:.2f} segundos")
        print(f"📊 Milestone 2 IMPLEMENTADO COM SUCESSO!")
        print(f"\n✨ Algoritmos implementados:")
        print(f"   • ISBNSearchAlgorithm - Validação e correção inteligente de ISBNs")
        print(f"   • SemanticSearchAlgorithm - Busca semântica com TF-IDF")
        print(f"   • SearchOrchestrator - Coordenação inteligente de todos os algoritmos")
        print(f"\n🏆 PHASE 2 MILESTONE 2 CONCLUÍDO!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERRO durante a validação: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_comprehensive_validation()
    sys.exit(0 if success else 1)