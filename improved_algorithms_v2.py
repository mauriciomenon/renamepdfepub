#!/usr/bin/env python3
"""
Algoritmos Melhorados v2 - Correcoes Baseadas em Dados Reais
============================================================

Versao corrigida baseada na analise dos resultados reais.
Foca em melhorar extração de metadados e performance semantica.
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from difflib import SequenceMatcher
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

class ImprovedMetadataExtractor:
    """Extrator melhorado baseado em padroes reais identificados"""
    
    def __init__(self):
        # Publishers com padroes mais robustos
        self.publisher_patterns = {
            'Manning': [r'manning', r'meap', r'Month of Lunches'],
            'Packt': [r'packt', r'cookbook'],
            'NoStarch': [r'no\s*starch', r'black\s*hat', r'ethical\s*hacking'],
            'OReilly': [r'o\'?reilly', r'animal\s*book'],
            'Wiley': [r'wiley', r'sybex'],
            'Addison': [r'addison', r'wesley'],
            'Pragmatic': [r'pragmatic', r'programmer'],
            'MIT': [r'mit\s*press'],
            'Cambridge': [r'cambridge'],
            'Apress': [r'apress'],
            'Syngress': [r'syngress']
        }
        
        # Categorias expandidas com sinonimos
        self.enhanced_categories = {
            'Programming': [
                'python', 'java', 'javascript', 'js', 'react', 'vue', 'angular',
                'programming', 'code', 'coding', 'development', 'dev', 'software',
                'algorithm', 'algorithms', 'data structures', 'functional',
                'object oriented', 'oop', 'design patterns'
            ],
            'Security': [
                'security', 'hacking', 'hack', 'cyber', 'cybersecurity',
                'malware', 'forensics', 'forensic', 'penetration', 'pentest',
                'ethical', 'bug bounty', 'vulnerability', 'exploitation',
                'incident', 'analysis', 'investigation'
            ],
            'Database': [
                'database', 'db', 'sql', 'mysql', 'postgresql', 'postgres',
                'mongo', 'mongodb', 'redis', 'cassandra', 'data',
                'analytics', 'analysis', 'warehouse', 'engineering'
            ],
            'AI_ML': [
                'machine learning', 'ml', 'ai', 'artificial intelligence',
                'data science', 'deep learning', 'neural', 'tensorflow',
                'pytorch', 'scikit', 'pandas', 'numpy', 'statistics'
            ],
            'Web': [
                'web', 'website', 'html', 'css', 'frontend', 'backend',
                'full stack', 'fullstack', 'responsive', 'ui', 'ux',
                'design', 'user experience'
            ],
            'DevOps': [
                'devops', 'docker', 'kubernetes', 'k8s', 'cloud',
                'aws', 'azure', 'gcp', 'infrastructure', 'deployment',
                'automation', 'ci/cd', 'continuous integration'
            ],
            'Mobile': [
                'mobile', 'android', 'ios', 'app', 'application',
                'swift', 'kotlin', 'react native', 'flutter'
            ],
            'Systems': [
                'linux', 'windows', 'unix', 'system', 'systems',
                'network', 'networking', 'server', 'administration'
            ]
        }
        
        # Padroes de autor melhorados
        self.author_patterns = [
            r'by\s+([A-Za-z\s\.]{3,40}?)(?:\s*-|\s*\(|\s*,|\s*$)',
            r'^([A-Za-z\s\.]{3,25}?)\s*-\s*',
            r'-\s*([A-Za-z\s\.]{3,25}?)(?:\s*-|\s*$)',
            r'Author:\s*([A-Za-z\s\.]{3,30})',
            r'([A-Za-z]+\s+[A-Za-z]+)\s*presents',
            r'with\s+([A-Za-z\s\.]{3,25}?)(?:\s|$)'
        ]
    
    def extract_enhanced_metadata(self, filename: str) -> Dict[str, Any]:
        """Extrair metadados com melhorias baseadas nos testes reais"""
        
        metadata = {
            'filename': filename,
            'title': '',
            'author': '',
            'publisher': '',
            'year': '',
            'edition': '',
            'version': '',
            'category': '',
            'subcategory': '',
            'keywords': [],
            'language': 'English',
            'confidence': 0.0,
            'extraction_details': {}
        }
        
        # Limpar nome
        clean_name = self._advanced_clean(filename)
        metadata['extraction_details']['cleaned_name'] = clean_name
        
        # Extrações melhoradas
        metadata['title'] = self._extract_enhanced_title(clean_name)
        metadata['author'] = self._extract_enhanced_author(clean_name)
        metadata['publisher'] = self._detect_enhanced_publisher(clean_name)
        metadata['year'] = self._extract_enhanced_year(clean_name)
        metadata['edition'] = self._extract_enhanced_edition(clean_name)
        metadata['version'] = self._extract_enhanced_version(clean_name)
        metadata['category'] = self._detect_enhanced_category(clean_name)
        metadata['subcategory'] = self._detect_subcategory(clean_name, metadata['category'])
        metadata['keywords'] = self._extract_enhanced_keywords(clean_name)
        metadata['language'] = self._detect_language(clean_name)
        
        # Confiança melhorada
        metadata['confidence'] = self._calculate_enhanced_confidence(metadata)
        
        return metadata
    
    def _advanced_clean(self, filename: str) -> str:
        """Limpeza avançada baseada nos padroes reais"""
        name = Path(filename).stem
        
        # Remover extensoes duplas/triplas
        extensions = ['.pdf', '.epub', '.mobi', '.azw3', '.txt']
        for ext in extensions:
            while name.lower().endswith(ext):
                name = name[:-len(ext)]
        
        # Padroes especificos identificados
        name = re.sub(r'_v\d+_MEAP', '', name, flags=re.IGNORECASE)
        name = re.sub(r'_V\d+', '', name, flags=re.IGNORECASE)
        name = re.sub(r'_MEAP\d*', '', name, flags=re.IGNORECASE)
        name = re.sub(r'_Second_Edition', ' Second Edition', name)
        name = re.sub(r'_Third_Edition', ' Third Edition', name)
        
        # Substituir separadores
        name = name.replace('_', ' ').replace('-', ' ')
        
        # Limpar espacos e caracteres especiais
        name = re.sub(r'\s+', ' ', name)
        name = re.sub(r'[^\w\s\.\(\)\[\]]', ' ', name)
        name = name.strip()
        
        return name
    
    def _extract_enhanced_title(self, text: str) -> str:
        """Extração de titulo melhorada"""
        title = text
        
        # Remover autor patterns
        for pattern in self.author_patterns:
            title = re.sub(pattern, '', title, flags=re.IGNORECASE)
        
        # Remover edicoes no final
        title = re.sub(r'\s+(Second|Third|Fourth|Fifth|Sixth)\s+Edition\s*$', '', title, flags=re.IGNORECASE)
        title = re.sub(r'\s+\d+(st|nd|rd|th)\s+Edition\s*$', '', title, flags=re.IGNORECASE)
        
        # Remover anos
        title = re.sub(r'\s+\b(19|20)\d{2}\b.*$', '', title)
        
        # Remover publishers conhecidos no final
        for publisher in self.publisher_patterns.keys():
            title = re.sub(f'\\s+{re.escape(publisher)}.*$', '', title, flags=re.IGNORECASE)
        
        # Limpar
        title = re.sub(r'\s+', ' ', title).strip()
        
        return title
    
    def _extract_enhanced_author(self, text: str) -> str:
        """Extração de autor melhorada"""
        for pattern in self.author_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                author = match.group(1).strip()
                # Validar se parece nome de autor
                if len(author) >= 3 and ' ' in author and not any(digit in author for digit in '0123456789'):
                    return author
        
        return ''
    
    def _detect_enhanced_publisher(self, text: str) -> str:
        """Detecção de publisher melhorada"""
        text_lower = text.lower()
        
        # Buscar padroes especificos por publisher
        for publisher, patterns in self.publisher_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return publisher
        
        # Padroes genericos baseados nos dados reais
        if 'cookbook' in text_lower:
            return 'Packt'
        elif 'exploring' in text_lower:
            return 'Manning'
        elif 'learn' in text_lower and ('month' in text_lower or 'lunches' in text_lower):
            return 'Manning'
        elif 'black hat' in text_lower or 'ethical hacking' in text_lower:
            return 'No Starch'
        
        return ''
    
    def _extract_enhanced_year(self, text: str) -> str:
        """Extração de ano melhorada"""
        # Buscar anos em varios contextos
        patterns = [
            r'\b(19|20)(\d{2})\b',
            r'Edition\s*(\d{4})',
            r'(\d{4})\s*Edition',
            r'Copyright\s*(\d{4})',
            r'Published\s*(\d{4})'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                if isinstance(matches[0], tuple):
                    year = matches[0][0] + matches[0][1]
                else:
                    year = matches[0]
                
                # Validar ano razoavel
                year_int = int(year)
                if 1990 <= year_int <= 2030:
                    return year
        
        return ''
    
    def _extract_enhanced_edition(self, text: str) -> str:
        """Extração de edição melhorada"""
        patterns = [
            r'(Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth)\s+Edition',
            r'(\d+)(st|nd|rd|th)\s+Edition',
            r'Edition\s+(\d+)',
            r'(\d+)e\s+Edition'  # Para "2e Edition"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return ''
    
    def _extract_enhanced_version(self, text: str) -> str:
        """Extração de versão melhorada"""
        if re.search(r'meap', text, re.IGNORECASE):
            version_match = re.search(r'v(\d+)', text, re.IGNORECASE)
            if version_match:
                return f"v{version_match.group(1)} MEAP"
            else:
                return "MEAP"
        
        return ''
    
    def _detect_enhanced_category(self, text: str) -> str:
        """Detecção de categoria melhorada"""
        text_lower = text.lower()
        
        # Contar matches ponderados por categoria
        category_scores = {}
        
        for category, keywords in self.enhanced_categories.items():
            score = 0
            for keyword in keywords:
                if keyword in text_lower:
                    # Peso baseado na especificidade
                    weight = 2.0 if len(keyword.split()) > 1 else 1.0
                    score += weight
            
            if score > 0:
                category_scores[category] = score
        
        if not category_scores:
            return 'General'
        
        # Retornar categoria com maior score
        best_category = max(category_scores.items(), key=lambda x: x[1])
        return best_category[0]
    
    def _detect_subcategory(self, text: str, main_category: str) -> str:
        """Detectar subcategoria dentro da categoria principal"""
        text_lower = text.lower()
        
        subcategories = {
            'Programming': {
                'Python': ['python'],
                'JavaScript': ['javascript', 'js', 'react', 'vue', 'angular', 'node'],
                'Java': ['java'],
                'C/C++': ['c++', 'cpp', 'c programming'],
                'Functional': ['functional', 'haskell', 'lisp', 'scala']
            },
            'Security': {
                'Ethical Hacking': ['ethical', 'penetration', 'pentest'],
                'Malware': ['malware', 'virus', 'trojan'],
                'Forensics': ['forensic', 'investigation', 'incident'],
                'Web Security': ['web security', 'sql injection', 'xss']
            },
            'Database': {
                'SQL': ['sql', 'mysql', 'postgresql'],
                'NoSQL': ['mongo', 'redis', 'cassandra'],
                'Analytics': ['analytics', 'analysis', 'science']
            }
        }
        
        if main_category in subcategories:
            for subcat, keywords in subcategories[main_category].items():
                if any(keyword in text_lower for keyword in keywords):
                    return subcat
        
        return ''
    
    def _extract_enhanced_keywords(self, text: str) -> List[str]:
        """Extração de palavras-chave melhorada"""
        text_lower = text.lower()
        keywords = set()
        
        # Buscar todas as keywords de todas as categorias
        for category_keywords in self.enhanced_categories.values():
            for keyword in category_keywords:
                if keyword in text_lower:
                    keywords.add(keyword)
        
        # Adicionar termos tecnicos especificos
        tech_terms = [
            'api', 'rest', 'graphql', 'microservices', 'container',
            'kubernetes', 'docker', 'cloud', 'aws', 'azure',
            'tensorflow', 'pytorch', 'pandas', 'numpy', 'scipy'
        ]
        
        for term in tech_terms:
            if term in text_lower:
                keywords.add(term)
        
        return sorted(list(keywords))
    
    def _detect_language(self, text: str) -> str:
        """Detectar idioma"""
        portuguese_indicators = [
            'aprenda', 'programar', 'com', 'desenvolvimento',
            'orientacao', 'objetos', 'conceitos', 'aplicabilidades'
        ]
        
        if any(indicator in text.lower() for indicator in portuguese_indicators):
            return 'Portuguese'
        
        return 'English'
    
    def _calculate_enhanced_confidence(self, metadata: Dict[str, Any]) -> float:
        """Calcular confiança melhorada"""
        score = 0.0
        
        # Titulo sempre presente
        if metadata['title']:
            score += 0.3
        
        # Metadados extraidos
        if metadata['author']:
            score += 0.15
        if metadata['publisher']:
            score += 0.15
        if metadata['year']:
            score += 0.1
        if metadata['edition']:
            score += 0.1
        
        # Categorizacao
        if metadata['category'] != 'General':
            score += 0.1
        if metadata['subcategory']:
            score += 0.05
        
        # Keywords
        if len(metadata['keywords']) > 0:
            score += min(len(metadata['keywords']) * 0.02, 0.05)
        
        return min(score, 1.0)

class EnhancedRealAlgorithms:
    """Algoritmos melhorados baseados na análise dos dados reais"""
    
    def __init__(self, books_data: List[Dict[str, Any]]):
        self.books_data = books_data
        self.extractor = ImprovedMetadataExtractor()
    
    def enhanced_fuzzy_search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Busca fuzzy melhorada"""
        query_clean = query.lower().strip()
        results = []
        
        for book in self.books_data:
            title_clean = book['title'].lower()
            
            if not title_clean:
                continue
            
            # Similaridade base
            similarity = SequenceMatcher(None, query_clean, title_clean).ratio()
            
            # Melhorias baseadas nos resultados reais
            
            # 1. Bonus para palavras completas em comum
            query_words = set(query_clean.split())
            title_words = set(title_clean.split())
            
            if query_words and title_words:
                common_words = query_words.intersection(title_words)
                exact_word_bonus = len(common_words) / len(query_words) * 0.4
                similarity += exact_word_bonus
            
            # 2. Bonus para keywords tecnicas
            query_keywords = set(self.extractor._extract_enhanced_keywords(query))
            book_keywords = set(book.get('keywords', []))
            
            if query_keywords and book_keywords:
                keyword_overlap = len(query_keywords.intersection(book_keywords))
                keyword_bonus = keyword_overlap * 0.15
                similarity += keyword_bonus
            
            # 3. Bonus para categoria matching
            book_cat = book.get('category', 'General')
            query_cat = self.extractor._detect_enhanced_category(query)
            
            if book_cat != 'General' and book_cat == query_cat:
                similarity += 0.2
            
            # 4. Bonus para publisher conhecido
            if book.get('publisher'):
                similarity += 0.05
            
            # 5. Penalty para matches muito genericos
            if len(title_clean.split()) > 1 and any(word in title_clean for word in ['guide', 'book', 'manual']):
                if not any(qword in title_clean for qword in query_clean.split()):
                    similarity *= 0.9
            
            similarity = min(similarity, 1.0)
            
            if similarity > 0.15:  # Threshold ajustado
                result = {
                    'title': book['title'],
                    'author': book.get('author', ''),
                    'publisher': book.get('publisher', ''),
                    'year': book.get('year', ''),
                    'category': book.get('category', ''),
                    'subcategory': book.get('subcategory', ''),
                    'filename': book['filename'],
                    'similarity_score': similarity,
                    'confidence': similarity * book.get('confidence', 0.5),
                    'algorithm': 'enhanced_fuzzy'
                }
                results.append(result)
        
        results.sort(key=lambda x: x['similarity_score'], reverse=True)
        return results[:limit]
    
    def enhanced_semantic_search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Busca semantica melhorada (corrigindo o score baixo)"""
        query_clean = query.lower().strip()
        results = []
        
        # Análise da query
        query_category = self.extractor._detect_enhanced_category(query)
        query_keywords = set(self.extractor._extract_enhanced_keywords(query))
        query_words = set(query_clean.split())
        
        for book in self.books_data:
            score = 0.0
            
            title_words = set(book['title'].lower().split())
            book_keywords = set(book.get('keywords', []))
            book_category = book.get('category', 'General')
            
            # 1. Score base melhorado - intersecao de palavras
            if title_words and query_words:
                common_words = title_words.intersection(query_words)
                word_score = len(common_words) / len(query_words.union(title_words))
                score += word_score * 0.4
            
            # 2. Categoria matching com peso maior
            if query_category != 'General' and book_category == query_category:
                score += 0.35  # Aumentado de 0.3
            
            # 3. Keywords matching melhorado
            if query_keywords and book_keywords:
                common_keywords = query_keywords.intersection(book_keywords)
                keyword_score = len(common_keywords) / len(query_keywords) if query_keywords else 0
                score += keyword_score * 0.25  # Aumentado de 0.2
            
            # 4. Subcategoria bonus
            book_subcat = book.get('subcategory', '')
            if book_subcat and any(word in book_subcat.lower() for word in query_words):
                score += 0.15
            
            # 5. Publisher reliability bonus
            publisher = book.get('publisher', '')
            if publisher in ['Manning', 'Packt', 'OReilly', 'No Starch']:
                score += 0.1
            
            # 6. Exact phrase matching
            if len(query_clean) > 3 and query_clean in book['title'].lower():
                score += 0.3
            
            # 7. Penalidade para matches muito vagos
            if score > 0 and len(common_words) == 0 if 'common_words' in locals() else False:
                score *= 0.7
            
            score = min(score, 1.0)
            
            if score > 0.2:  # Threshold aumentado
                result = {
                    'title': book['title'],
                    'author': book.get('author', ''),
                    'publisher': book.get('publisher', ''),
                    'year': book.get('year', ''),
                    'category': book.get('category', ''),
                    'subcategory': book.get('subcategory', ''),
                    'filename': book['filename'],
                    'similarity_score': score,
                    'confidence': score * book.get('confidence', 0.5),
                    'algorithm': 'enhanced_semantic'
                }
                results.append(result)
        
        results.sort(key=lambda x: x['similarity_score'], reverse=True)
        return results[:limit]
    
    def enhanced_orchestrator(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Orquestrador melhorado com weights otimizados"""
        all_results = {}
        
        # Executar algoritmos com pesos ajustados
        fuzzy_results = self.enhanced_fuzzy_search(query, limit * 2)
        semantic_results = self.enhanced_semantic_search(query, limit * 2)
        
        # Weights baseados na performance observada
        weights = {
            'enhanced_fuzzy': 1.0,    # Base
            'enhanced_semantic': 0.8  # Reduzido devido ao score mais baixo
        }
        
        # Combinar resultados
        for results, weight in [(fuzzy_results, weights['enhanced_fuzzy']), 
                               (semantic_results, weights['enhanced_semantic'])]:
            for result in results:
                title_key = result['title'].lower()
                
                if title_key not in all_results:
                    result_copy = result.copy()
                    result_copy['combined_score'] = result['similarity_score'] * weight
                    result_copy['algorithms'] = [result['algorithm']]
                    result_copy['algorithm_count'] = 1
                    all_results[title_key] = result_copy
                else:
                    # Combinacao inteligente
                    existing = all_results[title_key]
                    existing['algorithm_count'] += 1
                    
                    # Bonus para resultados que aparecem em multiplos algoritmos
                    multi_algo_bonus = 1.0 + (existing['algorithm_count'] - 1) * 0.1
                    
                    # Media ponderada com bonus
                    current_score = existing['combined_score']
                    new_contribution = result['similarity_score'] * weight
                    combined = (current_score + new_contribution) / 2 * multi_algo_bonus
                    
                    existing['combined_score'] = min(combined, 1.0)
                    existing['algorithms'].append(result['algorithm'])
        
        # Converter para lista final
        final_results = list(all_results.values())
        for result in final_results:
            result['similarity_score'] = result['combined_score']
            result['algorithm'] = 'enhanced_orchestrator'
        
        final_results.sort(key=lambda x: x['combined_score'], reverse=True)
        return final_results[:limit]

