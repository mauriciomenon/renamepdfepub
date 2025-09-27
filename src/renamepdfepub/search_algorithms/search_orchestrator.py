"""
Search Orchestrator - Coordenação inteligente de múltiplos algoritmos de busca.

Gerencia a execução de diferentes algoritmos de busca, combinando resultados
e selecionando as melhores estratégias baseado no contexto da query.
"""

import time
from typing import Dict, List, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from .base_search import BaseSearchAlgorithm, SearchQuery, SearchResult


class SearchOrchestrator:
    """
    Coordenador que gerencia múltiplos algoritmos de busca.
    
    Responsável por:
    - Selecionar algoritmos adequados para cada query
    - Executar buscas em paralelo quando possível
    - Combinar e ranquear resultados de múltiplos algoritmos
    - Aplicar estratégias de fallback
    """
    
    def __init__(self, max_workers: int = 3):
        """
        Inicializa o orquestrador.
        
        Args:
            max_workers: Número máximo de workers para execução paralela
        """
        self.algorithms: Dict[str, BaseSearchAlgorithm] = {}
        self.max_workers = max_workers
        self.default_strategy = 'adaptive'
        self.combination_weights = {
            'score': 0.7,
            'algorithm_reliability': 0.2,
            'result_consistency': 0.1
        }
        
    def register_algorithm(self, algorithm: BaseSearchAlgorithm) -> bool:
        """
        Registra um algoritmo de busca.
        
        Args:
            algorithm: Instância do algoritmo a ser registrado
            
        Returns:
            bool: True se registro foi bem-sucedido
        """
        try:
            self.algorithms[algorithm.name] = algorithm
            return True
        except Exception:
            return False
    
    def unregister_algorithm(self, algorithm_name: str) -> bool:
        """
        Remove um algoritmo registrado.
        
        Args:
            algorithm_name: Nome do algoritmo a ser removido
            
        Returns:
            bool: True se remoção foi bem-sucedida
        """
        return self.algorithms.pop(algorithm_name, None) is not None
    
    def search(self, 
               query: SearchQuery, 
               strategy: str = 'auto',
               max_results: int = 10) -> List[SearchResult]:
        """
        Executa busca coordenada usando múltiplos algoritmos.
        
        Args:
            query: Query de busca
            strategy: Estratégia de busca ('auto', 'parallel', 'sequential', 'best_match')
            max_results: Número máximo de resultados
            
        Returns:
            List[SearchResult]: Resultados combinados e ranqueados
        """
        if strategy == 'auto':
            strategy = self._select_optimal_strategy(query)
        
        if strategy == 'parallel':
            return self._parallel_search(query, max_results)
        elif strategy == 'sequential':
            return self._sequential_search(query, max_results)
        elif strategy == 'best_match':
            return self._best_match_search(query, max_results)
        else:
            # Default to adaptive strategy
            return self._adaptive_search(query, max_results)
    
    def _select_optimal_strategy(self, query: SearchQuery) -> str:
        """
        Seleciona a estratégia ótima baseada na query.
        
        Args:
            query: Query a ser analisada
            
        Returns:
            str: Nome da estratégia recomendada
        """
        suitable_algorithms = [
            algo for algo in self.algorithms.values()
            if algo.is_suitable_for_query(query)
        ]
        
        if len(suitable_algorithms) <= 1:
            return 'best_match'
        elif len(suitable_algorithms) <= 3:
            return 'parallel'
        else:
            return 'adaptive'
    
    def _parallel_search(self, query: SearchQuery, max_results: int) -> List[SearchResult]:
        """
        Executa busca paralela em todos os algoritmos adequados.
        
        Args:
            query: Query de busca
            max_results: Máximo de resultados
            
        Returns:
            List[SearchResult]: Resultados combinados
        """
        suitable_algorithms = [
            algo for algo in self.algorithms.values()
            if algo.is_suitable_for_query(query)
        ]
        
        if not suitable_algorithms:
            return []
        
        all_results = []
        
        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(suitable_algorithms))) as executor:
            # Submit search tasks
            future_to_algorithm = {
                executor.submit(algorithm.search, query): algorithm
                for algorithm in suitable_algorithms
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_algorithm):
                algorithm = future_to_algorithm[future]
                try:
                    results = future.result(timeout=30)  # 30 second timeout
                    all_results.extend(results)
                except Exception as e:
                    # Log error but continue with other algorithms
                    print(f"Algorithm {algorithm.name} failed: {e}")
        
        return self._combine_and_rank_results(all_results, max_results)
    
    def _sequential_search(self, query: SearchQuery, max_results: int) -> List[SearchResult]:
        """
        Executa busca sequencial com estratégia de fallback.
        
        Args:
            query: Query de busca
            max_results: Máximo de resultados
            
        Returns:
            List[SearchResult]: Resultados da busca
        """
        # Order algorithms by preference/reliability
        ordered_algorithms = self._get_ordered_algorithms(query)
        
        for algorithm in ordered_algorithms:
            try:
                results = algorithm.search(query)
                if results and results[0].score >= 0.8:
                    # High confidence result found, return immediately
                    return results[:max_results]
            except Exception as e:
                print(f"Algorithm {algorithm.name} failed: {e}")
                continue
        
        # If no high-confidence results, collect all results
        all_results = []
        for algorithm in ordered_algorithms:
            try:
                results = algorithm.search(query)
                all_results.extend(results)
            except Exception:
                continue
        
        return self._combine_and_rank_results(all_results, max_results)
    
    def _best_match_search(self, query: SearchQuery, max_results: int) -> List[SearchResult]:
        """
        Seleciona o melhor algoritmo para a query e executa apenas ele.
        
        Args:
            query: Query de busca
            max_results: Máximo de resultados
            
        Returns:
            List[SearchResult]: Resultados do melhor algoritmo
        """
        best_algorithm = self._select_best_algorithm(query)
        
        if not best_algorithm:
            return []
        
        try:
            results = best_algorithm.search(query)
            return results[:max_results]
        except Exception as e:
            print(f"Best algorithm {best_algorithm.name} failed: {e}")
            return []
    
    def _adaptive_search(self, query: SearchQuery, max_results: int) -> List[SearchResult]:
        """
        Estratégia adaptativa que combina sequential e parallel baseado no contexto.
        
        Args:
            query: Query de busca
            max_results: Máximo de resultados
            
        Returns:
            List[SearchResult]: Resultados adaptados
        """
        # Start with best algorithm
        best_algorithm = self._select_best_algorithm(query)
        
        if best_algorithm:
            try:
                initial_results = best_algorithm.search(query)
                if initial_results and initial_results[0].score >= 0.9:
                    # Very high confidence, return immediately
                    return initial_results[:max_results]
            except Exception:
                pass
        
        # If no high confidence result, run parallel search with limited algorithms
        suitable_algorithms = [
            algo for algo in self.algorithms.values()
            if algo.is_suitable_for_query(query)
        ][:3]  # Limit to top 3 algorithms
        
        return self._parallel_search_limited(query, suitable_algorithms, max_results)
    
    def _parallel_search_limited(self, 
                               query: SearchQuery, 
                               algorithms: List[BaseSearchAlgorithm],
                               max_results: int) -> List[SearchResult]:
        """
        Executa busca paralela em conjunto limitado de algoritmos.
        
        Args:
            query: Query de busca
            algorithms: Lista de algoritmos a executar
            max_results: Máximo de resultados
            
        Returns:
            List[SearchResult]: Resultados combinados
        """
        if not algorithms:
            return []
        
        all_results = []
        
        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(algorithms))) as executor:
            future_to_algorithm = {
                executor.submit(algorithm.search, query): algorithm
                for algorithm in algorithms
            }
            
            for future in as_completed(future_to_algorithm):
                try:
                    results = future.result(timeout=30)
                    all_results.extend(results)
                except Exception:
                    continue
        
        return self._combine_and_rank_results(all_results, max_results)
    
    def _combine_and_rank_results(self, 
                                results: List[SearchResult], 
                                max_results: int) -> List[SearchResult]:
        """
        Combina e ranqueia resultados de múltiplos algoritmos.
        
        Args:
            results: Lista de todos os resultados
            max_results: Máximo de resultados a retornar
            
        Returns:
            List[SearchResult]: Resultados combinados e ranqueados
        """
        if not results:
            return []
        
        # Group results by ISBN or title+author to identify duplicates
        grouped_results = self._group_similar_results(results)
        
        # Calculate combined scores for each group
        final_results = []
        for group in grouped_results:
            combined_result = self._combine_result_group(group)
            final_results.append(combined_result)
        
        # Sort by combined score
        final_results.sort(key=lambda x: x.score, reverse=True)
        
        return final_results[:max_results]
    
    def _group_similar_results(self, results: List[SearchResult]) -> List[List[SearchResult]]:
        """
        Agrupa resultados similares (mesmo livro de algoritmos diferentes).
        
        Args:
            results: Lista de resultados
            
        Returns:
            List[List[SearchResult]]: Grupos de resultados similares
        """
        groups = []
        used_results = set()
        
        for i, result in enumerate(results):
            if i in used_results:
                continue
            
            group = [result]
            used_results.add(i)
            
            # Find similar results
            for j, other_result in enumerate(results):
                if j in used_results or i == j:
                    continue
                
                if self._are_results_similar(result, other_result):
                    group.append(other_result)
                    used_results.add(j)
            
            groups.append(group)
        
        return groups
    
    def _are_results_similar(self, result1: SearchResult, result2: SearchResult) -> bool:
        """
        Verifica se dois resultados representam o mesmo livro.
        
        Args:
            result1: Primeiro resultado
            result2: Segundo resultado
            
        Returns:
            bool: True se os resultados são similares
        """
        # Check ISBN first (most reliable)
        isbn1 = result1.metadata.get('isbn')
        isbn2 = result2.metadata.get('isbn')
        if isbn1 and isbn2 and isbn1 == isbn2:
            return True
        
        # Check title and first author
        title1 = result1.metadata.get('title', '').lower()
        title2 = result2.metadata.get('title', '').lower()
        
        authors1 = result1.metadata.get('authors', [])
        authors2 = result2.metadata.get('authors', [])
        
        first_author1 = authors1[0].lower() if authors1 else ''
        first_author2 = authors2[0].lower() if authors2 else ''
        
        # Simple similarity check
        title_similar = title1 and title2 and (
            title1 in title2 or title2 in title1 or
            abs(len(title1) - len(title2)) <= 3
        )
        
        author_similar = first_author1 and first_author2 and (
            first_author1 in first_author2 or first_author2 in first_author1
        )
        
        return title_similar and author_similar
    
    def _combine_result_group(self, group: List[SearchResult]) -> SearchResult:
        """
        Combina um grupo de resultados similares em um resultado único.
        
        Args:
            group: Grupo de resultados similares
            
        Returns:
            SearchResult: Resultado combinado
        """
        if len(group) == 1:
            return group[0]
        
        # Use result with highest score as base
        base_result = max(group, key=lambda x: x.score)
        
        # Calculate weighted average score
        total_weight = 0.0
        weighted_score = 0.0
        
        for result in group:
            # Weight based on algorithm reliability (simplified)
            weight = 1.0  # In real implementation, use algorithm stats
            weighted_score += result.score * weight
            total_weight += weight
        
        combined_score = min(weighted_score / total_weight if total_weight > 0 else 0.0, 1.0)
        
        # Combine metadata (prefer most complete)
        combined_metadata = base_result.metadata.copy()
        
        # Add details from all algorithms
        combined_details = {
            'source_algorithms': [r.algorithm for r in group],
            'individual_scores': [r.score for r in group],
            'combination_method': 'weighted_average'
        }
        
        return SearchResult(
            score=combined_score,
            metadata=combined_metadata,
            algorithm='OrchesteredSearch',
            details=combined_details
        )
    
    def _get_ordered_algorithms(self, query: SearchQuery) -> List[BaseSearchAlgorithm]:
        """
        Ordena algoritmos por adequação à query.
        
        Args:
            query: Query para análise
            
        Returns:
            List[BaseSearchAlgorithm]: Algoritmos ordenados por preferência
        """
        suitable = [
            algo for algo in self.algorithms.values()
            if algo.is_suitable_for_query(query)
        ]
        
        # Simple ordering by name for now
        # In real implementation, would use algorithm stats and suitability scores
        return sorted(suitable, key=lambda x: x.name)
    
    def _select_best_algorithm(self, query: SearchQuery) -> Optional[BaseSearchAlgorithm]:
        """
        Seleciona o melhor algoritmo para a query.
        
        Args:
            query: Query para análise
            
        Returns:
            Optional[BaseSearchAlgorithm]: Melhor algoritmo ou None
        """
        suitable = self._get_ordered_algorithms(query)
        return suitable[0] if suitable else None
    
    def get_algorithm_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Retorna estatísticas de todos os algoritmos registrados.
        
        Returns:
            Dict[str, Dict[str, Any]]: Estatísticas por algoritmo
        """
        return {
            name: algo.get_stats()
            for name, algo in self.algorithms.items()
        }
    
    def reset_all_stats(self):
        """Reseta estatísticas de todos os algoritmos."""
        for algorithm in self.algorithms.values():
            algorithm.reset_stats()