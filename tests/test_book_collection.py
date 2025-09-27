#!/usr/bin/env python3
"""
Sistema Abrangente de Testes para Coleção de Livros
==================================================

Este módulo implementa testes extensivos para validar os algoritmos de busca
contra a coleção completa de livros na pasta books/.

Objetivos:
- Meta inicial: 50% de acurácia
- Progressão: 10% em 10% até 90%
- Testes por algoritmo: Fuzzy, ISBN, Semântico
- Preparação para expansão (editoras, catálogos, Amazon)

Estrutura Modular:
- TestBookCollection: Classe principal de testes
- TestAlgorithmPerformance: Testes específicos por algoritmo
- TestAccuracyProgression: Validação de metas de acurácia
- TestBookMetadata: Validação de metadados extraídos
"""

import os
import sys
import time
import json
import logging
import statistics
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest
import unittest
from unittest.mock import Mock, patch

# Adicionar src ao path para imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

try:
    from renamepdfepub.search_algorithms.fuzzy_search import FuzzySearchAlgorithm
    from renamepdfepub.search_algorithms.isbn_search import ISBNSearchAlgorithm
    from renamepdfepub.search_algorithms.semantic_search import SemanticSearchAlgorithm
    from renamepdfepub.search_algorithms.search_orchestrator import SearchOrchestrator
    from renamepdfepub.metadata_extractor import MetadataExtractor
    from renamepdfepub.logging_config import setup_logging
except ImportError as e:
    print(f"Erro de importação: {e}")
    sys.exit(1)

# Configurar logging
logger = setup_logging(__name__)

@dataclass
class BookTestResult:
    """Resultado de teste para um livro específico"""
    filename: str
    original_title: str
    algorithm: str
    search_query: str
    found_results: List[Dict[str, Any]]
    best_match: Optional[Dict[str, Any]]
    confidence_score: float
    response_time_ms: float
    accuracy_score: float
    success: bool
    error_message: Optional[str] = None

@dataclass
class AlgorithmStats:
    """Estatísticas de performance por algoritmo"""
    algorithm_name: str
    total_tests: int
    successful_tests: int
    failed_tests: int
    accuracy_rate: float
    avg_response_time: float
    avg_confidence: float
    accuracy_by_book_type: Dict[str, float]

class BookCollectionAnalyzer:
    """Analisador da coleção de livros para categorização"""
    
    def __init__(self, books_dir: str):
        self.books_dir = Path(books_dir)
        self.book_categories = {
            'programming': ['python', 'javascript', 'java', 'c++', 'react', 'node'],
            'data_science': ['data', 'machine', 'learning', 'ai', 'pandas'],
            'security': ['hack', 'security', 'cyber', 'penetration', 'malware'],
            'web_development': ['web', 'html', 'css', 'frontend', 'backend'],
            'database': ['sql', 'mysql', 'postgresql', 'database', 'mongo'],
            'devops': ['docker', 'cloud', 'aws', 'kubernetes', 'ci'],
            'technical': ['api', 'architecture', 'design', 'patterns']
        }
    
    def get_all_books(self) -> List[Path]:
        """Obter todos os arquivos de livros"""
        extensions = {'.pdf', '.epub', '.mobi'}
        books = []
        
        for file_path in self.books_dir.iterdir():
            if file_path.suffix.lower() in extensions:
                books.append(file_path)
        
        logger.info(f"Encontrados {len(books)} livros na coleção")
        return sorted(books)
    
    def categorize_book(self, book_path: Path) -> str:
        """Categorizar livro baseado no nome do arquivo"""
        filename_lower = book_path.name.lower()
        
        for category, keywords in self.book_categories.items():
            if any(keyword in filename_lower for keyword in keywords):
                return category
        
        return 'general'
    
    def extract_expected_metadata(self, book_path: Path) -> Dict[str, str]:
        """Extrair metadados esperados do nome do arquivo"""
        filename = book_path.stem
        
        # Remover extensões duplas como .pdf.pdf
        while filename.endswith('.pdf') or filename.endswith('.epub'):
            filename = filename[:-4]
        
        # Padrões comuns de nomes de arquivo
        metadata = {
            'filename': book_path.name,
            'extracted_title': filename,
            'category': self.categorize_book(book_path),
            'file_size': book_path.stat().st_size,
            'extension': book_path.suffix.lower()
        }
        
        # Tentar extrair versão/edição
        if '_v' in filename:
            parts = filename.split('_v')
            metadata['title_clean'] = parts[0].replace('_', ' ')
            metadata['version'] = parts[1].split('_')[0]
        elif 'edition' in filename.lower():
            metadata['has_edition'] = True
        
        return metadata

