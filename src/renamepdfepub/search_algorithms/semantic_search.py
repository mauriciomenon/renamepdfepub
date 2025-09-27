"""
Semantic Search Algorithm - Busca semântica usando TF-IDF e N-grams.

Implementa algoritmos avançados para:
- Similaridade semântica usando TF-IDF
- Correspondência de N-gramas para nomes de autores
- Análise de contexto e relevância
- Normalização inteligente de termos
"""

import re
import time
import math
from typing import Dict, List, Any, Optional, Tuple, Set
from collections import Counter, defaultdict
from .base_search import BaseSearchAlgorithm, SearchQuery, SearchResult


class TextNormalizer:
    """Normalizador de texto para análise semântica."""
    
    # Common stop words (English and Portuguese)
    STOP_WORDS = {
        'english': {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have',
            'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those'
        },
        'portuguese': {
            'o', 'a', 'os', 'as', 'um', 'uma', 'uns', 'umas', 'de', 'do', 'da', 
            'dos', 'das', 'em', 'no', 'na', 'nos', 'nas', 'para', 'por', 'com',
            'sem', 'sobre', 'entre', 'até', 'desde', 'é', 'são', 'foi', 'foram',
            'ser', 'estar', 'ter', 'haver', 'que', 'qual', 'quando', 'onde',
            'como', 'porque', 'se', 'mas', 'ou', 'e', 'não', 'sim'
        }
    }
    
    # Common technical terms that should be preserved
    TECHNICAL_TERMS = {
        'api', 'sdk', 'gui', 'cli', 'ide', 'sql', 'nosql', 'json', 'xml', 'html',
        'css', 'javascript', 'python', 'java', 'cpp', 'csharp', 'ruby', 'php',
        'react', 'angular', 'vue', 'node', 'express', 'django', 'flask', 'spring',
        'docker', 'kubernetes', 'aws', 'azure', 'gcp', 'git', 'github', 'gitlab',
        'ci', 'cd', 'devops', 'agile', 'scrum', 'kanban', 'tdd', 'bdd', 'ddd',
        'ml', 'ai', 'nlp', 'cv', 'dl', 'nn', 'cnn', 'rnn', 'lstm', 'bert'
    }
    
    @classmethod
    def normalize_text(cls, text: str, language: str = 'english') -> List[str]:
        """
        Normaliza texto para análise semântica.
        
        Args:
            text: Texto para normalizar
            language: Idioma ('english' ou 'portuguese')
            
        Returns:
            List[str]: Lista de tokens normalizados
        """
        if not text:
            return []
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters but preserve alphanumeric and spaces
        text = re.sub(r'[^\w\s\-]', ' ', text)
        
        # Handle common abbreviations and technical terms
        text = cls._preserve_technical_terms(text)
        
        # Split into tokens
        tokens = text.split()
        
        # Remove stop words
        stop_words = cls.STOP_WORDS.get(language, cls.STOP_WORDS['english'])
        tokens = [token for token in tokens if token not in stop_words]
        
        # Remove very short tokens (except preserved technical terms)
        tokens = [
            token for token in tokens 
            if len(token) > 2 or token in cls.TECHNICAL_TERMS
        ]
        
        return tokens
    
    @classmethod
    def _preserve_technical_terms(cls, text: str) -> str:
        """
        Preserva termos técnicos importantes durante a normalização.
        
        Args:
            text: Texto para processar
            
        Returns:
            str: Texto com termos técnicos preservados
        """
        # Convert common abbreviations
        abbreviations = {
            'c++': 'cpp',
            'c#': 'csharp',
            '.net': 'dotnet',
            'node.js': 'nodejs',
            'react.js': 'react',
            'vue.js': 'vue',
            'angular.js': 'angular'
        }
        
        for abbrev, replacement in abbreviations.items():
            text = text.replace(abbrev, replacement)
        
        return text
    
    @classmethod
    def generate_ngrams(cls, tokens: List[str], n: int) -> List[str]:
        """
        Gera N-gramas de uma lista de tokens.
        
        Args:
            tokens: Lista de tokens
            n: Tamanho dos N-gramas
            
        Returns:
            List[str]: Lista de N-gramas
        """
        if len(tokens) < n:
            return []
        
        ngrams = []
        for i in range(len(tokens) - n + 1):
            ngram = ' '.join(tokens[i:i + n])
            ngrams.append(ngram)
        
        return ngrams
    
    @classmethod
    def extract_author_variants(cls, author_name: str) -> Set[str]:
        """
        Extrai variantes de um nome de autor.
        
        Args:
            author_name: Nome do autor
            
        Returns:
            Set[str]: Conjunto de variantes
        """
        if not author_name:
            return set()
        
        variants = set()
        name_parts = author_name.strip().split()
        
        if not name_parts:
            return set()
        
        # Original name
        variants.add(author_name.lower().strip())
        
        # First name + Last name
        if len(name_parts) >= 2:
            variants.add(f"{name_parts[0]} {name_parts[-1]}".lower())
        
        # Last name, First name
        if len(name_parts) >= 2:
            variants.add(f"{name_parts[-1]}, {name_parts[0]}".lower())
        
        # Initials + Last name
        if len(name_parts) >= 2:
            initials = ''.join([part[0] for part in name_parts[:-1]])
            variants.add(f"{initials}. {name_parts[-1]}".lower())
            variants.add(f"{initials} {name_parts[-1]}".lower())
        
        # Just last name
        if len(name_parts) >= 2:
            variants.add(name_parts[-1].lower())
        
        return variants


