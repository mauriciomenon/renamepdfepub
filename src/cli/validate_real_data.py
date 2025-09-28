#!/usr/bin/env python3
"""
Validador de Dados Reais - Algoritmos de Busca
==============================================

Este script valida se os algoritmos realmente extraem dados corretos
dos livros, sem usar dados mockados ou caracteres malucos.
"""

import os
import re
import sys
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from difflib import SequenceMatcher

# Configurar paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

# Configurar logging simples
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class BookMetadataExtractor:
    """Extrator robusto de metadados reais de livros"""
    
    def __init__(self):
        self.publishers = [
            'Manning', 'Packt', 'OReilly', 'O\'Reilly', 'Wiley', 'Pearson', 
            'Addison', 'Wesley', 'MIT', 'Cambridge', 'Oxford', 'Apress',
            'No Starch', 'Pragmatic', 'MEAP'
        ]
        
        self.tech_categories = {
            'Programming': ['python', 'java', 'javascript', 'react', 'vue', 'angular'],
            'Security': ['hacking', 'security', 'cyber', 'malware', 'forensics'],
            'Database': ['sql', 'mysql', 'postgresql', 'database', 'mongo'],
            'AI/ML': ['machine', 'learning', 'ai', 'data', 'science'],
            'DevOps': ['docker', 'kubernetes', 'cloud', 'aws', 'azure'],
            'Web': ['web', 'html', 'css', 'frontend', 'backend']
        }
    
    def extract_real_metadata(self, filename: str) -> Dict[str, Any]:
        """Extrair metadados reais do nome do arquivo"""
        original_name = filename
        clean_name = self._clean_filename(filename)
        
        metadata = {
            'original_filename': original_name,
            'cleaned_title': clean_name,
            'extracted_title': '',
            'extracted_author': '',
            'extracted_publisher': '',
            'extracted_year': '',
            'extracted_edition': '',
            'detected_category': '',
            'isbn_candidate': '',
            'confidence_score': 0.0
        }
        
        # Extrair título principal
        title = self._extract_title(clean_name)
        metadata['extracted_title'] = title
        
        # Extrair autor
        author = self._extract_author(clean_name)
        metadata['extracted_author'] = author
        
        # Extrair publisher
        publisher = self._extract_publisher(clean_name)
        metadata['extracted_publisher'] = publisher
        
        # Extrair ano
        year = self._extract_year(clean_name)
        metadata['extracted_year'] = year
        
        # Extrair edição
        edition = self._extract_edition(clean_name)
        metadata['extracted_edition'] = edition
        
        # Detectar categoria
        category = self._detect_category(clean_name)
        metadata['detected_category'] = category
        
        # Buscar ISBN candidato
        isbn = self._extract_isbn_candidate(clean_name)
        metadata['isbn_candidate'] = isbn
        
        # Calcular confiança
        confidence = self._calculate_confidence(metadata)
        metadata['confidence_score'] = confidence
        
        return metadata
    
    def _clean_filename(self, filename: str) -> str:
        """Limpar nome do arquivo"""
        # Remover extensões
        name = Path(filename).stem
        
        # Remover extensões duplas
        while name.endswith(('.pdf', '.epub', '.mobi')):
            name = name[:-4]
        
        # Substituir separadores
        name = name.replace('_', ' ').replace('-', ' ')
        
        # Remover padrões comuns
        name = re.sub(r'\s+v\d+.*MEAP.*$', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\s+MEAP.*$', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\s+Second\s+Edition.*$', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\s+Third\s+Edition.*$', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\s+Fourth\s+Edition.*$', '', name, flags=re.IGNORECASE)
        
        # Limpar espaços
        name = re.sub(r'\s+', ' ', name).strip()
        
        return name
    
    def _extract_title(self, text: str) -> str:
        """Extrair título principal"""
        # Remover padrões de autor e publisher
        title = text
        
        # Remover "by Author"
        title = re.sub(r'\s+by\s+.*$', '', title, flags=re.IGNORECASE)
        
        # Remover years
        title = re.sub(r'\s+\d{4}.*$', '', title)
        
        # Remover publishers conhecidos
        for pub in self.publishers:
            title = re.sub(f'\\s+{re.escape(pub)}.*$', '', title, flags=re.IGNORECASE)
        
        return title.strip()
    
    def _extract_author(self, text: str) -> str:
        """Extrair autor se possível"""
        # Padrão "by Author"
        match = re.search(r'by\s+([A-Za-z\s]+)', text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        # Padrão "Author -"
        match = re.search(r'^([A-Za-z\s]{5,30})\s*-', text)
        if match:
            return match.group(1).strip()
        
        return ''
    
    def _extract_publisher(self, text: str) -> str:
        """Extrair publisher"""
        for pub in self.publishers:
            if pub.lower() in text.lower():
                return pub
        return ''
    
    def _extract_year(self, text: str) -> str:
        """Extrair ano"""
        match = re.search(r'\b(19|20)\d{2}\b', text)
        return match.group(0) if match else ''
    
    def _extract_edition(self, text: str) -> str:
        """Extrair edição"""
        patterns = [
            r'(Second|Third|Fourth|Fifth)\s+Edition',
            r'(\d+)(st|nd|rd|th)\s+Edition',
            r'Edition\s+(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return ''
    
    def _detect_category(self, text: str) -> str:
        """Detectar categoria técnica"""
        text_lower = text.lower()
        
        for category, keywords in self.tech_categories.items():
            if any(keyword in text_lower for keyword in keywords):
                return category
        
        return 'General'
    
    def _extract_isbn_candidate(self, text: str) -> str:
        """Buscar possível ISBN"""
        # Buscar padrões numéricos que poderiam ser ISBN
        matches = re.findall(r'\b\d{10,13}\b', text)
        return matches[0] if matches else ''
    
    def _calculate_confidence(self, metadata: Dict) -> float:
        """Calcular confiança da extração"""
        score = 0.0
        
        if metadata['extracted_title']:
            score += 0.3
        if metadata['extracted_author']:
            score += 0.2
        if metadata['extracted_publisher']:
            score += 0.2
        if metadata['extracted_year']:
            score += 0.1
        if metadata['detected_category'] != 'General':
            score += 0.1
        if metadata['extracted_edition']:
            score += 0.1
        
        return min(score, 1.0)

class RealDataValidator:
    """Validador de dados reais"""
    
    def __init__(self):
        self.extractor = BookMetadataExtractor()
        self.books_data = []
    
    def load_books_collection(self, max_books: int = 100) -> None:
        """Carregar coleção de livros"""
        books_dir = project_root / "books"
        
        count = 0
        for file_path in books_dir.iterdir():
            if count >= max_books:
                break
                
            if file_path.suffix.lower() in ['.pdf', '.epub', '.mobi'] and file_path.name != '.DS_Store':
                metadata = self.extractor.extract_real_metadata(file_path.name)
                metadata['file_path'] = str(file_path)
                self.books_data.append(metadata)
                count += 1
        
        logger.info(f"Carregados {len(self.books_data)} livros para validacao")
    
    def validate_extraction_quality(self) -> Dict[str, Any]:
        """Validar qualidade da extração"""
        stats = {
            'total_books': len(self.books_data),
            'books_with_title': 0,
            'books_with_author': 0,
            'books_with_publisher': 0,
            'books_with_year': 0,
            'books_with_edition': 0,
            'books_with_category': 0,
            'avg_confidence': 0.0,
            'high_confidence_books': 0,  # > 0.7
            'medium_confidence_books': 0,  # 0.4-0.7
            'low_confidence_books': 0,    # < 0.4
        }
        
        total_confidence = 0.0
        
        for book in self.books_data:
            if book['extracted_title']:
                stats['books_with_title'] += 1
            if book['extracted_author']:
                stats['books_with_author'] += 1
            if book['extracted_publisher']:
                stats['books_with_publisher'] += 1
            if book['extracted_year']:
                stats['books_with_year'] += 1
            if book['extracted_edition']:
                stats['books_with_edition'] += 1
            if book['detected_category'] != 'General':
                stats['books_with_category'] += 1
            
            confidence = book['confidence_score']
            total_confidence += confidence
            
            if confidence > 0.7:
                stats['high_confidence_books'] += 1
            elif confidence >= 0.4:
                stats['medium_confidence_books'] += 1
            else:
                stats['low_confidence_books'] += 1
        
        stats['avg_confidence'] = total_confidence / len(self.books_data) if self.books_data else 0
        
        return stats
    
    def test_fuzzy_algorithm(self, query: str, limit: int = 5) -> List[Dict]:
        """Testar algoritmo fuzzy com dados reais"""
        query_lower = query.lower().strip()
        results = []
        
        for book in self.books_data:
            title_lower = book['extracted_title'].lower()
            
            if not title_lower:
                continue
            
            # Calcular similaridade real
            similarity = SequenceMatcher(None, query_lower, title_lower).ratio()
            
            # Bonus para palavras em comum
            query_words = set(query_lower.split())
            title_words = set(title_lower.split())
            common_words = query_words.intersection(title_words)
            
            if query_words and title_words:
                word_bonus = len(common_words) / max(len(query_words), len(title_words)) * 0.3
                similarity = min(similarity + word_bonus, 1.0)
            
            # Bonus para substring
            if query_lower in title_lower or title_lower in query_lower:
                similarity += 0.1
                similarity = min(similarity, 1.0)
            
            if similarity > 0.2:  # Threshold
                result = {
                    'title': book['extracted_title'],
                    'author': book['extracted_author'],
                    'publisher': book['extracted_publisher'],
                    'year': book['extracted_year'],
                    'category': book['detected_category'],
                    'similarity_score': similarity,
                    'confidence': similarity * book['confidence_score'],
                    'original_filename': book['original_filename']
                }
                results.append(result)
        
        results.sort(key=lambda x: x['similarity_score'], reverse=True)
        return results[:limit]
    
    def test_semantic_algorithm(self, query: str, limit: int = 5) -> List[Dict]:
        """Testar algoritmo semântico com dados reais"""
        query_lower = query.lower()
        results = []
        
        # Detectar categoria da query
        query_category = self.extractor._detect_category(query)
        
        for book in self.books_data:
            title_lower = book['extracted_title'].lower()
            
            if not title_lower:
                continue
            
            score = 0.0
            
            # Score base por palavras
            query_words = set(query_lower.split())
            title_words = set(title_lower.split())
            common_words = query_words.intersection(title_words)
            
            if query_words and title_words:
                base_score = len(common_words) / max(len(query_words), len(title_words))
                score += base_score * 0.6
            
            # Bonus por categoria
            if query_category != 'General' and book['detected_category'] == query_category:
                score += 0.4
            
            # Bonus por publisher conhecido
            if book['extracted_publisher']:
                score += 0.1
            
            score = min(score, 1.0)
            
            if score > 0.2:
                result = {
                    'title': book['extracted_title'],
                    'author': book['extracted_author'],
                    'publisher': book['extracted_publisher'],
                    'year': book['extracted_year'], 
                    'category': book['detected_category'],
                    'similarity_score': score,
                    'confidence': score * book['confidence_score'],
                    'original_filename': book['original_filename']
                }
                results.append(result)
        
        results.sort(key=lambda x: x['similarity_score'], reverse=True)
        return results[:limit]
    
    def print_sample_extractions(self, count: int = 10) -> None:
        """Imprimir amostras de extrações para validação"""
        print("\n=== AMOSTRAS DE EXTRACOES ===")
        
        for i, book in enumerate(self.books_data[:count]):
            print(f"\n{i+1}. {book['original_filename']}")
            print(f"   Titulo: '{book['extracted_title']}'")
            print(f"   Autor: '{book['extracted_author']}'")
            print(f"   Publisher: '{book['extracted_publisher']}'") 
            print(f"   Ano: '{book['extracted_year']}'")
            print(f"   Categoria: '{book['detected_category']}'")
            print(f"   Confianca: {book['confidence_score']:.2f}")
    
    def run_validation_tests(self) -> None:
        """Executar testes de validação completos"""
        print("=== VALIDADOR DE DADOS REAIS ===")
        
        # Carregar livros
        self.load_books_collection(50)
        
        # Validar extração
        stats = self.validate_extraction_quality()
        
        print(f"\nESTATISTICAS DE EXTRACAO:")
        print(f"Total de livros: {stats['total_books']}")
        print(f"Com titulo: {stats['books_with_title']} ({stats['books_with_title']/stats['total_books']*100:.1f}%)")
        print(f"Com autor: {stats['books_with_author']} ({stats['books_with_author']/stats['total_books']*100:.1f}%)")
        print(f"Com publisher: {stats['books_with_publisher']} ({stats['books_with_publisher']/stats['total_books']*100:.1f}%)")
        print(f"Com ano: {stats['books_with_year']} ({stats['books_with_year']/stats['total_books']*100:.1f}%)")
        print(f"Com categoria: {stats['books_with_category']} ({stats['books_with_category']/stats['total_books']*100:.1f}%)")
        print(f"Confianca media: {stats['avg_confidence']:.2f}")
        
        print(f"\nDISTRIBUICAO DE CONFIANCA:")
        print(f"Alta (>0.7): {stats['high_confidence_books']}")
        print(f"Media (0.4-0.7): {stats['medium_confidence_books']}")
        print(f"Baixa (<0.4): {stats['low_confidence_books']}")
        
        # Mostrar amostras
        self.print_sample_extractions(10)
        
        # Testar algoritmos
        print("\n=== TESTES DE ALGORITMOS ===")
        
        test_queries = [
            "Python Programming",
            "JavaScript React",
            "Machine Learning",
            "Web Development",
            "Database SQL"
        ]
        
        for query in test_queries:
            print(f"\nTeste Query: '{query}'")
            
            # Testar Fuzzy
            fuzzy_results = self.test_fuzzy_algorithm(query, 3)
            print(f"Fuzzy ({len(fuzzy_results)} resultados):")
            for r in fuzzy_results:
                print(f"  - {r['title']} (score: {r['similarity_score']:.2f})")
            
            # Testar Semantic
            semantic_results = self.test_semantic_algorithm(query, 3)
            print(f"Semantic ({len(semantic_results)} resultados):")
            for r in semantic_results:
                print(f"  - {r['title']} (score: {r['similarity_score']:.2f})")

def main():
    """Função principal"""
    validator = RealDataValidator()
    validator.run_validation_tests()

if __name__ == "__main__":
    main()