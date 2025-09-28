#!/usr/bin/env python3
"""
Validação Rápida do Estado Atual do Projeto
==========================================

Este script executa uma validação rápida para verificar:
1. Estado dos algoritmos implementados
2. Testes básicos com livros da coleção
3. Acurácia atual dos algoritmos
4. Performance e tempo de resposta
5. Status da infraestrutura de expansão

Uso:
    python quick_validation.py [--sample-size=20] [--verbose]
"""

import os
import sys
import time
import json
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import statistics
import random

# Adicionar src ao path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

# Configurar logging básico
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_project_structure():
    """Verificar estrutura do projeto"""
    logger.info("=== VERIFICANDO ESTRUTURA DO PROJETO ===")
    
    required_dirs = [
        "src/renamepdfepub",
        "src/renamepdfepub/search_algorithms", 
        "src/renamepdfepub/cli",
        "src/renamepdfepub/core",
        "tests",
        "books"
    ]
    
    required_files = [
        "src/renamepdfepub/search_algorithms/fuzzy_search.py",
        "src/renamepdfepub/search_algorithms/isbn_search.py", 
        "src/renamepdfepub/search_algorithms/semantic_search.py",
        "src/renamepdfepub/search_algorithms/search_orchestrator.py",
        "tests/test_book_collection.py",
        "run_comprehensive_tests.py"
    ]
    
    structure_ok = True
    
    # Verificar diretórios
    for dir_path in required_dirs:
        full_path = project_root / dir_path
        if full_path.exists():
            logger.info(f" {dir_path}")
        else:
            logger.error(f" {dir_path} - AUSENTE")
            structure_ok = False
    
    # Verificar arquivos
    for file_path in required_files:
        full_path = project_root / file_path
        if full_path.exists():
            logger.info(f" {file_path}")
        else:
            logger.error(f" {file_path} - AUSENTE")
            structure_ok = False
    
    return structure_ok

def check_books_collection():
    """Verificar coleção de livros"""
    logger.info("\n=== VERIFICANDO COLEÇÃO DE LIVROS ===")
    
    books_dir = project_root / "books"
    if not books_dir.exists():
        logger.error(" Diretório books/ não encontrado")
        return False, 0, {}
    
    # Contar livros por extensão
    extensions = {'.pdf': 0, '.epub': 0, '.mobi': 0}
    total_books = 0
    
    for file_path in books_dir.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in extensions:
            extensions[file_path.suffix.lower()] += 1
            total_books += 1
    
    logger.info(f"📚 Total de livros: {total_books}")
    for ext, count in extensions.items():
        if count > 0:
            logger.info(f"   {ext}: {count} livros")
    
    # Verificar se há livros suficientes para teste
    if total_books < 10:
        logger.warning(f"⚠  Poucos livros para teste ({total_books}). Recomendado: pelo menos 50")
    else:
        logger.info(f" Coleção adequada para testes ({total_books} livros)")
    
    return total_books >= 10, total_books, extensions

