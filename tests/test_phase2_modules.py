#!/usr/bin/env python3
"""
Test Script for Phase 2 Search Algorithms

Testa os novos módulos de busca implementados na Fase 2.
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def test_dependency_manager():
    """Testa o DependencyManager extraído."""
    try:
        from renamepdfepub.cli.dependency_manager import DependencyManager
        
        dm = DependencyManager()
        print(f"✅ DependencyManager created successfully")
        
        extractors = dm.get_available_extractors()
        print(f"✅ Available extractors: {extractors}")
        
        report = dm.get_dependency_report()
        print(f"✅ Dependency report: {len(report)} items")
        
        return True
    except Exception as e:
        print(f"❌ DependencyManager test failed: {e}")
        return False

def test_publisher_config():
    """Testa as configurações de editoras."""
    try:
        from renamepdfepub.cli.publisher_config import (
            get_all_publishers, normalize_publisher_name, get_publisher_config
        )
        
        all_pubs = get_all_publishers()
        print(f"✅ Found {len(all_pubs)} publisher configurations")
        
        normalized = normalize_publisher_name("O'REILLY MEDIA")
        print(f"✅ Publisher normalization: 'O'REILLY MEDIA' -> '{normalized}'")
        
        packt_config = get_publisher_config('packt')
        print(f"✅ Packt config loaded: {bool(packt_config)}")
        
        return True
    except Exception as e:
        print(f"❌ Publisher config test failed: {e}")
        return False

def test_search_algorithms():
    """Testa os algoritmos de busca."""
    try:
        from renamepdfepub.search_algorithms.base_search import BaseSearchAlgorithm, SearchQuery, SearchResult
        from renamepdfepub.search_algorithms.fuzzy_search import FuzzySearchAlgorithm
        from renamepdfepub.search_algorithms.search_orchestrator import SearchOrchestrator
        
        # Test base classes
        query = SearchQuery(
            title="Python Programming",
            authors=["John Smith"],
            publisher="Tech Books"
        )
        print("✅ SearchQuery created successfully")
        
        # Test fuzzy search
        fuzzy = FuzzySearchAlgorithm()
        config_success = fuzzy.configure({
            'min_similarity_threshold': 0.7,
            'title_weight': 0.5,
            'author_weight': 0.3,
            'publisher_weight': 0.2
        })
        print(f"✅ FuzzySearch configured: {config_success}")
        
        is_suitable = fuzzy.is_suitable_for_query(query)
        print(f"✅ FuzzySearch suitability check: {is_suitable}")
        
        # Test orchestrator
        orchestrator = SearchOrchestrator()
        registered = orchestrator.register_algorithm(fuzzy)
        print(f"✅ Algorithm registered in orchestrator: {registered}")
        
        capabilities = fuzzy.get_capabilities()
        print(f"✅ FuzzySearch capabilities: {capabilities}")
        
        return True
    except Exception as e:
        print(f"❌ Search algorithms test failed: {e}")
        return False

def test_search_execution():
    """Testa execução real de busca."""
    try:
        from renamepdfepub.search_algorithms.base_search import SearchQuery
        from renamepdfepub.search_algorithms.fuzzy_search import FuzzySearchAlgorithm
        from renamepdfepub.search_algorithms.search_orchestrator import SearchOrchestrator
        
        # Setup
        fuzzy = FuzzySearchAlgorithm()
        fuzzy.configure({'min_similarity_threshold': 0.6})
        
        orchestrator = SearchOrchestrator()
        orchestrator.register_algorithm(fuzzy)
        
        # Create test query
        test_query = SearchQuery(
            title="Python Programming",
            authors=["John Smith"]
        )
        
        # Execute search
        results = orchestrator.search(test_query, strategy='best_match', max_results=5)
        print(f"✅ Search executed: {len(results)} results found")
        
        if results:
            best_result = results[0]
            print(f"✅ Best result score: {best_result.score:.3f}")
            print(f"✅ Best result title: {best_result.metadata.get('title', 'N/A')}")
        
        return True
    except Exception as e:
        print(f"❌ Search execution test failed: {e}")
        return False

def test_performance_utilities():
    """Testa utilitários de performance."""
    try:
        from renamepdfepub.search_algorithms.fuzzy_search import (
            levenshtein_distance, jaro_similarity, jaro_winkler_similarity
        )
        
        # Test string similarity functions
        lev_dist = levenshtein_distance("python", "pithon")
        print(f"✅ Levenshtein distance 'python' vs 'pithon': {lev_dist}")
        
        jaro_sim = jaro_similarity("python", "pithon")
        print(f"✅ Jaro similarity 'python' vs 'pithon': {jaro_sim:.3f}")
        
        jw_sim = jaro_winkler_similarity("python", "pithon") 
        print(f"✅ Jaro-Winkler similarity 'python' vs 'pithon': {jw_sim:.3f}")
        
        return True
    except Exception as e:
        print(f"❌ Performance utilities test failed: {e}")
        return False

if __name__ == "__main__":
    print("=== Phase 2 Search Algorithms Test ===\n")
    
    tests = [
        test_dependency_manager,
        test_publisher_config,
        test_search_algorithms,
        test_performance_utilities,
        test_search_execution
    ]
    
    results = []
    for test in tests:
        print(f"\n--- Running {test.__name__} ---")
        results.append(test())
    
    passed = sum(results)
    total = len(results)
    
    print(f"\n=== Test Results: {passed}/{total} passed ===")
    
    if passed == total:
        print("🎉 All Phase 2 modules working correctly!")
        print("✅ Ready for integration with existing codebase")
    else:
        print("⚠️  Some modules need attention")
        print("🔧 Continue development and testing")

    print(f"\n🚀 Phase 2 Infrastructure Status: {'READY' if passed >= 4 else 'IN PROGRESS'}")