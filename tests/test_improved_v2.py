#!/usr/bin/env python3
"""
Teste Completo dos Algoritmos Melhorados V2
==========================================

Executa teste completo dos algoritmos melhorados e compara com versao anterior.
"""

import sys
import time
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from core.enhanced_algorithms import ImprovedMetadataExtractor, EnhancedRealAlgorithms

def main():
    start_time = time.time()
    print(f"Iniciando teste completo dos algoritmos melhorados...")
    
    # Carregar base de livros
    books_dir = Path("books")
    if not books_dir.exists():
        print("ERRO: Diretório 'books' não encontrado!")
        sys.exit(1)
    
    # Construir base melhorada
    extractor = ImprovedMetadataExtractor()
    enhanced_books = []
    
    print("Processando livros...")
    count = 0
    for file_path in books_dir.iterdir():
        if count >= 80:  # Limitar para teste
            break
        if file_path.suffix.lower() in ['.pdf', '.epub', '.mobi'] and file_path.name != '.DS_Store':
            try:
                metadata = extractor.extract_enhanced_metadata(file_path.name)
                enhanced_books.append(metadata)
                count += 1
                if count % 10 == 0:
                    print(f"  Processados: {count}")
            except Exception as e:
                print(f"Erro processando {file_path.name}: {e}")
    
    print(f"Base criada com {len(enhanced_books)} livros")
    
    # Estatísticas da base
    stats = {
        'total_books': len(enhanced_books),
        'with_title': sum(1 for b in enhanced_books if b.get('title')),
        'with_author': sum(1 for b in enhanced_books if b.get('author')),
        'with_publisher': sum(1 for b in enhanced_books if b.get('publisher')),
        'with_year': sum(1 for b in enhanced_books if b.get('year')),
        'with_category': sum(1 for b in enhanced_books if b.get('category') and b['category'] != 'General'),
        'avg_confidence': sum(b.get('confidence', 0) for b in enhanced_books) / len(enhanced_books) if enhanced_books else 0
    }
    
    print("\n=== ESTATÍSTICAS DA BASE MELHORADA ===")
    for key, value in stats.items():
        if key.startswith('with_'):
            field_name = key.replace('with_', '').replace('_', ' ').title()
            percentage = (value / stats['total_books'] * 100) if stats['total_books'] > 0 else 0
            print(f"{field_name}: {value} ({percentage:.1f}%)")
        elif key == 'avg_confidence':
            print(f"Confiança Média: {value:.3f}")
    
    # Queries de teste
    test_queries = [
        'Python Programming',
        'JavaScript React',
        'Machine Learning',
        'Database SQL',
        'Security Hacking',
        'Web Development',
        'Docker Kubernetes',
        'Data Science',
        'Network Security',
        'Software Engineering',
        'Algorithm Design',
        'System Administration',
        'Cloud Computing',
        'Mobile Development',
        'DevOps Practices',
    ]
    
    print(f"\n=== TESTANDO ALGORITMOS COM {len(test_queries)} QUERIES ===")
    
    # Inicializar algoritmos
    algorithms = EnhancedRealAlgorithms(enhanced_books)
    
    results = {
        'enhanced_fuzzy': [],
        'enhanced_semantic': [],
        'enhanced_orchestrator': []
    }
    
    total_queries = len(test_queries)
    for i, query in enumerate(test_queries, 1):
        print(f"Query {i}/{total_queries}: '{query}'")
        
        # Testar cada algoritmo
        try:
            fuzzy_results = algorithms.enhanced_fuzzy_search(query, 5)
            semantic_results = algorithms.enhanced_semantic_search(query, 5)
            orchestrator_results = algorithms.enhanced_orchestrator(query, 5)
            
            results['enhanced_fuzzy'].append({
                'query': query,
                'results': fuzzy_results,
                'count': len(fuzzy_results),
                'avg_score': sum(r['similarity_score'] for r in fuzzy_results) / len(fuzzy_results) if fuzzy_results else 0
            })
            
            results['enhanced_semantic'].append({
                'query': query,
                'results': semantic_results,
                'count': len(semantic_results),
                'avg_score': sum(r['similarity_score'] for r in semantic_results) / len(semantic_results) if semantic_results else 0
            })
            
            results['enhanced_orchestrator'].append({
                'query': query,
                'results': orchestrator_results,
                'count': len(orchestrator_results),
                'avg_score': sum(r['similarity_score'] for r in orchestrator_results) / len(orchestrator_results) if orchestrator_results else 0
            })
            
            print(f"  Fuzzy: {len(fuzzy_results)} resultados (avg: {results['enhanced_fuzzy'][-1]['avg_score']:.3f})")
            print(f"  Semantic: {len(semantic_results)} resultados (avg: {results['enhanced_semantic'][-1]['avg_score']:.3f})")
            print(f"  Orchestrator: {len(orchestrator_results)} resultados (avg: {results['enhanced_orchestrator'][-1]['avg_score']:.3f})")
            
        except Exception as e:
            print(f"  ERRO na query '{query}': {e}")
    
    # Calcular performance geral
    print("\n=== PERFORMANCE GERAL ===")
    
    for algo_name, algo_results in results.items():
        total_results = sum(r['count'] for r in algo_results)
        queries_with_results = sum(1 for r in algo_results if r['count'] > 0)
        avg_results_per_query = total_results / len(algo_results) if algo_results else 0
        overall_avg_score = sum(r['avg_score'] for r in algo_results) / len(algo_results) if algo_results else 0
        success_rate = queries_with_results / len(test_queries) * 100 if test_queries else 0
        
        print(f"\n{algo_name.upper()}:")
        print(f"  Queries com resultados: {queries_with_results}/{len(test_queries)} ({success_rate:.1f}%)")
        print(f"  Média de resultados por query: {avg_results_per_query:.1f}")
        print(f"  Score médio geral: {overall_avg_score:.3f}")
    
    # Salvar resultados
    output_data = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'stats': stats,
        'test_queries': test_queries,
        'results': results,
        'execution_time': time.time() - start_time
    }
    
    output_file = 'improved_algorithms_v2_results.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n=== MELHORIAS IMPLEMENTADAS ===")
    print(" Extração de metadados robusta (publisher detection)")
    print(" Algoritmo semântico fortalecido")
    print(" Weights otimizados no orchestrator")  
    print(" Bonus para multi-algoritmo matching")
    print(" Thresholds ajustados")
    print(" Categorização aprimorada")
    print(" Keywords expansion")
    
    print(f"\nResultados salvos em: {output_file}")
    print(f"Tempo total de execução: {time.time() - start_time:.1f} segundos")
    
    # Comparação rápida com versão anterior se existir
    try:
        with open('real_data_test_results.json', 'r') as f:
            previous_data = json.load(f)
        
        print("\n=== COMPARAÇÃO COM VERSÃO ANTERIOR ===")
        
        # Comparar stats de metadados
        prev_stats = previous_data.get('database_stats', {})
        print("Melhorias na extração de metadados:")
        
        if 'publisher_detection' in prev_stats:
            old_pub = prev_stats['publisher_detection']
            new_pub = stats['with_publisher'] / stats['total_books'] * 100
            print(f"  Publisher: {old_pub:.1f}% → {new_pub:.1f}% (+{new_pub - old_pub:.1f}%)")
        
        if 'year_extraction' in prev_stats:
            old_year = prev_stats['year_extraction']  
            new_year = stats['with_year'] / stats['total_books'] * 100
            print(f"  Year: {old_year:.1f}% → {new_year:.1f}% (+{new_year - old_year:.1f}%)")
            
    except FileNotFoundError:
        print("(Sem dados anteriores para comparação)")

if __name__ == "__main__":
    main()
