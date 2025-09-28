"""
Sistema de Cache Iterativo Inteligente
=====================================

Sistema que refina dados progressivamente através de múltiplas iterações,
criando um buffer de dados otimizado para acelerar processamentos futuros.
Suporta:
- Controle por tempo, iterações ou performance desejada
- Cache de metadados e "best guess" para arquivos não baixados
- Integração com Google Drive, OneDrive e listas de arquivos
- Tabelas separadas para dados consolidados vs predições
"""

import time
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Callable, Any
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import logging

@dataclass
class IterationConfig:
    """Configuração para controle de iterações"""
    max_iterations: Optional[int] = None
    max_time_minutes: Optional[int] = None
    target_performance: Optional[float] = None  # 0.0 - 1.0
    performance_metric: str = "accuracy"  # accuracy, speed, completeness
    batch_size: int = 50
    thread_count: int = 4
    cache_interval: int = 10  # salvar cache a cada N iterações

@dataclass
class CacheEntry:
    """Entrada individual do cache"""
    file_path: str
    file_hash: Optional[str]
    confidence_score: float  # 0.0 - 1.0
    metadata: Dict[str, Any]
    predictions: Dict[str, Any]
    iteration_created: int
    last_updated: datetime
    is_consolidated: bool = False
    source_type: str = "local"  # local, gdrive, onedrive, prediction