class TestBookCollection(unittest.TestCase):
    """Classe principal de testes para a coleção de livros"""
    
    @classmethod
    def setUpClass(cls):
        """Configuração inicial dos testes"""
        cls.books_dir = project_root / "books"
        cls.results_dir = project_root / "test_results"
        cls.results_dir.mkdir(exist_ok=True)
        
        # Inicializar analisador
        cls.analyzer = BookCollectionAnalyzer(str(cls.books_dir))
        cls.books = cls.analyzer.get_all_books()
        
        # Inicializar algoritmos de busca
        cls.fuzzy_search = FuzzySearchAlgorithm()
        cls.isbn_search = ISBNSearchAlgorithm()
        cls.semantic_search = SemanticSearchAlgorithm()
        cls.orchestrator = SearchOrchestrator()
        
        # Configurações de teste
        cls.accuracy_targets = [0.5, 0.6, 0.7, 0.8, 0.9]  # 50% até 90%
        cls.max_concurrent_tests = 5
        
        logger.info(f"Configurados testes para {len(cls.books)} livros")
    
    def setUp(self):
        """Configuração antes de cada teste"""
        self.test_results = []
        self.start_time = time.time()
    
    def tearDown(self):
        """Limpeza após cada teste"""
        total_time = time.time() - self.start_time
        logger.info(f"Teste concluído em {total_time:.2f}s")
    
    def test_fuzzy_search_algorithm(self):
        """Testar algoritmo de busca fuzzy em toda coleção"""
        logger.info("=== TESTANDO ALGORITMO FUZZY SEARCH ===")
        
        results = self._run_algorithm_tests(
            algorithm_name="fuzzy",
            search_function=self._test_fuzzy_search_book,
            target_accuracy=0.5
        )
        
        self._validate_accuracy_target(results, 0.5, "Fuzzy Search")
        self._save_detailed_results(results, "fuzzy_search_results.json")
    
    def test_isbn_search_algorithm(self):
        """Testar algoritmo de busca por ISBN em toda coleção"""
        logger.info("=== TESTANDO ALGORITMO ISBN SEARCH ===")
        
        results = self._run_algorithm_tests(
            algorithm_name="isbn",
            search_function=self._test_isbn_search_book,
            target_accuracy=0.6
        )
        
        self._validate_accuracy_target(results, 0.6, "ISBN Search")
        self._save_detailed_results(results, "isbn_search_results.json")
    
    def test_semantic_search_algorithm(self):
        """Testar algoritmo de busca semântica em toda coleção"""
        logger.info("=== TESTANDO ALGORITMO SEMANTIC SEARCH ===")
        
        results = self._run_algorithm_tests(
            algorithm_name="semantic",
            search_function=self._test_semantic_search_book,
            target_accuracy=0.7
        )
        
        self._validate_accuracy_target(results, 0.7, "Semantic Search")
        self._save_detailed_results(results, "semantic_search_results.json")
    
    def test_orchestrator_integration(self):
        """Testar orquestrador com todos os algoritmos"""
        logger.info("=== TESTANDO SEARCH ORCHESTRATOR ===")
        
        results = self._run_algorithm_tests(
            algorithm_name="orchestrator",
            search_function=self._test_orchestrator_search_book,
            target_accuracy=0.8
        )
        
        self._validate_accuracy_target(results, 0.8, "Search Orchestrator")
        self._save_detailed_results(results, "orchestrator_results.json")
    
    def test_accuracy_progression(self):
        """Testar progressão de acurácia de 50% até 90%"""
        logger.info("=== TESTANDO PROGRESSÃO DE ACURÁCIA ===")
        
        all_results = {}
        
        # Testar cada algoritmo
        algorithms = [
            ("fuzzy", self._test_fuzzy_search_book),
            ("isbn", self._test_isbn_search_book),
            ("semantic", self._test_semantic_search_book),
            ("orchestrator", self._test_orchestrator_search_book)
        ]
        
        for algorithm_name, search_function in algorithms:
            logger.info(f"Testando progressão para {algorithm_name}")
            
            results = self._run_algorithm_tests(
                algorithm_name=algorithm_name,
                search_function=search_function,
                target_accuracy=0.5
            )
            
            all_results[algorithm_name] = results
        
        # Validar progressão
        self._validate_accuracy_progression(all_results)
        self._save_detailed_results(all_results, "accuracy_progression.json")
    
    def test_performance_benchmarks(self):
        """Testar benchmarks de performance"""
        logger.info("=== TESTANDO PERFORMANCE BENCHMARKS ===")
        
        # Teste de stress com livros aleatórios
        import random
        test_books = random.sample(self.books, min(50, len(self.books)))
        
        performance_results = {}
        
        algorithms = [
            ("fuzzy", self._test_fuzzy_search_book),
            ("isbn", self._test_isbn_search_book),
            ("semantic", self._test_semantic_search_book),
            ("orchestrator", self._test_orchestrator_search_book)
        ]
        
        for algorithm_name, search_function in algorithms:
            logger.info(f"Benchmark de performance para {algorithm_name}")
            
            times = []
            confidences = []
            
            for book in test_books[:20]:  # Teste com 20 livros
                result = search_function(book)
                times.append(result.response_time_ms)
                confidences.append(result.confidence_score)
            
            performance_results[algorithm_name] = {
                'avg_response_time': statistics.mean(times),
                'max_response_time': max(times),
                'min_response_time': min(times),
                'avg_confidence': statistics.mean(confidences),
                'total_tests': len(times)
            }
        
        # Validar targets de performance
        for algorithm, stats in performance_results.items():
            self.assertLess(
                stats['avg_response_time'], 100,
                f"{algorithm}: Tempo médio {stats['avg_response_time']:.2f}ms > 100ms"
            )
        
        self._save_detailed_results(performance_results, "performance_benchmarks.json")
    
    def _run_algorithm_tests(self, algorithm_name: str, search_function, target_accuracy: float) -> List[BookTestResult]:
        """Executar testes para um algoritmo específico"""
        results = []
        
        # Usar ThreadPoolExecutor para testes paralelos
        with ThreadPoolExecutor(max_workers=self.max_concurrent_tests) as executor:
            # Submeter tarefas
            future_to_book = {
                executor.submit(search_function, book): book 
                for book in self.books[:100]  # Testar primeiros 100 livros
            }
            
            # Coletar resultados
            for future in as_completed(future_to_book):
                book = future_to_book[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    if len(results) % 10 == 0:
                        logger.info(f"{algorithm_name}: {len(results)} testes concluídos")
                        
                except Exception as exc:
                    logger.error(f"Erro testando {book}: {exc}")
                    
                    # Criar resultado de erro
                    error_result = BookTestResult(
                        filename=book.name,
                        original_title=book.stem,
                        algorithm=algorithm_name,
                        search_query="",
                        found_results=[],
                        best_match=None,
                        confidence_score=0.0,
                        response_time_ms=0.0,
                        accuracy_score=0.0,
                        success=False,
                        error_message=str(exc)
                    )
                    results.append(error_result)
        
        logger.info(f"Concluídos {len(results)} testes para {algorithm_name}")
        return results
    
    def _test_fuzzy_search_book(self, book_path: Path) -> BookTestResult:
        """Testar busca fuzzy para um livro específico"""
        start_time = time.time()
        
        try:
            # Extrair metadados esperados
            metadata = self.analyzer.extract_expected_metadata(book_path)
            query = metadata['extracted_title']
            
            # Executar busca fuzzy
            results = self.fuzzy_search.search(query, limit=5)
            
            response_time = (time.time() - start_time) * 1000
            
            # Calcular acurácia
            best_match = results[0] if results else None
            accuracy = self._calculate_accuracy(query, best_match)
            confidence = best_match.get('confidence', 0.0) if best_match else 0.0
            
            return BookTestResult(
                filename=book_path.name,
                original_title=metadata['extracted_title'],
                algorithm="fuzzy",
                search_query=query,
                found_results=results,
                best_match=best_match,
                confidence_score=confidence,
                response_time_ms=response_time,
                accuracy_score=accuracy,
                success=len(results) > 0
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return BookTestResult(
                filename=book_path.name,
                original_title=book_path.stem,
                algorithm="fuzzy",
                search_query="",
                found_results=[],
                best_match=None,
                confidence_score=0.0,
                response_time_ms=response_time,
                accuracy_score=0.0,
                success=False,
                error_message=str(e)
            )
    
    def _test_isbn_search_book(self, book_path: Path) -> BookTestResult:
        """Testar busca ISBN para um livro específico"""
        start_time = time.time()
        
        try:
            # Tentar extrair ISBN do arquivo
            metadata = self.analyzer.extract_expected_metadata(book_path)
            
            # Usar MetadataExtractor para tentar encontrar ISBN
            extractor = MetadataExtractor()
            file_metadata = extractor.extract_from_file(str(book_path))
            
            isbn = file_metadata.get('isbn') or 'unknown'
            query = isbn if isbn != 'unknown' else metadata['extracted_title']
            
            # Executar busca ISBN
            results = self.isbn_search.search(query, limit=5)
            
            response_time = (time.time() - start_time) * 1000
            
            # Calcular acurácia
            best_match = results[0] if results else None
            accuracy = self._calculate_accuracy(metadata['extracted_title'], best_match)
            confidence = best_match.get('confidence', 0.0) if best_match else 0.0
            
            return BookTestResult(
                filename=book_path.name,
                original_title=metadata['extracted_title'],
                algorithm="isbn",
                search_query=query,
                found_results=results,
                best_match=best_match,
                confidence_score=confidence,
                response_time_ms=response_time,
                accuracy_score=accuracy,
                success=len(results) > 0
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return BookTestResult(
                filename=book_path.name,
                original_title=book_path.stem,
                algorithm="isbn",
                search_query="",
                found_results=[],
                best_match=None,
                confidence_score=0.0,
                response_time_ms=response_time,
                accuracy_score=0.0,
                success=False,
                error_message=str(e)
            )
    
    def _test_semantic_search_book(self, book_path: Path) -> BookTestResult:
        """Testar busca semântica para um livro específico"""
        start_time = time.time()
        
        try:
            # Extrair metadados e criar query semântica
            metadata = self.analyzer.extract_expected_metadata(book_path)
            
            # Criar query mais rica para busca semântica
            query_parts = [metadata['extracted_title']]
            if metadata.get('category'):
                query_parts.append(metadata['category'])
            
            query = ' '.join(query_parts)
            
            # Executar busca semântica
            results = self.semantic_search.search(query, limit=5)
            
            response_time = (time.time() - start_time) * 1000
            
            # Calcular acurácia
            best_match = results[0] if results else None
            accuracy = self._calculate_accuracy(metadata['extracted_title'], best_match)
            confidence = best_match.get('confidence', 0.0) if best_match else 0.0
            
            return BookTestResult(
                filename=book_path.name,
                original_title=metadata['extracted_title'],
                algorithm="semantic",
                search_query=query,
                found_results=results,
                best_match=best_match,
                confidence_score=confidence,
                response_time_ms=response_time,
                accuracy_score=accuracy,
                success=len(results) > 0
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return BookTestResult(
                filename=book_path.name,
                original_title=book_path.stem,
                algorithm="semantic",
                search_query="",
                found_results=[],
                best_match=None,
                confidence_score=0.0,
                response_time_ms=response_time,
                accuracy_score=0.0,
                success=False,
                error_message=str(e)
            )
    
    def _test_orchestrator_search_book(self, book_path: Path) -> BookTestResult:
        """Testar orquestrador para um livro específico"""
        start_time = time.time()
        
        try:
            # Extrair metadados
            metadata = self.analyzer.extract_expected_metadata(book_path)
            query = metadata['extracted_title']
            
            # Executar busca orquestrada
            results = self.orchestrator.search(query, limit=5)
            
            response_time = (time.time() - start_time) * 1000
            
            # Calcular acurácia
            best_match = results[0] if results else None
            accuracy = self._calculate_accuracy(query, best_match)
            confidence = best_match.get('confidence', 0.0) if best_match else 0.0
            
            return BookTestResult(
                filename=book_path.name,
                original_title=metadata['extracted_title'],
                algorithm="orchestrator",
                search_query=query,
                found_results=results,
                best_match=best_match,
                confidence_score=confidence,
                response_time_ms=response_time,
                accuracy_score=accuracy,
                success=len(results) > 0
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return BookTestResult(
                filename=book_path.name,
                original_title=book_path.stem,
                algorithm="orchestrator",
                search_query="",
                found_results=[],
                best_match=None,
                confidence_score=0.0,
                response_time_ms=response_time,
                accuracy_score=0.0,
                success=False,
                error_message=str(e)
            )
    
    def _calculate_accuracy(self, expected_title: str, result: Optional[Dict]) -> float:
        """Calcular acurácia comparando título esperado com resultado"""
        if not result or not result.get('title'):
            return 0.0
        
        found_title = result['title'].lower()
        expected_title = expected_title.lower()
        
        # Usar algoritmo de similaridade simples
        from difflib import SequenceMatcher
        similarity = SequenceMatcher(None, expected_title, found_title).ratio()
        
        return similarity
    
    def _validate_accuracy_target(self, results: List[BookTestResult], target: float, algorithm_name: str):
        """Validar se algoritmo atingiu meta de acurácia"""
        successful_results = [r for r in results if r.success]
        total_accuracy = sum(r.accuracy_score for r in successful_results)
        
        if successful_results:
            average_accuracy = total_accuracy / len(successful_results)
            
            logger.info(f"{algorithm_name}: Acurácia {average_accuracy:.1%} (Meta: {target:.1%})")
            
            self.assertGreaterEqual(
                average_accuracy, target,
                f"{algorithm_name} não atingiu meta de acurácia {target:.1%}"
            )
        else:
            self.fail(f"{algorithm_name}: Nenhum teste bem-sucedido")
    
    def _validate_accuracy_progression(self, all_results: Dict[str, List[BookTestResult]]):
        """Validar progressão de acurácia entre algoritmos"""
        algorithm_accuracies = {}
        
        for algorithm, results in all_results.items():
            successful_results = [r for r in results if r.success]
            if successful_results:
                average_accuracy = sum(r.accuracy_score for r in successful_results) / len(successful_results)
                algorithm_accuracies[algorithm] = average_accuracy
        
        logger.info("=== PROGRESSÃO DE ACURÁCIA ===")
        for algorithm, accuracy in sorted(algorithm_accuracies.items(), key=lambda x: x[1]):
            logger.info(f"{algorithm}: {accuracy:.1%}")
        
        # Validar que orquestrador tem melhor performance
        if 'orchestrator' in algorithm_accuracies:
            orchestrator_accuracy = algorithm_accuracies['orchestrator']
            
            for algorithm, accuracy in algorithm_accuracies.items():
                if algorithm != 'orchestrator':
                    self.assertGreaterEqual(
                        orchestrator_accuracy, accuracy * 0.9,  # 90% da acurácia individual
                        f"Orquestrador deveria ter performance similar ou melhor que {algorithm}"
                    )
    
    def _save_detailed_results(self, results: Any, filename: str):
        """Salvar resultados detalhados em arquivo JSON"""
        output_file = self.results_dir / filename
        
        # Converter dataclasses para dict se necessário
        if isinstance(results, list) and results and isinstance(results[0], BookTestResult):
            results_dict = [asdict(result) for result in results]
        elif isinstance(results, dict):
            results_dict = {}
            for key, value in results.items():
                if isinstance(value, list) and value and isinstance(value[0], BookTestResult):
                    results_dict[key] = [asdict(result) for result in value]
                else:
                    results_dict[key] = value
        else:
            results_dict = results
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results_dict, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Resultados salvos em {output_file}")

if __name__ == "__main__":
    # Executar testes
    unittest.main(verbosity=2)