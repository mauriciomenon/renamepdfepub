#!/usr/bin/env python3
"""
CLI para Sistema de Cache Iterativo
==================================

Interface de linha de comando para o sistema de cache iterativo inteligente.
Permite configurar e executar processamento iterativo com diferentes parâmetros.
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime
import json

# Adiciona o diretório src ao path para imports (corrigido)
SRC = Path(__file__).parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from core.iterative_cache_system import (
    IterativeCacheSystem, 
    IterationConfig, 
    create_iterative_cache_system
)

def main():
    parser = argparse.ArgumentParser(
        description='Sistema de Cache Iterativo para Processamento de Metadados',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:

1. Processamento por tempo (30 minutos):
   python start_iterative_cache.py --max-time 30 --batch-size 100

2. Processamento por iterações (50 iterações):
   python start_iterative_cache.py --max-iterations 50 --performance-metric accuracy

3. Processamento até atingir performance (85% de acurácia):
   python start_iterative_cache.py --target-performance 0.85 --threads 8

4. Adicionar arquivos de uma lista:
   python start_iterative_cache.py --add-files file_list.txt --source-type local

5. Adicionar arquivos remotos do Google Drive:
   python start_iterative_cache.py --add-remote gdrive_files.json --source-type gdrive

6. Executar com configuração personalizada:
   python start_iterative_cache.py --config config.json
        """
    )
    
    # Comandos principais
    parser.add_argument('--action', 
                       choices=['run', 'add-files', 'add-remote', 'export', 'status'],
                       default='run',
                       help='Ação a executar (default: run)')
    
    # Configurações de processamento
    parser.add_argument('--max-iterations', type=int,
                       help='Número máximo de iterações')
    
    parser.add_argument('--max-time', type=int,
                       help='Tempo máximo em minutos')
    
    parser.add_argument('--target-performance', type=float,
                       help='Performance alvo (0.0-1.0)')
    
    parser.add_argument('--performance-metric', 
                       choices=['accuracy', 'improvement', 'completeness'],
                       default='accuracy',
                       help='Métrica de performance (default: accuracy)')
    
    parser.add_argument('--batch-size', type=int, default=50,
                       help='Tamanho do lote por iteração (default: 50)')
    
    parser.add_argument('--threads', type=int, default=4,
                       help='Número de threads (default: 4)')
    
    parser.add_argument('--cache-interval', type=int, default=10,
                       help='Intervalo para salvar cache (default: 10)')
    
    # Arquivos e dados
    parser.add_argument('--add-files', type=str,
                       help='Arquivo com lista de caminhos para adicionar')
    
    parser.add_argument('--add-remote', type=str,
                       help='Arquivo JSON com mapeamento de arquivos remotos')
    
    parser.add_argument('--source-type', 
                       choices=['local', 'gdrive', 'onedrive'],
                       default='local',
                       help='Tipo de fonte dos arquivos (default: local)')
    
    # Configuração e output
    parser.add_argument('--config', type=str,
                       help='Arquivo de configuração JSON')
    
    parser.add_argument('--cache-dir', type=str,
                       help='Diretório do cache (default: data/cache/iterative)')
    
    parser.add_argument('--export-file', type=str,
                       help='Arquivo para exportar resumo')
    
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Output verbose')
    
    args = parser.parse_args()
    
    # Configura cache directory
    cache_dir = Path(args.cache_dir) if args.cache_dir else None
    
    try:
        if args.action == 'run':
            run_iterative_processing(args, cache_dir)
        elif args.action == 'add-files':
            add_files_action(args, cache_dir)
        elif args.action == 'add-remote':
            add_remote_action(args, cache_dir) 
        elif args.action == 'export':
            export_action(args, cache_dir)
        elif args.action == 'status':
            status_action(args, cache_dir)
            
    except KeyboardInterrupt:
        print("\n[WARN] Processamento interrompido pelo usuario")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