def quick_algorithm_test(sample_size: int = 20):
    """Teste rápido dos algoritmos"""
    logger.info(f"\n=== TESTE RÁPIDO DOS ALGORITMOS (sample: {sample_size}) ===")
    
    try:
        # Importar módulos necessários
        from renamepdfepub.search_algorithms.fuzzy_search import FuzzySearchAlgorithm
        from renamepdfepub.search_algorithms.isbn_search import ISBNSearchAlgorithm
        from renamepdfepub.search_algorithms.semantic_search import SemanticSearchAlgorithm
        from renamepdfepub.search_algorithms.search_orchestrator import SearchOrchestrator
    except ImportError as e:
        logger.error(f" Erro importando algoritmos: {e}") 
        return False, {}
    
    # Inicializar algoritmos
    try:
        fuzzy = FuzzySearchAlgorithm()
        isbn = ISBNSearchAlgorithm()
        semantic = SemanticSearchAlgorithm()
        orchestrator = SearchOrchestrator()
        
        algorithms = {
            'fuzzy': fuzzy,
            'isbn': isbn,
            'semantic': semantic,
            'orchestrator': orchestrator
        }
        
        logger.info(" Algoritmos carregados com sucesso")
        
    except Exception as e:
        logger.error(f" Erro inicializando algoritmos: {e}")
        return False, {}
    
    # Obter sample de livros para teste
    books_dir = project_root / "books"
    books = []
    
    for file_path in books_dir.iterdir():
        if file_path.suffix.lower() in ['.pdf', '.epub', '.mobi']:
            books.append(file_path)
    
    if len(books) < sample_size:
        sample_size = len(books)
        logger.warning(f"⚠  Reduzindo sample para {sample_size} (todos os livros disponíveis)")
    
    test_books = random.sample(books, sample_size)
    logger.info(f"📖 Testando com {len(test_books)} livros")
    
    # Executar testes
    results = {}
    
    for algo_name, algorithm in algorithms.items():
        logger.info(f"\n--- Testando {algo_name.upper()} ---")
        
        algo_results = {
            'tests': 0,
            'successes': 0,
            'failures': 0,
            'total_time': 0,
            'times': [],
            'errors': []
        }
        
        for book in test_books:
            # Extrair query do nome do arquivo
            query = book.stem.replace('_', ' ').replace('-', ' ')
            
            # Limitar tamanho da query
            if len(query) > 100:
                query = query[:100]
            
            try:
                start_time = time.time()
                
                # Executar busca
                search_results = algorithm.search(query, limit=3)
                
                end_time = time.time()
                response_time = (end_time - start_time) * 1000  # ms
                
                algo_results['tests'] += 1
                algo_results['total_time'] += response_time
                algo_results['times'].append(response_time)
                
                if search_results and len(search_results) > 0:
                    algo_results['successes'] += 1
                else:
                    algo_results['failures'] += 1
                
                # Log progresso a cada 5 testes
                if algo_results['tests'] % 5 == 0:
                    logger.info(f"   {algo_results['tests']}/{len(test_books)} testes concluídos")
                    
            except Exception as e:
                algo_results['tests'] += 1
                algo_results['failures'] += 1
                algo_results['errors'].append(str(e))
                logger.error(f"   Erro testando '{query[:30]}...': {e}")
        
        # Calcular estatísticas
        if algo_results['tests'] > 0:
            algo_results['success_rate'] = algo_results['successes'] / algo_results['tests']
            algo_results['avg_time'] = algo_results['total_time'] / algo_results['tests']
            
            if algo_results['times']:
                algo_results['min_time'] = min(algo_results['times'])
                algo_results['max_time'] = max(algo_results['times'])
        
        results[algo_name] = algo_results
        
        # Log resultados do algoritmo
        logger.info(f"   Resultados {algo_name}:")
        logger.info(f"     Testes: {algo_results['tests']}")
        logger.info(f"     Sucessos: {algo_results['successes']}")
        logger.info(f"     Taxa de sucesso: {algo_results.get('success_rate', 0):.1%}")
        logger.info(f"     Tempo médio: {algo_results.get('avg_time', 0):.1f}ms")
        
        if algo_results['errors']:
            logger.warning(f"     Erros: {len(algo_results['errors'])}")
    
    return True, results

def analyze_results(results: Dict[str, Any]):
    """Analisar resultados dos testes"""
    logger.info("\n=== ANÁLISE DOS RESULTADOS ===")
    
    if not results:
        logger.error(" Nenhum resultado para analisar")
        return
    
    # Resumo geral
    logger.info("📊 RESUMO GERAL:")
    
    best_algorithm = None
    best_score = 0
    
    for algo_name, algo_results in results.items():
        success_rate = algo_results.get('success_rate', 0)
        avg_time = algo_results.get('avg_time', 0)
        
        # Calcular score combinado (70% sucesso, 30% velocidade)
        time_score = max(0, 1 - (avg_time / 1000))  # Penalizar > 1s
        combined_score = (success_rate * 0.7) + (time_score * 0.3)
        
        logger.info(f"\n{algo_name.upper()}:")
        logger.info(f"  Taxa de sucesso: {success_rate:.1%}")
        logger.info(f"  Tempo médio: {avg_time:.1f}ms")
        logger.info(f"  Score combinado: {combined_score:.3f}")
        
        if combined_score > best_score:
            best_score = combined_score
            best_algorithm = algo_name
        
        # Análise de performance
        if success_rate >= 0.5:
            logger.info(f"   Meta de 50% ATINGIDA")
        else:
            logger.info(f"   Meta de 50% NÃO atingida")
        
        if avg_time <= 100:
            logger.info(f"   Performance adequada (< 100ms)")
        else:
            logger.info(f"  ⚠  Performance lenta (> 100ms)")
    
    # Melhor algoritmo
    logger.info(f"\n🏆 MELHOR ALGORITMO: {best_algorithm.upper()} (score: {best_score:.3f})")
    
    # Recomendações
    logger.info("\n💡 RECOMENDAÇÕES:")
    
    for algo_name, algo_results in results.items():
        success_rate = algo_results.get('success_rate', 0)
        avg_time = algo_results.get('avg_time', 0)
        
        if success_rate < 0.5:
            logger.info(f"  🔧 {algo_name}: Refinar algoritmo (sucesso < 50%)")
        
        if avg_time > 100:
            logger.info(f"  ⚡ {algo_name}: Otimizar performance (tempo > 100ms)")
        
        if len(algo_results.get('errors', [])) > 0:
            logger.info(f"  🐛 {algo_name}: Corrigir {len(algo_results['errors'])} erros")

