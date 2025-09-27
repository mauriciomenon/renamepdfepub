"""
Performance Optimization Module - Sistema de otimização de performance.

Funcionalidades:
- Indexação de dados para busca rápida
- Otimização de memória
- Profiling e monitoramento
- Auto-tuning de algoritmos
"""

import time
import threading
import psutil
import gc
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from pathlib import Path
from collections import defaultdict, deque
import pickle
import json
import gzip

from ..search_algorithms.base_search import SearchResult, SearchQuery


@dataclass
class PerformanceMetrics:
    """Métricas de performance do sistema."""
    
    # Timing metrics
    total_execution_time: float = 0.0
    average_execution_time: float = 0.0
    min_execution_time: float = float('inf')
    max_execution_time: float = 0.0
    
    # Memory metrics
    peak_memory_usage: float = 0.0
    current_memory_usage: float = 0.0
    memory_growth: float = 0.0
    
    # Cache metrics
    cache_hit_rate: float = 0.0
    cache_miss_rate: float = 0.0
    cache_size: int = 0
    
    # Algorithm metrics
    algorithm_usage: Dict[str, int] = field(default_factory=dict)
    algorithm_performance: Dict[str, float] = field(default_factory=dict)
    
    # Query metrics
    query_complexity_distribution: Dict[str, int] = field(default_factory=dict)
    popular_queries: List[Tuple[str, int]] = field(default_factory=list)
    
    # System metrics
    cpu_usage: float = 0.0
    disk_io: Dict[str, float] = field(default_factory=dict)
    
    # Timestamps
    start_time: float = field(default_factory=time.time)
    last_update: float = field(default_factory=time.time)


