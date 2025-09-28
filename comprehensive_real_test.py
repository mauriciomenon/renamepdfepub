#!/usr/bin/env python3
"""
Sistema de Teste Rigoroso com Dados Reais
========================================

Testa TODOS os algoritmos com dados reais da pasta books/
Validacao completa de precisao, extração de metadados reais.
"""

import json
import time
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple
import logging
from dataclasses import dataclass, asdict
import unicodedata

# Importa algoritmos existentes
from final_v3_complete_test import V3CompleteSystem
from rigorous_validation import DataValidator, ValidationResult

@dataclass
class AlgorithmResult:
    """Resultado de um algoritmo para um livro"""
    filename: str
    algorithm_name: str
    title: str
    author: str
    publisher: str
    year: str
    isbn10: str
    isbn13: str
    confidence: float
    execution_time: float
    validation_result: ValidationResult

@dataclass 
class ComparisonResult:
    """Resultado da comparacao entre algoritmos"""
    filename: str
    ground_truth: Dict[str, str]
    algorithm_results: List[AlgorithmResult]
    best_algorithm: str
    accuracy_scores: Dict[str, float]

class RealDataExtractor:
    """Extrai dados reais dos nomes de arquivos"""
    
    def __init__(self):
        self.setup_logging()
        
        # Padroes para extrair informacoes dos nomes
        self.author_patterns = [
            r'^([A-Za-z][A-Za-z\s\.]+?)\s+-\s+',  # "Autor - Titulo"
            r'^([A-Za-z][^-]+)\s+-\s+',  # Variacao mais flexivel
        ]
        
        self.year_pattern = r'\((\d{4})\)'
        
        # Publishers conhecidos nos nomes de arquivos
        self.publisher_indicators = {
            'manning': 'Manning Publications',
            'packt': 'Packt Publishing',
            'oreilly': "O'Reilly Media",
            'nostarch': 'No Starch Press',
            'addison': 'Addison-Wesley',
            'wiley': 'Wiley',
            'mit': 'MIT Press',
            'apress': 'Apress',
            'pearson': 'Pearson'
        }

    def setup_logging(self):
        """Configura logging"""
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def extract_ground_truth(self, filename: str) -> Dict[str, str]:
        """Extrai verdade fundamental do nome do arquivo"""
        ground_truth = {
            'title': '',
            'author': '',
            'publisher': '',
            'year': '',
            'isbn10': '',
            'isbn13': ''
        }
        
        # Remove extensao
        name_clean = Path(filename).stem
        
        # Extrai autor (primeira parte antes do " - ")
        for pattern in self.author_patterns:
            match = re.search(pattern, name_clean)
            if match:
                author = match.group(1).strip()
                if self.is_valid_author(author):
                    ground_truth['author'] = author
                    # Remove autor do nome para extrair titulo
                    name_clean = name_clean[len(match.group(0)):].strip()
                    break
        
        # Extrai ano
        year_match = re.search(self.year_pattern, name_clean)
        if year_match:
            ground_truth['year'] = year_match.group(1)
            # Remove ano do nome
            name_clean = re.sub(self.year_pattern, '', name_clean).strip()
        
        # Extrai publisher se estiver no nome
        name_lower = name_clean.lower()
        for indicator, publisher in self.publisher_indicators.items():
            if indicator in name_lower:
                ground_truth['publisher'] = publisher
                break
        
        # O que sobrou e o titulo (remove caracteres extras)
        title = name_clean.strip()
        title = re.sub(r'\s*\([^)]*\)\s*$', '', title)  # Remove parenteses finais
        title = re.sub(r'\s*-\s*$', '', title)  # Remove hifen final
        title = title.strip()
        
        if title and len(title) > 2:
            ground_truth['title'] = title
        
        return ground_truth

    def is_valid_author(self, author: str) -> bool:
        """Verifica se string parece ser um autor valido"""
        if not author or len(author) < 3:
            return False
        
        # Nao deve comecar com numeros
        if author[0].isdigit():
            return False
        
        # Deve ter pelo menos uma letra
        if not re.search(r'[a-zA-Z]', author):
            return False
        
        # Nao deve ter palavras suspeitas
        suspicious_words = ['www', 'com', 'pdf', 'epub', 'book', 'edition']
        for word in suspicious_words:
            if word.lower() in author.lower():
                return False
        
        return True

