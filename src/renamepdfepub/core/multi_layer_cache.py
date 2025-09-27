"""
Multi-Layer Cache System - Sistema de cache avançado para otimização de performance.

Funcionalidades:
- Cache em memória com LRU eviction
- Cache persistente em disco
- Cache distribuído (simulado)
- Invalidação inteligente
- Métricas e monitoramento
"""

import time
import json
import hashlib
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from collections import OrderedDict
from abc import ABC, abstractmethod

from ..search_algorithms.base_search import SearchQuery, SearchResult


@dataclass
class CacheEntry:
    """Entrada do cache com metadados."""
    key: str
    value: Any
    timestamp: float
    access_count: int = 0
    last_access: float = 0.0
    ttl: Optional[float] = None  # Time to live in seconds
    size_bytes: int = 0
    
    def is_expired(self) -> bool:
        """Verifica se a entrada expirou."""
        if self.ttl is None:
            return False
        return time.time() - self.timestamp > self.ttl
    
    def touch(self):
        """Marca a entrada como acessada."""
        self.access_count += 1
        self.last_access = time.time()


@dataclass
class CacheStats:
    """Estatísticas do cache."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size: int = 0
    max_size: int = 0
    total_requests: int = 0
    average_access_time: float = 0.0
    hit_rate: float = 0.0
    
    def update_hit_rate(self):
        """Atualiza a taxa de acerto."""
        if self.total_requests > 0:
            self.hit_rate = self.hits / self.total_requests


class CacheLayer(ABC):
    """Interface abstrata para camadas de cache."""
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Obtém valor do cache."""
        pass
    
    @abstractmethod
    def put(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        """Armazena valor no cache."""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """Remove valor do cache."""
        pass
    
    @abstractmethod
    def clear(self) -> bool:
        """Limpa todo o cache."""
        pass
    
    @abstractmethod
    def get_stats(self) -> CacheStats:
        """Obtém estatísticas do cache."""
        pass


class MemoryCache(CacheLayer):
    """Cache em memória com LRU eviction."""
    
    def __init__(self, max_size: int = 1000, default_ttl: Optional[float] = 3600):
        """
        Inicializa cache em memória.
        
        Args:
            max_size: Tamanho máximo do cache
            default_ttl: TTL padrão em segundos
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.stats = CacheStats(max_size=max_size)
        self.lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """Obtém valor do cache."""
        start_time = time.time()
        
        with self.lock:
            self.stats.total_requests += 1
            
            if key in self.cache:
                entry = self.cache[key]
                
                # Check if expired
                if entry.is_expired():
                    del self.cache[key]
                    self.stats.misses += 1
                    self.stats.size -= 1
                    return None
                
                # Move to end (most recently used)
                self.cache.move_to_end(key)
                entry.touch()
                
                self.stats.hits += 1
                access_time = time.time() - start_time
                self._update_average_access_time(access_time)
                self.stats.update_hit_rate()
                
                return entry.value
            else:
                self.stats.misses += 1
                self.stats.update_hit_rate()
                return None
    
    def put(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        """Armazena valor no cache."""
        with self.lock:
            ttl = ttl or self.default_ttl
            
            # Calculate approximate size
            size_bytes = self._calculate_size(value)
            
            # If key already exists, update it
            if key in self.cache:
                self.cache[key].value = value
                self.cache[key].timestamp = time.time()
                self.cache[key].ttl = ttl
                self.cache[key].size_bytes = size_bytes
                self.cache.move_to_end(key)
                return True
            
            # Check if we need to evict
            while len(self.cache) >= self.max_size:
                self._evict_lru()
            
            # Add new entry
            entry = CacheEntry(
                key=key,
                value=value,
                timestamp=time.time(),
                ttl=ttl,
                size_bytes=size_bytes
            )
            
            self.cache[key] = entry
            self.stats.size += 1
            
            return True
    
    def delete(self, key: str) -> bool:
        """Remove valor do cache."""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                self.stats.size -= 1
                return True
            return False
    
    def clear(self) -> bool:
        """Limpa todo o cache."""
        with self.lock:
            self.cache.clear()
            self.stats.size = 0
            return True
    
    def get_stats(self) -> CacheStats:
        """Obtém estatísticas do cache."""
        with self.lock:
            return CacheStats(
                hits=self.stats.hits,
                misses=self.stats.misses,
                evictions=self.stats.evictions,
                size=self.stats.size,
                max_size=self.stats.max_size,
                total_requests=self.stats.total_requests,
                average_access_time=self.stats.average_access_time,
                hit_rate=self.stats.hit_rate
            )
    
    def _evict_lru(self):
        """Remove o item menos recentemente usado."""
        if self.cache:
            key, entry = self.cache.popitem(last=False)  # Remove first (oldest)
            self.stats.evictions += 1
            self.stats.size -= 1
    
    def _calculate_size(self, value: Any) -> int:
        """Calcula o tamanho aproximado de um valor."""
        try:
            if isinstance(value, str):
                return len(value.encode('utf-8'))
            elif isinstance(value, (list, dict)):
                return len(json.dumps(value, default=str).encode('utf-8'))
            elif hasattr(value, '__sizeof__'):
                return value.__sizeof__()
            else:
                return len(str(value).encode('utf-8'))
        except:
            return 100  # Default size estimate
    
    def _update_average_access_time(self, access_time: float):
        """Atualiza tempo médio de acesso."""
        if self.stats.hits == 1:
            self.stats.average_access_time = access_time
        else:
            # Moving average
            alpha = 0.1  # Weight for new measurement
            self.stats.average_access_time = (
                alpha * access_time + 
                (1 - alpha) * self.stats.average_access_time
            )


class DiskCache(CacheLayer):
    """Cache persistente em disco."""
    
    def __init__(self, cache_dir: str = ".cache", max_size_mb: int = 100):
        """
        Inicializa cache em disco.
        
        Args:
            cache_dir: Diretório do cache
            max_size_mb: Tamanho máximo em MB
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.stats = CacheStats()
        self.lock = threading.RLock()
        
        # Index file to track cache entries
        self.index_file = self.cache_dir / "cache_index.json"
        self.index = self._load_index()
    
    def get(self, key: str) -> Optional[Any]:
        """Obtém valor do cache em disco."""
        with self.lock:
            self.stats.total_requests += 1
            
            key_hash = self._hash_key(key)
            
            if key_hash in self.index:
                file_path = self.cache_dir / f"{key_hash}.json"
                
                if file_path.exists():
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        entry = CacheEntry(**data['entry'])
                        
                        # Check if expired
                        if entry.is_expired():
                            self.delete(key)
                            self.stats.misses += 1
                            return None
                        
                        entry.touch()
                        self._update_index(key_hash, entry)
                        
                        self.stats.hits += 1
                        self.stats.update_hit_rate()
                        
                        return data['value']
                    
                    except (json.JSONDecodeError, KeyError, FileNotFoundError):
                        # Corrupted cache entry, remove it
                        self.delete(key)
                        self.stats.misses += 1
                        return None
                else:
                    # Index entry exists but file doesn't, clean up
                    self.delete(key)
                    self.stats.misses += 1
                    return None
            else:
                self.stats.misses += 1
                self.stats.update_hit_rate()
                return None
    
    def put(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        """Armazena valor no cache em disco."""
        with self.lock:
            try:
                key_hash = self._hash_key(key)
                file_path = self.cache_dir / f"{key_hash}.json"
                
                entry = CacheEntry(
                    key=key,
                    value=value,
                    timestamp=time.time(),
                    ttl=ttl or 3600,  # Default 1 hour
                    size_bytes=0
                )
                
                data = {
                    'entry': asdict(entry),
                    'value': value
                }
                
                # Serialize value if it's a complex object
                if hasattr(value, '__dict__'):
                    data['value'] = self._serialize_complex_object(value)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, default=str)
                
                # Update size
                entry.size_bytes = file_path.stat().st_size
                
                # Update index
                self._update_index(key_hash, entry)
                
                # Check if we need to evict old entries
                self._cleanup_if_needed()
                
                return True
                
            except Exception:
                return False
    
    def delete(self, key: str) -> bool:
        """Remove valor do cache em disco."""
        with self.lock:
            key_hash = self._hash_key(key)
            
            if key_hash in self.index:
                file_path = self.cache_dir / f"{key_hash}.json"
                
                try:
                    if file_path.exists():
                        file_path.unlink()
                    
                    del self.index[key_hash]
                    self._save_index()
                    
                    return True
                except:
                    return False
            
            return False
    
    def clear(self) -> bool:
        """Limpa todo o cache em disco."""
        with self.lock:
            try:
                # Remove all cache files
                for file_path in self.cache_dir.glob("*.json"):
                    if file_path.name != "cache_index.json":
                        file_path.unlink()
                
                # Clear index
                self.index.clear()
                self._save_index()
                
                return True
            except:
                return False
    
    def get_stats(self) -> CacheStats:
        """Obtém estatísticas do cache."""
        with self.lock:
            self.stats.size = len(self.index)
            return CacheStats(
                hits=self.stats.hits,
                misses=self.stats.misses,
                evictions=self.stats.evictions,
                size=self.stats.size,
                max_size=self.max_size_bytes,
                total_requests=self.stats.total_requests,
                hit_rate=self.stats.hit_rate
            )
    
    def _hash_key(self, key: str) -> str:
        """Gera hash do key."""
        return hashlib.md5(key.encode('utf-8')).hexdigest()
    
    def _load_index(self) -> Dict[str, Dict[str, Any]]:
        """Carrega índice do cache."""
        try:
            if self.index_file.exists():
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except:
            pass
        return {}
    
    def _save_index(self):
        """Salva índice do cache."""
        try:
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(self.index, f, indent=2, default=str)
        except:
            pass
    
    def _update_index(self, key_hash: str, entry: CacheEntry):
        """Atualiza entrada no índice."""
        self.index[key_hash] = asdict(entry)
        self._save_index()
    
    def _cleanup_if_needed(self):
        """Limpa entradas antigas se necessário."""
        # Calculate total size
        total_size = sum(
            entry.get('size_bytes', 0) 
            for entry in self.index.values()
        )
        
        if total_size > self.max_size_bytes:
            # Sort by last access time and remove oldest
            sorted_entries = sorted(
                self.index.items(),
                key=lambda x: x[1].get('last_access', 0)
            )
            
            # Remove oldest entries until under limit
            for key_hash, entry in sorted_entries:
                if total_size <= self.max_size_bytes * 0.8:  # Remove until 80% of limit
                    break
                
                file_path = self.cache_dir / f"{key_hash}.json"
                try:
                    if file_path.exists():
                        file_path.unlink()
                    del self.index[key_hash]
                    total_size -= entry.get('size_bytes', 0)
                    self.stats.evictions += 1
                except:
                    pass
            
            self._save_index()
    
    def _serialize_complex_object(self, obj: Any) -> Dict[str, Any]:
        """Serializa objeto complexo para JSON."""
        if hasattr(obj, '__dict__'):
            return {'__type__': obj.__class__.__name__, '__data__': obj.__dict__}
        else:
            return {'__type__': 'unknown', '__data__': str(obj)}


class MultiLayerCache:
    """
    Sistema de cache multi-camadas com fallback inteligente.
    
    Camadas:
    1. Memory Cache (mais rápido)
    2. Disk Cache (persistente)
    3. Distributed Cache (simulado)
    """
    
    def __init__(self, 
                 memory_size: int = 500,
                 disk_size_mb: int = 50,
                 cache_dir: str = ".cache"):
        """
        Inicializa sistema de cache multi-camadas.
        
        Args:
            memory_size: Tamanho do cache em memória
            disk_size_mb: Tamanho do cache em disco (MB)
            cache_dir: Diretório do cache em disco
        """
        self.memory_cache = MemoryCache(max_size=memory_size)
        self.disk_cache = DiskCache(cache_dir=cache_dir, max_size_mb=disk_size_mb)
        
        self.global_stats = CacheStats()
        self.lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """
        Obtém valor do cache, tentando todas as camadas.
        
        Args:
            key: Chave do cache
            
        Returns:
            Optional[Any]: Valor encontrado ou None
        """
        start_time = time.time()
        
        with self.lock:
            self.global_stats.total_requests += 1
            
            # Try memory cache first
            value = self.memory_cache.get(key)
            if value is not None:
                self.global_stats.hits += 1
                self._update_global_stats(start_time)
                return value
            
            # Try disk cache
            value = self.disk_cache.get(key)
            if value is not None:
                # Promote to memory cache
                self.memory_cache.put(key, value)
                self.global_stats.hits += 1
                self._update_global_stats(start_time)
                return value
            
            # Cache miss
            self.global_stats.misses += 1
            self.global_stats.update_hit_rate()
            return None
    
    def put(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        """
        Armazena valor em todas as camadas apropriadas.
        
        Args:
            key: Chave do cache
            value: Valor a ser armazenado
            ttl: Time to live em segundos
            
        Returns:
            bool: True se pelo menos uma camada teve sucesso
        """
        with self.lock:
            success = False
            
            # Store in memory cache
            if self.memory_cache.put(key, value, ttl):
                success = True
            
            # Store in disk cache for persistence
            if self.disk_cache.put(key, value, ttl):
                success = True
            
            return success
    
    def delete(self, key: str) -> bool:
        """
        Remove valor de todas as camadas.
        
        Args:
            key: Chave a ser removida
            
        Returns:
            bool: True se pelo menos uma camada teve sucesso
        """
        with self.lock:
            success = False
            
            if self.memory_cache.delete(key):
                success = True
            
            if self.disk_cache.delete(key):
                success = True
            
            return success
    
    def clear(self) -> bool:
        """Limpa todas as camadas do cache."""
        with self.lock:
            memory_success = self.memory_cache.clear()
            disk_success = self.disk_cache.clear()
            
            return memory_success and disk_success
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Obtém estatísticas abrangentes de todas as camadas."""
        with self.lock:
            return {
                'global': asdict(self.global_stats),
                'memory': asdict(self.memory_cache.get_stats()),
                'disk': asdict(self.disk_cache.get_stats()),
                'total_hit_rate': self.global_stats.hit_rate,
                'memory_promotion_rate': self._calculate_promotion_rate()
            }
    
    def _update_global_stats(self, start_time: float):
        """Atualiza estatísticas globais."""
        access_time = time.time() - start_time
        
        if self.global_stats.hits == 1:
            self.global_stats.average_access_time = access_time
        else:
            # Moving average
            alpha = 0.1
            self.global_stats.average_access_time = (
                alpha * access_time + 
                (1 - alpha) * self.global_stats.average_access_time
            )
        
        self.global_stats.update_hit_rate()
    
    def _calculate_promotion_rate(self) -> float:
        """Calcula taxa de promoção do disk para memory cache."""
        disk_hits = self.disk_cache.get_stats().hits
        total_hits = self.global_stats.hits
        
        if total_hits > 0:
            return disk_hits / total_hits
        return 0.0


class SearchCache:
    """
    Cache especializado para resultados de busca.
    
    Funcionalidades:
    - Cache inteligente baseado em hash da query
    - Invalidação baseada em tempo e relevância
    - Compressão de resultados grandes
    """
    
    def __init__(self, cache_dir: str = ".search_cache"):
        """
        Inicializa cache de busca.
        
        Args:
            cache_dir: Diretório do cache
        """
        self.cache = MultiLayerCache(
            memory_size=200,  # Menor para resultados de busca
            disk_size_mb=25,
            cache_dir=cache_dir
        )
    
    def get_search_results(self, query: SearchQuery) -> Optional[List[SearchResult]]:
        """
        Obtém resultados de busca do cache.
        
        Args:
            query: Query de busca
            
        Returns:
            Optional[List[SearchResult]]: Resultados ou None
        """
        query_key = self._generate_query_key(query)
        
        cached_data = self.cache.get(query_key)
        if cached_data:
            # Reconstruct SearchResult objects
            results = []
            for result_data in cached_data:
                result = SearchResult(
                    score=result_data['score'],
                    metadata=result_data['metadata'],
                    algorithm=result_data['algorithm'],
                    details=result_data.get('details', {})
                )
                results.append(result)
            
            return results
        
        return None
    
    def cache_search_results(self, query: SearchQuery, results: List[SearchResult], ttl: float = 1800):
        """
        Armazena resultados de busca no cache.
        
        Args:
            query: Query de busca
            results: Resultados para cachear
            ttl: Time to live em segundos (default: 30 minutos)
        """
        query_key = self._generate_query_key(query)
        
        # Convert SearchResult objects to serializable format
        serializable_results = []
        for result in results[:20]:  # Limit to top 20 results
            serializable_results.append({
                'score': result.score,
                'metadata': result.metadata,
                'algorithm': result.algorithm,
                'details': result.details
            })
        
        self.cache.put(query_key, serializable_results, ttl)
    
    def invalidate_query(self, query: SearchQuery) -> bool:
        """
        Invalida cache para uma query específica.
        
        Args:
            query: Query para invalidar
            
        Returns:
            bool: True se sucesso
        """
        query_key = self._generate_query_key(query)
        return self.cache.delete(query_key)
    
    def _generate_query_key(self, query: SearchQuery) -> str:
        """
        Gera chave única para uma query.
        
        Args:
            query: Query de busca
            
        Returns:
            str: Chave única
        """
        # Create a canonical representation of the query
        components = [
            f"title:{query.title or ''}",
            f"authors:{','.join(query.authors) if query.authors else ''}",
            f"isbn:{query.isbn or ''}",
            f"text:{query.text_content or ''}"
        ]
        
        query_string = "|".join(components)
        return hashlib.sha256(query_string.encode('utf-8')).hexdigest()
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtém estatísticas do cache de busca."""
        return self.cache.get_comprehensive_stats()