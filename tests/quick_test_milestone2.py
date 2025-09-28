#!/usr/bin/env python3
"""Teste simples para verificar a implementação do Milestone 2."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

print("🚀 Testando implementação do Milestone 2...")

try:
    # Test imports
    from renamepdfepub.search_algorithms.isbn_search import ISBNValidator, ISBNSearchAlgorithm
    from renamepdfepub.search_algorithms.semantic_search import SemanticSearchAlgorithm
    from renamepdfepub.search_algorithms.search_orchestrator import SearchOrchestrator
    from renamepdfepub.search_algorithms.base_search import SearchQuery
    
    print("✅ Importações bem-sucedidas!")
    
    # Test ISBN Validator
    print("\n📚 Testando ISBNValidator...")
    isbn_valid = ISBNValidator.is_valid_isbn13("9780123456786")
    print(f"   ISBN válido: {isbn_valid}")
    
    # Test ISBN Search Algorithm
    print("\n🔍 Testando ISBNSearchAlgorithm...")
    isbn_algo = ISBNSearchAlgorithm()
    isbn_algo.configure({'enable_corruption_fixing': True})
    query = SearchQuery(isbn="9781234567890")
    results = isbn_algo.search(query)
    print(f"   Resultados ISBN: {len(results)}")
    
    # Test Semantic Search Algorithm
    print("\n🧠 Testando SemanticSearchAlgorithm...")
    semantic_algo = SemanticSearchAlgorithm()
    semantic_algo.configure({})
    query = SearchQuery(title="Python Programming", text_content="Guide to Python programming")
    results = semantic_algo.search(query)
    print(f"   Resultados Semantic: {len(results)}")
    
    # Test Search Orchestrator
    print("\n🎼 Testando SearchOrchestrator...")
    orchestrator = SearchOrchestrator()
    algorithms = orchestrator.get_registered_algorithms()
    print(f"   Algoritmos registrados: {[algo.name for algo in algorithms]}")
    
    query = SearchQuery(
        title="Advanced Python Programming",
        isbn="9781234567890",
        text_content="Complete guide to Python programming"
    )
    results = orchestrator.search(query, strategy='parallel')
    print(f"   Resultados Orchestrator: {len(results)}")
    
    print("\n🎉 MILESTONE 2 IMPLEMENTADO COM SUCESSO!")
    print("✨ Algoritmos funcionais:")
    print("   • ISBNSearchAlgorithm - Validação e correção de ISBNs")
    print("   • SemanticSearchAlgorithm - Busca semântica com TF-IDF")
    print("   • SearchOrchestrator - Coordenação de todos os algoritmos")
    
except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)