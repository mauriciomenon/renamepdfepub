#!/usr/bin/env python3
"""
Sistema de Validacao Rigorosa - RenamePDFEpub
============================================

Sistema completo de validacao de dados reais para todos os algoritmos.
Verifica se realmente extrai dados corretos: autor, titulo, editora, ano, ISBN.
"""

import json
import re
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import unicodedata

@dataclass
class ValidationResult:
    """Resultado da validacao de um livro"""
    title: str
    author: str
    publisher: str
    year: str
    isbn10: str
    isbn13: str
    confidence: float
    validation_score: float
    errors: List[str]
    warnings: List[str]

class DataValidator:
    """Validador rigoroso de dados extraidos"""
    
    def __init__(self):
        self.setup_logging()
        
        # Padroes para validacao
        self.author_patterns = [
            r'^[A-Za-z\s\.\-\']+$',  # Nomes validos
        ]
        
        self.year_pattern = r'^(19|20)\d{2}$'  # Anos validos 1900-2099
        
        self.isbn10_pattern = r'^\d{9}[\dX]$'
        self.isbn13_pattern = r'^97[89]\d{10}$'
        
        # Publishers conhecidos
        self.known_publishers = {
            'Manning', 'Packt', 'OReilly', 'O\'Reilly', 'NoStarch', 'No Starch',
            'Wiley', 'Addison-Wesley', 'MIT Press', 'Apress', 'Pearson',
            'McGraw-Hill', 'Springer', 'Elsevier', 'Cambridge', 'Oxford'
        }
        
        # Palavras que NAO sao autores
        self.invalid_author_words = {
            'www', 'com', 'org', 'net', 'pdf', 'epub', 'mobi', 'book',
            'ebook', 'download', 'free', 'torrent', 'copy', 'version'
        }
        
        # Palavras que NAO sao titulos
        self.invalid_title_words = {
            'untitled', 'document', 'scan', 'copy', 'download'
        }

    def setup_logging(self):
        """Configura logging detalhado"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('validation_detailed.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def validate_author(self, author: str) -> Tuple[bool, List[str]]:
        """Valida se o autor e real e valido"""
        errors = []
        
        if not author or len(author.strip()) < 2:
            errors.append("Autor muito curto ou vazio")
            return False, errors
        
        author_clean = author.strip().lower()
        
        # Verifica palavras invalidas
        for invalid_word in self.invalid_author_words:
            if invalid_word in author_clean:
                errors.append(f"Contem palavra invalida para autor: {invalid_word}")
        
        # Verifica se tem pelo menos uma letra
        if not re.search(r'[a-zA-Z]', author):
            errors.append("Nao contem letras validas")
        
        # Verifica se nao e so numeros
        if author.strip().isdigit():
            errors.append("Autor nao pode ser apenas numeros")
        
        # Verifica tamanho razoavel
        if len(author) > 100:
            errors.append("Autor muito longo (suspeito)")
        
        # Verifica caracteres especiais excessivos
        special_chars = re.findall(r'[^a-zA-Z\s\.\-\']', author)
        if len(special_chars) > 3:
            errors.append(f"Muitos caracteres especiais: {special_chars}")
        
        return len(errors) == 0, errors

    def validate_title(self, title: str) -> Tuple[bool, List[str]]:
        """Valida se o titulo e real e valido"""
        errors = []
        
        if not title or len(title.strip()) < 3:
            errors.append("Titulo muito curto ou vazio")
            return False, errors
        
        title_clean = title.strip().lower()
        
        # Verifica palavras invalidas
        for invalid_word in self.invalid_title_words:
            if invalid_word in title_clean:
                errors.append(f"Contem palavra invalida para titulo: {invalid_word}")
        
        # Verifica se tem pelo menos algumas letras
        letter_count = len(re.findall(r'[a-zA-Z]', title))
        if letter_count < 3:
            errors.append("Titulo deve ter pelo menos 3 letras")
        
        # Verifica se nao e so numeros/simbolos
        if re.match(r'^[\d\W]+$', title):
            errors.append("Titulo nao pode ser apenas numeros/simbolos")
        
        # Verifica tamanho razoavel
        if len(title) > 200:
            errors.append("Titulo muito longo (suspeito)")
        
        return len(errors) == 0, errors

    def validate_publisher(self, publisher: str) -> Tuple[bool, List[str], float]:
        """Valida editora com score de confianca"""
        errors = []
        confidence = 0.0
        
        if not publisher:
            errors.append("Publisher vazio")
            return False, errors, 0.0
        
        publisher_clean = publisher.strip()
        
        # Verifica se e publisher conhecido
        for known in self.known_publishers:
            if known.lower() in publisher_clean.lower():
                confidence = 0.9
                return True, [], confidence
        
        # Verifica padroes de publisher
        if re.search(r'(press|publishing|publications|books|media)', publisher_clean, re.IGNORECASE):
            confidence = 0.7
        elif len(publisher_clean) > 2 and not publisher_clean.isdigit():
            confidence = 0.5
        else:
            errors.append("Publisher nao parece valido")
        
        return len(errors) == 0, errors, confidence

    def validate_year(self, year: str) -> Tuple[bool, List[str]]:
        """Valida ano de publicacao"""
        errors = []
        
        if not year:
            errors.append("Ano vazio")
            return False, errors
        
        # Extrai ano se estiver em string maior
        year_match = re.search(r'(19|20)\d{2}', str(year))
        if year_match:
            year_clean = year_match.group()
        else:
            errors.append("Formato de ano invalido")
            return False, errors
        
        # Valida range razoavel
        year_int = int(year_clean)
        if year_int < 1900 or year_int > 2025:
            errors.append(f"Ano fora do range valido: {year_int}")
        
        return len(errors) == 0, errors

    def validate_isbn(self, isbn: str, isbn_type: str) -> Tuple[bool, List[str]]:
        """Valida ISBN-10 ou ISBN-13"""
        errors = []
        
        if not isbn:
            return True, []  # ISBN opcional
        
        # Remove espacos e hifens
        isbn_clean = re.sub(r'[\s\-]', '', isbn)
        
        if isbn_type == "isbn10":
            if not re.match(self.isbn10_pattern, isbn_clean):
                errors.append(f"ISBN-10 formato invalido: {isbn}")
            else:
                # Valida checksum ISBN-10
                if not self.validate_isbn10_checksum(isbn_clean):
                    errors.append(f"ISBN-10 checksum invalido: {isbn}")
        
        elif isbn_type == "isbn13":
            if not re.match(self.isbn13_pattern, isbn_clean):
                errors.append(f"ISBN-13 formato invalido: {isbn}")
            else:
                # Valida checksum ISBN-13
                if not self.validate_isbn13_checksum(isbn_clean):
                    errors.append(f"ISBN-13 checksum invalido: {isbn}")
        
        return len(errors) == 0, errors

    def validate_isbn10_checksum(self, isbn10: str) -> bool:
        """Valida checksum do ISBN-10"""
        if len(isbn10) != 10:
            return False
        
        try:
            total = 0
            for i in range(9):
                total += int(isbn10[i]) * (10 - i)
            
            check_digit = isbn10[9]
            if check_digit == 'X':
                check_digit = 10
            else:
                check_digit = int(check_digit)
            
            return (total + check_digit) % 11 == 0
        except:
            return False

    def validate_isbn13_checksum(self, isbn13: str) -> bool:
        """Valida checksum do ISBN-13"""
        if len(isbn13) != 13:
            return False
        
        try:
            total = 0
            for i in range(12):
                multiplier = 1 if i % 2 == 0 else 3
                total += int(isbn13[i]) * multiplier
            
            check_digit = int(isbn13[12])
            return (total + check_digit) % 10 == 0
        except:
            return False

    def validate_book_data(self, book_data: Dict[str, Any]) -> ValidationResult:
        """Valida todos os dados de um livro"""
        errors = []
        warnings = []
        
        # Extrai campos
        title = book_data.get('title', '')
        author = book_data.get('author', '')
        publisher = book_data.get('publisher', '')
        year = book_data.get('year', '')
        isbn10 = book_data.get('isbn10', '')
        isbn13 = book_data.get('isbn13', '')
        confidence = book_data.get('confidence', 0.0)
        
        # Valida cada campo
        title_valid, title_errors = self.validate_title(title)
        author_valid, author_errors = self.validate_author(author)
        publisher_valid, publisher_errors, publisher_confidence = self.validate_publisher(publisher)
        year_valid, year_errors = self.validate_year(year)
        isbn10_valid, isbn10_errors = self.validate_isbn(isbn10, "isbn10")
        isbn13_valid, isbn13_errors = self.validate_isbn(isbn13, "isbn13")
        
        # Consolida erros
        errors.extend(title_errors)
        errors.extend(author_errors)
        errors.extend(publisher_errors)
        errors.extend(year_errors)
        errors.extend(isbn10_errors)
        errors.extend(isbn13_errors)
        
        # Calcula score de validacao
        validation_score = 0.0
        total_fields = 0
        
        if title_valid:
            validation_score += 0.3
        if author_valid:
            validation_score += 0.3
        if publisher_valid:
            validation_score += 0.2
        if year_valid:
            validation_score += 0.1
        if isbn10_valid and isbn10:
            validation_score += 0.05
        if isbn13_valid and isbn13:
            validation_score += 0.05
        
        # Warnings para campos vazios importantes
        if not title:
            warnings.append("Titulo vazio")
        if not author:
            warnings.append("Autor vazio")
        if not publisher:
            warnings.append("Publisher vazio")
        if not year:
            warnings.append("Ano vazio")
        
        return ValidationResult(
            title=title,
            author=author,
            publisher=publisher,
            year=year,
            isbn10=isbn10,
            isbn13=isbn13,
            confidence=confidence,
            validation_score=validation_score,
            errors=errors,
            warnings=warnings
        )

class RealDataTester:
    """Testador com dados reais rigoroso"""
    
    def __init__(self):
        self.validator = DataValidator()
        self.setup_logging()
        
        # Dados reais conhecidos para teste
        self.real_test_books = [
            {
                'filename': 'clean_code_martin.pdf',
                'expected': {
                    'title': 'Clean Code',
                    'author': 'Robert C. Martin',
                    'publisher': 'Prentice Hall',
                    'year': '2008',
                    'isbn13': '9780132350884'
                }
            },
            {
                'filename': 'python_crash_course.pdf',
                'expected': {
                    'title': 'Python Crash Course',
                    'author': 'Eric Matthes',
                    'publisher': 'No Starch Press',
                    'year': '2019',
                    'isbn13': '9781593279288'
                }
            },
            {
                'filename': 'design_patterns_gof.pdf',
                'expected': {
                    'title': 'Design Patterns',
                    'author': 'Erich Gamma',
                    'publisher': 'Addison-Wesley',
                    'year': '1994',
                    'isbn10': '0201633612'
                }
            },
            {
                'filename': 'javascript_definitive_guide.pdf',
                'expected': {
                    'title': 'JavaScript: The Definitive Guide',
                    'author': 'David Flanagan',
                    'publisher': 'O\'Reilly Media',
                    'year': '2020',
                    'isbn13': '9781491952023'
                }
            },
            {
                'filename': 'effective_java_bloch.pdf',
                'expected': {
                    'title': 'Effective Java',
                    'author': 'Joshua Bloch',
                    'publisher': 'Addison-Wesley',
                    'year': '2017',
                    'isbn13': '9780134685991'
                }
            }
        ]

    def setup_logging(self):
        """Configura logging"""
        self.logger = logging.getLogger(__name__)

    def test_algorithm_with_real_data(self, algorithm_func, algorithm_name: str) -> Dict[str, Any]:
        """Testa algoritmo com dados reais"""
        self.logger.info(f"Testando algoritmo: {algorithm_name}")
        
        results = {
            'algorithm_name': algorithm_name,
            'total_tests': len(self.real_test_books),
            'passed_tests': 0,
            'failed_tests': 0,
            'validation_scores': [],
            'detailed_results': [],
            'average_accuracy': 0.0,
            'execution_time': 0.0
        }
        
        start_time = time.time()
        
        for test_book in self.real_test_books:
            try:
                # Executa algoritmo
                extracted_data = algorithm_func(test_book['filename'])
                
                # Valida dados extraidos
                validation_result = self.validator.validate_book_data(extracted_data)
                
                # Compara com dados esperados
                accuracy_score = self.calculate_accuracy(extracted_data, test_book['expected'])
                
                # Resultado detalhado
                detailed_result = {
                    'filename': test_book['filename'],
                    'expected': test_book['expected'],
                    'extracted': extracted_data,
                    'validation_result': validation_result,
                    'accuracy_score': accuracy_score,
                    'passed': accuracy_score > 0.5 and validation_result.validation_score > 0.5
                }
                
                results['detailed_results'].append(detailed_result)
                results['validation_scores'].append(validation_result.validation_score)
                
                if detailed_result['passed']:
                    results['passed_tests'] += 1
                else:
                    results['failed_tests'] += 1
                
                self.logger.info(f"  {test_book['filename']}: Accuracy={accuracy_score:.3f}, Validation={validation_result.validation_score:.3f}")
                
            except Exception as e:
                self.logger.error(f"Erro testando {test_book['filename']}: {e}")
                results['failed_tests'] += 1
        
        results['execution_time'] = time.time() - start_time
        results['average_accuracy'] = sum(results['validation_scores']) / len(results['validation_scores']) if results['validation_scores'] else 0.0
        
        return results

    def calculate_accuracy(self, extracted: Dict[str, Any], expected: Dict[str, Any]) -> float:
        """Calcula precisao comparando dados extraidos com esperados"""
        score = 0.0
        total_fields = 0
        
        for field, expected_value in expected.items():
            total_fields += 1
            extracted_value = extracted.get(field, '')
            
            if field == 'title':
                similarity = self.calculate_title_similarity(extracted_value, expected_value)
                score += similarity * 0.4  # Titulo tem peso 40%
            elif field == 'author':
                similarity = self.calculate_author_similarity(extracted_value, expected_value)
                score += similarity * 0.3  # Autor tem peso 30%
            elif field == 'publisher':
                similarity = self.calculate_publisher_similarity(extracted_value, expected_value)
                score += similarity * 0.2  # Publisher tem peso 20%
            elif field == 'year':
                similarity = 1.0 if str(extracted_value) == str(expected_value) else 0.0
                score += similarity * 0.05  # Ano tem peso 5%
            elif field in ['isbn10', 'isbn13']:
                similarity = 1.0 if str(extracted_value) == str(expected_value) else 0.0
                score += similarity * 0.025  # ISBN tem peso 2.5% cada
        
        return min(score, 1.0)

    def calculate_title_similarity(self, extracted: str, expected: str) -> float:
        """Calcula similaridade entre titulos"""
        if not extracted or not expected:
            return 0.0
        
        extracted_clean = self.normalize_text(extracted)
        expected_clean = self.normalize_text(expected)
        
        # Exact match
        if extracted_clean == expected_clean:
            return 1.0
        
        # Containment
        if expected_clean in extracted_clean or extracted_clean in expected_clean:
            return 0.8
        
        # Word overlap
        extracted_words = set(extracted_clean.split())
        expected_words = set(expected_clean.split())
        
        if not extracted_words or not expected_words:
            return 0.0
        
        overlap = len(extracted_words.intersection(expected_words))
        total_words = len(extracted_words.union(expected_words))
        
        return overlap / total_words

    def calculate_author_similarity(self, extracted: str, expected: str) -> float:
        """Calcula similaridade entre autores"""
        if not extracted or not expected:
            return 0.0
        
        extracted_clean = self.normalize_text(extracted)
        expected_clean = self.normalize_text(expected)
        
        # Exact match
        if extracted_clean == expected_clean:
            return 1.0
        
        # Last name match (common in citations)
        extracted_parts = extracted_clean.split()
        expected_parts = expected_clean.split()
        
        if extracted_parts and expected_parts:
            if extracted_parts[-1] == expected_parts[-1]:
                return 0.7
        
        # Word overlap
        extracted_words = set(extracted_clean.split())
        expected_words = set(expected_clean.split())
        
        if not extracted_words or not expected_words:
            return 0.0
        
        overlap = len(extracted_words.intersection(expected_words))
        total_words = len(extracted_words.union(expected_words))
        
        return overlap / total_words

    def calculate_publisher_similarity(self, extracted: str, expected: str) -> float:
        """Calcula similaridade entre publishers"""
        if not extracted or not expected:
            return 0.0
        
        extracted_clean = self.normalize_text(extracted)
        expected_clean = self.normalize_text(expected)
        
        # Exact match
        if extracted_clean == expected_clean:
            return 1.0
        
        # Partial match (common abbreviations)
        if 'oreilly' in extracted_clean and 'oreilly' in expected_clean:
            return 0.9
        if 'addison' in extracted_clean and 'addison' in expected_clean:
            return 0.9
        if 'prentice' in extracted_clean and 'prentice' in expected_clean:
            return 0.9
        
        # Containment
        if expected_clean in extracted_clean or extracted_clean in expected_clean:
            return 0.6
        
        return 0.0

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

def main():
    """Funcao principal de teste rigoroso"""
    print("SISTEMA DE VALIDACAO RIGOROSA - RenamePDFEpub")
    print("=" * 60)
    print("Validando todos os algoritmos com dados reais...")
    print()
    
    # Cria testador
    tester = RealDataTester()
    
    # Lista de algoritmos para testar (placeholder - serao implementados)
    algorithms_to_test = [
        # ('algorithm_v1', 'V1 Basic Algorithm'),
        # ('algorithm_v2', 'V2 Enhanced Algorithm'),
        # ('algorithm_v3', 'V3 Ultimate Algorithm'),
    ]
    
    all_results = []
    
    print("NOTA: Este e o framework de validacao.")
    print("Os algoritmos especificos serao testados na proxima etapa.")
    print()
    
    # Exemplo de como usar o validador
    validator = DataValidator()
    
    print("EXEMPLO DE VALIDACAO:")
    print("-" * 30)
    
    # Dados de exemplo
    sample_data = {
        'title': 'Clean Code: A Handbook of Agile Software Craftsmanship',
        'author': 'Robert C. Martin',
        'publisher': 'Prentice Hall',
        'year': '2008',
        'isbn10': '0132350882',
        'isbn13': '9780132350884',
        'confidence': 0.85
    }
    
    validation_result = validator.validate_book_data(sample_data)
    
    print(f"Titulo: {validation_result.title}")
    print(f"Autor: {validation_result.author}")
    print(f"Publisher: {validation_result.publisher}")
    print(f"Ano: {validation_result.year}")
    print(f"ISBN-10: {validation_result.isbn10}")
    print(f"ISBN-13: {validation_result.isbn13}")
    print(f"Validation Score: {validation_result.validation_score:.3f}")
    
    if validation_result.errors:
        print("ERROS:")
        for error in validation_result.errors:
            print(f"  - {error}")
    
    if validation_result.warnings:
        print("AVISOS:")
        for warning in validation_result.warnings:
            print(f"  - {warning}")
    
    print()
    print("PROXIMO PASSO: Implementar e testar algoritmos especificos")
    print("Framework de validacao esta pronto para uso!")

if __name__ == "__main__":
    main()