class AlgorithmTester:
    """Testa algoritmos com dados reais"""
    
    def __init__(self):
        self.setup_logging()
        self.validator = DataValidator()
        self.extractor = RealDataExtractor()
        
        # Carrega dados dos livros
        self.books_data = self.load_books_data()
        
        # Inicializa algoritmos
        if self.books_data:
            self.v3_system = V3CompleteSystem(self.books_data)
        else:
            self.v3_system = None
            self.logger.warning("Nao foi possivel carregar dados dos livros")

    def setup_logging(self):
        """Configura logging detalhado"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('real_data_testing.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def load_books_data(self) -> List[Dict[str, Any]]:
        """Carrega dados dos livros da pasta books/"""
        books_dir = Path("books")
        if not books_dir.exists():
            self.logger.error("Pasta books/ nao encontrada!")
            return []
        
        books_data = []
        
        for file_path in books_dir.iterdir():
            if file_path.suffix.lower() in ['.pdf', '.epub', '.mobi'] and not file_path.name.startswith('.'):
                try:
                    # Usa extrator existente se disponivel
                    from final_v3_test import FinalV3MetadataExtractor
                    extractor = FinalV3MetadataExtractor()
                    metadata = extractor.extract_metadata(file_path.name)
                    books_data.append(metadata)
                except Exception as e:
                    # Fallback: dados basicos do nome do arquivo
                    metadata = {
                        'filename': file_path.name,
                        'title': file_path.stem,
                        'author': '',
                        'publisher': '',
                        'year': '',
                        'category': 'Programming',
                        'confidence': 0.5
                    }
                    books_data.append(metadata)
        
        self.logger.info(f"Carregados {len(books_data)} livros")
        return books_data

    def test_v3_enhanced_fuzzy(self, filename: str) -> AlgorithmResult:
        """Testa algoritmo V3 Enhanced Fuzzy"""
        start_time = time.time()
        
        if not self.v3_system:
            return self.create_empty_result(filename, "V3 Enhanced Fuzzy", start_time)
        
        try:
            # Extrai termos de busca do nome do arquivo
            search_query = self.filename_to_query(filename)
            
            # Executa busca
            results = self.v3_system.v3_enhanced_fuzzy_search(search_query, limit=1)
            
            if results:
                best_result = results[0]
                extracted_data = {
                    'title': best_result.get('title', ''),
                    'author': best_result.get('author', ''),
                    'publisher': best_result.get('publisher', ''),
                    'year': best_result.get('year', ''),
                    'isbn10': '',
                    'isbn13': '',
                    'confidence': best_result.get('similarity_score', 0.0)
                }
            else:
                extracted_data = self.create_empty_data()
            
            validation_result = self.validator.validate_book_data(extracted_data)
            
            return AlgorithmResult(
                filename=filename,
                algorithm_name="V3 Enhanced Fuzzy",
                title=extracted_data['title'],
                author=extracted_data['author'],
                publisher=extracted_data['publisher'],
                year=extracted_data['year'],
                isbn10=extracted_data['isbn10'],
                isbn13=extracted_data['isbn13'],
                confidence=extracted_data['confidence'],
                execution_time=time.time() - start_time,
                validation_result=validation_result
            )
            
        except Exception as e:
            self.logger.error(f"Erro no V3 Enhanced Fuzzy para {filename}: {e}")
            return self.create_empty_result(filename, "V3 Enhanced Fuzzy", start_time)

    def test_v3_semantic_search(self, filename: str) -> AlgorithmResult:
        """Testa algoritmo V3 Semantic Search"""
        start_time = time.time()
        
        if not self.v3_system:
            return self.create_empty_result(filename, "V3 Semantic Search", start_time)
        
        try:
            search_query = self.filename_to_query(filename)
            results = self.v3_system.v3_super_semantic_search(search_query, limit=1)
            
            if results:
                best_result = results[0]
                extracted_data = {
                    'title': best_result.get('title', ''),
                    'author': best_result.get('author', ''),
                    'publisher': best_result.get('publisher', ''),
                    'year': best_result.get('year', ''),
                    'isbn10': '',
                    'isbn13': '',
                    'confidence': best_result.get('similarity_score', 0.0)
                }
            else:
                extracted_data = self.create_empty_data()
            
            validation_result = self.validator.validate_book_data(extracted_data)
            
            return AlgorithmResult(
                filename=filename,
                algorithm_name="V3 Semantic Search",
                title=extracted_data['title'],
                author=extracted_data['author'],
                publisher=extracted_data['publisher'],
                year=extracted_data['year'],
                isbn10=extracted_data['isbn10'],
                isbn13=extracted_data['isbn13'],
                confidence=extracted_data['confidence'],
                execution_time=time.time() - start_time,
                validation_result=validation_result
            )
            
        except Exception as e:
            self.logger.error(f"Erro no V3 Semantic Search para {filename}: {e}")
            return self.create_empty_result(filename, "V3 Semantic Search", start_time)

    def test_v3_ultimate_orchestrator(self, filename: str) -> AlgorithmResult:
        """Testa algoritmo V3 Ultimate Orchestrator"""
        start_time = time.time()
        
        if not self.v3_system:
            return self.create_empty_result(filename, "V3 Ultimate Orchestrator", start_time)
        
        try:
            search_query = self.filename_to_query(filename)
            results = self.v3_system.v3_ultimate_orchestrator(search_query, limit=1)
            
            if results:
                best_result = results[0]
                extracted_data = {
                    'title': best_result.get('title', ''),
                    'author': best_result.get('author', ''),
                    'publisher': best_result.get('publisher', ''),
                    'year': best_result.get('year', ''),
                    'isbn10': '',
                    'isbn13': '',
                    'confidence': best_result.get('similarity_score', 0.0)
                }
            else:
                extracted_data = self.create_empty_data()
            
            validation_result = self.validator.validate_book_data(extracted_data)
            
            return AlgorithmResult(
                filename=filename,
                algorithm_name="V3 Ultimate Orchestrator",
                title=extracted_data['title'],
                author=extracted_data['author'],
                publisher=extracted_data['publisher'],
                year=extracted_data['year'],
                isbn10=extracted_data['isbn10'],
                isbn13=extracted_data['isbn13'],
                confidence=extracted_data['confidence'],
                execution_time=time.time() - start_time,
                validation_result=validation_result
            )
            
        except Exception as e:
            self.logger.error(f"Erro no V3 Ultimate Orchestrator para {filename}: {e}")
            return self.create_empty_result(filename, "V3 Ultimate Orchestrator", start_time)

    def filename_to_query(self, filename: str) -> str:
        """Converte nome de arquivo em query de busca"""
        # Remove extensao
        query = Path(filename).stem
        
        # Remove padroes comuns
        query = re.sub(r'\s*\([^)]*\)\s*', ' ', query)  # Remove parenteses
        query = re.sub(r'\s*-\s*\d+\s*$', '', query)  # Remove numeros finais
        query = re.sub(r'[_]+', ' ', query)  # Underscores para espacos
        query = ' '.join(query.split())  # Normaliza espacos
        
        return query

    def create_empty_data(self) -> Dict[str, Any]:
        """Cria dados vazios"""
        return {
            'title': '',
            'author': '',
            'publisher': '',
            'year': '',
            'isbn10': '',
            'isbn13': '',
            'confidence': 0.0
        }

    def create_empty_result(self, filename: str, algorithm_name: str, start_time: float) -> AlgorithmResult:
        """Cria resultado vazio"""
        validation_result = ValidationResult(
            title='', author='', publisher='', year='', isbn10='', isbn13='',
            confidence=0.0, validation_score=0.0, errors=['Algorithm failed'], warnings=[]
        )
        
        return AlgorithmResult(
            filename=filename,
            algorithm_name=algorithm_name,
            title='',
            author='',
            publisher='',
            year='',
            isbn10='',
            isbn13='',
            confidence=0.0,
            execution_time=time.time() - start_time,
            validation_result=validation_result
        )

    def calculate_accuracy_score(self, extracted: AlgorithmResult, ground_truth: Dict[str, str]) -> float:
        """Calcula score de precisao comparando com ground truth"""
        score = 0.0
        
        # Titulo (peso 40%)
        if ground_truth['title'] and extracted.title:
            title_similarity = self.calculate_text_similarity(extracted.title, ground_truth['title'])
            score += title_similarity * 0.4
        
        # Autor (peso 30%)
        if ground_truth['author'] and extracted.author:
            author_similarity = self.calculate_text_similarity(extracted.author, ground_truth['author'])
            score += author_similarity * 0.3
        
        # Publisher (peso 20%)
        if ground_truth['publisher'] and extracted.publisher:
            publisher_similarity = self.calculate_text_similarity(extracted.publisher, ground_truth['publisher'])
            score += publisher_similarity * 0.2
        
        # Ano (peso 10%)
        if ground_truth['year'] and extracted.year:
            year_match = 1.0 if str(extracted.year) == str(ground_truth['year']) else 0.0
            score += year_match * 0.1
        
        return min(score, 1.0)

    def calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calcula similaridade entre textos"""
        if not text1 or not text2:
            return 0.0
        
        # Normaliza textos
        t1 = self.normalize_text(text1)
        t2 = self.normalize_text(text2)
        
        # Exact match
        if t1 == t2:
            return 1.0
        
        # Containment
        if t1 in t2 or t2 in t1:
            return 0.8
        
        # Word overlap
        words1 = set(t1.split())
        words2 = set(t2.split())
        
        if not words1 or not words2:
            return 0.0
        
        overlap = len(words1.intersection(words2))
        total = len(words1.union(words2))
        
        return overlap / total if total > 0 else 0.0

    def normalize_text(self, text: str) -> str:
        """Normaliza texto para comparacao"""
        if not text:
            return ""
        
        # Remove acentos
        text = unicodedata.normalize('NFD', text)
        text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
        
        # Lowercase e remove caracteres especiais
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        text = ' '.join(text.split())
        
        return text

    def run_comprehensive_test(self, max_books: int = 50) -> Dict[str, Any]:
        """Executa teste abrangente com dados reais"""
        self.logger.info(f"Iniciando teste abrangente com ate {max_books} livros")
        
        # Pega sample de livros
        books_dir = Path("books")
        book_files = [f for f in books_dir.iterdir() 
                     if f.suffix.lower() in ['.pdf', '.epub', '.mobi'] 
                     and not f.name.startswith('.')]
        
        if len(book_files) > max_books:
            book_files = book_files[:max_books]
        
        self.logger.info(f"Testando {len(book_files)} livros")
        
        # Estrutura de resultados
        test_results = {
            'test_info': {
                'total_books': len(book_files),
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'algorithms_tested': ['V3 Enhanced Fuzzy', 'V3 Semantic Search', 'V3 Ultimate Orchestrator']
            },
            'detailed_results': [],
            'algorithm_summary': {},
            'comparison_table': []
        }
        
        # Testa cada livro
        for i, book_file in enumerate(book_files, 1):
            self.logger.info(f"Testando livro {i}/{len(book_files)}: {book_file.name}")
            
            # Extrai ground truth
            ground_truth = self.extractor.extract_ground_truth(book_file.name)
            
            # Testa cada algoritmo
            algorithm_results = []
            
            # V3 Enhanced Fuzzy
            fuzzy_result = self.test_v3_enhanced_fuzzy(book_file.name)
            algorithm_results.append(fuzzy_result)
            
            # V3 Semantic Search
            semantic_result = self.test_v3_semantic_search(book_file.name)
            algorithm_results.append(semantic_result)
            
            # V3 Ultimate Orchestrator
            orchestrator_result = self.test_v3_ultimate_orchestrator(book_file.name)
            algorithm_results.append(orchestrator_result)
            
            # Calcula accuracy scores
            accuracy_scores = {}
            for result in algorithm_results:
                accuracy_scores[result.algorithm_name] = self.calculate_accuracy_score(result, ground_truth)
            
            # Determina melhor algoritmo
            best_algorithm = max(accuracy_scores, key=accuracy_scores.get)
            
            # Cria resultado da comparacao
            comparison_result = ComparisonResult(
                filename=book_file.name,
                ground_truth=ground_truth,
                algorithm_results=algorithm_results,
                best_algorithm=best_algorithm,
                accuracy_scores=accuracy_scores
            )
            
            test_results['detailed_results'].append(comparison_result)
            
            # Adiciona linha na tabela de comparacao
            comparison_row = {
                'filename': book_file.name[:50],
                'ground_truth_title': ground_truth.get('title', '')[:30],
                'ground_truth_author': ground_truth.get('author', '')[:20],
            }
            
            for result in algorithm_results:
                prefix = result.algorithm_name.replace(' ', '_').lower()
                comparison_row[f'{prefix}_title'] = result.title[:30]
                comparison_row[f'{prefix}_author'] = result.author[:20]
                comparison_row[f'{prefix}_accuracy'] = accuracy_scores[result.algorithm_name]
                comparison_row[f'{prefix}_validation'] = result.validation_result.validation_score
            
            comparison_row['best_algorithm'] = best_algorithm
            test_results['comparison_table'].append(comparison_row)
        
        # Calcula sumarios por algoritmo
        for algorithm_name in test_results['test_info']['algorithms_tested']:
            algorithm_accuracies = []
            algorithm_validations = []
            algorithm_times = []
            
            for result in test_results['detailed_results']:
                for alg_result in result.algorithm_results:
                    if alg_result.algorithm_name == algorithm_name:
                        algorithm_accuracies.append(result.accuracy_scores[algorithm_name])
                        algorithm_validations.append(alg_result.validation_result.validation_score)
                        algorithm_times.append(alg_result.execution_time)
            
            if algorithm_accuracies:
                test_results['algorithm_summary'][algorithm_name] = {
                    'average_accuracy': sum(algorithm_accuracies) / len(algorithm_accuracies),
                    'average_validation': sum(algorithm_validations) / len(algorithm_validations),
                    'average_time': sum(algorithm_times) / len(algorithm_times),
                    'best_results': sum(1 for r in test_results['detailed_results'] if r.best_algorithm == algorithm_name),
                    'success_rate': sum(1 for acc in algorithm_accuracies if acc > 0.5) / len(algorithm_accuracies)
                }
        
        return test_results

