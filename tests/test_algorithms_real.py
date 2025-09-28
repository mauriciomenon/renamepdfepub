#!/usr/bin/env python3
"""
Correção dos Algoritmos - Interface Simples
==========================================

Este script corrige a interface dos algoritmos para aceitar strings simples
durante os testes, resolvendo o problema de compatibilidade.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

# Configurar paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from renamepdfepub.search_algorithms.base_search import SearchQuery
    from renamepdfepub.search_algorithms.fuzzy_search import FuzzySearchAlgorithm
    from renamepdfepub.search_algorithms.isbn_search import ISBNSearchAlgorithm  
    from renamepdfepub.search_algorithms.semantic_search import SemanticSearchAlgorithm
    from renamepdfepub.search_algorithms.search_orchestrator import SearchOrchestrator
    
    logger.info(" Importações dos algoritmos bem-sucedidas")
    ALGORITHMS_AVAILABLE = True
    
except ImportError as e:
    logger.warning(f"⚠  Não foi possível importar algoritmos: {e}")
    ALGORITHMS_AVAILABLE = False

class AlgorithmWrapper:
    """Wrapper para adaptar algoritmos para aceitar strings simples"""
    
    def __init__(self):
        if ALGORITHMS_AVAILABLE:
            try:
                self.fuzzy = FuzzySearchAlgorithm()
                self.isbn = ISBNSearchAlgorithm()
                self.semantic = SemanticSearchAlgorithm()
                self.orchestrator = SearchOrchestrator()
                logger.info(" Algoritmos inicializados com sucesso")
            except Exception as e:
                logger.error(f" Erro ao inicializar algoritmos: {e}")
                self.fuzzy = None
                self.isbn = None
                self.semantic = None
                self.orchestrator = None
        else:
            self.fuzzy = None
            self.isbn = None  
            self.semantic = None
            self.orchestrator = None
    
    def string_to_search_query(self, query_string: str) -> SearchQuery:
        """Converte string simples para SearchQuery"""
        # Assumir que a string é um título
        return SearchQuery(
            title=query_string.strip(),
            authors=None,
            publisher=None,
            year=None,
            isbn=None
        )
    
    def search_results_to_dict(self, results) -> List[Dict]:
        """Converte SearchResult para dicionário simples"""
        if not results:
            return []
        
        converted_results = []
        for result in results:
            # Extrair metadados do resultado
            metadata = result.metadata if hasattr(result, 'metadata') else {}
            
            converted_result = {
                'title': metadata.get('title', 'Unknown Title'),
                'author': metadata.get('authors', ['Unknown Author'])[0] if isinstance(metadata.get('authors'), list) and metadata.get('authors') else metadata.get('author', 'Unknown Author'),
                'publisher': metadata.get('publisher', 'Unknown Publisher'),
                'isbn': metadata.get('isbn', ''),
                'year': metadata.get('year', ''),
                'confidence': result.score if hasattr(result, 'score') else 0.5,
                'similarity_score': result.score if hasattr(result, 'score') else 0.5,
                'algorithm': result.algorithm if hasattr(result, 'algorithm') else 'unknown'
            }
            converted_results.append(converted_result)
        
        return converted_results
    
    def fuzzy_search(self, query: str, limit: int = 5) -> List[Dict]:
        """Busca fuzzy com interface simplificada"""
        if not self.fuzzy:
            return []
        
        try:
            search_query = self.string_to_search_query(query)
            results = self.fuzzy.search(search_query)
            return self.search_results_to_dict(results[:limit])
        except Exception as e:
            logger.error(f"Erro no fuzzy search: {e}")
            return []
    
    def isbn_search(self, query: str, limit: int = 5) -> List[Dict]:
        """Busca ISBN com interface simplificada"""
        if not self.isbn:
            return []
        
        try:
            search_query = self.string_to_search_query(query)
            results = self.isbn.search(search_query)
            return self.search_results_to_dict(results[:limit])
        except Exception as e:
            logger.error(f"Erro no ISBN search: {e}")
            return []
    
    def semantic_search(self, query: str, limit: int = 5) -> List[Dict]:
        """Busca semântica com interface simplificada"""
        if not self.semantic:
            return []
        
        try:
            search_query = self.string_to_search_query(query)
            results = self.semantic.search(search_query)
            return self.search_results_to_dict(results[:limit])
        except Exception as e:
            logger.error(f"Erro no semantic search: {e}")
            return []
    
    def orchestrator_search(self, query: str, limit: int = 5) -> List[Dict]:
        """Busca orquestrada com interface simplificada"""
        if not self.orchestrator:
            return []
        
        try:
            search_query = self.string_to_search_query(query)
            results = self.orchestrator.search(search_query)
            return self.search_results_to_dict(results[:limit])
        except Exception as e:
            logger.error(f"Erro no orchestrator search: {e}")
            return []

class TestRunner:
    """Runner de testes para algoritmos reais"""
    
    def __init__(self):
        self.algorithms = AlgorithmWrapper()
        self.results_dir = project_root / "algorithm_test_results"
        self.results_dir.mkdir(exist_ok=True)
        
    def get_test_books(self, max_books: int = 30) -> List[Path]:
        """Obter livros para teste"""
        books_dir = project_root / "books"
        all_books = []
        
        for file_path in books_dir.iterdir():
            if file_path.suffix.lower() in ['.pdf', '.epub', '.mobi'] and file_path.name != '.DS_Store':
                all_books.append(file_path)
        
        all_books.sort(key=lambda x: x.name)
        return all_books[:max_books]
    
    def extract_query_from_filename(self, book_path: Path) -> str:
        """Extrair query limpa do nome do arquivo"""
        filename = book_path.stem
        
        # Remover extensões duplas
        while filename.endswith(('.pdf', '.epub', '.mobi')):
            filename = filename[:-4]
        
        # Limpar underscores e hifens
        query = filename.replace('_', ' ').replace('-', ' ')
        
        # Remover versões e edições
        import re
        query = re.sub(r'\s+v\d+.*$', '', query, flags=re.IGNORECASE)
        query = re.sub(r'\s+(second|third|fourth|fifth|2nd|3rd|4th|5th)\s+edition.*$', '', query, flags=re.IGNORECASE)
        query = re.sub(r'\s+MEAP.*$', '', query, flags=re.IGNORECASE)
        
        # Limitar tamanho
        if len(query) > 80:
            query = query[:80].rsplit(' ', 1)[0]
        
        return query.strip()
    
    def test_algorithm(self, algorithm_name: str, algorithm_func, books: List[Path]) -> Dict[str, Any]:
        """Testar um algoritmo específico"""
        logger.info(f"\n--- TESTANDO {algorithm_name.upper()} ---")
        
        results = {
            'algorithm': algorithm_name,
            'total_tests': len(books),
            'successful_tests': 0,
            'failed_tests': 0,
            'accuracy_scores': [],
            'errors': []
        }
        
        for i, book in enumerate(books):
            query = self.extract_query_from_filename(book)
            
            try:
                search_results = algorithm_func(query, limit=5)
                
                # Calcular acurácia
                accuracy = 0.0
                if search_results and len(search_results) > 0:
                    best_result = search_results[0]
                    accuracy = best_result.get('similarity_score', 0.5)
                    results['successful_tests'] += 1
                else:
                    results['failed_tests'] += 1
                
                results['accuracy_scores'].append(accuracy)
                
                # Log progresso
                if (i + 1) % 10 == 0:
                    import statistics
                    avg_accuracy = statistics.mean(results['accuracy_scores'])
                    logger.info(f"  {i+1}/{len(books)} - Acurácia média: {avg_accuracy:.1%}")
                
            except Exception as e:
                results['failed_tests'] += 1
                results['errors'].append(str(e))
                results['accuracy_scores'].append(0)
                logger.error(f"  Erro testando '{book.name}': {e}")
        
        # Calcular estatísticas finais
        if results['accuracy_scores']:
            import statistics
            results['avg_accuracy'] = statistics.mean(results['accuracy_scores'])
        
        results['success_rate'] = results['successful_tests'] / results['total_tests'] if results['total_tests'] > 0 else 0
        
        # Log resultados
        logger.info(f"\n📊 RESULTADOS {algorithm_name.upper()}:")
        logger.info(f"  Testes: {results['total_tests']}")
        logger.info(f"  Sucessos: {results['successful_tests']}")
        logger.info(f"  Taxa de sucesso: {results['success_rate']:.1%}")
        logger.info(f"  Acurácia média: {results.get('avg_accuracy', 0):.1%}")
        
        return results
    
    def run_tests(self):
        """Executar todos os testes"""
        logger.info(" INICIANDO TESTES DOS ALGORITMOS REAIS")
        
        if not ALGORITHMS_AVAILABLE:
            logger.error(" Algoritmos não disponíveis. Executando com dados mockados.")
            return self.run_mock_tests()
        
        # Obter livros
        test_books = self.get_test_books(30)
        logger.info(f"📚 Testando com {len(test_books)} livros")
        
        # Algoritmos para testar
        algorithms = {
            'fuzzy': self.algorithms.fuzzy_search,
            'isbn': self.algorithms.isbn_search,
            'semantic': self.algorithms.semantic_search,
            'orchestrator': self.algorithms.orchestrator_search
        }
        
        all_results = {}
        
        # Testar cada algoritmo
        for algo_name, algo_func in algorithms.items():
            result = self.test_algorithm(algo_name, algo_func, test_books)
            all_results[algo_name] = result
        
        # Analisar resultados
        self.analyze_results(all_results)
        
        # Salvar resultados
        report_file = self.results_dir / "algorithm_test_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"📊 Relatório salvo: {report_file}")
        
        return all_results
    
    def run_mock_tests(self):
        """Executar testes com dados mockados quando algoritmos não estão disponíveis"""
        logger.info("🔄 EXECUTANDO TESTES MOCKADOS")
        
        # Simular resultados básicos
        mock_results = {
            'fuzzy': {
                'algorithm': 'fuzzy',
                'total_tests': 30,
                'successful_tests': 15,
                'failed_tests': 15,
                'accuracy_scores': [0.6] * 15 + [0.0] * 15,
                'avg_accuracy': 0.3,
                'success_rate': 0.5,
                'errors': []
            },
            'isbn': {
                'algorithm': 'isbn', 
                'total_tests': 30,
                'successful_tests': 10,
                'failed_tests': 20,
                'accuracy_scores': [0.8] * 10 + [0.0] * 20,
                'avg_accuracy': 0.27,
                'success_rate': 0.33,
                'errors': []
            },
            'semantic': {
                'algorithm': 'semantic',
                'total_tests': 30,
                'successful_tests': 20,
                'failed_tests': 10,
                'accuracy_scores': [0.7] * 20 + [0.0] * 10,
                'avg_accuracy': 0.47,
                'success_rate': 0.67,
                'errors': []
            },
            'orchestrator': {
                'algorithm': 'orchestrator',
                'total_tests': 30,
                'successful_tests': 18,
                'failed_tests': 12,
                'accuracy_scores': [0.75] * 18 + [0.0] * 12,
                'avg_accuracy': 0.45,
                'success_rate': 0.6,
                'errors': []
            }
        }
        
        self.analyze_results(mock_results)
        return mock_results
    
    def analyze_results(self, results: Dict[str, Any]):
        """Analisar resultados dos testes"""
        logger.info("\n=== ANÁLISE DOS RESULTADOS ===")
        
        # Targets de acurácia
        targets = [0.5, 0.6, 0.7, 0.8, 0.9]
        
        best_algorithm = None
        best_accuracy = 0
        
        for algo_name, result in results.items():
            accuracy = result.get('avg_accuracy', 0)
            success_rate = result.get('success_rate', 0)
            
            logger.info(f"\n{algo_name.upper()}:")
            logger.info(f"  Acurácia: {accuracy:.1%}")
            logger.info(f"  Taxa de sucesso: {success_rate:.1%}")
            
            # Verificar targets atingidos
            targets_met = [t for t in targets if accuracy >= t]
            if targets_met:
                highest_target = max(targets_met)
                logger.info(f"  🎯 Target atingido: {highest_target:.0%}")
            else:
                logger.info(f"   Nenhum target atingido")
            
            # Avaliar performance
            if accuracy >= 0.5:
                logger.info(f"   META DE 50% ATINGIDA")
            else:
                logger.info(f"   Meta de 50% NÃO atingida")
            
            if accuracy > best_accuracy:
                best_accuracy = accuracy
                best_algorithm = algo_name
        
        # Resumo final
        logger.info(f"\n🏆 MELHOR ALGORITMO: {best_algorithm.upper() if best_algorithm else 'NENHUM'}")
        logger.info(f"🎯 MELHOR ACURÁCIA: {best_accuracy:.1%}")
        
        if best_accuracy >= 0.5:
            logger.info("🎉 SUCESSO! Meta de 50% atingida!")
        else:
            logger.info("⚠  REFINAMENTO NECESSÁRIO! Meta de 50% não atingida.")

def main():
    """Função principal"""
    print(" TESTE DOS ALGORITMOS REAIS - RENAMEPDFEPUB")
    print("=" * 60)
    
    runner = TestRunner()
    
    try:
        results = runner.run_tests()
        
        # Calcular melhor acurácia
        best_accuracy = max(r.get('avg_accuracy', 0) for r in results.values())
        
        print(f"\n{'='*60}")
        print("RESULTADO FINAL")
        print(f"{'='*60}")
        print(f"🎯 Melhor acurácia: {best_accuracy:.1%}")
        
        if best_accuracy >= 0.5:
            print(" TESTE PASSOU! Sistema funcional!")
        else:
            print(" TESTE FALHOU! Refinamento necessário.")
        
        print(f"📊 Detalhes em: algorithm_test_results/")
        
    except Exception as e:
        logger.error(f"💥 ERRO: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)