class TFIDFCalculator:
    """Calculadora de TF-IDF para análise de similaridade."""
    
    def __init__(self):
        self.document_frequency = defaultdict(int)
        self.total_documents = 0
        self.vocabulary = set()
        
    def add_document(self, tokens: List[str]):
        """
        Adiciona um documento ao corpus.
        
        Args:
            tokens: Tokens do documento
        """
        unique_tokens = set(tokens)
        
        for token in unique_tokens:
            self.document_frequency[token] += 1
            self.vocabulary.add(token)
        
        self.total_documents += 1
    
    def calculate_tf(self, tokens: List[str]) -> Dict[str, float]:
        """
        Calcula Term Frequency (TF).
        
        Args:
            tokens: Tokens do documento
            
        Returns:
            Dict[str, float]: TF para cada termo
        """
        if not tokens:
            return {}
        
        token_count = Counter(tokens)
        total_tokens = len(tokens)
        
        tf_scores = {}
        for token, count in token_count.items():
            tf_scores[token] = count / total_tokens
        
        return tf_scores
    
    def calculate_idf(self, term: str) -> float:
        """
        Calcula Inverse Document Frequency (IDF).
        
        Args:
            term: Termo para calcular IDF
            
        Returns:
            float: IDF score
        """
        if self.total_documents == 0:
            return 0.0
        
        df = self.document_frequency.get(term, 0)
        if df == 0:
            return 0.0
        
        return math.log(self.total_documents / df)
    
    def calculate_tfidf_vector(self, tokens: List[str]) -> Dict[str, float]:
        """
        Calcula vetor TF-IDF para um documento.
        
        Args:
            tokens: Tokens do documento
            
        Returns:
            Dict[str, float]: Vetor TF-IDF
        """
        tf_scores = self.calculate_tf(tokens)
        tfidf_vector = {}
        
        for term, tf in tf_scores.items():
            idf = self.calculate_idf(term)
            tfidf_vector[term] = tf * idf
        
        return tfidf_vector
    
    def cosine_similarity(self, vector1: Dict[str, float], vector2: Dict[str, float]) -> float:
        """
        Calcula similaridade coseno entre dois vetores TF-IDF.
        
        Args:
            vector1: Primeiro vetor TF-IDF
            vector2: Segundo vetor TF-IDF
            
        Returns:
            float: Similaridade coseno (0.0 - 1.0)
        """
        if not vector1 or not vector2:
            return 0.0
        
        # Calculate dot product
        dot_product = 0.0
        for term in vector1:
            if term in vector2:
                dot_product += vector1[term] * vector2[term]
        
        # Calculate magnitudes
        magnitude1 = math.sqrt(sum(score ** 2 for score in vector1.values()))
        magnitude2 = math.sqrt(sum(score ** 2 for score in vector2.values()))
        
        if magnitude1 == 0.0 or magnitude2 == 0.0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)


