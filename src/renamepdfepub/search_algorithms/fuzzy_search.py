"""
Fuzzy Search Algorithm - Implementação de algoritmos de busca fuzzy.

Utiliza algoritmos como Levenshtein distance e Jaro-Winkler similarity
para encontrar correspondências aproximadas em títulos, autores e outros metadados.
"""

import re
import time
from typing import Dict, List, Any, Optional
from .base_search import BaseSearchAlgorithm, SearchQuery, SearchResult


def levenshtein_distance(s1: str, s2: str) -> int:
    """
    Calcula a distância de Levenshtein entre duas strings.
    
    Args:
        s1: Primeira string
        s2: Segunda string
        
    Returns:
        int: Distância de Levenshtein (número de edições necessárias)
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]


def jaro_similarity(s1: str, s2: str) -> float:
    """
    Calcula a similaridade de Jaro entre duas strings.
    
    Args:
        s1: Primeira string
        s2: Segunda string
        
    Returns:
        float: Similaridade de Jaro (0.0 - 1.0)
    """
    if s1 == s2:
        return 1.0
    
    len1, len2 = len(s1), len(s2)
    if len1 == 0 or len2 == 0:
        return 0.0
    
    match_distance = (max(len1, len2) // 2) - 1
    if match_distance < 0:
        match_distance = 0
    
    s1_matches = [False] * len1
    s2_matches = [False] * len2
    matches = 0
    transpositions = 0
    
    # Identify matches
    for i in range(len1):
        start = max(0, i - match_distance)
        end = min(i + match_distance + 1, len2)
        
        for j in range(start, end):
            if s2_matches[j] or s1[i] != s2[j]:
                continue
            s1_matches[i] = True
            s2_matches[j] = True
            matches += 1
            break
    
    if matches == 0:
        return 0.0
    
    # Count transpositions
    k = 0
    for i in range(len1):
        if not s1_matches[i]:
            continue
        while not s2_matches[k]:
            k += 1
        if s1[i] != s2[k]:
            transpositions += 1
        k += 1
    
    return (matches / len1 + matches / len2 + 
            (matches - transpositions / 2) / matches) / 3.0


def jaro_winkler_similarity(s1: str, s2: str, p: float = 0.1) -> float:
    """
    Calcula a similaridade de Jaro-Winkler entre duas strings.
    
    Args:
        s1: Primeira string
        s2: Segunda string
        p: Fator de escala para prefixos comuns (padrão: 0.1)
        
    Returns:
        float: Similaridade de Jaro-Winkler (0.0 - 1.0)
    """
    jaro_sim = jaro_similarity(s1, s2)
    
    if jaro_sim < 0.7:
        return jaro_sim
    
    # Calculate common prefix length (up to 4 characters)
    prefix_len = 0
    for i in range(min(len(s1), len(s2), 4)):
        if s1[i] == s2[i]:
            prefix_len += 1
        else:
            break
    
    return jaro_sim + (prefix_len * p * (1 - jaro_sim))


def normalize_text_for_comparison(text: str) -> str:
    """
    Normaliza texto para comparação fuzzy.
    
    Args:
        text: Texto a ser normalizado
        
    Returns:
        str: Texto normalizado
    """
    if not text:
        return ""
    
    # Convert to lowercase and remove extra whitespace
    normalized = re.sub(r'\s+', ' ', text.lower().strip())
    
    # Remove common punctuation
    normalized = re.sub(r'[^\w\s]', '', normalized)
    
    return normalized


class FuzzySearchAlgorithm(BaseSearchAlgorithm):
    """
    Algoritmo de busca fuzzy usando Levenshtein e Jaro-Winkler.
    
    Especializado em encontrar correspondências aproximadas quando
    há pequenas diferenças de grafia, tipografia ou formatação.
    """
    
    def __init__(self):
        super().__init__("FuzzySearch", "1.0.0")
        self.min_similarity_threshold = 0.8
        self.title_weight = 0.4
        self.author_weight = 0.3
        self.publisher_weight = 0.2
        self.year_weight = 0.1
        
    def configure(self, config: Dict[str, Any]) -> bool:
        """
        Configura parâmetros do algoritmo fuzzy.
        
        Args:
            config: Configurações incluindo thresholds e pesos
            
        Returns:
            bool: True se configuração foi bem-sucedida
        """
        try:
            self.min_similarity_threshold = config.get('min_similarity_threshold', 0.8)
            self.title_weight = config.get('title_weight', 0.4)
            self.author_weight = config.get('author_weight', 0.3)
            self.publisher_weight = config.get('publisher_weight', 0.2)
            self.year_weight = config.get('year_weight', 0.1)
            
            # Validate weights sum to 1.0
            total_weight = (self.title_weight + self.author_weight + 
                          self.publisher_weight + self.year_weight)
            if abs(total_weight - 1.0) > 0.01:
                # Normalize weights
                self.title_weight /= total_weight
                self.author_weight /= total_weight
                self.publisher_weight /= total_weight
                self.year_weight /= total_weight
            
            self.is_configured = True
            return True
            
        except Exception:
            return False
    
    def search(self, query: SearchQuery) -> List[SearchResult]:
        """
        Executa busca fuzzy baseada na query.
        
        Args:
            query: Query com critérios de busca
            
        Returns:
            List[SearchResult]: Resultados ordenados por similaridade
        """
        start_time = time.time()
        results = []
        
        # Para demonstração, vamos simular alguns resultados
        # Em implementação real, seria busca em base de dados/APIs
        mock_database = self._get_mock_database()
        
        for candidate in mock_database:
            similarity_score = self._calculate_similarity(query, candidate)
            
            if similarity_score >= self.min_similarity_threshold:
                result = SearchResult(
                    score=similarity_score,
                    metadata=candidate,
                    algorithm=self.name,
                    details={
                        'title_similarity': self._title_similarity(query.title, candidate.get('title')),
                        'author_similarity': self._author_similarity(query.authors, candidate.get('authors', [])),
                        'publisher_similarity': self._publisher_similarity(query.publisher, candidate.get('publisher')),
                        'year_match': query.year == candidate.get('year')
                    }
                )
                results.append(result)
        
        # Sort by score descending
        results.sort(key=lambda x: x.score, reverse=True)
        
        execution_time = time.time() - start_time
        avg_score = sum(r.score for r in results) / len(results) if results else 0.0
        self._update_stats(execution_time, avg_score)
        
        return results
    
    def is_suitable_for_query(self, query: SearchQuery) -> bool:
        """
        Verifica se o algoritmo fuzzy é adequado para a query.
        
        Args:
            query: Query a ser avaliada
            
        Returns:
            bool: True se há dados suficientes para busca fuzzy
        """
        # Fuzzy search é adequado quando temos pelo menos título ou autores
        return bool(query.title or query.authors)
    
    def get_capabilities(self) -> List[str]:
        """Retorna capacidades do algoritmo fuzzy."""
        return [
            'fuzzy_matching',
            'title_similarity',
            'author_similarity',
            'publisher_similarity',
            'typo_tolerance',
            'partial_matching'
        ]
    
    def _calculate_similarity(self, query: SearchQuery, candidate: Dict[str, Any]) -> float:
        """
        Calcula similaridade total entre query e candidato.
        
        Args:
            query: Query de busca
            candidate: Candidato da base de dados
            
        Returns:
            float: Score de similaridade ponderado
        """
        total_score = 0.0
        
        # Title similarity
        if query.title and candidate.get('title'):
            title_sim = self._title_similarity(query.title, candidate['title'])
            total_score += title_sim * self.title_weight
        
        # Author similarity
        if query.authors and candidate.get('authors'):
            author_sim = self._author_similarity(query.authors, candidate['authors'])
            total_score += author_sim * self.author_weight
        
        # Publisher similarity
        if query.publisher and candidate.get('publisher'):
            pub_sim = self._publisher_similarity(query.publisher, candidate['publisher'])
            total_score += pub_sim * self.publisher_weight
        
        # Year match
        if query.year and candidate.get('year'):
            year_match = 1.0 if query.year == candidate['year'] else 0.0
            total_score += year_match * self.year_weight
        
        return min(total_score, 1.0)
    
    def _title_similarity(self, title1: Optional[str], title2: Optional[str]) -> float:
        """Calcula similaridade entre títulos."""
        if not title1 or not title2:
            return 0.0
        
        norm1 = normalize_text_for_comparison(title1)
        norm2 = normalize_text_for_comparison(title2)
        
        return jaro_winkler_similarity(norm1, norm2)
    
    def _author_similarity(self, authors1: Optional[List[str]], authors2: Optional[List[str]]) -> float:
        """Calcula similaridade entre listas de autores."""
        if not authors1 or not authors2:
            return 0.0
        
        # Find best matches between author lists
        max_similarities = []
        
        for author1 in authors1:
            norm1 = normalize_text_for_comparison(author1)
            best_sim = 0.0
            
            for author2 in authors2:
                norm2 = normalize_text_for_comparison(author2)
                sim = jaro_winkler_similarity(norm1, norm2)
                best_sim = max(best_sim, sim)
            
            max_similarities.append(best_sim)
        
        # Return average of best similarities
        return sum(max_similarities) / len(max_similarities) if max_similarities else 0.0
    
    def _publisher_similarity(self, pub1: Optional[str], pub2: Optional[str]) -> float:
        """Calcula similaridade entre editoras."""
        if not pub1 or not pub2:
            return 0.0
        
        norm1 = normalize_text_for_comparison(pub1)
        norm2 = normalize_text_for_comparison(pub2)
        
        return jaro_winkler_similarity(norm1, norm2)
    
    def _get_mock_database(self) -> List[Dict[str, Any]]:
        """
        Retorna base de dados mock para demonstração.
        Em implementação real, seria substituído por acesso a APIs/DB.
        """
        return [
            {
                'title': 'Python Programming',
                'authors': ['John Smith'],
                'publisher': 'Tech Books',
                'year': '2023',
                'isbn': '9781234567890'
            },
            {
                'title': 'Machine Learning Basics',
                'authors': ['Jane Doe', 'Bob Wilson'],
                'publisher': 'AI Publications',
                'year': '2022',
                'isbn': '9781234567891'
            },
            {
                'title': 'Web Development Guide',
                'authors': ['Alice Johnson'],
                'publisher': 'Web Press',
                'year': '2023',
                'isbn': '9781234567892'
            }
        ]