def save_validation_report(structure_ok: bool, books_info: Dict, algorithm_results: Dict):
    """Salvar relatório de validação"""
    logger.info("\n=== SALVANDO RELATÓRIO ===")
    
    report = {
        'validation_date': datetime.now().isoformat(),
        'project_structure': {
            'status': 'OK' if structure_ok else 'ISSUES',
            'structure_valid': structure_ok
        },
        'books_collection': books_info,
        'algorithm_tests': algorithm_results,
        'summary': {
            'ready_for_comprehensive_testing': structure_ok and books_info.get('adequate', False),
            'algorithms_functional': len(algorithm_results) > 0,
            'recommended_next_steps': []
        }
    }
    
    # Gerar recomendações
    if not structure_ok:
        report['summary']['recommended_next_steps'].append("Corrigir estrutura do projeto")
    
    if not books_info.get('adequate', False):
        report['summary']['recommended_next_steps'].append("Adicionar mais livros à coleção")
    
    if algorithm_results:
        best_success_rate = max(r.get('success_rate', 0) for r in algorithm_results.values())
        if best_success_rate < 0.5:
            report['summary']['recommended_next_steps'].append("Refinar algoritmos (acurácia < 50%)")
        elif best_success_rate < 0.7:
            report['summary']['recommended_next_steps'].append("Otimizar algoritmos para maior acurácia")
        else:
            report['summary']['recommended_next_steps'].append("Executar testes abrangentes")
    
    # Salvar relatório
    report_file = project_root / "validation_report.json"
    
    try:
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f" Relatório salvo: {report_file}")
        
    except Exception as e:
        logger.error(f" Erro salvando relatório: {e}")

def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description="Validação Rápida do Projeto")
    parser.add_argument('--sample-size', type=int, default=20, 
                       help="Tamanho da amostra para teste rápido")
    parser.add_argument('--verbose', action='store_true', 
                       help="Output detalhado")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info(" INICIANDO VALIDAÇÃO RÁPIDA DO PROJETO")
    logger.info(f"Sample size: {args.sample_size}")
    
    start_time = time.time()
    
    # 1. Verificar estrutura do projeto
    structure_ok = check_project_structure()
    
    # 2. Verificar coleção de livros
    books_adequate, total_books, book_types = check_books_collection()
    books_info = {
        'adequate': books_adequate,
        'total_books': total_books,
        'types': book_types
    }
    
    # 3. Teste rápido dos algoritmos
    algorithm_results = {}
    if structure_ok:
        algorithms_ok, algorithm_results = quick_algorithm_test(args.sample_size)
        
        if algorithms_ok:
            analyze_results(algorithm_results)
        else:
            logger.error(" Falha nos testes dos algoritmos")
    else:
        logger.error(" Estrutura do projeto com problemas - pulando testes")
    
    # 4. Salvar relatório
    save_validation_report(structure_ok, books_info, algorithm_results)
    
    # 5. Resumo final
    total_time = time.time() - start_time
    
    logger.info(f"\n{'='*60}")
    logger.info("RESUMO DA VALIDAÇÃO")
    logger.info(f"{'='*60}")
    logger.info(f"⏱  Tempo total: {total_time:.2f}s")
    logger.info(f"📁 Estrutura: {' OK' if structure_ok else ' PROBLEMAS'}")
    logger.info(f"📚 Livros: {' ADEQUADO' if books_adequate else '⚠  INSUFICIENTE'} ({total_books})")
    logger.info(f"🔍 Algoritmos: {' FUNCIONAIS' if algorithm_results else ' PROBLEMAS'}")
    
    if structure_ok and books_adequate and algorithm_results:
        # Calcular melhor taxa de sucesso
        best_rate = max(r.get('success_rate', 0) for r in algorithm_results.values())
        
        logger.info(f"🎯 Melhor acurácia: {best_rate:.1%}")
        
        if best_rate >= 0.5:
            logger.info("🎉 PROJETO PRONTO PARA TESTES ABRANGENTES!")
            logger.info("\nPróximos passos recomendados:")
            logger.info("1. python run_comprehensive_tests.py --algorithm=all --max-books=100")
            logger.info("2. Analisar relatório HTML gerado")
            logger.info("3. Refinar algoritmos com base nos resultados")
        else:
            logger.info("⚠  ALGORITMOS PRECISAM DE REFINAMENTO")
            logger.info("Executar testes individuais para diagnóstico")
    else:
        logger.info(" PROJETO PRECISA DE CORREÇÕES ANTES DOS TESTES")
    
    logger.info(f"{'='*60}")

if __name__ == "__main__":
    main()