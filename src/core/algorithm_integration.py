"""
Integração com Algoritmos Existentes para Cache Iterativo
========================================================

Este módulo integra os algoritmos existentes do projeto com o sistema
de cache iterativo, permitindo que sejam usados para refinar dados
progressivamente através de múltiplas iterações.
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging
import json

# Adiciona diretórios ao path para imports
sys.path.append(str(Path(__file__).parent.parent))

try:
    # Imports dos algoritmos existentes
    from advanced_algorithm_comparison import (
        AlgorithmComparator,
        run_comparative_analysis
    )
    from algorithms_v3 import MetadataExtractor
    from auto_rename_system import AutoRenameSystem
    from performance_analyzer import PerformanceAnalyzer
    from metadata_extractor import extract_metadata_from_file
    from metadata_enricher import enrich_metadata
except ImportError as e:
    logging.warning(f"Alguns módulos não puderam ser importados: {e}")
    # Continuará com algoritmos básicos

class AlgorithmIntegrator:
    """Integra algoritmos existentes com o sistema de cache iterativo"""
    
    def __init__(self):
        self.logger = logging.getLogger('algorithm_integrator')
        self.available_algorithms = self._discover_algorithms()
        
    def _discover_algorithms(self) -> Dict[str, Dict]:
        """Descobre quais algoritmos estão disponíveis"""
        algorithms = {}
        
        # Algoritmo de comparação avançada
        try:
            from advanced_algorithm_comparison import AlgorithmComparator
            algorithms['advanced_comparison'] = {
                'name': 'Comparação Avançada de Algoritmos',
                'function': self.advanced_comparison_adapter,
                'weight': 2.0,
                'confidence_boost': 0.3,
                'description': 'Usa múltiplos algoritmos para extrair metadados'
            }
        except ImportError:
            pass
        
        # Algoritmo v3
        try:
            from algorithms_v3 import MetadataExtractor
            algorithms['metadata_v3'] = {
                'name': 'Extrator de Metadados v3',
                'function': self.metadata_v3_adapter,
                'weight': 1.8,
                'confidence_boost': 0.25,
                'description': 'Algoritmo de extração de metadados versão 3'
            }
        except ImportError:
            pass
        
        # Sistema de renomeação automática
        try:
            from auto_rename_system import AutoRenameSystem
            algorithms['auto_rename'] = {
                'name': 'Sistema de Renomeação Automática',
                'function': self.auto_rename_adapter,
                'weight': 1.5,
                'confidence_boost': 0.2,
                'description': 'Análise e sugestão de renomeação'
            }
        except ImportError:
            pass
        
        # Extrator básico de metadados
        try:
            from metadata_extractor import extract_metadata_from_file
            algorithms['basic_extractor'] = {
                'name': 'Extrator Básico de Metadados',
                'function': self.basic_extractor_adapter,
                'weight': 1.0,
                'confidence_boost': 0.15,
                'description': 'Extração básica de metadados de arquivos'
            }
        except ImportError:
            pass
        
        # Enriquecedor de metadados
        try:
            from metadata_enricher import enrich_metadata
            algorithms['metadata_enricher'] = {
                'name': 'Enriquecedor de Metadados',
                'function': self.metadata_enricher_adapter,
                'weight': 1.3,
                'confidence_boost': 0.18,
                'description': 'Enriquece metadados com dados externos'
            }
        except ImportError:
            pass
        
        # Sempre disponível: análise de nome de arquivo
        algorithms['filename_analyzer'] = {
            'name': 'Analisador de Nome de Arquivo',
            'function': self.filename_analyzer_adapter,
            'weight': 0.8,
            'confidence_boost': 0.1,
            'description': 'Análise inteligente do nome do arquivo'
        }
        
        self.logger.info(f"Algoritmos descobertos: {list(algorithms.keys())}")
        return algorithms
    
    def get_available_algorithms(self) -> Dict[str, Dict]:
        """Retorna algoritmos disponíveis"""
        return self.available_algorithms
    
    def advanced_comparison_adapter(self, file_path: str, current_prediction: Dict) -> Dict:
        """Adapter para o algoritmo de comparação avançada"""
        try:
            # Verifica se arquivo existe localmente
            if not Path(file_path).exists():
                return self._create_prediction_result(
                    current_prediction, 0.05, 
                    {'error': 'file_not_found'}, 
                    ['file_not_accessible']
                )
            
            # Executa algoritmo de comparação
            comparator = AlgorithmComparator()
            results = comparator.analyze_file(file_path)
            
            # Converte resultados para formato padrão
            metadata = self._extract_metadata_from_comparison(results)
            confidence_boost = 0.3 if results.get('consensus_found', False) else 0.15
            
            return self._create_prediction_result(
                current_prediction, confidence_boost, metadata,
                ['advanced_comparison', 'multi_algorithm_consensus']
            )
            
        except Exception as e:
            self.logger.error(f"Erro no advanced_comparison para {file_path}: {e}")
            return self._create_error_result(current_prediction, str(e))
    
    def metadata_v3_adapter(self, file_path: str, current_prediction: Dict) -> Dict:
        """Adapter para o algoritmo de metadados v3"""
        try:
            if not Path(file_path).exists():
                return self._create_prediction_result(
                    current_prediction, 0.05,
                    {'error': 'file_not_found'}, 
                    ['file_not_accessible']
                )
            
            # Executa extrator v3
            extractor = MetadataExtractor()
            metadata = extractor.extract(file_path)
            
            # Calcula boost de confiança baseado na qualidade dos dados
            confidence_boost = self._calculate_v3_confidence_boost(metadata)
            
            return self._create_prediction_result(
                current_prediction, confidence_boost, metadata,
                ['metadata_v3_extraction', 'file_analysis']
            )
            
        except Exception as e:
            self.logger.error(f"Erro no metadata_v3 para {file_path}: {e}")
            return self._create_error_result(current_prediction, str(e))
    
    def auto_rename_adapter(self, file_path: str, current_prediction: Dict) -> Dict:
        """Adapter para o sistema de renomeação automática"""
        try:
            # Sistema de renomeação pode trabalhar com nomes de arquivo mesmo sem o arquivo
            rename_system = AutoRenameSystem()
            
            # Analisa nome atual e sugere melhorias
            analysis = rename_system.analyze_filename(file_path)
            
            # Extrai metadados da análise
            metadata = {
                'suggested_title': analysis.get('title', ''),
                'suggested_author': analysis.get('author', ''),
                'suggested_year': analysis.get('year', ''),
                'filename_quality_score': analysis.get('quality_score', 0.0),
                'rename_confidence': analysis.get('confidence', 0.0)
            }
            
            confidence_boost = min(analysis.get('confidence', 0.1), 0.2)
            
            return self._create_prediction_result(
                current_prediction, confidence_boost, metadata,
                ['auto_rename_analysis', 'filename_intelligence']
            )
            
        except Exception as e:
            self.logger.error(f"Erro no auto_rename para {file_path}: {e}")
            return self._create_error_result(current_prediction, str(e))
    
    def basic_extractor_adapter(self, file_path: str, current_prediction: Dict) -> Dict:
        """Adapter para o extrator básico de metadados"""
        try:
            if not Path(file_path).exists():
                return self._create_prediction_result(
                    current_prediction, 0.05,
                    {'error': 'file_not_found'}, 
                    ['file_not_accessible']
                )
            
            # Executa extração básica
            metadata = extract_metadata_from_file(file_path)
            
            # Calcula boost baseado na quantidade de dados extraídos
            data_quality = sum(1 for v in metadata.values() if v and str(v).strip())
            confidence_boost = min(data_quality * 0.03, 0.15)
            
            return self._create_prediction_result(
                current_prediction, confidence_boost, metadata,
                ['basic_metadata_extraction', 'file_content_analysis']
            )
            
        except Exception as e:
            self.logger.error(f"Erro no basic_extractor para {file_path}: {e}")
            return self._create_error_result(current_prediction, str(e))
    
    def metadata_enricher_adapter(self, file_path: str, current_prediction: Dict) -> Dict:
        """Adapter para o enriquecedor de metadados"""
        try:
            # Pega metadados atuais para enriquecer
            current_metadata = current_prediction.get('metadata', {})
            
            # Executa enriquecimento
            enriched_metadata = enrich_metadata(current_metadata, file_path)
            
            # Verifica quantos campos foram enriquecidos
            new_fields = 0
            for key, value in enriched_metadata.items():
                if key not in current_metadata and value:
                    new_fields += 1
            
            confidence_boost = min(new_fields * 0.04, 0.18)
            
            return self._create_prediction_result(
                current_prediction, confidence_boost, enriched_metadata,
                ['metadata_enrichment', 'external_data_integration']
            )
            
        except Exception as e:
            self.logger.error(f"Erro no metadata_enricher para {file_path}: {e}")
            return self._create_error_result(current_prediction, str(e))
    
    def filename_analyzer_adapter(self, file_path: str, current_prediction: Dict) -> Dict:
        """Adapter para análise avançada de nome de arquivo"""
        try:
            filename = Path(file_path).name
            
            # Análise avançada do nome do arquivo
            analysis = self._advanced_filename_analysis(filename)
            
            # Mescla com metadados atuais
            current_metadata = current_prediction.get('metadata', {})
            enhanced_metadata = {**current_metadata, **analysis['metadata']}
            
            return self._create_prediction_result(
                current_prediction, analysis['confidence_boost'], enhanced_metadata,
                ['advanced_filename_analysis', 'pattern_recognition']
            )
            
        except Exception as e:
            self.logger.error(f"Erro no filename_analyzer para {file_path}: {e}")
            return self._create_error_result(current_prediction, str(e))
    
    def _advanced_filename_analysis(self, filename: str) -> Dict:
        """Análise avançada de nome de arquivo"""
        import re
        
        metadata = {}
        confidence_boost = 0.05
        
        # Remove extensão para análise
        name_without_ext = Path(filename).stem
        
        # Padrões de análise mais sofisticados
        patterns = {
            'author_title_year': r'^([^-]+)\s*-\s*([^(]+)\s*\((\d{4})\)',
            'title_author_year': r'^([^-]+)\s*-\s*([^(]+)\s*\((\d{4})\)',
            'author_title': r'^([^-]+)\s*-\s*(.+)$',
            'title_only': r'^([^(]+)(?:\s*\((\d{4})\))?',
        }
        
        for pattern_name, pattern in patterns.items():
            match = re.match(pattern, name_without_ext.strip())
            if match:
                if pattern_name == 'author_title_year':
                    metadata.update({
                        'extracted_author': match.group(1).strip(),
                        'extracted_title': match.group(2).strip(),
                        'extracted_year': int(match.group(3))
                    })
                    confidence_boost = 0.15
                    break
                elif pattern_name == 'author_title':
                    metadata.update({
                        'extracted_author': match.group(1).strip(),
                        'extracted_title': match.group(2).strip()
                    })
                    confidence_boost = 0.12
                    break
                elif pattern_name == 'title_only':
                    metadata['extracted_title'] = match.group(1).strip()
                    if match.group(2):
                        metadata['extracted_year'] = int(match.group(2))
                        confidence_boost = 0.1
                    else:
                        confidence_boost = 0.08
                    break
        
        # Análise de qualidade do nome
        quality_indicators = [
            ' - ' in filename,  # Separador estruturado
            bool(re.search(r'\d{4}', filename)),  # Tem ano
            len(name_without_ext.split()) >= 3,  # Múltiplas palavras
            not bool(re.search(r'[_]{2,}|[.]{2,}', filename)),  # Não tem caracteres repetidos
            filename[0].isupper()  # Começa com maiúscula
        ]
        
        quality_score = sum(quality_indicators) / len(quality_indicators)
        metadata['filename_quality_score'] = quality_score
        
        # Ajusta confiança baseado na qualidade
        confidence_boost *= (0.5 + quality_score * 0.5)
        
        return {
            'metadata': metadata,
            'confidence_boost': confidence_boost
        }
    
    def _extract_metadata_from_comparison(self, comparison_results: Dict) -> Dict:
        """Extrai metadados dos resultados da comparação de algoritmos"""
        metadata = {}
        
        if 'consensus_metadata' in comparison_results:
            metadata.update(comparison_results['consensus_metadata'])
        
        if 'best_algorithm_result' in comparison_results:
            metadata.update(comparison_results['best_algorithm_result'])
        
        # Adiciona informações sobre a análise
        metadata['comparison_score'] = comparison_results.get('overall_score', 0.0)
        metadata['algorithms_used'] = comparison_results.get('algorithms_used', [])
        metadata['consensus_level'] = comparison_results.get('consensus_level', 0.0)
        
        return metadata
    
    def _calculate_v3_confidence_boost(self, metadata: Dict) -> float:
        """Calcula boost de confiança baseado na qualidade dos metadados v3"""
        confidence_boost = 0.1
        
        # Campos importantes que aumentam confiança
        important_fields = ['title', 'author', 'year', 'genre', 'language']
        filled_important = sum(1 for field in important_fields if metadata.get(field))
        
        confidence_boost += (filled_important / len(important_fields)) * 0.15
        
        # Bonus por qualidade dos dados
        if metadata.get('extraction_confidence', 0) > 0.8:
            confidence_boost += 0.05
        
        return min(confidence_boost, 0.25)
    
    def _create_prediction_result(self, current_prediction: Dict, confidence_boost: float,
                                 new_metadata: Dict, improvements: List[str]) -> Dict:
        """Cria resultado padrão de predição"""
        current_confidence = current_prediction.get('confidence_score', 0.1)
        new_confidence = min(current_confidence + confidence_boost, 1.0)
        
        # Mescla metadados, priorizando novos dados não vazios
        current_metadata = current_prediction.get('metadata', {})
        merged_metadata = current_metadata.copy()
        
        for key, value in new_metadata.items():
            if value and (key not in merged_metadata or not merged_metadata[key]):
                merged_metadata[key] = value
        
        return {
            'confidence': new_confidence,
            'metadata': merged_metadata,
            'improvements': improvements,
            'algorithm_boost': confidence_boost
        }
    
    def _create_error_result(self, current_prediction: Dict, error_msg: str) -> Dict:
        """Cria resultado de erro"""
        return {
            'confidence': current_prediction.get('confidence_score', 0.1),
            'metadata': current_prediction.get('metadata', {}),
            'improvements': ['error_handled'],
            'error': error_msg,
            'algorithm_boost': 0.0
        }


def register_algorithms_with_cache_system(cache_system):
    """Registra todos os algoritmos disponíveis com o sistema de cache"""
    integrator = AlgorithmIntegrator()
    algorithms = integrator.get_available_algorithms()
    
    registered_count = 0
    for algo_name, algo_info in algorithms.items():
        try:
            cache_system.register_algorithm(
                name=algo_name,
                algorithm_func=algo_info['function'],
                weight=algo_info['weight']
            )
            registered_count += 1
            
        except Exception as e:
            logging.error(f"Erro ao registrar algoritmo {algo_name}: {e}")
    
    logging.info(f"Registrados {registered_count} algoritmos com o sistema de cache")
    return registered_count


# Função de conveniência para criar sistema completo
def create_complete_iterative_system(cache_dir: Path = None):
    """Cria sistema de cache iterativo com todos os algoritmos integrados"""
    from iterative_cache_system import IterativeCacheSystem
    
    # Cria sistema base
    system = IterativeCacheSystem(cache_dir)
    
    # Registra algoritmos
    register_algorithms_with_cache_system(system)
    
    return system