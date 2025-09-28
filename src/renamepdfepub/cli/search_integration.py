"""
CLI Integration Module - Integração completa dos algoritmos de busca com o CLI.

Funcionalidades:
- Interface unificada para todos os algoritmos de busca
- Integração com QueryPreprocessor e MultiLayerCache
- Commands avançados para busca inteligente
- Configuração e monitoramento
"""

import json
import time
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

from .query_preprocessor import QueryPreprocessor, QueryAnalysis
from ..core.multi_layer_cache import SearchCache
from ..search_algorithms.search_orchestrator import SearchOrchestrator
from ..search_algorithms.base_search import SearchQuery, SearchResult


class SearchCLIIntegration:
    """
    Integração completa dos algoritmos de busca com CLI.
    
    Combina:
    - QueryPreprocessor para análise inteligente de queries
    - SearchOrchestrator para execução de algoritmos
    - MultiLayerCache para performance otimizada
    """
    
    def __init__(self, config_file: str = "search_config.json"):
        """
        Inicializa integração CLI.
        
        Args:
            config_file: Arquivo de configuração
        """
        self.config_file = Path(config_file)
        self.config = self._load_config()
        
        # Initialize components
        self.preprocessor = QueryPreprocessor()
        self.orchestrator = SearchOrchestrator(
            max_workers=self.config.get('max_workers', 4)
        )
        self.cache = SearchCache(
            cache_dir=self.config.get('cache_dir', '.search_cache')
        )
        
        # Configure algorithms
        self._configure_algorithms()
        
        # Statistics
        self.session_stats = {
            'queries_processed': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'total_search_time': 0.0,
            'average_search_time': 0.0,
            'session_start': time.time()
        }
    
    def search_intelligent(self, 
                          query_text: str,
                          strategy: str = 'auto',
                          max_results: int = 10,
                          use_cache: bool = True,
                          preprocessing: bool = True) -> Dict[str, Any]:
        """
        Executa busca inteligente completa.
        
        Args:
            query_text: Texto da query
            strategy: Estratégia de busca
            max_results: Número máximo de resultados
            use_cache: Se deve usar cache
            preprocessing: Se deve preprocessar a query
            
        Returns:
            Dict[str, Any]: Resultado completo com metadados
        """
        start_time = time.time()
        
        # Update session stats
        self.session_stats['queries_processed'] += 1
        
        try:
            # Step 1: Preprocess query
            if preprocessing:
                analysis = self.preprocessor.analyze_query(query_text)
                search_query = self.preprocessor.preprocess_for_search(query_text)
            else:
                analysis = None
                search_query = SearchQuery(text_content=query_text)
            
            # Step 2: Check cache
            cached_results = None
            if use_cache:
                cached_results = self.cache.get_search_results(search_query)
                if cached_results:
                    self.session_stats['cache_hits'] += 1
                    
                    execution_time = time.time() - start_time
                    self._update_session_stats(execution_time)
                    
                    return {
                        'results': cached_results[:max_results],
                        'total_found': len(cached_results),
                        'execution_time': execution_time,
                        'source': 'cache',
                        'query_analysis': analysis,
                        'search_strategy': strategy,
                        'cache_hit': True
                    }
            
            # Cache miss
            if use_cache:
                self.session_stats['cache_misses'] += 1
            
            # Step 3: Execute search
            results = self.orchestrator.search(
                search_query,
                strategy=strategy,
                max_results=max_results * 2  # Get more for caching
            )
            
            # Step 4: Cache results
            if use_cache and results:
                cache_ttl = self.config.get('cache_ttl', 1800)  # 30 minutes
                self.cache.cache_search_results(search_query, results, cache_ttl)
            
            execution_time = time.time() - start_time
            self._update_session_stats(execution_time)
            
            return {
                'results': results[:max_results],
                'total_found': len(results),
                'execution_time': execution_time,
                'source': 'search',
                'query_analysis': analysis,
                'search_strategy': strategy,
                'cache_hit': False,
                'algorithms_used': list(set(r.algorithm for r in results))
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._update_session_stats(execution_time)
            
            return {
                'error': str(e),
                'execution_time': execution_time,
                'results': [],
                'total_found': 0,
                'source': 'error'
            }
    
    def get_query_suggestions(self, partial_query: str) -> Dict[str, Any]:
        """
        Obtém sugestões para query parcial.
        
        Args:
            partial_query: Query parcial
            
        Returns:
            Dict[str, Any]: Sugestões e completações
        """
        suggestions = self.preprocessor.get_auto_suggestions(partial_query)
        
        return {
            'suggestions': suggestions.suggestions,
            'completions': suggestions.completions,
            'corrections': suggestions.corrections,
            'confidence': suggestions.confidence
        }
    
    def analyze_query(self, query_text: str) -> Dict[str, Any]:
        """
        Analisa uma query sem executar busca.
        
        Args:
            query_text: Texto da query
            
        Returns:
            Dict[str, Any]: Análise completa
        """
        analysis = self.preprocessor.analyze_query(query_text)
        
        return {
            'original_query': analysis.original_query,
            'cleaned_query': analysis.cleaned_query,
            'detected_entities': analysis.detected_entities,
            'suggested_corrections': analysis.suggested_corrections,
            'confidence_scores': analysis.confidence_scores,
            'query_type': analysis.query_type,
            'language': analysis.language,
            'complexity_score': analysis.complexity_score,
            'processing_time': analysis.processing_time,
            'suitable_algorithms': [
                algo.name for algo in self.orchestrator.get_registered_algorithms()
                if algo.is_suitable_for_query(self.preprocessor.preprocess_for_search(query_text))
            ]
        }
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Obtém estatísticas abrangentes do sistema."""
        return {
            'session': self.session_stats,
            'preprocessor': self.preprocessor.get_stats(),
            'orchestrator': self.orchestrator.get_performance_stats(),
            'algorithms': self.orchestrator.get_algorithm_stats(),
            'cache': self.cache.get_stats()
        }
    
    def configure_algorithm(self, algorithm_name: str, config: Dict[str, Any]) -> bool:
        """
        Configura algoritmo específico.
        
        Args:
            algorithm_name: Nome do algoritmo
            config: Configuração
            
        Returns:
            bool: True se sucesso
        """
        algorithms = {algo.name: algo for algo in self.orchestrator.get_registered_algorithms()}
        
        if algorithm_name in algorithms:
            return algorithms[algorithm_name].configure(config)
        
        return False
    
    def clear_cache(self) -> bool:
        """Limpa todo o cache."""
        return self.cache.cache.clear()
    
    def export_session_report(self, output_file: str) -> bool:
        """
        Exporta relatório da sessão.
        
        Args:
            output_file: Arquivo de saída
            
        Returns:
            bool: True se sucesso
        """
        try:
            report = {
                'session_info': {
                    'start_time': self.session_stats['session_start'],
                    'duration': time.time() - self.session_stats['session_start'],
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                },
                'statistics': self.get_comprehensive_stats(),
                'configuration': self.config
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, default=str)
            
            return True
            
        except Exception:
            return False
    
    def _load_config(self) -> Dict[str, Any]:
        """Carrega configuração."""
        default_config = {
            'max_workers': 4,
            'cache_dir': '.search_cache',
            'cache_ttl': 1800,
            'algorithms': {
                'fuzzy': {
                    'similarity_threshold': 0.6,
                    'use_levenshtein': True,
                    'use_jaro_winkler': True,
                    'levenshtein_weight': 0.6,
                    'jaro_winkler_weight': 0.4
                },
                'isbn': {
                    'partial_match_threshold': 0.8,
                    'enable_corruption_fixing': True,
                    'cache': {'clear_on_configure': False}
                },
                'semantic': {
                    'min_similarity_threshold': 0.1,
                    'author_ngram_size': 2,
                    'title_weight': 0.6,
                    'author_weight': 0.3,
                    'content_weight': 0.1
                }
            }
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                
                # Merge with default config
                default_config.update(user_config)
                
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        
        # Save current config
        self._save_config(default_config)
        
        return default_config
    
    def _save_config(self, config: Dict[str, Any]):
        """Salva configuração."""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
        except:
            pass
    
    def _configure_algorithms(self):
        """Configura todos os algoritmos."""
        algorithm_configs = self.config.get('algorithms', {})
        
        for algo in self.orchestrator.get_registered_algorithms():
            if algo.name.lower() in algorithm_configs:
                algo.configure(algorithm_configs[algo.name.lower()])
    
    def _update_session_stats(self, execution_time: float):
        """Atualiza estatísticas da sessão."""
        self.session_stats['total_search_time'] += execution_time
        self.session_stats['average_search_time'] = (
            self.session_stats['total_search_time'] / 
            self.session_stats['queries_processed']
        )


class SearchCommands:
    """Comandos CLI para o sistema de busca."""
    
    def __init__(self, integration: SearchCLIIntegration):
        """
        Inicializa comandos CLI.
        
        Args:
            integration: Integração CLI
        """
        self.integration = integration
    
    def search(self, query: str, **kwargs) -> str:
        """
        Comando de busca principal.
        
        Args:
            query: Texto da query
            **kwargs: Argumentos adicionais
            
        Returns:
            str: Resultado formatado
        """
        result = self.integration.search_intelligent(query, **kwargs)
        
        return self._format_search_results(result)
    
    def analyze(self, query: str) -> str:
        """
        Comando de análise de query.
        
        Args:
            query: Texto da query
            
        Returns:
            str: Análise formatada
        """
        analysis = self.integration.analyze_query(query)
        
        return self._format_query_analysis(analysis)
    
    def suggest(self, partial_query: str) -> str:
        """
        Comando de sugestões.
        
        Args:
            partial_query: Query parcial
            
        Returns:
            str: Sugestões formatadas
        """
        suggestions = self.integration.get_query_suggestions(partial_query)
        
        return self._format_suggestions(suggestions)
    
    def stats(self) -> str:
        """
        Comando de estatísticas.
        
        Returns:
            str: Estatísticas formatadas
        """
        stats = self.integration.get_comprehensive_stats()
        
        return self._format_stats(stats)
    
    def clear_cache(self) -> str:
        """
        Comando para limpar cache.
        
        Returns:
            str: Resultado da operação
        """
        success = self.integration.clear_cache()
        
        if success:
            return " Cache limpo com sucesso!"
        else:
            return " Erro ao limpar cache."
    
    def export_report(self, filename: str) -> str:
        """
        Comando para exportar relatório.
        
        Args:
            filename: Nome do arquivo
            
        Returns:
            str: Resultado da operação
        """
        success = self.integration.export_session_report(filename)
        
        if success:
            return f" Relatório exportado para {filename}"
        else:
            return " Erro ao exportar relatório."
    
    def _format_search_results(self, result: Dict[str, Any]) -> str:
        """Formata resultados de busca."""
        if 'error' in result:
            return f" Erro: {result['error']}"
        
        lines = []
        lines.append(f"🔍 Busca executada em {result['execution_time']:.3f}s")
        lines.append(f"📊 {result['total_found']} resultados encontrados")
        lines.append(f"🎯 Fonte: {result['source']}")
        
        if result.get('cache_hit'):
            lines.append("💾 Cache HIT")
        
        if result.get('algorithms_used'):
            lines.append(f"🤖 Algoritmos: {', '.join(result['algorithms_used'])}")
        
        lines.append("")
        
        for i, search_result in enumerate(result['results'][:5], 1):
            lines.append(f"{i}. Score: {search_result.score:.3f} | {search_result.algorithm}")
            lines.append(f"   📚 {search_result.metadata.get('title', 'N/A')}")
            lines.append(f"   👤 {search_result.metadata.get('authors', 'N/A')}")
            if search_result.metadata.get('isbn'):
                lines.append(f"   📖 ISBN: {search_result.metadata['isbn']}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_query_analysis(self, analysis: Dict[str, Any]) -> str:
        """Formata análise de query."""
        lines = []
        lines.append(f"🔍 Análise da Query")
        lines.append(f"Original: {analysis['original_query']}")
        lines.append(f"Limpa: {analysis['cleaned_query']}")
        lines.append(f"Tipo: {analysis['query_type']}")
        lines.append(f"Idioma: {analysis['language']}")
        lines.append(f"Complexidade: {analysis['complexity_score']:.2f}")
        lines.append("")
        
        if analysis['detected_entities']:
            lines.append("🎯 Entidades Detectadas:")
            for entity_type, entities in analysis['detected_entities'].items():
                if entities:
                    lines.append(f"  {entity_type}: {entities}")
        
        if analysis['suggested_corrections']:
            lines.append("✏ Correções Sugeridas:")
            for correction in analysis['suggested_corrections']:
                lines.append(f"  • {correction}")
        
        if analysis['suitable_algorithms']:
            lines.append(f"🤖 Algoritmos Adequados: {', '.join(analysis['suitable_algorithms'])}")
        
        return "\n".join(lines)
    
    def _format_suggestions(self, suggestions: Dict[str, Any]) -> str:
        """Formata sugestões."""
        lines = []
        lines.append("💡 Sugestões:")
        
        if suggestions['suggestions']:
            lines.append("📝 Queries Sugeridas:")
            for suggestion in suggestions['suggestions'][:5]:
                lines.append(f"  • {suggestion}")
        
        if suggestions['completions']:
            lines.append("🔤 Completações:")
            for completion in suggestions['completions'][:5]:
                lines.append(f"  • {completion}")
        
        if suggestions['corrections']:
            lines.append("✏ Correções:")
            for correction in suggestions['corrections']:
                lines.append(f"  • {correction}")
        
        lines.append(f"🎯 Confiança: {suggestions['confidence']:.2f}")
        
        return "\n".join(lines)
    
    def _format_stats(self, stats: Dict[str, Any]) -> str:
        """Formata estatísticas."""
        lines = []
        lines.append("📊 Estatísticas do Sistema")
        lines.append("")
        
        # Session stats
        session = stats['session']
        lines.append("🔄 Sessão:")
        lines.append(f"  Queries processadas: {session['queries_processed']}")
        lines.append(f"  Cache hits: {session['cache_hits']}")
        lines.append(f"  Cache misses: {session['cache_misses']}")
        lines.append(f"  Tempo médio: {session['average_search_time']:.3f}s")
        lines.append("")
        
        # Algorithm stats
        algorithms = stats['algorithms']
        lines.append("🤖 Algoritmos:")
        for algo_name, algo_stats in algorithms.items():
            lines.append(f"  {algo_name}: {algo_stats['executions']} execuções")
        lines.append("")
        
        # Cache stats
        cache = stats['cache']
        if 'global' in cache:
            global_cache = cache['global']
            lines.append("💾 Cache:")
            lines.append(f"  Hit rate: {global_cache['hit_rate']:.2%}")
            lines.append(f"  Total requests: {global_cache['total_requests']}")
        
        return "\n".join(lines)