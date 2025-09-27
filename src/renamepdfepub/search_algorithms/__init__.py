"""
Search Algorithms Package - Algoritmos de busca e similaridade para metadados.

Este pacote contém implementações de vários algoritmos de busca e similaridade
para melhorar a precisão da identificação de metadados de livros.

Módulos disponíveis:
- base_search: Interface base para algoritmos
- fuzzy_search: Algoritmos de busca fuzzy (Levenshtein, Jaro-Winkler)
- semantic_search: Busca semântica (TF-IDF, N-grams)
- isbn_search: Busca especializada por ISBN
- hybrid_search: Combinação de múltiplos algoritmos
- search_orchestrator: Coordenação inteligente de algoritmos
"""

from .base_search import BaseSearchAlgorithm
from .search_orchestrator import SearchOrchestrator

__all__ = [
    'BaseSearchAlgorithm',
    'SearchOrchestrator'
]

# Versão do módulo de busca
__version__ = '0.1.0'