def print_results_table(test_results: Dict[str, Any]):
    """Imprime tabela de resultados"""
    print("\nTABELA DE COMPARACAO DE ALGORITMOS")
    print("=" * 120)
    
    # Header
    print(f"{'Arquivo':<25} {'Titulo Real':<20} {'Autor Real':<15} {'Fuzzy Acc':<10} {'Sem Acc':<10} {'Orch Acc':<10} {'Melhor':<15}")
    print("-" * 120)
    
    # Dados
    for row in test_results['comparison_table'][:20]:  # Primeiros 20
        print(f"{row['filename']:<25} "
              f"{row['ground_truth_title']:<20} "
              f"{row['ground_truth_author']:<15} "
              f"{row['v3_enhanced_fuzzy_accuracy']:<10.3f} "
              f"{row['v3_semantic_search_accuracy']:<10.3f} "
              f"{row['v3_ultimate_orchestrator_accuracy']:<10.3f} "
              f"{row['best_algorithm']:<15}")

def print_algorithm_summary(test_results: Dict[str, Any]):
    """Imprime sumario dos algoritmos"""
    print("\nSUMARIO DOS ALGORITMOS")
    print("=" * 80)
    
    for algorithm_name, summary in test_results['algorithm_summary'].items():
        print(f"\n{algorithm_name}:")
        print(f"  Precisao Media: {summary['average_accuracy']:.3f} ({summary['average_accuracy']*100:.1f}%)")
        print(f"  Validacao Media: {summary['average_validation']:.3f}")
        print(f"  Tempo Medio: {summary['average_time']:.3f}s")
        print(f"  Melhores Resultados: {summary['best_results']}")
        print(f"  Taxa de Sucesso: {summary['success_rate']:.3f} ({summary['success_rate']*100:.1f}%)")

