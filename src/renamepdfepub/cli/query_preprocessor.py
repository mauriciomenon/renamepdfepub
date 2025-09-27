"""
Advanced Query Preprocessor - Processamento inteligente de queries.

Funcionalidades:
- Limpeza e normalização avançada de queries
- Análise de contexto e intenção
- Sugestões automáticas e auto-completar
- Detecção de entidades (ISBN, autores, títulos)
- Correção automática de typos
"""

import re
import time
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from collections import Counter
from ..search_algorithms.base_search import SearchQuery


@dataclass
class QueryAnalysis:
    """Resultado da análise de uma query."""
    original_query: str
    cleaned_query: str
    detected_entities: Dict[str, List[str]] = field(default_factory=dict)
    suggested_corrections: List[str] = field(default_factory=list)
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    query_type: str = "mixed"  # 'isbn', 'title', 'author', 'mixed'
    language: str = "unknown"
    complexity_score: float = 0.0
    processing_time: float = 0.0


@dataclass
class SuggestionResult:
    """Resultado de sugestões automáticas."""
    suggestions: List[str] = field(default_factory=list)
    corrections: List[str] = field(default_factory=list)
    completions: List[str] = field(default_factory=list)
    confidence: float = 0.0


class EntityDetector:
    """Detector de entidades em queries de busca."""
    
    # Regex patterns for entity detection
    ISBN_PATTERNS = [
        re.compile(r'(?:ISBN[:\s]*)?(?:97[89][\d\-\s]{10,17}[\dXx])', re.IGNORECASE),
        re.compile(r'(?:ISBN[:\s]*)?(?<!\d)(\d{9}[\dXx])(?!\d)', re.IGNORECASE)
    ]
    
    # Common author indicators
    AUTHOR_INDICATORS = {
        'english': ['by', 'author', 'written by', 'authored by', 'dr.', 'prof.', 'mr.', 'ms.', 'mrs.'],
        'portuguese': ['por', 'autor', 'autora', 'escrito por', 'dr.', 'dra.', 'prof.', 'profa.']
    }
    
    # Common title indicators
    TITLE_INDICATORS = {
        'english': ['title', 'book', 'guide', 'handbook', 'manual', 'introduction', 'advanced'],
        'portuguese': ['título', 'livro', 'guia', 'manual', 'introdução', 'avançado', 'fundamentos']
    }
    
    # Publisher indicators
    PUBLISHER_INDICATORS = {
        'english': ['publisher', 'published by', 'press', 'publications', 'books'],
        'portuguese': ['editora', 'publicado por', 'edições', 'publicações', 'livros']
    }
    
    @classmethod
    def detect_isbn(cls, text: str) -> List[str]:
        """
        Detecta ISBNs no texto.
        
        Args:
            text: Texto para análise
            
        Returns:
            List[str]: Lista de ISBNs encontrados
        """
        isbns = []
        
        for pattern in cls.ISBN_PATTERNS:
            matches = pattern.findall(text)
            for match in matches:
                # Clean and validate
                cleaned = re.sub(r'[^\dXx]', '', match.upper())
                if len(cleaned) in [10, 13]:
                    isbns.append(cleaned)
        
        return list(set(isbns))  # Remove duplicates
    
    @classmethod
    def detect_authors(cls, text: str, language: str = 'english') -> List[str]:
        """
        Detecta nomes de autores no texto.
        
        Args:
            text: Texto para análise
            language: Idioma para contexto
            
        Returns:
            List[str]: Lista de possíveis autores
        """
        authors = []
        indicators = cls.AUTHOR_INDICATORS.get(language, cls.AUTHOR_INDICATORS['english'])
        
        # Look for patterns like "by John Doe" or "author: Jane Smith"
        for indicator in indicators:
            pattern = rf'{re.escape(indicator)}[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
            matches = re.findall(pattern, text, re.IGNORECASE)
            authors.extend(matches)
        
        # Look for capitalized names (potential authors)
        name_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b'
        potential_names = re.findall(name_pattern, text)
        
        # Filter out common words that might match the pattern
        common_words = {'The', 'And', 'For', 'With', 'From', 'To', 'In', 'On', 'At', 'By'}
        potential_names = [name for name in potential_names if not any(word in common_words for word in name.split())]
        
        authors.extend(potential_names[:3])  # Limit to avoid false positives
        
        return list(set(authors))
    
    @classmethod
    def detect_titles(cls, text: str, language: str = 'english') -> List[str]:
        """
        Detecta possíveis títulos de livros.
        
        Args:
            text: Texto para análise
            language: Idioma para contexto
            
        Returns:
            List[str]: Lista de possíveis títulos
        """
        titles = []
        indicators = cls.TITLE_INDICATORS.get(language, cls.TITLE_INDICATORS['english'])
        
        # Look for quoted strings (often titles)
        quoted_pattern = r'["\'"](.*?)["\'""]'
        quoted_matches = re.findall(quoted_pattern, text)
        titles.extend([match for match in quoted_matches if len(match) > 5])
        
        # Look for patterns with title indicators
        for indicator in indicators:
            if indicator in text.lower():
                # This is a simple heuristic - in practice, would use more sophisticated NLP
                words = text.split()
                for i, word in enumerate(words):
                    if word.lower() == indicator and i < len(words) - 1:
                        # Take next few words as potential title
                        potential_title = ' '.join(words[i+1:i+5])
                        if len(potential_title) > 5:
                            titles.append(potential_title)
        
        return list(set(titles))[:3]  # Limit results
    
    @classmethod
    def detect_language(cls, text: str) -> str:
        """
        Detecta o idioma do texto.
        
        Args:
            text: Texto para análise
            
        Returns:
            str: Idioma detectado ('english', 'portuguese', ou 'unknown')
        """
        # Simple language detection based on common words
        english_words = {'the', 'and', 'or', 'by', 'with', 'for', 'in', 'on', 'at', 'to', 'from'}
        portuguese_words = {'o', 'a', 'e', 'ou', 'por', 'com', 'para', 'em', 'de', 'do', 'da'}
        
        text_lower = text.lower()
        words = set(re.findall(r'\b\w+\b', text_lower))
        
        english_score = len(words.intersection(english_words))
        portuguese_score = len(words.intersection(portuguese_words))
        
        if english_score > portuguese_score:
            return 'english'
        elif portuguese_score > english_score:
            return 'portuguese'
        else:
            return 'unknown'