class IterativeCacheSystem:
    """Sistema principal de cache iterativo"""
    
    def __init__(self, cache_dir: Path = None):
        self.cache_dir = cache_dir or Path("data/cache/iterative")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Bancos de dados separados
        self.consolidated_db = self.cache_dir / "consolidated_data.db"
        self.predictions_db = self.cache_dir / "best_guess_predictions.db"
        self.performance_db = self.cache_dir / "performance_metrics.db"
        
        self._init_databases()
        self.logger = self._setup_logging()
        
        # Algoritmos disponíveis (será expandido)
        self.algorithms = {}
        self.current_iteration = 0
        self.session_start = datetime.now()
        
    def _init_databases(self):
        """Inicializa os bancos de dados SQLite"""
        
        # Banco de dados consolidados (dados confirmados)
        with sqlite3.connect(self.consolidated_db) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS consolidated_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT UNIQUE NOT NULL,
                    file_hash TEXT,
                    confidence_score REAL NOT NULL,
                    metadata TEXT NOT NULL,
                    iteration_created INTEGER NOT NULL,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source_type TEXT DEFAULT 'local'
                )
            ''')
            
        # Banco de predições (best guess para arquivos não baixados)
        with sqlite3.connect(self.predictions_db) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS prediction_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT UNIQUE NOT NULL,
                    predicted_metadata TEXT NOT NULL,
                    confidence_score REAL NOT NULL,
                    prediction_basis TEXT,  -- Como foi feita a predição
                    iteration_created INTEGER NOT NULL,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    remote_source TEXT,  -- gdrive_id, onedrive_url, etc
                    is_downloaded BOOLEAN DEFAULT FALSE
                )
            ''')
            
        # Banco de métricas de performance
        with sqlite3.connect(self.performance_db) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    iteration INTEGER NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    processing_time REAL NOT NULL,
                    files_processed INTEGER NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
    
    def _setup_logging(self) -> logging.Logger:
        """Configura logging específico para o sistema iterativo"""
        logger = logging.getLogger('iterative_cache')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.FileHandler(self.cache_dir / 'iterative_cache.log')
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
    
    def register_algorithm(self, name: str, algorithm_func: Callable, 
                          weight: float = 1.0):
        """Registra um algoritmo para uso nas iterações"""
        self.algorithms[name] = {
            'func': algorithm_func,
            'weight': weight,
            'performance_history': []
        }
        self.logger.info(f"Algoritmo registrado: {name} (peso: {weight})")
    
    def add_file_list(self, file_paths: List[str], source_type: str = "local"):
        """Adiciona lista de arquivos para processamento iterativo"""
        added_count = 0
        
        with sqlite3.connect(self.predictions_db) as conn:
            for file_path in file_paths:
                try:
                    # Cria predição inicial baseada no nome do arquivo
                    initial_prediction = self._create_initial_prediction(file_path)
                    
                    conn.execute('''
                        INSERT OR IGNORE INTO prediction_cache 
                        (file_path, predicted_metadata, confidence_score, 
                         prediction_basis, iteration_created, remote_source)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        file_path,
                        json.dumps(initial_prediction['metadata']),
                        initial_prediction['confidence'],
                        initial_prediction['basis'],
                        0,  # iteration 0 = initial
                        initial_prediction.get('remote_source', '')
                    ))
                    added_count += 1
                    
                except Exception as e:
                    self.logger.error(f"Erro ao adicionar {file_path}: {e}")
        
        self.logger.info(f"Adicionados {added_count} arquivos do tipo {source_type}")
        return added_count
    
    def add_remote_files(self, remote_files: Dict[str, str], 
                        source_type: str = "gdrive"):
        """
        Adiciona arquivos remotos (Google Drive, OneDrive, etc)
        remote_files: {file_path: remote_id/url}
        """
        file_paths = []
        
        with sqlite3.connect(self.predictions_db) as conn:
            for file_path, remote_id in remote_files.items():
                initial_prediction = self._create_initial_prediction(file_path)
                initial_prediction['remote_source'] = remote_id
                
                conn.execute('''
                    INSERT OR REPLACE INTO prediction_cache 
                    (file_path, predicted_metadata, confidence_score, 
                     prediction_basis, iteration_created, remote_source)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    file_path,
                    json.dumps(initial_prediction['metadata']),
                    initial_prediction['confidence'],
                    initial_prediction['basis'],
                    0,
                    remote_id
                ))
                file_paths.append(file_path)
        
        self.logger.info(f"Adicionados {len(file_paths)} arquivos remotos ({source_type})")
        return file_paths
    
    def _create_initial_prediction(self, file_path: str) -> Dict:
        """Cria predição inicial baseada no nome do arquivo"""
        path_obj = Path(file_path)
        filename = path_obj.name
        extension = path_obj.suffix.lower()
        
        # Análise básica do nome do arquivo
        prediction = {
            'metadata': {
                'filename': filename,
                'extension': extension,
                'estimated_title': self._extract_title_from_filename(filename),
                'estimated_author': self._extract_author_from_filename(filename),
                'estimated_year': self._extract_year_from_filename(filename),
                'file_type': 'ebook' if extension in ['.pdf', '.epub', '.mobi'] else 'unknown'
            },
            'confidence': self._calculate_initial_confidence(filename),
            'basis': 'filename_analysis',
            'remote_source': None
        }
        
        return prediction
    
    def _extract_title_from_filename(self, filename: str) -> Optional[str]:
        """Extrai título provável do nome do arquivo"""
        # Remove extensão
        name_without_ext = Path(filename).stem
        
        # Padrões comuns: "Author - Title (Year)" ou "Title - Author"  
        if ' - ' in name_without_ext:
            parts = name_without_ext.split(' - ')
            if len(parts) >= 2:
                # Se a primeira parte parece ser um autor (tem espaços), título é o segundo
                if len(parts[0].split()) <= 3:  # Provavelmente autor
                    return parts[1].strip()
                else:  # Provavelmente título é o primeiro
                    return parts[0].strip()
        
        # Se não tem padrão claro, usa o nome completo limpo
        return name_without_ext.replace('_', ' ').strip()
    
    def _extract_author_from_filename(self, filename: str) -> Optional[str]:
        """Extrai autor provável do nome do arquivo"""
        name_without_ext = Path(filename).stem
        
        if ' - ' in name_without_ext:
            parts = name_without_ext.split(' - ')
            if len(parts) >= 2:
                # Se primeira parte parece autor (poucas palavras)
                if len(parts[0].split()) <= 3:
                    return parts[0].strip()
        
        return None
    
    def _extract_year_from_filename(self, filename: str) -> Optional[int]:
        """Extrai ano provável do nome do arquivo"""
        import re
        
        # Procura por anos entre parênteses ou no final
        year_patterns = [
            r'\((\d{4})\)',  # (2023)
            r'(\d{4})\.pdf$',  # 2023.pdf
            r'(\d{4})\.epub$',  # 2023.epub
            r'\s(\d{4})\s',  # espaço 2023 espaço
        ]
        
        for pattern in year_patterns:
            match = re.search(pattern, filename)
            if match:
                year = int(match.group(1))
                if 1900 <= year <= 2030:  # Validação básica
                    return year
        
        return None
    
    def _calculate_initial_confidence(self, filename: str) -> float:
        """Calcula confiança inicial baseada na qualidade do nome do arquivo"""
        confidence = 0.1  # Base mínima
        
        # Bônus por estrutura organizada
        if ' - ' in filename:
            confidence += 0.3
        
        # Bônus por ter ano
        if self._extract_year_from_filename(filename):
            confidence += 0.2
            
        # Bônus por extensão reconhecida
        if Path(filename).suffix.lower() in ['.pdf', '.epub', '.mobi']:
            confidence += 0.2
            
        # Penalidade por nome muito simples ou bagunçado
        if len(filename.replace('_', ' ').split()) < 2:
            confidence -= 0.1
            
        return min(max(confidence, 0.1), 0.8)  # Entre 0.1 e 0.8
    
    def run_iterative_processing(self, config: IterationConfig, 
                                file_filter: Optional[Callable] = None):
        """
        Executa processamento iterativo principal
        """
        self.logger.info(f"Iniciando processamento iterativo com config: {config}")
        
        start_time = time.time()
        iteration = 0
        best_performance = 0.0
        
        while self._should_continue(iteration, start_time, best_performance, config):
            iteration += 1
            self.current_iteration = iteration
            
            self.logger.info(f"=== ITERAÇÃO {iteration} ===")
            
            # Seleciona arquivos para esta iteração
            files_to_process = self._select_files_for_iteration(
                config.batch_size, file_filter
            )
            
            if not files_to_process:
                self.logger.info("Nenhum arquivo para processar nesta iteração")
                break
            
            # Processa lote de arquivos
            iteration_results = self._process_iteration_batch(
                files_to_process, config
            )
            
            # Calcula métricas de performance
            performance = self._calculate_iteration_performance(
                iteration_results, config.performance_metric
            )
            
            # Salva métricas
            self._save_performance_metrics(iteration, performance, 
                                         len(files_to_process))
            
            # Atualiza cache se necessário
            if iteration % config.cache_interval == 0:
                self._update_cache_from_results(iteration_results)
            
            # Verifica se atingiu performance desejada
            if performance > best_performance:
                best_performance = performance
                
            self.logger.info(
                f"Iteração {iteration}: "
                f"arquivos={len(files_to_process)}, "
                f"performance={performance:.3f}"
            )
            
            # Pausa breve para não sobrecarregar
            time.sleep(0.1)
        
        # Salva cache final
        final_stats = self._generate_final_statistics(iteration, start_time)
        self.logger.info(f"Processamento concluído: {final_stats}")
        
        return final_stats
    
    def _should_continue(self, iteration: int, start_time: float, 
                        current_performance: float, config: IterationConfig) -> bool:
        """Determina se deve continuar iterando"""
        
        # Verifica limite de iterações
        if config.max_iterations and iteration >= config.max_iterations:
            return False
            
        # Verifica limite de tempo
        if config.max_time_minutes:
            elapsed_minutes = (time.time() - start_time) / 60
            if elapsed_minutes >= config.max_time_minutes:
                return False
                
        # Verifica performance desejada
        if config.target_performance and current_performance >= config.target_performance:
            return False
            
        return True
    
    def _select_files_for_iteration(self, batch_size: int, 
                                   file_filter: Optional[Callable]) -> List[str]:
        """Seleciona arquivos para processar na iteração atual"""
        files = []
        
        # Prioriza arquivos com menor confiança (mais margem para melhoria)
        with sqlite3.connect(self.predictions_db) as conn:
            cursor = conn.execute('''
                SELECT file_path, confidence_score 
                FROM prediction_cache 
                WHERE is_downloaded = FALSE
                ORDER BY confidence_score ASC, last_updated ASC
                LIMIT ?
            ''', (batch_size,))
            
            for row in cursor.fetchall():
                file_path = row[0]
                
                if file_filter is None or file_filter(file_path):
                    files.append(file_path)
        
        return files
    
    def _process_iteration_batch(self, files: List[str], 
                                config: IterationConfig) -> Dict:
        """Processa um lote de arquivos usando algoritmos registrados"""
        results = {
            'processed_files': [],
            'improved_predictions': [],
            'consolidated_data': [],
            'errors': []
        }
        
        # Processamento paralelo
        with ThreadPoolExecutor(max_workers=config.thread_count) as executor:
            future_to_file = {
                executor.submit(self._process_single_file, file_path): file_path
                for file_path in files
            }
            
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                
                try:
                    file_result = future.result()
                    results['processed_files'].append(file_result)
                    
                    # Categoriza resultado
                    if file_result['improved']:
                        results['improved_predictions'].append(file_result)
                    
                    if file_result['confidence'] >= 0.8:  # Alta confiança
                        results['consolidated_data'].append(file_result)
                        
                except Exception as e:
                    results['errors'].append({'file': file_path, 'error': str(e)})
                    self.logger.error(f"Erro processando {file_path}: {e}")
        
        return results
    
    def _process_single_file(self, file_path: str) -> Dict:
        """Processa um arquivo individual com todos os algoritmos"""
        
        # Carrega predição atual
        current_prediction = self._load_current_prediction(file_path)
        
        # Aplica todos os algoritmos registrados
        algorithm_results = {}
        total_weight = 0
        
        for algo_name, algo_info in self.algorithms.items():
            try:
                # Executa algoritmo
                algo_result = algo_info['func'](file_path, current_prediction)
                algorithm_results[algo_name] = algo_result
                total_weight += algo_info['weight']
                
            except Exception as e:
                self.logger.error(f"Erro no algoritmo {algo_name} para {file_path}: {e}")
                continue
        
        # Combina resultados dos algoritmos (weighted average)
        combined_result = self._combine_algorithm_results(
            algorithm_results, current_prediction
        )
        
        # Verifica se houve melhoria
        old_confidence = current_prediction.get('confidence_score', 0.0)
        new_confidence = combined_result['confidence']
        improved = new_confidence > old_confidence
        
        return {
            'file_path': file_path,
            'old_confidence': old_confidence,
            'new_confidence': new_confidence,
            'improved': improved,
            'confidence': new_confidence,
            'metadata': combined_result['metadata'],
            'algorithm_results': algorithm_results
        }
    
    def _load_current_prediction(self, file_path: str) -> Dict:
        """Carrega predição atual do arquivo"""
        with sqlite3.connect(self.predictions_db) as conn:
            cursor = conn.execute('''
                SELECT predicted_metadata, confidence_score, prediction_basis
                FROM prediction_cache 
                WHERE file_path = ?
            ''', (file_path,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'metadata': json.loads(row[0]),
                    'confidence_score': row[1],
                    'prediction_basis': row[2]
                }
        
        # Se não encontrou, cria predição inicial
        return self._create_initial_prediction(file_path)
    
    def _combine_algorithm_results(self, algorithm_results: Dict, 
                                  current_prediction: Dict) -> Dict:
        """Combina resultados de múltiplos algoritmos"""
        if not algorithm_results:
            return current_prediction
        
        # Estratégia simples: média ponderada das confianças
        # e mesclagem inteligente dos metadados
        
        total_confidence = 0
        total_weight = 0
        combined_metadata = current_prediction.get('metadata', {}).copy()
        
        for algo_name, result in algorithm_results.items():
            algo_weight = self.algorithms[algo_name]['weight']
            
            if 'confidence' in result:
                total_confidence += result['confidence'] * algo_weight
                total_weight += algo_weight
            
            # Mescla metadados (prioriza resultados com maior confiança)
            if 'metadata' in result and result.get('confidence', 0) > 0.5:
                for key, value in result['metadata'].items():
                    if value and (key not in combined_metadata or not combined_metadata[key]):
                        combined_metadata[key] = value
        
        final_confidence = total_confidence / total_weight if total_weight > 0 else 0
        
        return {
            'confidence': final_confidence,
            'metadata': combined_metadata
        }
    
    def _calculate_iteration_performance(self, results: Dict, 
                                       metric_type: str) -> float:
        """Calcula métrica de performance da iteração"""
        if not results['processed_files']:
            return 0.0
        
        if metric_type == "accuracy":
            # Média das confianças finais
            confidences = [f['new_confidence'] for f in results['processed_files']]
            return sum(confidences) / len(confidences)
            
        elif metric_type == "improvement":
            # Proporção de arquivos que melhoraram
            improved_count = len(results['improved_predictions'])
            return improved_count / len(results['processed_files'])
            
        elif metric_type == "completeness":
            # Proporção de dados consolidados (alta confiança)
            consolidated_count = len(results['consolidated_data'])
            return consolidated_count / len(results['processed_files'])
        
        return 0.0
    
    def _save_performance_metrics(self, iteration: int, performance: float, 
                                 files_processed: int):
        """Salva métricas de performance no banco"""
        processing_time = time.time() - self.session_start.timestamp()
        
        with sqlite3.connect(self.performance_db) as conn:
            conn.execute('''
                INSERT INTO performance_metrics 
                (iteration, metric_name, metric_value, processing_time, files_processed)
                VALUES (?, ?, ?, ?, ?)
            ''', (iteration, 'performance', performance, processing_time, files_processed))
    
    def _update_cache_from_results(self, results: Dict):
        """Atualiza cache com os resultados da iteração"""
        
        # Atualiza predições
        with sqlite3.connect(self.predictions_db) as conn:
            for file_result in results['processed_files']:
                conn.execute('''
                    UPDATE prediction_cache 
                    SET predicted_metadata = ?, confidence_score = ?, 
                        last_updated = CURRENT_TIMESTAMP
                    WHERE file_path = ?
                ''', (
                    json.dumps(file_result['metadata']),
                    file_result['new_confidence'],
                    file_result['file_path']
                ))
        
        # Move dados consolidados para banco principal
        with sqlite3.connect(self.consolidated_db) as conn:
            for consolidated in results['consolidated_data']:
                file_hash = self._calculate_file_hash(consolidated['file_path'])
                
                conn.execute('''
                    INSERT OR REPLACE INTO consolidated_cache 
                    (file_path, file_hash, confidence_score, metadata, 
                     iteration_created, source_type)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    consolidated['file_path'],
                    file_hash,
                    consolidated['new_confidence'],
                    json.dumps(consolidated['metadata']),
                    self.current_iteration,
                    'iterative_processing'
                ))
    
    def _calculate_file_hash(self, file_path: str) -> Optional[str]:
        """Calcula hash do arquivo se ele existir localmente"""
        path_obj = Path(file_path)
        if path_obj.exists():
            with open(path_obj, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        return None
    
    def _generate_final_statistics(self, iterations: int, start_time: float) -> Dict:
        """Gera estatísticas finais do processamento"""
        elapsed_time = time.time() - start_time
        
        with sqlite3.connect(self.predictions_db) as conn:
            cursor = conn.execute('SELECT COUNT(*) FROM prediction_cache')
            total_predictions = cursor.fetchone()[0]
            
            cursor = conn.execute('''
                SELECT COUNT(*) FROM prediction_cache 
                WHERE confidence_score >= 0.8
            ''')
            high_confidence = cursor.fetchone()[0]
        
        with sqlite3.connect(self.consolidated_db) as conn:
            cursor = conn.execute('SELECT COUNT(*) FROM consolidated_cache')
            consolidated_count = cursor.fetchone()[0]
        
        return {
            'iterations_completed': iterations,
            'elapsed_time_seconds': elapsed_time,
            'total_predictions': total_predictions,
            'high_confidence_predictions': high_confidence,
            'consolidated_entries': consolidated_count,
            'average_confidence': self._calculate_average_confidence(),
            'performance_trend': self._get_performance_trend()
        }
    
    def _calculate_average_confidence(self) -> float:
        """Calcula confiança média atual"""
        with sqlite3.connect(self.predictions_db) as conn:
            cursor = conn.execute('SELECT AVG(confidence_score) FROM prediction_cache')
            result = cursor.fetchone()[0]
            return result if result else 0.0
    
    def _get_performance_trend(self) -> List[float]:
        """Obtém tendência de performance das últimas iterações"""
        with sqlite3.connect(self.performance_db) as conn:
            cursor = conn.execute('''
                SELECT metric_value FROM performance_metrics 
                WHERE metric_name = 'performance'
                ORDER BY iteration DESC LIMIT 10
            ''')
            return [row[0] for row in cursor.fetchall()]
    
    def get_predictions_for_files(self, file_patterns: List[str]) -> Dict[str, Dict]:
        """Obtém predições para arquivos específicos ou padrões"""
        predictions = {}
        
        with sqlite3.connect(self.predictions_db) as conn:
            for pattern in file_patterns:
                cursor = conn.execute('''
                    SELECT file_path, predicted_metadata, confidence_score, remote_source
                    FROM prediction_cache 
                    WHERE file_path LIKE ?
                    ORDER BY confidence_score DESC
                ''', (f'%{pattern}%',))
                
                for row in cursor.fetchall():
                    file_path, metadata_json, confidence, remote_source = row
                    predictions[file_path] = {
                        'metadata': json.loads(metadata_json),
                        'confidence': confidence,
                        'remote_source': remote_source,
                        'ready_for_download': confidence >= 0.6
                    }
        
        return predictions
    
    def export_cache_summary(self, output_file: Path = None) -> Path:
        """Exporta resumo do cache para análise"""
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.cache_dir / f"cache_summary_{timestamp}.json"
        
        summary = {
            'generation_time': datetime.now().isoformat(),
            'statistics': self._generate_final_statistics(
                self.current_iteration, self.session_start.timestamp()
            ),
            'top_predictions': self._get_top_predictions(50),
            'algorithm_performance': self._get_algorithm_performance_summary(),
            'cache_health': self._analyze_cache_health()
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Resumo do cache exportado para: {output_file}")
        return output_file
    
    def _get_top_predictions(self, limit: int) -> List[Dict]:
        """Obtém as melhores predições"""
        with sqlite3.connect(self.predictions_db) as conn:
            cursor = conn.execute('''
                SELECT file_path, predicted_metadata, confidence_score
                FROM prediction_cache 
                ORDER BY confidence_score DESC LIMIT ?
            ''', (limit,))
            
            return [
                {
                    'file_path': row[0],
                    'metadata': json.loads(row[1]),
                    'confidence': row[2]
                }
                for row in cursor.fetchall()
            ]
    
    def _get_algorithm_performance_summary(self) -> Dict:
        """Resume performance dos algoritmos"""
        summary = {}
        for algo_name, algo_info in self.algorithms.items():
            summary[algo_name] = {
                'weight': algo_info['weight'],
                'performance_history': algo_info['performance_history'][-10:],  # Últimas 10
                'average_performance': (
                    sum(algo_info['performance_history']) / len(algo_info['performance_history'])
                    if algo_info['performance_history'] else 0.0
                )
            }
        return summary
    
    def _analyze_cache_health(self) -> Dict:
        """Analisa saúde geral do cache"""
        health = {}
        
        # Distribuição de confiança
        with sqlite3.connect(self.predictions_db) as conn:
            cursor = conn.execute('''
                SELECT 
                    COUNT(CASE WHEN confidence_score < 0.3 THEN 1 END) as low,
                    COUNT(CASE WHEN confidence_score BETWEEN 0.3 AND 0.7 THEN 1 END) as medium,
                    COUNT(CASE WHEN confidence_score > 0.7 THEN 1 END) as high
                FROM prediction_cache
            ''')
            
            row = cursor.fetchone()
            health['confidence_distribution'] = {
                'low': row[0],
                'medium': row[1], 
                'high': row[2]
            }
        
        return health


# Função de conveniência para criar e configurar o sistema
def create_iterative_cache_system(cache_dir: Path = None) -> IterativeCacheSystem:
    """Cria e configura um sistema de cache iterativo"""
    system = IterativeCacheSystem(cache_dir)
    
    # Registra algoritmos básicos (placeholder - serão implementados)
    system.register_algorithm('filename_analyzer', dummy_filename_algorithm, weight=1.0)
    system.register_algorithm('metadata_enhancer', dummy_metadata_algorithm, weight=1.5)
    
    return system


# Algoritmos de exemplo (placeholder)
def dummy_filename_algorithm(file_path: str, current_prediction: Dict) -> Dict:
    """Algoritmo de exemplo para análise de nome de arquivo"""
    confidence_boost = 0.1 if ' - ' in Path(file_path).name else 0.05
    
    return {
        'confidence': min(current_prediction.get('confidence_score', 0.1) + confidence_boost, 1.0),
        'metadata': current_prediction.get('metadata', {}),
        'improvements': ['filename_structure_analysis']
    }

def dummy_metadata_algorithm(file_path: str, current_prediction: Dict) -> Dict:
    """Algoritmo de exemplo para enriquecimento de metadados"""
    metadata = current_prediction.get('metadata', {}).copy()
    
    # Simula enriquecimento de metadados
    if not metadata.get('genre') and '.pdf' in file_path.lower():
        metadata['genre'] = 'technical_book'
    
    return {
        'confidence': min(current_prediction.get('confidence_score', 0.1) + 0.15, 1.0),
        'metadata': metadata,
        'improvements': ['metadata_enrichment']
    }