def load_config_from_file(config_file: str) -> dict:
    """Carrega configuração de arquivo JSON"""
    with open(config_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def create_iteration_config(args) -> IterationConfig:
    """Cria configuração de iteração a partir dos argumentos"""
    
    # Carrega configuração de arquivo se especificado
    config_data = {}
    if args.config:
        config_data = load_config_from_file(args.config)
    
    # Argumentos de linha de comando têm prioridade
    return IterationConfig(
        max_iterations=args.max_iterations or config_data.get('max_iterations'),
        max_time_minutes=args.max_time or config_data.get('max_time_minutes'),
        target_performance=args.target_performance or config_data.get('target_performance'),
        performance_metric=args.performance_metric or config_data.get('performance_metric', 'accuracy'),
        batch_size=args.batch_size or config_data.get('batch_size', 50),
        thread_count=args.threads or config_data.get('thread_count', 4),
        cache_interval=args.cache_interval or config_data.get('cache_interval', 10)
    )

def run_iterative_processing(args, cache_dir):
    """Executa processamento iterativo principal"""
    print(" Iniciando Sistema de Cache Iterativo")
    print("=" * 50)
    
    # Cria sistema
    system = create_iterative_cache_system(cache_dir)
    
    # Cria configuração
    config = create_iteration_config(args)
    
    print("Configuracao:")
    print(f"   - Iteracoes maximas: {config.max_iterations or 'Ilimitado'}")
    print(f"   - Tempo maximo: {config.max_time_minutes or 'Ilimitado'} min")
    print(f"   - Performance alvo: {config.target_performance or 'Nao definida'}")
    print(f"   - Metrica: {config.performance_metric}")
    print(f"   - Tamanho do lote: {config.batch_size}")
    print(f"   - Threads: {config.thread_count}")
    print()
    
    # Verifica se há dados para processar
    predictions_count = get_predictions_count(system)
    if predictions_count == 0:
        print("[WARN] Nenhum arquivo encontrado para processar.")
        print("       Use --add-files ou --add-remote para adicionar arquivos primeiro.")
        return
    
    print(f"Arquivos para processar: {predictions_count}")
    print()
    
    # Executa processamento
    start_time = datetime.now()
    print(f"Inicio: {start_time.strftime('%H:%M:%S')}")
    
    try:
        final_stats = system.run_iterative_processing(config)
        
        end_time = datetime.now()
        print()
        print("Processamento concluido!")
        print("=" * 50)
        print(f"Tempo total: {end_time - start_time}")
        print(f"Iteracoes: {final_stats['iterations_completed']}")
        print(f"📊 Predições totais: {final_stats['total_predictions']}")
        print(f"✨ Alta confiança: {final_stats['high_confidence_predictions']}")
        print(f"🎯 Dados consolidados: {final_stats['consolidated_entries']}")
        print(f"📈 Confiança média: {final_stats['average_confidence']:.3f}")
        
        # Exporta resumo
        if args.export_file:
            export_file = Path(args.export_file)
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_file = Path(f"reports/outputs/current/iterative_cache_summary_{timestamp}.json")
            
        summary_file = system.export_cache_summary(export_file)
        print(f"📄 Resumo exportado: {summary_file}")
        
    except Exception as e:
        print(f" Erro durante processamento: {e}")
        raise

def add_files_action(args, cache_dir):
    """Adiciona arquivos de uma lista"""
    if not args.add_files:
        print(" Especifique --add-files com o caminho para o arquivo de lista")
        return
    
    list_file = Path(args.add_files)
    if not list_file.exists():
        print(f" Arquivo não encontrado: {list_file}")
        return
    
    print(f"📝 Adicionando arquivos de: {list_file}")
    
    # Lê lista de arquivos
    with open(list_file, 'r', encoding='utf-8') as f:
        file_paths = [line.strip() for line in f if line.strip()]
    
    print(f"📁 Encontrados {len(file_paths)} arquivos")
    
    # Adiciona ao sistema
    system = create_iterative_cache_system(cache_dir)
    added_count = system.add_file_list(file_paths, args.source_type)
    
    print(f" Adicionados {added_count} arquivos como {args.source_type}")

def add_remote_action(args, cache_dir):
    """Adiciona arquivos remotos de mapeamento JSON"""
    if not args.add_remote:
        print(" Especifique --add-remote com o caminho para o arquivo JSON")
        return
    
    json_file = Path(args.add_remote)
    if not json_file.exists():
        print(f" Arquivo não encontrado: {json_file}")
        return
    
    print(f"☁  Adicionando arquivos remotos de: {json_file}")
    
    # Lê mapeamento de arquivos remotos
    with open(json_file, 'r', encoding='utf-8') as f:
        remote_files = json.load(f)
    
    print(f"📁 Encontrados {len(remote_files)} arquivos remotos")
    
    # Adiciona ao sistema
    system = create_iterative_cache_system(cache_dir)
    file_paths = system.add_remote_files(remote_files, args.source_type)
    
    print(f" Adicionados {len(file_paths)} arquivos remotos ({args.source_type})")

def export_action(args, cache_dir):
    """Exporta resumo do cache"""
    print("📊 Exportando resumo do cache...")
    
    system = create_iterative_cache_system(cache_dir)
    
    export_file = Path(args.export_file) if args.export_file else None
    summary_file = system.export_cache_summary(export_file)
    
    print(f" Resumo exportado: {summary_file}")

def status_action(args, cache_dir):
    """Mostra status atual do cache"""
    print("📊 Status do Cache Iterativo")
    print("=" * 40)
    
    system = create_iterative_cache_system(cache_dir)
    
    # Estatísticas básicas
    predictions_count = get_predictions_count(system)
    consolidated_count = get_consolidated_count(system)
    avg_confidence = system._calculate_average_confidence()
    
    print(f"📁 Total de predições: {predictions_count}")
    print(f"✨ Dados consolidados: {consolidated_count}")
    print(f"📈 Confiança média: {avg_confidence:.3f}")
    
    # Distribuição de confiança
    health = system._analyze_cache_health()
    conf_dist = health['confidence_distribution']
    
    print()
    print("📊 Distribuição de Confiança:")
    print(f"   • Baixa (< 0.3): {conf_dist['low']}")
    print(f"   • Média (0.3-0.7): {conf_dist['medium']}")
    print(f"   • Alta (> 0.7): {conf_dist['high']}")
    
    # Performance recente
    trend = system._get_performance_trend()
    if trend:
        print()
        print(f"📈 Performance recente: {trend[0]:.3f}")
        if len(trend) > 1:
            direction = "📈" if trend[0] > trend[1] else "📉" if trend[0] < trend[1] else "➡"
            print(f"   Tendência: {direction}")

def get_predictions_count(system) -> int:
    """Obtém número de predições no cache"""
    import sqlite3
    with sqlite3.connect(system.predictions_db) as conn:
        cursor = conn.execute('SELECT COUNT(*) FROM prediction_cache')
        return cursor.fetchone()[0]

def get_consolidated_count(system) -> int:
    """Obtém número de dados consolidados"""
    import sqlite3
    with sqlite3.connect(system.consolidated_db) as conn:
        cursor = conn.execute('SELECT COUNT(*) FROM consolidated_cache')
        return cursor.fetchone()[0]

if __name__ == "__main__":
    main()
