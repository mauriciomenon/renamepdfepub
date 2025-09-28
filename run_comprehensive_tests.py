#!/usr/bin/env python3
"""
Runner de Testes Abrangente para Algoritmos de Busca
==================================================

Este runner executa testes sistemáticos nos algoritmos de busca,
organizados por tipo de algoritmo e com metas progressivas de acurácia.

Uso:
    python run_comprehensive_tests.py [--algorithm=fuzzy|isbn|semantic|orchestrator|all]
                                     [--target-accuracy=0.5-0.9] 
                                     [--max-books=100]
                                     [--parallel-tests=5]
                                     [--generate-report]

Funcionalidades:
- Testes por algoritmo específico
- Progressão de acurácia 50% → 90%
- Relatórios detalhados em HTML/JSON
- Análise de performance
- Preparação para expansão (editoras, catálogos)
"""

import os
import sys
import json
import time
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import statistics

# Adicionar src ao path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from tests.test_book_collection import TestBookCollection, BookCollectionAnalyzer
from src.renamepdfepub.logging_config import setup_logging

logger = setup_logging(__name__)

class ComprehensiveTestRunner:
    """Runner para testes abrangentes da coleção de livros"""
    
    def __init__(self, books_dir: str, results_dir: str = None):
        self.books_dir = Path(books_dir)
        self.results_dir = Path(results_dir) if results_dir else project_root / "test_results"
        self.results_dir.mkdir(exist_ok=True)
        
        # Configurações padrão
        self.default_config = {
            'max_books': 100,
            'parallel_tests': 5,
            'target_accuracies': [0.5, 0.6, 0.7, 0.8, 0.9],
            'algorithms': ['fuzzy', 'isbn', 'semantic', 'orchestrator'],
            'performance_thresholds': {
                'max_response_time': 100,  # ms
                'min_accuracy': 0.5,
                'min_success_rate': 0.8
            }
        }
        
        # Inicializar componentes
        self.analyzer = BookCollectionAnalyzer(str(self.books_dir))
        self.books = self.analyzer.get_all_books()
        
        logger.info(f"Inicializado runner com {len(self.books)} livros")
    
    def run_algorithm_test(self, algorithm: str, max_books: int = 100) -> Dict[str, Any]:
        """Executar teste para um algoritmo específico"""
        logger.info(f"\n{'='*60}")
        logger.info(f"TESTANDO ALGORITMO: {algorithm.upper()}")
        logger.info(f"{'='*60}")
        
        start_time = time.time()
        
        # Configurar teste
        test_suite = TestBookCollection()
        test_suite.setUpClass()
        
        # Limitar número de livros se especificado
        original_books = test_suite.books
        if max_books < len(test_suite.books):
            test_suite.books = test_suite.books[:max_books]
            logger.info(f"Limitando teste a {max_books} livros")
        
        try:
            # Executar teste específico do algoritmo
            if algorithm == 'fuzzy':
                test_suite.test_fuzzy_search_algorithm()
            elif algorithm == 'isbn':
                test_suite.test_isbn_search_algorithm()
            elif algorithm == 'semantic':
                test_suite.test_semantic_search_algorithm()
            elif algorithm == 'orchestrator':
                test_suite.test_orchestrator_integration()
            else:
                raise ValueError(f"Algoritmo desconhecido: {algorithm}")
            
            # Coletar estatísticas
            results = self._collect_algorithm_stats(algorithm, test_suite.results_dir)
            
        except Exception as e:
            logger.error(f"Erro executando teste {algorithm}: {e}")
            results = {'error': str(e), 'success': False}
        
        finally:
            # Restaurar lista original
            test_suite.books = original_books
        
        total_time = time.time() - start_time
        results['execution_time'] = total_time
        
        logger.info(f"Teste {algorithm} concluído em {total_time:.2f}s")
        return results
    
    def run_accuracy_progression_test(self, max_books: int = 100) -> Dict[str, Any]:
        """Executar teste de progressão de acurácia"""
        logger.info(f"\n{'='*60}")
        logger.info("TESTE DE PROGRESSÃO DE ACURÁCIA")
        logger.info(f"{'='*60}")
        
        start_time = time.time()
        progression_results = {}
        
        # Testar cada algoritmo
        for algorithm in self.default_config['algorithms']:
            logger.info(f"\nTestando progressão para {algorithm}...")
            
            try:
                result = self.run_algorithm_test(algorithm, max_books)
                progression_results[algorithm] = result
                
                # Log da acurácia alcançada
                if 'accuracy_rate' in result:
                    logger.info(f"{algorithm}: {result['accuracy_rate']:.1%} de acurácia")
                
            except Exception as e:
                logger.error(f"Erro testando {algorithm}: {e}")
                progression_results[algorithm] = {'error': str(e)}
        
        # Analisar progressão
        progression_analysis = self._analyze_accuracy_progression(progression_results)
        
        total_time = time.time() - start_time
        
        final_results = {
            'individual_results': progression_results,
            'progression_analysis': progression_analysis,
            'execution_time': total_time,
            'timestamp': datetime.now().isoformat()
        }
        
        # Salvar resultados
        self._save_results(final_results, 'accuracy_progression_complete.json')
        
        logger.info(f"Teste de progressão concluído em {total_time:.2f}s")
        return final_results
    
    def run_performance_benchmark(self, max_books: int = 50) -> Dict[str, Any]:
        """Executar benchmark de performance"""
        logger.info(f"\n{'='*60}")
        logger.info("BENCHMARK DE PERFORMANCE")
        logger.info(f"{'='*60}")
        
        start_time = time.time()
        benchmark_results = {}
        
        # Configurar teste
        test_suite = TestBookCollection()
        test_suite.setUpClass()
        
        # Selecionar livros para benchmark (sample aleatório)
        import random
        test_books = random.sample(test_suite.books, min(max_books, len(test_suite.books)))
        
        for algorithm in self.default_config['algorithms']:
            logger.info(f"\nBenchmark {algorithm}...")
            
            algorithm_times = []
            algorithm_accuracies = []
            algorithm_successes = 0
            
            # Executar testes individuais
            for i, book in enumerate(test_books):
                try:
                    # Escolher função de teste baseada no algoritmo
                    if algorithm == 'fuzzy':
                        result = test_suite._test_fuzzy_search_book(book)
                    elif algorithm == 'isbn':
                        result = test_suite._test_isbn_search_book(book)
                    elif algorithm == 'semantic':
                        result = test_suite._test_semantic_search_book(book)
                    elif algorithm == 'orchestrator':
                        result = test_suite._test_orchestrator_search_book(book)
                    
                    algorithm_times.append(result.response_time_ms)
                    algorithm_accuracies.append(result.accuracy_score)
                    if result.success:
                        algorithm_successes += 1
                    
                    if (i + 1) % 10 == 0:
                        logger.info(f"{algorithm}: {i + 1}/{len(test_books)} testes concluídos")
                        
                except Exception as e:
                    logger.error(f"Erro testando {book.name} com {algorithm}: {e}")
            
            # Calcular estatísticas
            if algorithm_times:
                benchmark_results[algorithm] = {
                    'total_tests': len(test_books),
                    'successful_tests': algorithm_successes,
                    'success_rate': algorithm_successes / len(test_books),
                    'avg_response_time_ms': statistics.mean(algorithm_times),
                    'max_response_time_ms': max(algorithm_times),
                    'min_response_time_ms': min(algorithm_times),
                    'avg_accuracy': statistics.mean(algorithm_accuracies),
                    'max_accuracy': max(algorithm_accuracies),
                    'performance_score': self._calculate_performance_score(
                        statistics.mean(algorithm_times),
                        statistics.mean(algorithm_accuracies),
                        algorithm_successes / len(test_books)
                    )
                }
        
        total_time = time.time() - start_time
        
        final_results = {
            'benchmark_results': benchmark_results,
            'test_configuration': {
                'max_books': max_books,
                'algorithms_tested': self.default_config['algorithms'],
                'performance_thresholds': self.default_config['performance_thresholds']
            },
            'execution_time': total_time,
            'timestamp': datetime.now().isoformat()
        }
        
        # Salvar resultados
        self._save_results(final_results, 'performance_benchmark.json')
        
        # Log resumo
        logger.info(f"\n{'='*40}")
        logger.info("RESUMO DE PERFORMANCE")
        logger.info(f"{'='*40}")
        
        for algorithm, stats in benchmark_results.items():
            logger.info(f"{algorithm.upper()}:")
            logger.info(f"  Tempo médio: {stats['avg_response_time_ms']:.1f}ms")
            logger.info(f"  Acurácia média: {stats['avg_accuracy']:.1%}")
            logger.info(f"  Taxa de sucesso: {stats['success_rate']:.1%}")
            logger.info(f"  Score de performance: {stats['performance_score']:.2f}")
        
        logger.info(f"\nBenchmark concluído em {total_time:.2f}s")
        return final_results
    
    def run_comprehensive_test_suite(self, algorithms: List[str] = None, max_books: int = 100) -> Dict[str, Any]:
        """Executar suite completa de testes"""
        logger.info(f"\n{'='*60}")
        logger.info("SUITE COMPLETA DE TESTES")
        logger.info(f"{'='*60}")
        
        algorithms = algorithms or self.default_config['algorithms']
        start_time = time.time()
        
        comprehensive_results = {
            'test_configuration': {
                'algorithms': algorithms,
                'max_books': max_books,
                'total_books_in_collection': len(self.books),
                'start_time': datetime.now().isoformat()
            },
            'individual_algorithm_tests': {},
            'accuracy_progression': {},
            'performance_benchmark': {},
            'summary': {}
        }
        
        try:
            # 1. Testes individuais por algoritmo
            logger.info("\n=== FASE 1: TESTES INDIVIDUAIS ===")
            for algorithm in algorithms:
                result = self.run_algorithm_test(algorithm, max_books)
                comprehensive_results['individual_algorithm_tests'][algorithm] = result
            
            # 2. Teste de progressão de acurácia
            logger.info("\n=== FASE 2: PROGRESSÃO DE ACURÁCIA ===")
            progression_result = self.run_accuracy_progression_test(max_books)
            comprehensive_results['accuracy_progression'] = progression_result
            
            # 3. Benchmark de performance
            logger.info("\n=== FASE 3: BENCHMARK DE PERFORMANCE ===")
            benchmark_result = self.run_performance_benchmark(min(50, max_books))
            comprehensive_results['performance_benchmark'] = benchmark_result
            
            # 4. Gerar resumo final
            logger.info("\n=== FASE 4: GERANDO RESUMO ===")
            summary = self._generate_comprehensive_summary(comprehensive_results)
            comprehensive_results['summary'] = summary
            
        except Exception as e:
            logger.error(f"Erro na suite de testes: {e}")
            comprehensive_results['error'] = str(e)
        
        total_time = time.time() - start_time
        comprehensive_results['total_execution_time'] = total_time
        comprehensive_results['end_time'] = datetime.now().isoformat()
        
        # Salvar resultados completos
        self._save_results(comprehensive_results, 'comprehensive_test_results.json')
        
        # Gerar relatório HTML
        self._generate_html_report(comprehensive_results)
        
        logger.info(f"\n{'='*60}")
        logger.info("SUITE COMPLETA CONCLUÍDA")
        logger.info(f"Tempo total: {total_time:.2f}s")
        logger.info(f"Resultados salvos em: {self.results_dir}")
        logger.info(f"{'='*60}")
        
        return comprehensive_results
    
    def _collect_algorithm_stats(self, algorithm: str, results_dir: Path) -> Dict[str, Any]:
        """Coletar estatísticas de um algoritmo específico"""
        try:
            # Tentar carregar resultados salvos
            result_files = {
                'fuzzy': 'fuzzy_search_results.json',
                'isbn': 'isbn_search_results.json', 
                'semantic': 'semantic_search_results.json',
                'orchestrator': 'orchestrator_results.json'
            }
            
            result_file = results_dir / result_files.get(algorithm, f"{algorithm}_results.json")
            
            if result_file.exists():
                with open(result_file, 'r', encoding='utf-8') as f:
                    results = json.load(f)
                
                if isinstance(results, list):
                    # Calcular estatísticas
                    total_tests = len(results)
                    successful_tests = sum(1 for r in results if r.get('success', False))
                    total_accuracy = sum(r.get('accuracy_score', 0) for r in results if r.get('success', False))
                    total_response_time = sum(r.get('response_time_ms', 0) for r in results)
                    
                    return {
                        'algorithm': algorithm,
                        'total_tests': total_tests,
                        'successful_tests': successful_tests,
                        'success_rate': successful_tests / total_tests if total_tests > 0 else 0,
                        'accuracy_rate': total_accuracy / successful_tests if successful_tests > 0 else 0,
                        'avg_response_time': total_response_time / total_tests if total_tests > 0 else 0,
                        'success': True
                    }
            
            return {'algorithm': algorithm, 'error': 'Results file not found', 'success': False}
            
        except Exception as e:
            return {'algorithm': algorithm, 'error': str(e), 'success': False}
    
    def _analyze_accuracy_progression(self, progression_results: Dict[str, Any]) -> Dict[str, Any]:
        """Analisar progressão de acurácia entre algoritmos"""
        analysis = {
            'algorithm_ranking': [],
            'accuracy_comparison': {},
            'progression_summary': {},
            'recommendations': []
        }
        
        # Extrair acurácias
        accuracies = {}
        for algorithm, result in progression_results.items():
            if 'accuracy_rate' in result:
                accuracies[algorithm] = result['accuracy_rate']
        
        # Ranking por acurácia
        analysis['algorithm_ranking'] = sorted(
            accuracies.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        analysis['accuracy_comparison'] = accuracies
        
        # Verificar se atingiu metas
        targets = self.default_config['target_accuracies']
        for algorithm, accuracy in accuracies.items():
            target_met = None
            for target in sorted(targets):
                if accuracy >= target:
                    target_met = target
            
            analysis['progression_summary'][algorithm] = {
                'accuracy': accuracy,
                'highest_target_met': target_met,
                'ready_for_production': accuracy >= 0.7
            }
        
        # Gerar recomendações
        if accuracies:
            best_algorithm = max(accuracies.items(), key=lambda x: x[1])
            analysis['recommendations'].append(
                f"Melhor algoritmo: {best_algorithm[0]} ({best_algorithm[1]:.1%})"
            )
            
            for algorithm, accuracy in accuracies.items():
                if accuracy < 0.5:
                    analysis['recommendations'].append(
                        f"{algorithm} precisa de refinamento (acurácia: {accuracy:.1%})"
                    )
        
        return analysis
    
    def _calculate_performance_score(self, avg_time: float, avg_accuracy: float, success_rate: float) -> float:
        """Calcular score de performance combinado"""
        # Normalizar métricas (0-1)
        time_score = max(0, 1 - (avg_time / 1000))  # Penalizar tempos > 1s
        accuracy_score = avg_accuracy
        success_score = success_rate
        
        # Média ponderada
        performance_score = (time_score * 0.3 + accuracy_score * 0.4 + success_score * 0.3)
        return performance_score
    
    def _generate_comprehensive_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Gerar resumo abrangente dos testes"""
        summary = {
            'test_overview': {},
            'algorithm_performance': {},
            'accuracy_achievements': {},
            'performance_benchmarks': {},
            'recommendations': [],
            'next_steps': []
        }
        
        # Overview dos testes
        config = results['test_configuration']
        summary['test_overview'] = {
            'algorithms_tested': len(config['algorithms']),
            'books_tested': config['max_books'],
            'total_collection_size': config['total_books_in_collection'],
            'execution_time': results.get('total_execution_time', 0)
        }
        
        # Performance dos algoritmos
        individual_tests = results.get('individual_algorithm_tests', {})
        for algorithm, result in individual_tests.items():
            if result.get('success', False):
                summary['algorithm_performance'][algorithm] = {
                    'accuracy': result.get('accuracy_rate', 0),
                    'success_rate': result.get('success_rate', 0),
                    'avg_response_time': result.get('avg_response_time', 0)
                }
        
        # Conquistas de acurácia
        progression = results.get('accuracy_progression', {})
        if 'progression_analysis' in progression:
            analysis = progression['progression_analysis']
            summary['accuracy_achievements'] = analysis.get('progression_summary', {})
        
        # Benchmarks de performance
        benchmark = results.get('performance_benchmark', {})
        if 'benchmark_results' in benchmark:
            summary['performance_benchmarks'] = benchmark['benchmark_results']
        
        # Gerar recomendações
        summary['recommendations'] = self._generate_recommendations(summary)
        summary['next_steps'] = self._generate_next_steps(summary)
        
        return summary
    
    def _generate_recommendations(self, summary: Dict[str, Any]) -> List[str]:
        """Gerar recomendações baseadas nos resultados"""
        recommendations = []
        
        # Analisar performance dos algoritmos
        performances = summary.get('algorithm_performance', {})
        if performances:
            # Encontrar melhor algoritmo
            best_algo = max(performances.items(), key=lambda x: x[1]['accuracy'])
            recommendations.append(
                f"Usar {best_algo[0]} como algoritmo principal (acurácia: {best_algo[1]['accuracy']:.1%})"
            )
            
            # Identificar algoritmos que precisam melhoria
            for algo, perf in performances.items():
                if perf['accuracy'] < 0.5:
                    recommendations.append(
                        f"Refinar {algo} - acurácia abaixo de 50%"
                    )
                elif perf['avg_response_time'] > 100:
                    recommendations.append(
                        f"Otimizar {algo} - tempo de resposta alto ({perf['avg_response_time']:.1f}ms)"
                    )
        
        # Analisar benchmarks
        benchmarks = summary.get('performance_benchmarks', {})
        if benchmarks:
            for algo, stats in benchmarks.items():
                if stats['performance_score'] < 0.7:
                    recommendations.append(
                        f"Melhorar performance geral de {algo} (score: {stats['performance_score']:.2f})"
                    )
        
        return recommendations
    
    def _generate_next_steps(self, summary: Dict[str, Any]) -> List[str]:
        """Gerar próximos passos baseados nos resultados"""
        next_steps = [
            "Implementar integração com catálogos de editoras",
            "Desenvolver scraper para Amazon e grandes vendedores",
            "Adicionar cache persistente com Redis/SQLite",
            "Implementar sistema de feedback para melhorar acurácia",
            "Criar API REST para os algoritmos de busca",
            "Desenvolver interface web para testes e monitoramento",
            "Implementar logging avançado com métricas de negócio",
            "Criar pipeline de CI/CD para testes automatizados"
        ]
        
        # Adicionar passos específicos baseados na performance
        performances = summary.get('algorithm_performance', {})
        if performances:
            worst_algo = min(performances.items(), key=lambda x: x[1]['accuracy'])
            if worst_algo[1]['accuracy'] < 0.7:
                next_steps.insert(0, f"Prioridade: Refinar algoritmo {worst_algo[0]}")
        
        return next_steps
    
    def _save_results(self, results: Any, filename: str):
        """Salvar resultados em arquivo JSON"""
        output_file = self.results_dir / filename
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Resultados salvos: {output_file}")
    
    def _generate_html_report(self, results: Dict[str, Any]):
        """Gerar relatório HTML dos resultados"""
        html_content = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatório de Testes - Algoritmos de Busca</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 5px; }}
        .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
        .success {{ background: #d4edda; border-color: #c3e6cb; }}
        .warning {{ background: #fff3cd; border-color: #ffeaa7; }}
        .error {{ background: #f8d7da; border-color: #f5c6cb; }}
        table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f8f9fa; }}
        .metric {{ font-size: 24px; font-weight: bold; color: #27ae60; }}
        .recommendation {{ background: #e8f4f8; padding: 10px; margin: 5px 0; border-left: 4px solid #3498db; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔍 Relatório Abrangente de Testes</h1>
        <p>Algoritmos de Busca - RenamePDFEPub</p>
        <p>Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
    </div>
    
    <div class="section success">
        <h2>📊 Resumo Executivo</h2>
        {self._generate_html_summary(results.get('summary', {}))}
    </div>
    
    <div class="section">
        <h2>🎯 Performance por Algoritmo</h2>
        {self._generate_html_algorithm_table(results.get('individual_algorithm_tests', {}))}
    </div>
    
    <div class="section">
        <h2>📈 Benchmark de Performance</h2>
        {self._generate_html_benchmark_table(results.get('performance_benchmark', {}))}
    </div>
    
    <div class="section warning">
        <h2>💡 Recomendações</h2>
        {self._generate_html_recommendations(results.get('summary', {}).get('recommendations', []))}
    </div>
    
    <div class="section">
        <h2> Próximos Passos</h2>
        {self._generate_html_next_steps(results.get('summary', {}).get('next_steps', []))}
    </div>
</body>
</html>
        """
        
        html_file = self.results_dir / 'comprehensive_test_report.html'
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"Relatório HTML gerado: {html_file}")
    
    def _generate_html_summary(self, summary: Dict[str, Any]) -> str:
        """Gerar seção HTML de resumo"""
        overview = summary.get('test_overview', {})
        
        return f"""
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px;">
            <div>
                <div class="metric">{overview.get('algorithms_tested', 0)}</div>
                <p>Algoritmos Testados</p>
            </div>
            <div>
                <div class="metric">{overview.get('books_tested', 0)}</div>
                <p>Livros Testados</p>
            </div>
            <div>
                <div class="metric">{overview.get('total_collection_size', 0)}</div>
                <p>Coleção Total</p>
            </div>
            <div>
                <div class="metric">{overview.get('execution_time', 0):.1f}s</div>
                <p>Tempo de Execução</p>
            </div>
        </div>
        """
    
    def _generate_html_algorithm_table(self, algorithm_results: Dict[str, Any]) -> str:
        """Gerar tabela HTML de resultados por algoritmo"""
        if not algorithm_results:
            return "<p>Nenhum resultado disponível</p>"
        
        html = "<table><tr><th>Algoritmo</th><th>Acurácia</th><th>Taxa de Sucesso</th><th>Tempo Médio</th><th>Status</th></tr>"
        
        for algorithm, result in algorithm_results.items():
            if result.get('success', False):
                accuracy = f"{result.get('accuracy_rate', 0):.1%}"
                success_rate = f"{result.get('success_rate', 0):.1%}"
                avg_time = f"{result.get('avg_response_time', 0):.1f}ms"
                status = " Sucesso"
                row_class = "success"
            else:
                accuracy = "N/A"
                success_rate = "N/A"
                avg_time = "N/A"
                status = " Erro"
                row_class = "error"
            
            html += f'<tr class="{row_class}"><td>{algorithm.title()}</td><td>{accuracy}</td><td>{success_rate}</td><td>{avg_time}</td><td>{status}</td></tr>'
        
        html += "</table>"
        return html
    
    def _generate_html_benchmark_table(self, benchmark_results: Dict[str, Any]) -> str:
        """Gerar tabela HTML de benchmark"""
        if not benchmark_results.get('benchmark_results'):
            return "<p>Nenhum benchmark disponível</p>"
        
        html = "<table><tr><th>Algoritmo</th><th>Performance Score</th><th>Tempo Médio</th><th>Acurácia Média</th><th>Taxa de Sucesso</th></tr>"
        
        benchmarks = benchmark_results['benchmark_results']
        for algorithm, stats in benchmarks.items():
            score = f"{stats['performance_score']:.2f}"
            avg_time = f"{stats['avg_response_time_ms']:.1f}ms"
            avg_accuracy = f"{stats['avg_accuracy']:.1%}"
            success_rate = f"{stats['success_rate']:.1%}"
            
            # Colorir baseado no score
            if stats['performance_score'] >= 0.8:
                row_class = "success"
            elif stats['performance_score'] >= 0.6:
                row_class = "warning"
            else:
                row_class = "error"
            
            html += f'<tr class="{row_class}"><td>{algorithm.title()}</td><td>{score}</td><td>{avg_time}</td><td>{avg_accuracy}</td><td>{success_rate}</td></tr>'
        
        html += "</table>"
        return html
    
    def _generate_html_recommendations(self, recommendations: List[str]) -> str:
        """Gerar seção HTML de recomendações"""
        if not recommendations:
            return "<p>Nenhuma recomendação gerada</p>"
        
        html = ""
        for rec in recommendations:
            html += f'<div class="recommendation">💡 {rec}</div>'
        
        return html
    
    def _generate_html_next_steps(self, next_steps: List[str]) -> str:
        """Gerar seção HTML de próximos passos"""
        if not next_steps:
            return "<p>Nenhum próximo passo definido</p>"
        
        html = "<ol>"
        for step in next_steps:
            html += f"<li>{step}</li>"
        html += "</ol>"
        
        return html

