"""
Base Search Algorithm - Interface abstrata para algoritmos de busca.

Define a interface comum que todos os algoritmos de busca devem implementar,
garantindo consistência e facilidade de integração.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class SearchResult:
    """
    Resultado de uma operação de busca.
    
    Attributes:
        score: Pontuação de confiança (0.0 - 1.0)
        metadata: Metadados encontrados
        algorithm: Nome do algoritmo que gerou o resultado
        details: Detalhes adicionais sobre a busca
    """
    score: float
    metadata: Dict[str, Any]
    algorithm: str
    details: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Valida a pontuação após inicialização."""
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"Score deve estar entre 0.0 e 1.0, recebido: {self.score}")


@dataclass 
class SearchQuery:
    """
    Query de busca com critérios e opções.
    
    Attributes:
        title: Título para buscar
        authors: Lista de autores
        isbn: ISBN (10 ou 13 dígitos)
        publisher: Nome da editora
        year: Ano de publicação
        text_content: Conteúdo textual extraído do arquivo
        file_path: Caminho do arquivo original
        options: Opções específicas do algoritmo
    """
    title: Optional[str] = None
    authors: Optional[List[str]] = None
    isbn: Optional[str] = None
    publisher: Optional[str] = None
    year: Optional[str] = None
    text_content: Optional[str] = None
    file_path: Optional[str] = None
    options: Optional[Dict[str, Any]] = None


class BaseSearchAlgorithm(ABC):
    """
    Interface abstrata para algoritmos de busca de metadados.
    
    Todos os algoritmos de busca devem herdar desta classe e implementar
    os métodos abstratos definidos.
    """
    
    def __init__(self, name: str, version: str = "1.0.0"):
        """
        Inicializa o algoritmo de busca.
        
        Args:
            name: Nome identificador do algoritmo
            version: Versão do algoritmo
        """
        self.name = name
        self.version = version
        self.is_configured = False
        self._stats = {
            'searches_performed': 0,
            'total_time': 0.0,
            'average_score': 0.0
        }
    
    @abstractmethod
    def configure(self, config: Dict[str, Any]) -> bool:
        """
        Configura o algoritmo com parâmetros específicos.
        
        Args:
            config: Dicionário com configurações específicas
            
        Returns:
            bool: True se configuração foi bem-sucedida
        """
        pass
    
    @abstractmethod
    def search(self, query: SearchQuery) -> List[SearchResult]:
        """
        Executa busca baseada na query fornecida.
        
        Args:
            query: Objeto SearchQuery com critérios de busca
            
        Returns:
            List[SearchResult]: Lista de resultados ordenados por score
        """
        pass
    
    @abstractmethod
    def is_suitable_for_query(self, query: SearchQuery) -> bool:
        """
        Verifica se este algoritmo é adequado para a query.
        
        Args:
            query: Query a ser avaliada
            
        Returns:
            bool: True se o algoritmo pode processar esta query
        """
        pass
    
    def get_capabilities(self) -> List[str]:
        """
        Retorna lista de capacidades do algoritmo.
        
        Returns:
            List[str]: Lista de capacidades suportadas
        """
        return ['basic_search']
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas de uso do algoritmo.
        
        Returns:
            Dict[str, Any]: Estatísticas de performance
        """
        return self._stats.copy()
    
    def reset_stats(self):
        """Reseta as estatísticas do algoritmo."""
        self._stats = {
            'searches_performed': 0,
            'total_time': 0.0,
            'average_score': 0.0
        }
    
    def _update_stats(self, execution_time: float, score: float):
        """
        Atualiza estatísticas internas.
        
        Args:
            execution_time: Tempo de execução em segundos
            score: Score obtido na busca
        """
        self._stats['searches_performed'] += 1
        self._stats['total_time'] += execution_time
        
        # Calcula média ponderada do score
        current_avg = self._stats['average_score']
        count = self._stats['searches_performed']
        self._stats['average_score'] = ((current_avg * (count - 1)) + score) / count
    
    def __str__(self) -> str:
        """Representação string do algoritmo."""
        return f"{self.name} v{self.version}"
    
    def __repr__(self) -> str:
        """Representação detalhada do algoritmo."""
        return f"<{self.__class__.__name__}(name='{self.name}', version='{self.version}')>"