class SearchIndexer:
    """
    Sistema de indexação para otimizar buscas.
    
    Cria índices invertidos e estruturas otimizadas para busca rápida.
    """
    
    def __init__(self, index_file: str = "search_index.pkl"):
        """
        Inicializa indexador.
        
        Args:
            index_file: Arquivo do índice
        """
        self.index_file = Path(index_file)
        
        # Índices
        self.title_index = defaultdict(set)
        self.author_index = defaultdict(set)
        self.isbn_index = defaultdict(set)
        self.keyword_index = defaultdict(set)
        
        # Metadados
        self.documents = {}  # doc_id -> metadata
        self.doc_counter = 0
        
        # Configuração
        self.min_word_length = 2
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'out', 'off', 'down', 'under', 'again'
        }
        
        # Load existing index
        self.load_index()
    
    def add_document(self, metadata: Dict[str, Any]) -> str:
        """
        Adiciona documento ao índice.
        
        Args:
            metadata: Metadados do documento
            
        Returns:
            str: ID do documento
        """
        doc_id = f"doc_{self.doc_counter}"
        self.doc_counter += 1
        
        self.documents[doc_id] = metadata
        
        # Index title
        if 'title' in metadata:
            title_words = self._tokenize(metadata['title'])
            for word in title_words:
                self.title_index[word].add(doc_id)
                self.keyword_index[word].add(doc_id)
        
        # Index authors
        if 'authors' in metadata:
            authors = metadata['authors']
            if isinstance(authors, str):
                authors = [authors]
            
            for author in authors:
                author_words = self._tokenize(author)
                for word in author_words:
                    self.author_index[word].add(doc_id)
                    self.keyword_index[word].add(doc_id)
        
        # Index ISBN
        if 'isbn' in metadata:
            isbn = self._clean_isbn(metadata['isbn'])
            if isbn:
                self.isbn_index[isbn].add(doc_id)
                # Also index partial ISBNs
                for i in range(3, len(isbn)):
                    partial = isbn[:i]
                    self.isbn_index[partial].add(doc_id)
        
        return doc_id
    
    def search_index(self, query: SearchQuery, max_results: int = 100) -> List[Dict[str, Any]]:
        """
        Busca usando índices.
        
        Args:
            query: Query de busca
            max_results: Máximo de resultados
            
        Returns:
            List[Dict[str, Any]]: Documentos encontrados
        """
        candidates = set()
        
        # Search in title
        if query.title:
            title_words = self._tokenize(query.title)
            for word in title_words:
                candidates.update(self.title_index.get(word, set()))
        
        # Search in authors
        if query.authors:
            for author in query.authors:
                author_words = self._tokenize(author)
                for word in author_words:
                    candidates.update(self.author_index.get(word, set()))
        
        # Search in ISBN
        if query.isbn:
            isbn = self._clean_isbn(query.isbn)
            if isbn:
                candidates.update(self.isbn_index.get(isbn, set()))
        
        # Search in general text
        if query.text_content:
            text_words = self._tokenize(query.text_content)
            for word in text_words:
                candidates.update(self.keyword_index.get(word, set()))
        
        # Convert to documents
        results = []
        for doc_id in list(candidates)[:max_results]:
            if doc_id in self.documents:
                results.append({
                    'doc_id': doc_id,
                    'metadata': self.documents[doc_id]
                })
        
        return results
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Obtém estatísticas do índice."""
        return {
            'total_documents': len(self.documents),
            'title_terms': len(self.title_index),
            'author_terms': len(self.author_index),
            'isbn_entries': len(self.isbn_index),
            'keyword_terms': len(self.keyword_index),
            'index_size_mb': self._get_index_size(),
            'most_common_terms': self._get_most_common_terms()
        }
    
    def save_index(self):
        """Salva índice em disco."""
        try:
            index_data = {
                'title_index': dict(self.title_index),
                'author_index': dict(self.author_index),
                'isbn_index': dict(self.isbn_index),
                'keyword_index': dict(self.keyword_index),
                'documents': self.documents,
                'doc_counter': self.doc_counter
            }
            
            with gzip.open(self.index_file, 'wb') as f:
                pickle.dump(index_data, f)
                
        except Exception:
            pass
    
    def load_index(self):
        """Carrega índice do disco."""
        if not self.index_file.exists():
            return
        
        try:
            with gzip.open(self.index_file, 'rb') as f:
                index_data = pickle.load(f)
            
            self.title_index = defaultdict(set, index_data.get('title_index', {}))
            self.author_index = defaultdict(set, index_data.get('author_index', {}))
            self.isbn_index = defaultdict(set, index_data.get('isbn_index', {}))
            self.keyword_index = defaultdict(set, index_data.get('keyword_index', {}))
            self.documents = index_data.get('documents', {})
            self.doc_counter = index_data.get('doc_counter', 0)
            
            # Convert lists back to sets
            for index in [self.title_index, self.author_index, self.isbn_index, self.keyword_index]:
                for key in index:
                    if isinstance(index[key], list):
                        index[key] = set(index[key])
                        
        except Exception:
            pass
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokeniza texto."""
        if not text:
            return []
        
        # Simple tokenization
        words = text.lower().replace(',', ' ').replace('.', ' ').split()
        
        # Filter words
        filtered_words = []
        for word in words:
            # Remove punctuation
            word = ''.join(c for c in word if c.isalnum())
            
            # Check length and stop words
            if len(word) >= self.min_word_length and word not in self.stop_words:
                filtered_words.append(word)
        
        return filtered_words
    
    def _clean_isbn(self, isbn: str) -> str:
        """Limpa ISBN."""
        if not isbn:
            return ""
        
        # Remove non-digits
        clean = ''.join(c for c in isbn if c.isdigit())
        
        return clean if len(clean) >= 10 else ""
    
    def _get_index_size(self) -> float:
        """Calcula tamanho do índice em MB."""
        try:
            if self.index_file.exists():
                return self.index_file.stat().st_size / (1024 * 1024)
        except:
            pass
        return 0.0
    
    def _get_most_common_terms(self) -> Dict[str, List[Tuple[str, int]]]:
        """Obtém termos mais comuns."""
        def get_top_terms(index, limit=10):
            term_counts = [(term, len(docs)) for term, docs in index.items()]
            return sorted(term_counts, key=lambda x: x[1], reverse=True)[:limit]
        
        return {
            'titles': get_top_terms(self.title_index),
            'authors': get_top_terms(self.author_index),
            'keywords': get_top_terms(self.keyword_index)
        }