def main():
    """Funcao principal"""
    print("SISTEMA DE TESTE RIGOROSO COM DADOS REAIS")
    print("=" * 60)
    print("Testando todos os algoritmos com livros reais da pasta books/")
    print()
    
    # Cria testador
    tester = AlgorithmTester()
    
    # Executa teste abrangente
    print("Executando teste abrangente...")
    test_results = tester.run_comprehensive_test(max_books=30)
    
    # Salva resultados detalhados
    with open('real_data_test_results_detailed.json', 'w', encoding='utf-8') as f:
        # Converte dataclasses para dict para JSON
        results_for_json = {
            'test_info': test_results['test_info'],
            'algorithm_summary': test_results['algorithm_summary'],
            'comparison_table': test_results['comparison_table'],
            'detailed_results': []
        }
        
        for result in test_results['detailed_results']:
            result_dict = {
                'filename': result.filename,
                'ground_truth': result.ground_truth,
                'best_algorithm': result.best_algorithm,
                'accuracy_scores': result.accuracy_scores,
                'algorithm_results': []
            }
            
            for alg_result in result.algorithm_results:
                alg_dict = asdict(alg_result)
                # Remove validation_result que e complexo
                alg_dict['validation_score'] = alg_result.validation_result.validation_score
                alg_dict['validation_errors'] = len(alg_result.validation_result.errors)
                del alg_dict['validation_result']
                result_dict['algorithm_results'].append(alg_dict)
            
            results_for_json['detailed_results'].append(result_dict)
        
        json.dump(results_for_json, f, indent=2, ensure_ascii=False)
    
    print("Resultados salvos em: real_data_test_results_detailed.json")
    
    # Imprime resultados
    print_results_table(test_results)
    print_algorithm_summary(test_results)
    
    print("\nTESTE COMPLETO FINALIZADO!")
    print("Verifique os logs em real_data_testing.log para detalhes")

if __name__ == "__main__":
    main()