class SemanticSearchAlgorithm(BaseSearchAlgorithm):
    """
    Algoritmo de busca semântica usando TF-IDF e N-gramas.
    
    Características:
    - Análise semântica avançada com TF-IDF
    - Correspondência de N-gramas para autores
    - Normalização inteligente de texto
    - Scoring contextual baseado em relevância
    """
    
    def __init__(self):
        super().__init__("SemanticSearch", "1.0.0")
        self.normalizer = TextNormalizer()
        self.tfidf_calculator = TFIDFCalculator()
        self.min_similarity_threshold = 0.1
        self.author_ngram_size = 2
        self.title_weight = 0.6
        self.author_weight = 0.3
        self.content_weight = 0.1
        self.corpus_initialized = False
        
    def configure(self, config: Dict[str, Any]) -> bool:
        """
        Configura parâmetros do algoritmo semântico.
        
        Args:
            config: Configurações incluindo pesos e thresholds
            
        Returns:
            bool: True se configuração foi bem-sucedida
        """
        try:
            self.min_similarity_threshold = config.get('min_similarity_threshold', 0.1)
            self.author_ngram_size = config.get('author_ngram_size', 2)
            self.title_weight = config.get('title_weight', 0.6)
            self.author_weight = config.get('author_weight', 0.3)
            self.content_weight = config.get('content_weight', 0.1)
            
            # Validate weights sum to 1.0
            total_weight = self.title_weight + self.author_weight + self.content_weight
            if abs(total_weight - 1.0) > 0.01:
                # Normalize weights
                self.title_weight /= total_weight
                self.author_weight /= total_weight
                self.content_weight /= total_weight
            
            self.is_configured = True
            return True
            
        except Exception:
            return False
    
    def search(self, query: SearchQuery) -> List[SearchResult]:
        """
        Executa busca semântica.
        
        Args:
            query: Query com critérios de busca
            
        Returns:
            List[SearchResult]: Resultados ordenados por relevância semântica
        """
        start_time = time.time()
        results = []
        
        # Initialize corpus if needed
        if not self.corpus_initialized:
            self._initialize_corpus(query)
        
        # Normalize query components
        normalized_query = self._normalize_query(query)
        
        # Generate mock candidate documents for demonstration
        candidates = self._get_candidate_documents(query)
        
        # Calculate semantic similarity for each candidate
        for candidate in candidates:
            similarity_score = self._calculate_semantic_similarity(normalized_query, candidate)
            
            if similarity_score >= self.min_similarity_threshold:
                result = SearchResult(
                    score=similarity_score,
                    metadata=candidate['metadata'],
                    algorithm=self.name,
                    details={
                        'similarity_components': candidate.get('similarity_breakdown', {}),
                        'matching_terms': candidate.get('matching_terms', []),
                        'semantic_method': 'tfidf_cosine'
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
        Verifica se o algoritmo semântico é adequado para a query.
        
        Args:
            query: Query a ser avaliada
            
        Returns:
            bool: True se há conteúdo textual suficiente
        """
        # Check if there's meaningful textual content
        text_sources = [query.title, query.text_content]
        if query.authors:
            text_sources.extend(query.authors)
        
        total_text = ' '.join(filter(None, text_sources))
        
        # Need at least some text for semantic analysis
        return len(total_text.strip()) > 10
    
    def get_capabilities(self) -> List[str]:
        """Retorna capacidades do algoritmo semântico."""
        return [
            'tfidf_similarity',
            'ngram_matching',
            'semantic_analysis',
            'author_name_variants',
            'contextual_scoring',
            'multilingual_support',
            'technical_term_preservation'
        ]
    
    def _initialize_corpus(self, initial_query: SearchQuery):
        """
        Inicializa o corpus TF-IDF com documentos de exemplo.
        
        Args:
            initial_query: Query inicial para contexto
        """
        # In a real implementation, this would load from a document database
        sample_documents = [
            "Python Programming Advanced Techniques Machine Learning",
            "JavaScript React Development Modern Web Applications",
            "Data Science Analytics Machine Learning Deep Learning",
            "Software Engineering Design Patterns Best Practices",
            "Artificial Intelligence Natural Language Processing",
            "Database Systems SQL NoSQL Big Data Analytics",
            "Cybersecurity Network Security Ethical Hacking",
            "Mobile Development iOS Android Cross Platform",
            "Cloud Computing AWS Azure DevOps Microservices",
            "Algorithms Data Structures Computer Science Theory"
        ]
        
        # Add sample documents to TF-IDF calculator
        for doc in sample_documents:
            tokens = self.normalizer.normalize_text(doc)
            self.tfidf_calculator.add_document(tokens)
        
        # Add query content to corpus
        if initial_query.text_content:
            query_tokens = self.normalizer.normalize_text(initial_query.text_content)
            self.tfidf_calculator.add_document(query_tokens)
        
        self.corpus_initialized = True
    
    def _normalize_query(self, query: SearchQuery) -> Dict[str, Any]:
        """
        Normaliza componentes da query para análise semântica.
        
        Args:
            query: Query original
            
        Returns:
            Dict[str, Any]: Query normalizada
        """
        normalized = {}
        
        # Normalize title
        if query.title:
            normalized['title_tokens'] = self.normalizer.normalize_text(query.title)
            normalized['title_vector'] = self.tfidf_calculator.calculate_tfidf_vector(
                normalized['title_tokens']
            )
        
        # Normalize authors
        if query.authors:
            normalized['author_variants'] = []
            for author in query.authors:
                variants = self.normalizer.extract_author_variants(author)
                normalized['author_variants'].extend(variants)
            
            # Generate author N-grams
            author_text = ' '.join(query.authors)
            author_tokens = self.normalizer.normalize_text(author_text)
            normalized['author_ngrams'] = self.normalizer.generate_ngrams(
                author_tokens, self.author_ngram_size
            )
        
        # Normalize text content
        if query.text_content:
            normalized['content_tokens'] = self.normalizer.normalize_text(query.text_content)
            normalized['content_vector'] = self.tfidf_calculator.calculate_tfidf_vector(
                normalized['content_tokens']
            )
        
        return normalized
    
    def _get_candidate_documents(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """
        Obtém documentos candidatos para comparação.
        
        Args:
            query: Query de busca
            
        Returns:
            List[Dict[str, Any]]: Lista de candidatos com metadados
        """
        # Mock candidate documents with realistic metadata
        candidates = [
            {
                'metadata': {
                    'title': 'Advanced Python Programming: Machine Learning Techniques',
                    'authors': ['John Smith', 'Maria Garcia'],
                    'publisher': 'Tech Publishing',
                    'year': '2023',
                    'subjects': ['programming', 'machine learning', 'python']
                },
                'text_content': 'python programming advanced machine learning algorithms data science'
            },
            {
                'metadata': {
                    'title': 'JavaScript and React: Modern Web Development',
                    'authors': ['Alice Johnson'],
                    'publisher': 'Web Press',
                    'year': '2022',
                    'subjects': ['javascript', 'react', 'web development']
                },
                'text_content': 'javascript react development modern web applications frontend'
            },
            {
                'metadata': {
                    'title': 'Data Science Fundamentals: Analytics and Visualization',
                    'authors': ['Robert Chen', 'Sarah Wilson'],
                    'publisher': 'Data Books',
                    'year': '2023',
                    'subjects': ['data science', 'analytics', 'visualization']
                },
                'text_content': 'data science analytics visualization statistics machine learning'
            },
            {
                'metadata': {
                    'title': 'Artificial Intelligence: Deep Learning and Neural Networks',
                    'authors': ['David Kumar'],
                    'publisher': 'AI Publications',
                    'year': '2024',
                    'subjects': ['artificial intelligence', 'deep learning', 'neural networks']
                },
                'text_content': 'artificial intelligence deep learning neural networks ai algorithms'
            }
        ]
        
        # Normalize candidate documents
        for candidate in candidates:
            # Title normalization
            title_tokens = self.normalizer.normalize_text(candidate['metadata']['title'])
            candidate['title_vector'] = self.tfidf_calculator.calculate_tfidf_vector(title_tokens)
            
            # Author normalization
            authors = candidate['metadata'].get('authors', [])
            candidate['author_variants'] = []
            for author in authors:
                variants = self.normalizer.extract_author_variants(author)
                candidate['author_variants'].extend(variants)
            
            # Content normalization
            content_tokens = self.normalizer.normalize_text(candidate['text_content'])
            candidate['content_vector'] = self.tfidf_calculator.calculate_tfidf_vector(content_tokens)
        
        return candidates
    
    def _calculate_semantic_similarity(self, normalized_query: Dict[str, Any], 
                                      candidate: Dict[str, Any]) -> float:
        """
        Calcula similaridade semântica entre query e candidato.
        
        Args:
            normalized_query: Query normalizada
            candidate: Documento candidato
            
        Returns:
            float: Score de similaridade (0.0 - 1.0)
        """
        similarity_components = {}
        
        # Title similarity
        title_sim = 0.0
        if 'title_vector' in normalized_query and 'title_vector' in candidate:
            title_sim = self.tfidf_calculator.cosine_similarity(
                normalized_query['title_vector'],
                candidate['title_vector']
            )
        similarity_components['title'] = title_sim
        
        # Author similarity
        author_sim = 0.0
        if 'author_variants' in normalized_query and 'author_variants' in candidate:
            author_sim = self._calculate_author_similarity(
                normalized_query['author_variants'],
                candidate['author_variants']
            )
        similarity_components['author'] = author_sim
        
        # Content similarity
        content_sim = 0.0
        if 'content_vector' in normalized_query and 'content_vector' in candidate:
            content_sim = self.tfidf_calculator.cosine_similarity(
                normalized_query['content_vector'],
                candidate['content_vector']
            )
        similarity_components['content'] = content_sim
        
        # Calculate weighted final score
        final_score = (
            title_sim * self.title_weight +
            author_sim * self.author_weight +
            content_sim * self.content_weight
        )
        
        # Store breakdown for debugging
        candidate['similarity_breakdown'] = similarity_components
        
        return final_score
    
    def _calculate_author_similarity(self, query_variants: List[str], 
                                   candidate_variants: List[str]) -> float:
        """
        Calcula similaridade entre variantes de nomes de autores.
        
        Args:
            query_variants: Variantes da query
            candidate_variants: Variantes do candidato
            
        Returns:
            float: Similaridade de autores (0.0 - 1.0)
        """
        if not query_variants or not candidate_variants:
            return 0.0
        
        max_similarity = 0.0
        
        # Check for exact matches first
        query_set = set(query_variants)
        candidate_set = set(candidate_variants)
        
        exact_matches = query_set.intersection(candidate_set)
        if exact_matches:
            max_similarity = 1.0
        else:
            # Check for partial matches using string similarity
            for query_variant in query_variants:
                for candidate_variant in candidate_variants:
                    # Simple word overlap similarity
                    similarity = self._word_overlap_similarity(query_variant, candidate_variant)
                    max_similarity = max(max_similarity, similarity)
        
        return max_similarity
    
    def _word_overlap_similarity(self, text1: str, text2: str) -> float:
        """
        Calcula similaridade baseada em sobreposição de palavras.
        
        Args:
            text1: Primeiro texto
            text2: Segundo texto
            
        Returns:
            float: Similaridade (0.0 - 1.0)
        """
        if not text1 or not text2:
            return 0.0
        
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def reset_corpus(self):
        """Reseta o corpus TF-IDF."""
        self.tfidf_calculator = TFIDFCalculator()
        self.corpus_initialized = False
    
    def get_corpus_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas do corpus.
        
        Returns:
            Dict[str, Any]: Estatísticas do corpus
        """
        return {
            'total_documents': self.tfidf_calculator.total_documents,
            'vocabulary_size': len(self.tfidf_calculator.vocabulary),
            'top_terms': list(self.tfidf_calculator.vocabulary)[:20] if self.tfidf_calculator.vocabulary else []
        }