class MemoryOptimizer:
    """
    Sistema de otimização de memória.
    
    Monitora e otimiza uso de memória do sistema.
    """
    
    def __init__(self, max_memory_mb: float = 500.0):
        """
        Inicializa otimizador.
        
        Args:
            max_memory_mb: Limite máximo de memória em MB
        """
        self.max_memory_mb = max_memory_mb
        self.process = psutil.Process()
        
        # Monitoring
        self.memory_history = deque(maxlen=100)
        self.last_gc_time = time.time()
        self.gc_threshold = 60.0  # seconds
        
        # Optimization strategies
        self.strategies = {
            'aggressive_gc': self._aggressive_gc,
            'cache_cleanup': self._cache_cleanup,
            'object_pooling': self._object_pooling
        }
    
    def check_memory_usage(self) -> Dict[str, float]:
        """
        Verifica uso atual de memória.
        
        Returns:
            Dict[str, float]: Métricas de memória
        """
        memory_info = self.process.memory_info()
        memory_mb = memory_info.rss / (1024 * 1024)
        
        self.memory_history.append({
            'timestamp': time.time(),
            'memory_mb': memory_mb,
            'memory_percent': self.process.memory_percent()
        })
        
        return {
            'current_mb': memory_mb,
            'max_mb': self.max_memory_mb,
            'percentage': (memory_mb / self.max_memory_mb) * 100,
            'is_over_limit': memory_mb > self.max_memory_mb
        }
    
    def optimize_if_needed(self) -> Dict[str, Any]:
        """
        Otimiza memória se necessário.
        
        Returns:
            Dict[str, Any]: Resultado da otimização
        """
        memory_status = self.check_memory_usage()
        
        if not memory_status['is_over_limit']:
            return {'optimized': False, 'reason': 'memory_under_limit'}
        
        # Apply optimization strategies
        results = {}
        
        for strategy_name, strategy_func in self.strategies.items():
            try:
                result = strategy_func()
                results[strategy_name] = result
                
                # Check if memory is now under control
                updated_status = self.check_memory_usage()
                if not updated_status['is_over_limit']:
                    break
                    
            except Exception as e:
                results[strategy_name] = {'error': str(e)}
        
        final_status = self.check_memory_usage()
        
        return {
            'optimized': True,
            'initial_memory': memory_status['current_mb'],
            'final_memory': final_status['current_mb'],
            'memory_freed': memory_status['current_mb'] - final_status['current_mb'],
            'strategies_applied': results
        }
    
    def get_memory_trends(self) -> Dict[str, Any]:
        """Obtém tendências de uso de memória."""
        if len(self.memory_history) < 2:
            return {'insufficient_data': True}
        
        recent_memory = [entry['memory_mb'] for entry in list(self.memory_history)[-10:]]
        
        return {
            'current': recent_memory[-1],
            'average_recent': sum(recent_memory) / len(recent_memory),
            'trend': 'increasing' if recent_memory[-1] > recent_memory[0] else 'decreasing',
            'peak_memory': max(entry['memory_mb'] for entry in self.memory_history),
            'min_memory': min(entry['memory_mb'] for entry in self.memory_history)
        }
    
    def _aggressive_gc(self) -> Dict[str, Any]:
        """Executa garbage collection agressivo."""
        if time.time() - self.last_gc_time < self.gc_threshold:
            return {'skipped': 'too_recent'}
        
        before_memory = self.process.memory_info().rss / (1024 * 1024)
        
        # Force garbage collection
        collected = gc.collect()
        
        after_memory = self.process.memory_info().rss / (1024 * 1024)
        self.last_gc_time = time.time()
        
        return {
            'objects_collected': collected,
            'memory_freed_mb': before_memory - after_memory,
            'before_mb': before_memory,
            'after_mb': after_memory
        }
    
    def _cache_cleanup(self) -> Dict[str, Any]:
        """Limpa caches desnecessários."""
        # This would be implemented to clean up specific caches
        # For now, just return a placeholder
        return {'cache_entries_removed': 0, 'memory_freed_mb': 0}
    
    def _object_pooling(self) -> Dict[str, Any]:
        """Implementa pooling de objetos."""
        # This would be implemented to reuse objects
        # For now, just return a placeholder
        return {'objects_pooled': 0, 'memory_saved_mb': 0}