def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description="Runner de Testes Abrangente")
    parser.add_argument('--algorithm', choices=['fuzzy', 'isbn', 'semantic', 'orchestrator', 'all'], 
                       default='all', help="Algoritmo específico para testar")
    parser.add_argument('--target-accuracy', type=float, default=0.5, 
                       help="Meta de acurácia (0.5-0.9)")
    parser.add_argument('--max-books', type=int, default=100, 
                       help="Número máximo de livros para testar")
    parser.add_argument('--parallel-tests', type=int, default=5, 
                       help="Número de testes paralelos")
    parser.add_argument('--generate-report', action='store_true', 
                       help="Gerar relatório HTML")
    parser.add_argument('--books-dir', default=str(project_root / "books"), 
                       help="Diretório dos livros")
    parser.add_argument('--results-dir', default=str(project_root / "test_results"), 
                       help="Diretório para salvar resultados")
    
    args = parser.parse_args()
    
    # Inicializar runner
    runner = ComprehensiveTestRunner(args.books_dir, args.results_dir)
    
    try:
        if args.algorithm == 'all':
            # Executar suite completa
            results = runner.run_comprehensive_test_suite(max_books=args.max_books)
            
            print(f"\n{'='*60}")
            print("RESULTADOS FINAIS")
            print(f"{'='*60}")
            
            summary = results.get('summary', {})
            performances = summary.get('algorithm_performance', {})
            
            for algorithm, perf in performances.items():
                print(f"{algorithm.upper()}:")
                print(f"  Acurácia: {perf['accuracy']:.1%}")
                print(f"  Taxa de sucesso: {perf['success_rate']:.1%}")
                print(f"  Tempo médio: {perf['avg_response_time']:.1f}ms")
                print()
            
            recommendations = summary.get('recommendations', [])
            if recommendations:
                print("RECOMENDAÇÕES:")
                for i, rec in enumerate(recommendations, 1):
                    print(f"  {i}. {rec}")
        
        else:
            # Testar algoritmo específico
            result = runner.run_algorithm_test(args.algorithm, args.max_books)
            
            if result.get('success', False):
                print(f"\n{args.algorithm.upper()} - RESULTADO:")
                print(f"Acurácia: {result['accuracy_rate']:.1%}")
                print(f"Taxa de sucesso: {result['success_rate']:.1%}")
                print(f"Tempo médio: {result['avg_response_time']:.1f}ms")
                
                if result['accuracy_rate'] >= args.target_accuracy:
                    print(f" Meta de {args.target_accuracy:.1%} ATINGIDA!")
                else:
                    print(f" Meta de {args.target_accuracy:.1%} NÃO atingida")
            else:
                print(f" Erro executando {args.algorithm}: {result.get('error', 'Erro desconhecido')}")
    
    except KeyboardInterrupt:
        logger.info("Teste interrompido pelo usuário")
    except Exception as e:
        logger.error(f"Erro executando testes: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()