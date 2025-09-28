#!/usr/bin/env python3
"""
Teste Completo Final V3 - Algoritmos Melhorados
===============================================

Teste definitivo dos algoritmos V3 com dados reais e comparação com versões anteriores.
"""

import sys
import time
import json
from pathlib import Path
import re
from typing import Dict, List, Any

class FinalV3MetadataExtractor:
    """Extrator final V3 baseado na validação bem-sucedida"""
    
    def __init__(self):
        self.author_patterns = [
            r'\bby\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)(?:\s|$|\(|\[|,|-)',
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s+presents\b',
            r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+?)\s*-\s*'
        ]
        
        self.year_patterns = [
            r'\b(20[0-2]\d)\b',
            r'\b(19[89]\d)\b',
            r'(\d{4})(?=\.pdf|\.epub|\.mobi|$)'
        ]
        
        self.publisher_patterns = {
            'Manning': [r'\bmanning\b', r'\bmeap\b', r'exploring', r'month.*lunches'],
            'Packt': [r'\bpackt\b', r'cookbook', r'hands[\s\-]on', r'mastering'],
            'NoStarch': [r'no\s*starch', r'black\s*hat', r'ethical\s*hacking'],
            'OReilly': [r'o\'?reilly', r'learning', r'definitive\s+guide'],
            'Wiley': [r'\bwiley\b', r'\bsybex\b'],
            'Addison': [r'addison', r'wesley'],
            'MIT': [r'mit\s*press'],
            'Apress': [r'\bapress\b']
        }
        
        self.super_categories = {
            'Programming': [
                'python', 'java', 'javascript', 'js', 'typescript', 'react', 'vue',
                'programming', 'code', 'coding', 'development', 'software',
                'algorithm', 'algorithms', 'c++', 'golang', 'rust'
            ],
            'Security': [
                'security', 'hacking', 'hack', 'cyber', 'cybersecurity',
                'malware', 'forensics', 'penetration', 'pentest', 'ethical',
                'cryptography', 'encryption'
            ],
            'Database': [
                'database', 'db', 'sql', 'mysql', 'postgresql', 'mongo',
                'mongodb', 'redis', 'data', 'analytics'
            ],
            'AI_ML': [
                'machine learning', 'ml', 'ai', 'artificial intelligence',
                'data science', 'deep learning', 'neural', 'tensorflow'
            ],
            'Web': [
                'web', 'website', 'html', 'css', 'frontend', 'backend',
                'full stack', 'ui', 'ux', 'api', 'rest'
            ],
            'DevOps': [
                'devops', 'docker', 'kubernetes', 'cloud', 'aws', 'azure',
                'deployment', 'automation', 'ci/cd'
            ],
            'Mobile': [
                'mobile', 'android', 'ios', 'app', 'swift', 'kotlin'
            ],
            'Systems': [
                'linux', 'windows', 'unix', 'system', 'network', 'server'
            ]
        }
    
    def extract_metadata(self, filename: str) -> Dict[str, Any]:
        """Extração final V3"""
        clean_name = self._clean_filename(filename)
        
        metadata = {
            'filename': filename,
            'title': '',
            'author': '',
            'publisher': '',
            'year': '',
            'edition': '',
            'category': '',
            'keywords': [],
            'confidence': 0.0
        }
        
        # Extrair metadados
        metadata['author'] = self._extract_author(clean_name)
        metadata['year'] = self._extract_year(clean_name)
        metadata['publisher'] = self._extract_publisher(clean_name)
        metadata['title'] = self._extract_title(clean_name, metadata)
        metadata['edition'] = self._extract_edition(clean_name)
        metadata['category'] = self._extract_category(clean_name)
        metadata['keywords'] = self._extract_keywords(clean_name)
        metadata['confidence'] = self._calculate_confidence(metadata)
        
        return metadata
    
    def _clean_filename(self, filename: str) -> str:
        """Limpeza mantendo informações importantes"""
        name = Path(filename).stem
        
        # Remover extensões
        for ext in ['.pdf', '.epub', '.mobi', '.azw3']:
            name = name.replace(ext, '')
        
        # Substituir separadores
        name = name.replace('_', ' ').replace('-', ' ')
        name = re.sub(r'\s+', ' ', name).strip()
        
        return name
    
    def _extract_author(self, text: str) -> str:
        """Extrair autor com validação"""
        for pattern in self.author_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                author = match.group(1).strip()
                if self._validate_author(author):
                    return author
        return ''
    
    def _validate_author(self, name: str) -> bool:
        """Validar nome de autor"""
        if not name or len(name) < 3:
            return False
        
        words = name.split()
        if len(words) < 2:
            return False
            
        # Não pode ter números
        if any(c.isdigit() for c in name):
            return False
            
        # Palavras que não são nomes
        invalid = ['edition', 'programming', 'guide', 'book', 'packt', 'manning']
        if any(word.lower() in invalid for word in words):
            return False
            
        return True
    
    def _extract_year(self, text: str) -> str:
        """Extrair ano"""
        for pattern in self.year_patterns:
            match = re.search(pattern, text)
            if match:
                year = match.group(1)
                if 1990 <= int(year) <= 2030:
                    return year
        return ''
    
    def _extract_publisher(self, text: str) -> str:
        """Extrair publisher"""
        text_lower = text.lower()
        
        for publisher, patterns in self.publisher_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return publisher
        return ''
    
    def _extract_title(self, text: str, metadata: Dict[str, Any]) -> str:
        """Extrair título removendo outros metadados"""
        title = text
        
        # Remover autor, publisher, ano encontrados
        if metadata.get('author'):
            title = title.replace(metadata['author'], '').strip()
        if metadata.get('publisher'):
            title = re.sub(f"\\b{metadata['publisher']}\\b", '', title, flags=re.IGNORECASE)
        if metadata.get('year'):
            title = title.replace(metadata['year'], '').strip()
        
        # Limpeza final
        title = re.sub(r'\s+', ' ', title).strip()
        title = re.sub(r'^[\-\s]+|[\-\s]+$', '', title)
        
        return title or text  # Fallback para texto original
    
    def _extract_edition(self, text: str) -> str:
        """Extrair edição"""
        patterns = [
            r'(Second|Third|Fourth|Fifth)\s+Edition',
            r'(\d+)(st|nd|rd|th)\s+Edition'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        return ''
    
    def _extract_category(self, text: str) -> str:
        """Extrair categoria"""
        text_lower = text.lower()
        scores = {}
        
        for category, keywords in self.super_categories.items():
            score = sum(2.0 if len(kw.split()) > 1 else 1.0 
                       for kw in keywords if kw in text_lower)
            if score > 0:
                scores[category] = score
        
        return max(scores.items(), key=lambda x: x[1])[0] if scores else 'General'
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extrair palavras-chave"""
        text_lower = text.lower()
        keywords = set()
        
        for category_kws in self.super_categories.values():
            for kw in category_kws:
                if kw in text_lower:
                    keywords.add(kw)
        
        return sorted(list(keywords))
    
    def _calculate_confidence(self, metadata: Dict[str, Any]) -> float:
        """Calcular confiança"""
        score = 0.25  # Base para título
        
        if metadata['author']:
            score += 0.20
        if metadata['publisher']:
            score += 0.15
        if metadata['year']:
            score += 0.15
        if metadata['edition']:
            score += 0.08
        if metadata['category'] != 'General':
            score += 0.12
        if len(metadata['keywords']) > 0:
            score += min(len(metadata['keywords']) * 0.01, 0.05)
        
        return min(score, 1.0)

def main():
    """Teste final V3 com dados reais"""
    start_time = time.time()
    print("=== TESTE FINAL V3 - ALGORITMOS MELHORADOS ===")
    
    # Verificar diretório de livros
    books_dir = Path("books")
    if not books_dir.exists():
        print(" Diretório 'books' não encontrado!")
        return
    
    # Criar extrator V3
    extractor = FinalV3MetadataExtractor()
    
    # Processar livros reais
    books_data = []
    count = 0
    
    print("Processando livros reais...")
    for file_path in books_dir.iterdir():
        if count >= 80:  # Limite para teste
            break
        if file_path.suffix.lower() in ['.pdf', '.epub', '.mobi'] and file_path.name != '.DS_Store':
            try:
                metadata = extractor.extract_metadata(file_path.name)
                books_data.append(metadata)
                count += 1
                
                if count % 20 == 0:
                    print(f"  Processados: {count}")
                    
            except Exception as e:
                print(f"Erro em {file_path.name}: {e}")
    
    print(f"Base V3 criada com {len(books_data)} livros")
    
    # Estatísticas V3
    stats = {
        'total_books': len(books_data),
        'with_title': sum(1 for b in books_data if b['title']),
        'with_author': sum(1 for b in books_data if b['author']),
        'with_publisher': sum(1 for b in books_data if b['publisher']),
        'with_year': sum(1 for b in books_data if b['year']),
        'with_category': sum(1 for b in books_data if b['category'] != 'General'),
        'avg_confidence': sum(b['confidence'] for b in books_data) / len(books_data)
    }
    
    print("\n=== ESTATÍSTICAS V3 ===")
    print(f"Total: {stats['total_books']}")
    print(f"Com título: {stats['with_title']} ({stats['with_title']/stats['total_books']*100:.1f}%)")
    print(f"Com autor: {stats['with_author']} ({stats['with_author']/stats['total_books']*100:.1f}%)")
    print(f"Com publisher: {stats['with_publisher']} ({stats['with_publisher']/stats['total_books']*100:.1f}%)")
    print(f"Com ano: {stats['with_year']} ({stats['with_year']/stats['total_books']*100:.1f}%)")
    print(f"Categorizados: {stats['with_category']} ({stats['with_category']/stats['total_books']*100:.1f}%)")
    print(f"Confiança média: {stats['avg_confidence']:.3f}")
    
    # Comparar com metas
    author_pct = stats['with_author'] / stats['total_books'] * 100
    year_pct = stats['with_year'] / stats['total_books'] * 100
    publisher_pct = stats['with_publisher'] / stats['total_books'] * 100
    
    print(f"\n=== AVALIAÇÃO CONTRA METAS ===")
    print(f"Autor (meta 40%): {'' if author_pct >= 40 else ''} {author_pct:.1f}%")
    print(f"Ano (meta 30%): {'' if year_pct >= 30 else ''} {year_pct:.1f}%")
    print(f"Publisher (meta 25%): {'' if publisher_pct >= 25 else ''} {publisher_pct:.1f}%")
    
    # Salvar resultados
    results = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'version': 'V3_Final',
        'stats': stats,
        'books_sample': books_data[:10],  # Amostra para análise
        'execution_time': time.time() - start_time,
        'meta_achievement': {
            'author': author_pct >= 40,
            'year': year_pct >= 30,
            'publisher': publisher_pct >= 25
        }
    }
    
    with open('final_v3_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # Status final
    all_metas = all(results['meta_achievement'].values())
    status = "🎯 TODAS AS METAS ATINGIDAS" if all_metas else "🔧 ALGUMAS METAS PENDENTES"
    
    print(f"\n=== RESULTADO FINAL V3 ===")
    print(f"Status: {status}")
    print(f"Tempo de execução: {time.time() - start_time:.1f}s")
    print(f"Resultados salvos em: final_v3_results.json")
    
    # Mostrar exemplos de sucesso
    print(f"\n=== EXEMPLOS DE EXTRAÇÃO SUCESSFUL ===")
    successful = [b for b in books_data if b['author'] or b['year'] or b['publisher']][:5]
    
    for i, book in enumerate(successful, 1):
        print(f"{i}. {book['filename']}")
        if book['author']:
            print(f"   Autor: {book['author']}")
        if book['year']:
            print(f"   Ano: {book['year']}")
        if book['publisher']:
            print(f"   Publisher: {book['publisher']}")
        print(f"   Confiança: {book['confidence']:.3f}")
        print()

if __name__ == "__main__":
    main()