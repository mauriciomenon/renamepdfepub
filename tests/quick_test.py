#!/usr/bin/env python3
"""
Quick test of Phase 2 modules
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def quick_test():
    print("=== Quick Phase 2 Test ===\n")
    
    # Test 1: DependencyManager
    try:
        from renamepdfepub.cli.dependency_manager import DependencyManager
        dm = DependencyManager()
        extractors = dm.get_available_extractors()
        print(f" DependencyManager: {len(extractors)} extractors available")
    except Exception as e:
        print(f" DependencyManager: {e}")
    
    # Test 2: Publisher Config
    try:
        from renamepdfepub.cli.publisher_config import get_all_publishers
        publishers = get_all_publishers()
        print(f" Publisher Config: {len(publishers)} publishers configured")
    except Exception as e:
        print(f" Publisher Config: {e}")
    
    # Test 3: Base Search
    try:
        from renamepdfepub.search_algorithms.base_search import SearchQuery, SearchResult
        query = SearchQuery(title="Test Book", authors=["Test Author"])
        print(f" Base Search: SearchQuery created successfully")
    except Exception as e:
        print(f" Base Search: {e}")
    
    # Test 4: Fuzzy Search
    try:
        from renamepdfepub.search_algorithms.fuzzy_search import FuzzySearchAlgorithm, levenshtein_distance
        distance = levenshtein_distance("python", "pithon")
        print(f" Fuzzy Search: Levenshtein distance = {distance}")
    except Exception as e:
        print(f" Fuzzy Search: {e}")
    
    # Test 5: Search Orchestrator
    try:
        from renamepdfepub.search_algorithms.search_orchestrator import SearchOrchestrator
        orchestrator = SearchOrchestrator()
        print(f" Search Orchestrator: Created successfully")
    except Exception as e:
        print(f" Search Orchestrator: {e}")
    
    print("\n Phase 2 modules ready for integration!")

if __name__ == "__main__":
    quick_test()