#!/usr/bin/env python3
"""
Algoritmos com Dados Reais - Versao Corrigida
============================================

Esta versao usa APENAS dados reais extraidos dos arquivos,
sem dados mockados ou caracteres especiais.
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from difflib import SequenceMatcher
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

class RealBookDatabase:
    """Base de dados construida com arquivos reais"""
    
    def __init__(self):
        self.books = []
        self.categories = {
            'Programming': ['python', 'java', 'javascript', 'react', 'vue', 'angular', 'programming', 'code'],
            'Security': ['hacking', 'security', 'cyber', 'malware', 'forensics', 'penetration'],
            'Database': ['sql', 'mysql', 'postgresql', 'database', 'mongo', 'data', 'analytics'],
            'AI_ML': ['machine', 'learning', 'ai', 'artificial', 'data', 'science'],
            'Web': ['web', 'html', 'css', 'frontend', 'backend', 'javascript'],
            'DevOps': ['docker', 'kubernetes', 'cloud', 'aws', 'azure', 'devops'],
            'Mobile': ['android', 'ios', 'mobile', 'app'],
            'Systems': ['linux', 'windows', 'system', 'network']
        }
        
        self.publishers = {
            'Manning': ['manning', 'meap'],
            'Packt': ['packt'],
            'NoStarch': ['nostarch', 'starch'],
            'OReilly': ['oreilly', 'o\'reilly'],
            'Wiley': ['wiley'],
            'Addison': ['addison'],
            'Pearson': ['pearson']
        }
    
    def build_from_files(self, books_dir: str = "books", max_books: int = 100):
        """Construir base de dados dos arquivos reais"""
        books_path = Path(books_dir)
        
        if not books_path.exists():
            logger.error(f"Diretorio {books_dir} nao encontrado")
            return
        
        count = 0
        for file_path in books_path.iterdir():
            if count >= max_books:
                break
                
            if file_path.suffix.lower() in ['.pdf', '.epub', '.mobi'] and file_path.name != '.DS_Store':
                book_data = self._extract_book_metadata(file_path)
                if book_data:
                    self.books.append(book_data)
                    count += 1
        
        logger.info(f"Base de dados construida com {len(self.books)} livros reais")
    
    def _extract_book_metadata(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Extrair metadados reais do arquivo"""
        filename = file_path.name
        
        # Metadata basico
        metadata = {
            'filename': filename,
            'filepath': str(file_path),
            'format': file_path.suffix.lower(),
            'title': '',
            'author': '',
            'publisher': '',
            'year': '',
            'edition': '',
            'version': '',
            'category': '',
            'keywords': [],
            'confidence': 0.0
        }
        
        # Limpar nome
        clean_name = self._clean_filename(filename)
        
        # Extrair titulo
        title = self._extract_title(clean_name)
        metadata['title'] = title
        
        # Extrair publisher
        publisher = self._detect_publisher(clean_name)
        metadata['publisher'] = publisher
        
        # Extrair ano
        year = self._extract_year(clean_name)
        metadata['year'] = year
        
        # Extrair edicao
        edition = self._extract_edition(clean_name)
        metadata['edition'] = edition
        
        # Extrair versao MEAP
        version = self._extract_version(clean_name)
        metadata['version'] = version
        
        # Detectar categoria
        category = self._detect_category(clean_name)
        metadata['category'] = category
        
        # Extrair keywords
        keywords = self._extract_keywords(clean_name)
        metadata['keywords'] = keywords
        
        # Calcular confianca
        confidence = self._calculate_confidence(metadata)
        metadata['confidence'] = confidence
        
        return metadata
    
    def _clean_filename(self, filename: str) -> str:
        """Limpar nome do arquivo"""
        # Remover extensao
        name = Path(filename).stem
        
        # Remover extensoes duplas comuns
        while name.endswith(('.pdf', '.epub', '.mobi')):
            name = name[:-4]
        
        # Substituir underscores e hifens por espacos
        name = name.replace('_', ' ').replace('-', ' ')
        
        # Remover versoes MEAP
        name = re.sub(r'\s*v\d+\s*MEAP\s*', ' ', name, flags=re.IGNORECASE)
        name = re.sub(r'\s*V\d+\s*', ' ', name, flags=re.IGNORECASE)
        
        # Limpar espacos multiplos
        name = re.sub(r'\s+', ' ', name).strip()
        
        return name
    
    def _extract_title(self, text: str) -> str:
        """Extrair titulo principal"""
        # Remover padroes de edicao no final
        title = re.sub(r'\s+(Second|Third|Fourth|Fifth)\s+Edition\s*$', '', text, flags=re.IGNORECASE)
        title = re.sub(r'\s+\d+(st|nd|rd|th)\s+Edition\s*$', '', title, flags=re.IGNORECASE)
        
        # Remover anos no final
        title = re.sub(r'\s+\d{4}\s*$', '', title)
        
        return title.strip()
    
    def _detect_publisher(self, text: str) -> str:
        """Detectar publisher baseado em padroes conhecidos"""
        text_lower = text.lower()
        
        for publisher, patterns in self.publishers.items():
            for pattern in patterns:
                if pattern in text_lower:
                    return publisher
        
        return ''
    
    def _extract_year(self, text: str) -> str:
        """Extrair ano"""
        match = re.search(r'\b(19|20)\d{2}\b', text)
        return match.group(0) if match else ''
    
    def _extract_edition(self, text: str) -> str:
        """Extrair edicao"""
        patterns = [
            r'(Second|Third|Fourth|Fifth)\s+Edition',
            r'\d+(st|nd|rd|th)\s+Edition'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return ''
    
    def _extract_version(self, text: str) -> str:
        """Extrair versao MEAP"""
        if 'meap' in text.lower():
            return 'MEAP'
        return ''
    
    def _detect_category(self, text: str) -> str:
        """Detectar categoria tecnica"""
        text_lower = text.lower()
        
        # Contar matches por categoria
        category_scores = {}
        for category, keywords in self.categories.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                category_scores[category] = score
        
        if not category_scores:
            return 'General'
        
        # Retornar categoria com maior score
        return max(category_scores.items(), key=lambda x: x[1])[0]
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extrair palavras-chave relevantes"""
        text_lower = text.lower()
        keywords = []
        
        # Buscar keywords de todas as categorias
        for category_keywords in self.categories.values():
            for keyword in category_keywords:
                if keyword in text_lower:
                    keywords.append(keyword)
        
        return list(set(keywords))  # Remove duplicatas
    
    def _calculate_confidence(self, metadata: Dict[str, Any]) -> float:
        """Calcular confianca da extração"""
        score = 0.0
        
        # Pontos por campo preenchido
        if metadata['title']:
            score += 0.4
        if metadata['category'] != 'General':
            score += 0.2
        if metadata['publisher']:
            score += 0.2
        if metadata['year']:
            score += 0.1
        if metadata['edition']:
            score += 0.1
        
        return min(score, 1.0)

class RealAlgorithms:
    """Algoritmos baseados em dados reais"""
    
    def __init__(self, database: RealBookDatabase):
        self.db = database
    
    def fuzzy_search_real(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Busca fuzzy usando dados reais"""
        query_clean = query.lower().strip()
        results = []
        
        for book in self.db.books:
            title_clean = book['title'].lower()
            
            if not title_clean:
                continue
            
            # Calcular similaridade usando SequenceMatcher
            similarity = SequenceMatcher(None, query_clean, title_clean).ratio()
            
            # Bonus para palavras em comum
            query_words = set(query_clean.split())
            title_words = set(title_clean.split())
            
            if query_words and title_words:
                common_words = query_words.intersection(title_words)
                word_ratio = len(common_words) / len(query_words.union(title_words))
                similarity = max(similarity, word_ratio)
            
            # Bonus para keywords em comum
            query_keywords = set(query_clean.split())
            book_keywords = set(book['keywords'])
            
            if query_keywords and book_keywords:
                keyword_overlap = len(query_keywords.intersection(book_keywords))
                if keyword_overlap > 0:
                    similarity += 0.2 * keyword_overlap
            
            similarity = min(similarity, 1.0)
            
            if similarity > 0.1:  # Threshold minimo
                result = {
                    'title': book['title'],
                    'author': book['author'],
                    'publisher': book['publisher'],
                    'year': book['year'],
                    'category': book['category'],
                    'filename': book['filename'],
                    'similarity_score': similarity,
                    'confidence': similarity * book['confidence'],
                    'algorithm': 'fuzzy_real'
                }
                results.append(result)
        
        # Ordenar por similaridade
        results.sort(key=lambda x: x['similarity_score'], reverse=True)
        return results[:limit]
    
    def semantic_search_real(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Busca semantica usando dados reais"""
        query_clean = query.lower().strip()
        results = []
        
        # Detectar categoria da query
        query_category = self.db._detect_category(query_clean)
        query_keywords = self.db._extract_keywords(query_clean)
        
        for book in self.db.books:
            score = 0.0
            
            # Score base: palavras em comum no titulo
            title_words = set(book['title'].lower().split())
            query_words = set(query_clean.split())
            
            if title_words and query_words:
                common_words = title_words.intersection(query_words)
                base_score = len(common_words) / len(title_words.union(query_words))
                score += base_score * 0.5
            
            # Bonus por categoria igual
            if query_category != 'General' and book['category'] == query_category:
                score += 0.3
            
            # Bonus por keywords em comum
            common_keywords = set(query_keywords).intersection(set(book['keywords']))
            if common_keywords:
                keyword_bonus = len(common_keywords) / max(len(query_keywords), 1) * 0.2
                score += keyword_bonus
            
            # Bonus por publisher conhecido
            if book['publisher']:
                score += 0.1
            
            score = min(score, 1.0)
            
            if score > 0.1:
                result = {
                    'title': book['title'],
                    'author': book['author'],
                    'publisher': book['publisher'],
                    'year': book['year'],
                    'category': book['category'],
                    'filename': book['filename'],
                    'similarity_score': score,
                    'confidence': score * book['confidence'],
                    'algorithm': 'semantic_real'
                }
                results.append(result)
        
        results.sort(key=lambda x: x['similarity_score'], reverse=True)
        return results[:limit]
    
    def isbn_search_real(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Busca ISBN usando dados reais (com fallback para titulo)"""
        # Verificar se a query parece um ISBN
        isbn_pattern = r'\d{10,13}'
        if re.match(f'^{isbn_pattern}$', query.replace('-', '').replace(' ', '')):
            # É um ISBN - por enquanto retorna vazio pois nao temos ISBNs nos nomes
            return []
        else:
            # Nao é ISBN, usar busca fuzzy
            return self.fuzzy_search_real(query, limit)
    
    def orchestrator_real(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Orquestrador que combina algoritmos reais"""
        all_results = {}
        
        # Executar todos os algoritmos
        fuzzy_results = self.fuzzy_search_real(query, limit * 2)
        semantic_results = self.semantic_search_real(query, limit * 2)
        isbn_results = self.isbn_search_real(query, limit * 2)
        
        # Combinar resultados por titulo
        for results, weight in [(fuzzy_results, 1.0), (semantic_results, 1.1), (isbn_results, 1.2)]:
            for result in results:
                title_key = result['title'].lower()
                
                if title_key not in all_results:
                    result_copy = result.copy()
                    result_copy['combined_score'] = result['similarity_score'] * weight
                    result_copy['algorithms'] = [result['algorithm']]
                    all_results[title_key] = result_copy
                else:
                    # Combinar scores
                    existing = all_results[title_key]
                    new_score = (existing['combined_score'] + result['similarity_score'] * weight) / 2
                    existing['combined_score'] = new_score
                    existing['algorithms'].append(result['algorithm'])
        
        # Converter para lista e ordenar
        final_results = list(all_results.values())
        for result in final_results:
            result['similarity_score'] = result['combined_score']
            result['algorithm'] = 'orchestrator_real'
        
        final_results.sort(key=lambda x: x['combined_score'], reverse=True)
        return final_results[:limit]

class RealDataTester:
    """Testador para validar algoritmos com dados reais"""
    
    def __init__(self):
        self.database = RealBookDatabase()
        self.algorithms = None
    
    def setup(self, max_books: int = 80):
        """Configurar testador"""
        logger.info("=== CONFIGURANDO TESTADOR COM DADOS REAIS ===")
        
        # Construir base de dados
        self.database.build_from_files(max_books=max_books)
        
        # Inicializar algoritmos
        self.algorithms = RealAlgorithms(self.database)
        
        # Mostrar estatisticas da base
        self._show_database_stats()
    
    def _show_database_stats(self):
        """Mostrar estatisticas da base de dados"""
        total = len(self.database.books)
        
        with_title = sum(1 for b in self.database.books if b['title'])
        with_publisher = sum(1 for b in self.database.books if b['publisher'])
        with_year = sum(1 for b in self.database.books if b['year'])
        with_category = sum(1 for b in self.database.books if b['category'] != 'General')
        
        avg_confidence = sum(b['confidence'] for b in self.database.books) / total if total > 0 else 0
        
        logger.info(f"Base de dados: {total} livros")
        logger.info(f"Com titulo: {with_title} ({with_title/total*100:.1f}%)")
        logger.info(f"Com publisher: {with_publisher} ({with_publisher/total*100:.1f}%)")
        logger.info(f"Com ano: {with_year} ({with_year/total*100:.1f}%)")
        logger.info(f"Com categoria: {with_category} ({with_category/total*100:.1f}%)")
        logger.info(f"Confianca media: {avg_confidence:.2f}")
    
    def test_algorithm(self, algorithm_name: str, algorithm_func, test_queries: List[str]) -> Dict[str, Any]:
        """Testar um algoritmo especifico"""
        logger.info(f"\n--- TESTANDO {algorithm_name.upper()} ---")
        
        results = {
            'algorithm': algorithm_name,
            'total_queries': len(test_queries),
            'results_found': 0,
            'avg_results_per_query': 0.0,
            'avg_score': 0.0,
            'max_score': 0.0,
            'query_results': []
        }
        
        total_results = 0
        total_score = 0.0
        max_score = 0.0
        
        for i, query in enumerate(test_queries):
            search_results = algorithm_func(query, 5)
            
            query_result = {
                'query': query,
                'results_count': len(search_results),
                'best_score': search_results[0]['similarity_score'] if search_results else 0.0,
                'results': search_results[:3]  # Top 3 apenas
            }
            
            results['query_results'].append(query_result)
            
            if search_results:
                results['results_found'] += 1
                total_results += len(search_results)
                
                for result in search_results:
                    score = result['similarity_score']
                    total_score += score
                    max_score = max(max_score, score)
            
            # Log progresso
            logger.info(f"Query {i+1}: '{query}' -> {len(search_results)} resultados (melhor: {query_result['best_score']:.2f})")
        
        # Calcular estatisticas
        results['avg_results_per_query'] = total_results / len(test_queries) if test_queries else 0
        results['avg_score'] = total_score / total_results if total_results > 0 else 0
        results['max_score'] = max_score
        
        logger.info(f"Resumo {algorithm_name}:")
        logger.info(f"  Queries com resultados: {results['results_found']}/{results['total_queries']}")
        logger.info(f"  Media de resultados por query: {results['avg_results_per_query']:.1f}")
        logger.info(f"  Score medio: {results['avg_score']:.2f}")
        logger.info(f"  Score maximo: {results['max_score']:.2f}")
        
        return results
    
    def run_comprehensive_test(self):
        """Executar teste abrangente"""
        logger.info("\n=== TESTE ABRANGENTE COM DADOS REAIS ===")
        
        # Queries de teste baseadas nos livros reais
        test_queries = [
            "Python Programming",
            "JavaScript React",
            "Machine Learning AI",
            "Web Development",
            "Database SQL",
            "Security Hacking",
            "Docker Kubernetes",
            "Data Science",
            "Ethical Hacking",
            "Network Security",
            "Android Mobile",
            "Algorithms Programming",
            "Cloud Computing",
            "Forensics Investigation",
            "Malware Analysis"
        ]
        
        # Algoritmos para testar
        algorithms_to_test = [
            ('fuzzy_real', self.algorithms.fuzzy_search_real),
            ('semantic_real', self.algorithms.semantic_search_real),
            ('isbn_real', self.algorithms.isbn_search_real),
            ('orchestrator_real', self.algorithms.orchestrator_real)
        ]
        
        all_results = {}
        
        # Testar cada algoritmo
        for algo_name, algo_func in algorithms_to_test:
            result = self.test_algorithm(algo_name, algo_func, test_queries)
            all_results[algo_name] = result
        
        # Analise comparativa
        self._comparative_analysis(all_results)
        
        return all_results
    
    def _comparative_analysis(self, results: Dict[str, Any]):
        """Analise comparativa dos algoritmos"""
        logger.info("\n=== ANALISE COMPARATIVA ===")
        
        # Tabela de comparacao
        logger.info("Algoritmo        | Queries OK | Avg Results | Avg Score | Max Score")
        logger.info("-" * 65)
        
        best_algo = None
        best_score = 0.0
        
        for algo_name, result in results.items():
            queries_ok = result['results_found']
            total_queries = result['total_queries']
            avg_results = result['avg_results_per_query']
            avg_score = result['avg_score']
            max_score = result['max_score']
            
            logger.info(f"{algo_name:15} | {queries_ok:2d}/{total_queries:2d}     | {avg_results:8.1f}   | {avg_score:7.2f}   | {max_score:7.2f}")
            
            if avg_score > best_score:
                best_score = avg_score
                best_algo = algo_name
        
        logger.info("-" * 65)
        logger.info(f"MELHOR ALGORITMO: {best_algo} (score: {best_score:.2f})")
        
        # Validacao final
        if best_score >= 0.7:
            logger.info("STATUS: EXCELENTE - Algoritmos funcionando bem com dados reais")
        elif best_score >= 0.5:
            logger.info("STATUS: BOM - Algoritmos funcionais, podem ser melhorados")
        elif best_score >= 0.3:
            logger.info("STATUS: REGULAR - Algoritmos precisam de ajustes")
        else:
            logger.info("STATUS: INADEQUADO - Algoritmos precisam ser revisados")

def main():
    """Funcao principal"""
    tester = RealDataTester()
    tester.setup(max_books=80)
    results = tester.run_comprehensive_test()
    
    # Salvar resultados
    output_file = Path("real_data_test_results.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    
    logger.info(f"\nResultados salvos em: {output_file}")

if __name__ == "__main__":
    main()