class PerformanceProfiler:
    """
    Sistema de profiling de performance.
    
    Monitora e analisa performance de todas as operações.
    """
    
    def __init__(self):
        """Inicializa profiler."""
        self.metrics = PerformanceMetrics()
        self.active_operations = {}  # operation_id -> start_time
        self.operation_history = deque(maxlen=1000)
        
        # Threading
        self.lock = threading.Lock()
        
        # Monitoring thread
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_system, daemon=True)
        self.monitor_thread.start()
    
    def start_operation(self, operation_id: str, operation_type: str = 'search') -> str:
        """
        Inicia profiling de operação.
        
        Args:
            operation_id: ID da operação
            operation_type: Tipo da operação
            
        Returns:
            str: ID da operação
        """
        with self.lock:
            self.active_operations[operation_id] = {
                'start_time': time.time(),
                'type': operation_type,
                'memory_start': self._get_memory_usage()
            }
        
        return operation_id
    
    def end_operation(self, operation_id: str, **metadata) -> Dict[str, Any]:
        """
        Finaliza profiling de operação.
        
        Args:
            operation_id: ID da operação
            **metadata: Metadados adicionais
            
        Returns:
            Dict[str, Any]: Métricas da operação
        """
        with self.lock:
            if operation_id not in self.active_operations:
                return {'error': 'operation_not_found'}
            
            operation_data = self.active_operations.pop(operation_id)
            
            end_time = time.time()
            execution_time = end_time - operation_data['start_time']
            memory_end = self._get_memory_usage()
            memory_used = memory_end - operation_data['memory_start']
            
            # Update metrics
            self._update_metrics(execution_time, memory_used, operation_data['type'])
            
            # Record operation
            operation_record = {
                'operation_id': operation_id,
                'type': operation_data['type'],
                'execution_time': execution_time,
                'memory_used': memory_used,
                'timestamp': end_time,
                **metadata
            }
            
            self.operation_history.append(operation_record)
            
            return operation_record
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Obtém relatório completo de performance."""
        with self.lock:
            return {
                'metrics': self.metrics,
                'recent_operations': list(self.operation_history)[-20:],
                'active_operations': len(self.active_operations),
                'system_info': self._get_system_info()
            }
    
    def get_bottlenecks(self) -> List[Dict[str, Any]]:
        """Identifica gargalos de performance."""
        bottlenecks = []
        
        # Analyze recent operations
        recent_ops = list(self.operation_history)[-100:]
        
        if not recent_ops:
            return bottlenecks
        
        # Find slow operations
        execution_times = [op['execution_time'] for op in recent_ops]
        avg_time = sum(execution_times) / len(execution_times)
        
        slow_ops = [op for op in recent_ops if op['execution_time'] > avg_time * 2]
        
        if slow_ops:
            bottlenecks.append({
                'type': 'slow_operations',
                'count': len(slow_ops),
                'average_time': sum(op['execution_time'] for op in slow_ops) / len(slow_ops),
                'details': slow_ops[:5]  # Top 5 slowest
            })
        
        # Memory usage issues
        if self.metrics.current_memory_usage > 400:  # MB
            bottlenecks.append({
                'type': 'high_memory_usage',
                'current_mb': self.metrics.current_memory_usage,
                'peak_mb': self.metrics.peak_memory_usage
            })
        
        # Low cache hit rate
        if self.metrics.cache_hit_rate < 0.5:
            bottlenecks.append({
                'type': 'low_cache_efficiency',
                'hit_rate': self.metrics.cache_hit_rate,
                'suggestion': 'consider_increasing_cache_size'
            })
        
        return bottlenecks
    
    def suggest_optimizations(self) -> List[Dict[str, Any]]:
        """Sugere otimizações baseadas no profiling."""
        suggestions = []
        bottlenecks = self.get_bottlenecks()
        
        for bottleneck in bottlenecks:
            if bottleneck['type'] == 'slow_operations':
                suggestions.append({
                    'optimization': 'algorithm_tuning',
                    'description': 'Consider optimizing algorithm parameters or using indexing',
                    'priority': 'high',
                    'estimated_improvement': '30-50% faster execution'
                })
            
            elif bottleneck['type'] == 'high_memory_usage':
                suggestions.append({
                    'optimization': 'memory_optimization',
                    'description': 'Implement memory cleanup and object pooling',
                    'priority': 'medium',
                    'estimated_improvement': '20-40% memory reduction'
                })
            
            elif bottleneck['type'] == 'low_cache_efficiency':
                suggestions.append({
                    'optimization': 'cache_optimization',
                    'description': 'Increase cache size or improve cache eviction strategy',
                    'priority': 'medium',
                    'estimated_improvement': '15-25% faster repeated queries'
                })
        
        return suggestions
    
    def _update_metrics(self, execution_time: float, memory_used: float, operation_type: str):
        """Atualiza métricas."""
        # Timing metrics
        self.metrics.total_execution_time += execution_time
        
        # Calculate average (simple moving average)
        if hasattr(self.metrics, '_operation_count'):
            self.metrics._operation_count += 1
        else:
            self.metrics._operation_count = 1
        
        self.metrics.average_execution_time = (
            self.metrics.total_execution_time / self.metrics._operation_count
        )
        
        self.metrics.min_execution_time = min(self.metrics.min_execution_time, execution_time)
        self.metrics.max_execution_time = max(self.metrics.max_execution_time, execution_time)
        
        # Memory metrics
        current_memory = self._get_memory_usage()
        self.metrics.current_memory_usage = current_memory
        self.metrics.peak_memory_usage = max(self.metrics.peak_memory_usage, current_memory)
        
        # Algorithm usage
        if operation_type not in self.metrics.algorithm_usage:
            self.metrics.algorithm_usage[operation_type] = 0
        self.metrics.algorithm_usage[operation_type] += 1
        
        # Update algorithm performance
        if operation_type not in self.metrics.algorithm_performance:
            self.metrics.algorithm_performance[operation_type] = execution_time
        else:
            # Moving average
            current_avg = self.metrics.algorithm_performance[operation_type]
            count = self.metrics.algorithm_usage[operation_type]
            self.metrics.algorithm_performance[operation_type] = (
                (current_avg * (count - 1) + execution_time) / count
            )
        
        self.metrics.last_update = time.time()
    
    def _monitor_system(self):
        """Thread de monitoramento do sistema."""
        while self.monitoring:
            try:
                # Update system metrics
                self.metrics.cpu_usage = psutil.cpu_percent(interval=1)
                
                # Update disk I/O
                disk_io = psutil.disk_io_counters()
                if disk_io:
                    self.metrics.disk_io = {
                        'read_mb': disk_io.read_bytes / (1024 * 1024),
                        'write_mb': disk_io.write_bytes / (1024 * 1024)
                    }
                
                time.sleep(5)  # Update every 5 seconds
                
            except Exception:
                time.sleep(5)
    
    def _get_memory_usage(self) -> float:
        """Obtém uso atual de memória em MB."""
        try:
            process = psutil.Process()
            return process.memory_info().rss / (1024 * 1024)
        except:
            return 0.0
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Obtém informações do sistema."""
        try:
            return {
                'cpu_count': psutil.cpu_count(),
                'memory_total_gb': psutil.virtual_memory().total / (1024**3),
                'memory_available_gb': psutil.virtual_memory().available / (1024**3),
                'disk_usage_percent': psutil.disk_usage('/').percent
            }
        except:
            return {}
    
    def stop_monitoring(self):
        """Para o monitoramento."""
        self.monitoring = False
        if self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1)