def main():
    """Teste dos algoritmos melhorados"""
    logger.info("=== ALGORITMOS MELHORADOS V2 ===")
    
    # Carregar dados da base anterior para comparacao
    try:
        with open('real_data_test_results.json', 'r') as f:
            previous_data = json.load(f)
        logger.info("Dados anteriores carregados para comparacao")
    except FileNotFoundError:
        logger.info("Executando primeira vez - sem dados de comparacao")
        previous_data = None
    
    # Construir base melhorada
    books_dir = Path("books")
    extractor = ImprovedMetadataExtractor()
    enhanced_books = []
    
    count = 0
    for file_path in books_dir.iterdir():
        if count >= 80:
            break
        if file_path.suffix.lower() in ['.pdf', '.epub', '.mobi'] and file_path.name != '.DS_Store':
            metadata = extractor.extract_enhanced_metadata(file_path.name)
            enhanced_books.append(metadata)
            count += 1
    
    logger.info(f"Base melhorada criada com {len(enhanced_books)} livros")
    
    # Estatisticas da base melhorada
    with_author = sum(1 for b in enhanced_books if b['author'])
    with_publisher = sum(1 for b in enhanced_books if b['publisher'])
    with_year = sum(1 for b in enhanced_books if b['year'])
    avg_confidence = sum(b['confidence'] for b in enhanced_books) / len(enhanced_books)
    
    logger.info(f"Com autor: {with_author} ({with_author/len(enhanced_books)*100:.1f}%)")
    logger.info(f"Com publisher: {with_publisher} ({with_publisher/len(enhanced_books)*100:.1f}%)")
    logger.info(f"Com ano: {with_year} ({with_year/len(enhanced_books)*100:.1f}%)")
    logger.info(f"Confianca media: {avg_confidence:.2f}")
    
    # Testar algoritmos melhorados
    algorithms = EnhancedRealAlgorithms(enhanced_books)
    
    test_queries = [
        "Python Programming",
        "JavaScript React", 
        "Machine Learning",
        "Database SQL",
        "Security Hacking"
    ]
    
    logger.info("\n=== TESTE RAPIDO ===")
    for query in test_queries:
        logger.info(f"\nQuery: '{query}'")
        
        # Testar algoritmo melhorado
        results = algorithms.enhanced_orchestrator(query, 3)
        logger.info(f"Enhanced Orchestrator ({len(results)} resultados):")
        for r in results:
            logger.info(f"  - {r['title'][:50]}... (score: {r['similarity_score']:.2f})")
    
    logger.info("\n=== MELHORIAS IMPLEMENTADAS ===")
    logger.info("1. Extração de metadados melhorada")
    logger.info("2. Algoritmo semantico fortalecido") 
    logger.info("3. Weights otimizados no orchestrator")
    logger.info("4. Bonus para resultados multi-algoritmo")
    logger.info("5. Thresholds ajustados")

if __name__ == "__main__":
    main()