class QueryCleaner:
    """Limpador e normalizador de queries."""
    
    # Common query noise patterns
    NOISE_PATTERNS = [
        r'\b(?:please\s+)?(find|search|look\s+for|get|show|display)\b',
        r'\b(?:me\s+)?(?:a\s+)?book\s+(?:about|on|called|titled|named)?\s*',
        r'\b(?:i\s+(?:want|need|am\s+looking\s+for))\b',
        r'\b(?:can\s+you|could\s+you|would\s+you)\b',
        r'\b(?:help\s+me|assist\s+me)\b',
        r'[?!]{2,}',  # Multiple punctuation
        r'\s{2,}',    # Multiple spaces
    ]
    
    # Typo correction patterns (common mistakes)
    TYPO_CORRECTIONS = {
        # Programming-related typos
        'pythno': 'python',
        'phyton': 'python',
        'pyton': 'python',
        'javascirpt': 'javascript',
        'javasript': 'javascript',
        'machien': 'machine',
        'learing': 'learning',
        'learinng': 'learning',
        'algorihtm': 'algorithm',
        'algorithem': 'algorithm',
        'programing': 'programming',
        'programmin': 'programming',
        
        # General typos
        'recieve': 'receive',
        'seperate': 'separate',
        'definately': 'definitely',
        'occured': 'occurred',
        'begining': 'beginning',
        'accomodate': 'accommodate',
        'achievment': 'achievement',
        'sucessful': 'successful',
        'excercise': 'exercise',
        'referance': 'reference',
    }
    
    @classmethod
    def clean_query(cls, query: str) -> str:
        """
        Limpa e normaliza uma query de busca.
        
        Args:
            query: Query original
            
        Returns:
            str: Query limpa
        """
        if not query:
            return ""
        
        cleaned = query.strip()
        
        # Remove noise patterns
        for pattern in cls.NOISE_PATTERNS:
            cleaned = re.sub(pattern, ' ', cleaned, flags=re.IGNORECASE)
        
        # Normalize whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        # Remove leading/trailing punctuation (except ISBN-related)
        cleaned = re.sub(r'^[^\w\d]+|[^\w\d]+$', '', cleaned)
        
        return cleaned
    
    @classmethod
    def suggest_corrections(cls, query: str) -> List[str]:
        """
        Sugere correções para typos na query.
        
        Args:
            query: Query para análise
            
        Returns:
            List[str]: Lista de correções sugeridas
        """
        suggestions = []
        words = query.lower().split()
        
        corrected_words = []
        has_corrections = False
        
        for word in words:
            if word in cls.TYPO_CORRECTIONS:
                corrected_words.append(cls.TYPO_CORRECTIONS[word])
                has_corrections = True
            else:
                corrected_words.append(word)
        
        if has_corrections:
            suggestions.append(' '.join(corrected_words))
        
        return suggestions
    
    @classmethod
    def calculate_complexity(cls, query: str) -> float:
        """
        Calcula um score de complexidade da query.
        
        Args:
            query: Query para análise
            
        Returns:
            float: Score de complexidade (0.0 - 1.0)
        """
        if not query:
            return 0.0
        
        factors = {
            'length': min(len(query) / 100, 1.0) * 0.2,
            'words': min(len(query.split()) / 20, 1.0) * 0.3,
            'special_chars': min(len(re.findall(r'[^\w\s]', query)) / 10, 1.0) * 0.2,
            'entities': 0.0,  # Will be calculated based on detected entities
            'structure': 0.0   # Will be calculated based on query structure
        }
        
        # Entity complexity
        if re.search(r'ISBN|978|979', query, re.IGNORECASE):
            factors['entities'] += 0.1
        if re.search(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b', query):  # Potential names
            factors['entities'] += 0.1
        
        # Structure complexity
        if '"' in query or "'" in query:  # Quoted strings
            factors['structure'] += 0.05
        if re.search(r'\b(?:and|or|not)\b', query, re.IGNORECASE):  # Boolean operators
            factors['structure'] += 0.1
        
        return min(sum(factors.values()), 1.0)


class AutoCompleter:
    """Sistema de auto-completar para queries."""
    
    def __init__(self):
        self.common_queries = self._load_common_queries()
        self.technical_terms = self._load_technical_terms()
        
    def _load_common_queries(self) -> List[str]:
        """Carrega queries comuns para auto-completar."""
        return [
            "Python programming guide",
            "Machine learning fundamentals",
            "JavaScript development",
            "Data science handbook",
            "Artificial intelligence introduction",
            "Web development tutorial",
            "Database design principles",
            "Software engineering practices",
            "Computer science algorithms",
            "Mobile app development",
            "Cybersecurity essentials",
            "Cloud computing basics",
            "DevOps practices",
            "React.js tutorial",
            "Node.js development",
            "Angular framework",
            "Vue.js guide",
            "SQL database tutorial",
            "NoSQL databases",
            "Big data analytics"
        ]
    
    def _load_technical_terms(self) -> List[str]:
        """Carrega termos técnicos comuns."""
        return [
            "algorithm", "algorithms", "programming", "development", "javascript",
            "python", "java", "react", "angular", "vue", "node", "express",
            "database", "sql", "nosql", "mongodb", "mysql", "postgresql",
            "machine learning", "artificial intelligence", "deep learning",
            "neural networks", "data science", "analytics", "statistics",
            "web development", "mobile development", "software engineering",
            "design patterns", "architecture", "microservices", "api", "rest",
            "graphql", "docker", "kubernetes", "aws", "azure", "gcp",
            "devops", "ci/cd", "git", "github", "testing", "tdd", "bdd"
        ]
    
    def get_suggestions(self, partial_query: str, max_suggestions: int = 5) -> SuggestionResult:
        """
        Obtém sugestões para uma query parcial.
        
        Args:
            partial_query: Query parcial
            max_suggestions: Número máximo de sugestões
            
        Returns:
            SuggestionResult: Resultado com sugestões
        """
        if not partial_query or len(partial_query) < 2:
            return SuggestionResult()
        
        partial_lower = partial_query.lower().strip()
        
        # Find matching common queries
        suggestions = []
        for query in self.common_queries:
            if partial_lower in query.lower():
                suggestions.append(query)
        
        # Find matching technical terms for completion
        completions = []
        words = partial_lower.split()
        if words:
            last_word = words[-1]
            for term in self.technical_terms:
                if term.startswith(last_word) and term != last_word:
                    # Complete the last word
                    completed_query = ' '.join(words[:-1] + [term])
                    completions.append(completed_query)
        
        # Sort by relevance (simple length-based for now)
        suggestions.sort(key=len)
        completions.sort(key=len)
        
        # Calculate confidence based on match quality
        confidence = 0.0
        if suggestions or completions:
            # Simple confidence based on number of matches and partial query length
            confidence = min(0.9, (len(suggestions) + len(completions)) * 0.1 + len(partial_query) * 0.01)
        
        return SuggestionResult(
            suggestions=suggestions[:max_suggestions],
            completions=completions[:max_suggestions],
            confidence=confidence
        )


class QueryPreprocessor:
    """
    Preprocessador avançado de queries com análise inteligente.
    
    Funcionalidades:
    - Limpeza e normalização
    - Detecção de entidades
    - Correção de typos
    - Análise de complexidade
    - Sugestões automáticas
    """
    
    def __init__(self):
        self.entity_detector = EntityDetector()
        self.query_cleaner = QueryCleaner()
        self.auto_completer = AutoCompleter()
        self.processing_stats = {
            'total_queries': 0,
            'total_time': 0.0,
            'average_time': 0.0
        }
    
    def analyze_query(self, query_text: str) -> QueryAnalysis:
        """
        Analisa uma query completamente.
        
        Args:
            query_text: Texto da query
            
        Returns:
            QueryAnalysis: Análise completa da query
        """
        start_time = time.time()
        
        if not query_text:
            return QueryAnalysis(
                original_query="",
                cleaned_query="",
                processing_time=time.time() - start_time
            )
        
        # Clean the query
        cleaned = self.query_cleaner.clean_query(query_text)
        
        # Detect language
        language = self.entity_detector.detect_language(query_text)
        
        # Detect entities
        entities = {
            'isbns': self.entity_detector.detect_isbn(query_text),
            'authors': self.entity_detector.detect_authors(query_text, language),
            'titles': self.entity_detector.detect_titles(query_text, language)
        }
        
        # Suggest corrections
        corrections = self.query_cleaner.suggest_corrections(query_text)
        
        # Calculate confidence scores
        confidence_scores = self._calculate_confidence_scores(query_text, entities)
        
        # Determine query type
        query_type = self._determine_query_type(entities)
        
        # Calculate complexity
        complexity = self.query_cleaner.calculate_complexity(query_text)
        
        processing_time = time.time() - start_time
        
        # Update stats
        self._update_stats(processing_time)
        
        return QueryAnalysis(
            original_query=query_text,
            cleaned_query=cleaned,
            detected_entities=entities,
            suggested_corrections=corrections,
            confidence_scores=confidence_scores,
            query_type=query_type,
            language=language,
            complexity_score=complexity,
            processing_time=processing_time
        )
    
    def preprocess_for_search(self, query_text: str) -> SearchQuery:
        """
        Preprocessa uma query e retorna SearchQuery otimizada.
        
        Args:
            query_text: Texto da query
            
        Returns:
            SearchQuery: Query preparada para busca
        """
        analysis = self.analyze_query(query_text)
        
        # Extract components for SearchQuery
        isbn = analysis.detected_entities['isbns'][0] if analysis.detected_entities['isbns'] else None
        authors = analysis.detected_entities['authors']
        
        # Determine title from cleaned query or detected titles
        title = None
        if analysis.detected_entities['titles']:
            title = analysis.detected_entities['titles'][0]
        elif analysis.cleaned_query and analysis.query_type in ['title', 'mixed']:
            title = analysis.cleaned_query
        
        return SearchQuery(
            title=title,
            authors=authors if authors else None,
            isbn=isbn,
            text_content=analysis.cleaned_query,
            metadata={'preprocessing_analysis': analysis}
        )
    
    def get_auto_suggestions(self, partial_query: str) -> SuggestionResult:
        """
        Obtém sugestões automáticas para query parcial.
        
        Args:
            partial_query: Query parcial
            
        Returns:
            SuggestionResult: Sugestões e completações
        """
        return self.auto_completer.get_suggestions(partial_query)
    
    def _calculate_confidence_scores(self, query: str, entities: Dict[str, List[str]]) -> Dict[str, float]:
        """Calcula scores de confiança para diferentes aspectos da query."""
        scores = {}
        
        # ISBN confidence
        if entities['isbns']:
            scores['isbn'] = 0.95  # High confidence for ISBN detection
        
        # Author confidence (based on name patterns)
        if entities['authors']:
            # Simple heuristic: longer names with proper capitalization = higher confidence
            avg_name_length = sum(len(name.split()) for name in entities['authors']) / len(entities['authors'])
            scores['author'] = min(0.9, 0.3 + avg_name_length * 0.2)
        
        # Title confidence
        if entities['titles']:
            scores['title'] = 0.7  # Moderate confidence for title detection
        
        # Overall confidence
        if scores:
            scores['overall'] = sum(scores.values()) / len(scores)
        else:
            scores['overall'] = 0.1  # Low confidence for unstructured queries
        
        return scores
    
    def _determine_query_type(self, entities: Dict[str, List[str]]) -> str:
        """Determina o tipo principal da query."""
        if entities['isbns']:
            return 'isbn'
        elif entities['authors'] and not entities['titles']:
            return 'author'
        elif entities['titles'] and not entities['authors']:
            return 'title'
        elif entities['authors'] and entities['titles']:
            return 'mixed'
        else:
            return 'text'
    
    def _update_stats(self, processing_time: float):
        """Atualiza estatísticas de processamento."""
        self.processing_stats['total_queries'] += 1
        self.processing_stats['total_time'] += processing_time
        self.processing_stats['average_time'] = (
            self.processing_stats['total_time'] / self.processing_stats['total_queries']
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas de processamento."""
        return self.processing_stats.copy()
    
    def reset_stats(self):
        """Reseta estatísticas."""
        self.processing_stats = {
            'total_queries': 0,
            'total_time': 0.0,
            'average_time': 0.0
        }