class AutoTuner:
    """
    Sistema de auto-tuning de algoritmos.
    
    Ajusta automaticamente parâmetros dos algoritmos baseado na performance.
    """
    
    def __init__(self, profiler: PerformanceProfiler):
        """
        Inicializa auto-tuner.
        
        Args:
            profiler: Profiler de performance
        """
        self.profiler = profiler
        self.tuning_history = {}
        
        # Tuning parameters
        self.tuning_threshold = 100  # Operations before tuning
        self.improvement_threshold = 0.05  # 5% improvement needed
        
        # Parameter ranges for algorithms
        self.parameter_ranges = {
            'fuzzy': {
                'similarity_threshold': (0.3, 0.9, 0.1),
                'levenshtein_weight': (0.3, 0.8, 0.1),
                'jaro_winkler_weight': (0.2, 0.7, 0.1)
            },
            'semantic': {
                'min_similarity_threshold': (0.05, 0.3, 0.05),
                'title_weight': (0.4, 0.8, 0.1),
                'author_weight': (0.2, 0.5, 0.1)
            }
        }
    
    def analyze_and_tune(self, algorithm_name: str) -> Dict[str, Any]:
        """
        Analisa performance e ajusta algoritmo.
        
        Args:
            algorithm_name: Nome do algoritmo
            
        Returns:
            Dict[str, Any]: Resultado do tuning
        """
        if algorithm_name not in self.parameter_ranges:
            return {'error': 'algorithm_not_supported'}
        
        # Get recent performance data
        recent_ops = [
            op for op in self.profiler.operation_history
            if op.get('algorithm') == algorithm_name
        ]
        
        if len(recent_ops) < self.tuning_threshold:
            return {'status': 'insufficient_data', 'operations': len(recent_ops)}
        
        # Analyze current performance
        current_performance = self._analyze_performance(recent_ops)
        
        # Get current best parameters
        if algorithm_name not in self.tuning_history:
            self.tuning_history[algorithm_name] = {
                'best_performance': current_performance,
                'best_parameters': self._get_default_parameters(algorithm_name),
                'attempts': 0
            }
        
        # Try parameter adjustments
        best_improvement = 0
        best_parameters = None
        
        for param_name, (min_val, max_val, step) in self.parameter_ranges[algorithm_name].items():
            improvement, params = self._test_parameter_adjustment(
                algorithm_name, param_name, min_val, max_val, step, recent_ops
            )
            
            if improvement > best_improvement:
                best_improvement = improvement
                best_parameters = params
        
        # Apply best parameters if improvement is significant
        if best_improvement > self.improvement_threshold:
            self.tuning_history[algorithm_name]['best_performance'] = current_performance + best_improvement
            self.tuning_history[algorithm_name]['best_parameters'] = best_parameters
            self.tuning_history[algorithm_name]['attempts'] += 1
            
            return {
                'status': 'tuned',
                'improvement': best_improvement,
                'new_parameters': best_parameters,
                'performance_gain': f"{best_improvement:.1%}"
            }
        
        return {
            'status': 'no_improvement',
            'current_performance': current_performance,
            'attempts_made': len(self.parameter_ranges[algorithm_name])
        }
    
    def get_tuning_recommendations(self) -> List[Dict[str, Any]]:
        """Obtém recomendações de tuning."""
        recommendations = []
        
        for algo_name in self.parameter_ranges.keys():
            # Get algorithm stats
            algo_usage = self.profiler.metrics.algorithm_usage.get(algo_name, 0)
            algo_performance = self.profiler.metrics.algorithm_performance.get(algo_name, 0)
            
            if algo_usage < self.tuning_threshold:
                continue
            
            # Check if algorithm is underperforming
            avg_performance = sum(self.profiler.metrics.algorithm_performance.values()) / len(self.profiler.metrics.algorithm_performance)
            
            if algo_performance > avg_performance * 1.5:  # 50% slower than average
                recommendations.append({
                    'algorithm': algo_name,
                    'issue': 'performance_below_average',
                    'current_time': algo_performance,
                    'average_time': avg_performance,
                    'recommendation': 'tune_parameters_for_speed',
                    'priority': 'high'
                })
            
            # Check if algorithm has low usage but good performance
            elif algo_usage < avg_performance * 0.5 and algo_performance < avg_performance:
                recommendations.append({
                    'algorithm': algo_name,
                    'issue': 'underutilized_good_performance',
                    'usage_count': algo_usage,
                    'performance': algo_performance,
                    'recommendation': 'increase_algorithm_priority',
                    'priority': 'medium'
                })
        
        return recommendations
    
    def _analyze_performance(self, operations: List[Dict[str, Any]]) -> float:
        """Analisa performance de operações."""
        if not operations:
            return 0.0
        
        # Calculate weighted performance score
        execution_times = [op['execution_time'] for op in operations]
        avg_time = sum(execution_times) / len(execution_times)
        
        # Consider accuracy if available
        accuracies = [op.get('accuracy', 1.0) for op in operations]
        avg_accuracy = sum(accuracies) / len(accuracies)
        
        # Performance score (lower is better for time, higher for accuracy)
        performance_score = avg_accuracy / avg_time
        
        return performance_score
    
    def _test_parameter_adjustment(self, 
                                 algorithm_name: str,
                                 param_name: str,
                                 min_val: float,
                                 max_val: float,
                                 step: float,
                                 test_operations: List[Dict[str, Any]]) -> Tuple[float, Dict[str, Any]]:
        """Testa ajuste de parâmetro."""
        # This is a simplified simulation of parameter testing
        # In real implementation, this would run actual tests
        
        current_params = self.tuning_history.get(algorithm_name, {}).get('best_parameters', {})
        current_performance = self._analyze_performance(test_operations)
        
        best_improvement = 0
        best_params = current_params.copy()
        
        # Test different values
        current_val = current_params.get(param_name, (min_val + max_val) / 2)
        
        for direction in [-1, 1]:  # Test both directions
            test_val = current_val + (direction * step)
            
            if min_val <= test_val <= max_val:
                # Simulate performance with new parameter
                # This is a placeholder - real implementation would test actual algorithm
                performance_change = self._simulate_parameter_change(
                    algorithm_name, param_name, test_val, current_val
                )
                
                if performance_change > best_improvement:
                    best_improvement = performance_change
                    best_params = current_params.copy()
                    best_params[param_name] = test_val
        
        return best_improvement, best_params
    
    def _simulate_parameter_change(self, 
                                 algorithm_name: str,
                                 param_name: str,
                                 new_val: float,
                                 current_val: float) -> float:
        """Simula mudança de performance com novo parâmetro."""
        # This is a simplified simulation
        # Real implementation would run actual algorithm tests
        
        # Simulate some improvement based on parameter direction
        if algorithm_name == 'fuzzy':
            if param_name == 'similarity_threshold':
                # Higher threshold might be faster but less accurate
                if new_val > current_val:
                    return 0.02  # 2% improvement in speed
                else:
                    return 0.01  # 1% improvement in accuracy
        
        elif algorithm_name == 'semantic':
            if param_name == 'title_weight':
                # Better balanced weights might improve results
                optimal = 0.6
                current_distance = abs(current_val - optimal)
                new_distance = abs(new_val - optimal)
                
                if new_distance < current_distance:
                    return 0.03  # 3% improvement
        
        return 0.0  # No improvement
    
    def _get_default_parameters(self, algorithm_name: str) -> Dict[str, Any]:
        """Obtém parâmetros padrão do algoritmo."""
        defaults = {
            'fuzzy': {
                'similarity_threshold': 0.6,
                'levenshtein_weight': 0.6,
                'jaro_winkler_weight': 0.4
            },
            'semantic': {
                'min_similarity_threshold': 0.1,
                'title_weight': 0.6,
                'author_weight': 0.3
            }
        }
        
        return defaults.get(algorithm_name, {})