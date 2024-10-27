import PyPDF2
import re
import requests
import time
from pathlib import Path
import json
import sqlite3
from concurrent import futures
from collections import Counter
import difflib
from typing import Dict, List, Optional, Set, Tuple
import logging
from dataclasses import dataclass, asdict
import unicodedata
from urllib.parse import quote
import xml.etree.ElementTree as ET
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
import argparse
import sys
import time

# Configurações de editoras e padrões
BRAZILIAN_PUBLISHERS = {
    'casa do codigo': {
        'pattern': r'Casa do [cC]ódigo.*?ISBN[:\s]*(97[89][-\s]*(?:\d[-\s]*){9}\d)',
        'confidence_boost': 0.1
    },
    'novatec': {
        'pattern': r'Novatec\s+Editora.*?ISBN[:\s]*(97[89][-\s]*(?:\d[-\s]*){9}\d)',
        'confidence_boost': 0.1
    },
    'alta books': {
        'pattern': r'Alta\s+Books.*?ISBN[:\s]*(97[89][-\s]*(?:\d[-\s]*){9}\d)',
        'confidence_boost': 0.1
    }
}

INTERNATIONAL_PUBLISHERS = {
    'packt': {
        'pattern': r'Packt\s+Publishing.*?ISBN[:\s]*(97[89][-\s]*(?:\d[-\s]*){9}\d)',
        'confidence_boost': 0.1,
        'corrupted_chars': {'@': '9', '>': '7', '?': '8', '_': '-'}
    },
    'oreilly': {
        'pattern': r"O'Reilly\s+Media.*?ISBN[:\s]*(97[89][-\s]*(?:\d[-\s]*){9}\d)",
        'confidence_boost': 0.1
    },
    'wiley': {
        'pattern': r'(?:John\s+)?Wiley\s+&\s+Sons.*?ISBN[:\s]*(97[89][-\s]*(?:\d[-\s]*){9}\d)',
        'confidence_boost': 0.1
    },
    'apress': {
        'pattern': r'Apress.*?ISBN[:\s]*(97[89][-\s]*(?:\d[-\s]*){9}\d)',
        'confidence_boost': 0.1
    }
}

@dataclass
class BookMetadata:
    title: str
    authors: List[str]
    publisher: str
    published_date: str
    isbn_10: Optional[str] = None
    isbn_13: Optional[str] = None
    confidence_score: float = 0.0
    source: str = "unknown"
    file_path: Optional[str] = None
    
class MetadataCache:
    def __init__(self, db_path: str = "metadata_cache.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metadata_cache (
                    isbn TEXT PRIMARY KEY,
                    metadata_json TEXT,
                    timestamp INTEGER,
                    publisher TEXT,
                    confidence_score REAL
                )
            """)

    def get(self, isbn: str) -> Optional[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute("""
                SELECT metadata_json 
                FROM metadata_cache 
                WHERE isbn = ? AND timestamp > ?
                """, 
                (isbn, int(time.time()) - 30*24*60*60)  # 30 dias de cache
            ).fetchone()
            return json.loads(result[0]) if result else None

    def set(self, isbn: str, metadata: Dict):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO metadata_cache 
                   (isbn, metadata_json, timestamp, publisher, confidence_score) 
                   VALUES (?, ?, ?, ?, ?)""",
                (isbn, json.dumps(metadata), int(time.time()),
                 metadata.get('publisher', 'unknown'),
                 metadata.get('confidence_score', 0.0))
            )
            
class ISBNExtractor:
    def __init__(self):
        self.isbn_patterns = [
            # Padrões básicos de ISBN
            r'ISBN(?:-13)?:?\s*(978[\d-]+)',
            r'ISBN(?:-10)?:?\s*([\dX-]{10,})',
            r'978[\d-]{10,}',
            r'[\dX-]{10,13}',
            
            # Padrões avançados
            r'ISBN(?:[\s-]*(?:Impresso|PDF|EPUB|MOBI)?:?)?\s*(97[89][-\s]*(?:\d[-\s]*){9}\d)',
            r'DOI:.*?ISBN:\s*(97[89][-\s]*(?:\d[-\s]*){9}\d)',
            
            # Padrão para múltiplos ISBNs (pega o primeiro)
            r'ISBN(?:s)?:?\s*(97[89][-\s]*(?:\d[-\s]*){9}\d)(?:\s*(?:(?:e|E)bk|EPUB|MOBI|PDF|Impresso)?)',
        ]
        
        # Adiciona padrões de editoras
        self.isbn_patterns.extend([pub['pattern'] for pub in BRAZILIAN_PUBLISHERS.values()])
        self.isbn_patterns.extend([pub['pattern'] for pub in INTERNATIONAL_PUBLISHERS.values()])

    def normalize_isbn(self, isbn: str) -> str:
        return re.sub(r'[^0-9X]', '', isbn.upper())

    def identify_publisher(self, text: str) -> Tuple[str, float]:
        """Identifica a editora e retorna boost de confiança."""
        text_lower = text.lower()
        
        for publisher, info in {**BRAZILIAN_PUBLISHERS, **INTERNATIONAL_PUBLISHERS}.items():
            if re.search(info['pattern'], text, re.IGNORECASE):
                return publisher, info['confidence_boost']
        
        return "unknown", 0.0

    def clean_corrupted_isbn(self, isbn: str, publisher: str) -> str:
        """Limpa ISBNs com caracteres corrompidos."""
        if publisher in INTERNATIONAL_PUBLISHERS and 'corrupted_chars' in INTERNATIONAL_PUBLISHERS[publisher]:
            chars = INTERNATIONAL_PUBLISHERS[publisher]['corrupted_chars']
            for corrupt, clean in chars.items():
                isbn = isbn.replace(corrupt, clean)
        return isbn

    def validate_isbn_10(self, isbn: str) -> bool:
        if len(isbn) != 10:
            return False
        
        try:
            total = 0
            for i in range(9):
                total += int(isbn[i]) * (10 - i)
            
            if isbn[9] == 'X':
                total += 10
            else:
                total += int(isbn[9])
                
            return total % 11 == 0
        except:
            return False

    def validate_isbn_13(self, isbn: str) -> bool:
        if len(isbn) != 13:
            return False
        
        try:
            total = 0
            for i in range(12):
                if i % 2 == 0:
                    total += int(isbn[i])
                else:
                    total += int(isbn[i]) * 3
                    
            check = (10 - (total % 10)) % 10
            return check == int(isbn[12])
        except:
            return False

    def isbn_10_to_13(self, isbn10: str) -> str:
        if len(isbn10) != 10:
            return None
            
        prefix = "978" + isbn10[:-1]
        
        total = 0
        for i in range(12):
            if i % 2 == 0:
                total += int(prefix[i])
            else:
                total += int(prefix[i]) * 3
                
        check = (10 - (total % 10)) % 10
        return prefix + str(check)

    def extract_from_text(self, text: str) -> Set[str]:
        """Extrai todos os ISBNs possíveis do texto."""
        found_isbns = set()
        publisher, confidence_boost = self.identify_publisher(text)
        
        for pattern in self.isbn_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                isbn = match.group(1) if '(' in pattern else match.group()
                isbn = self.normalize_isbn(isbn)
                isbn = self.clean_corrupted_isbn(isbn, publisher)
                
                if self.validate_isbn_10(isbn):
                    found_isbns.add(isbn)
                    isbn13 = self.isbn_10_to_13(isbn)
                    if isbn13:
                        found_isbns.add(isbn13)
                elif self.validate_isbn_13(isbn):
                    found_isbns.add(isbn)
        
        return found_isbns
    
class MetadataFetcher:
    def __init__(self, isbndb_api_key: Optional[str] = None):
        self.cache = MetadataCache()
        self.session = requests.Session()
        self.isbndb_api_key = isbndb_api_key
        
        # Configuração de retry mais robusta
        retry_strategy = Retry(
            total=5,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
        )
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=100,
            pool_maxsize=100
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; BookMetadataBot/1.0)'
        })

    def fetch_google_books(self, isbn: str) -> Optional[BookMetadata]:
        """Busca na API do Google Books global."""
        try:
            url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
            response = self.session.get(url, timeout=10)
            data = response.json()
            
            if 'items' not in data:
                return None
                
            book_info = data['items'][0]['volumeInfo']
            
            return BookMetadata(
                title=book_info.get('title', 'Unknown'),
                authors=book_info.get('authors', ['Unknown']),
                publisher=book_info.get('publisher', 'Unknown'),
                published_date=book_info.get('publishedDate', 'Unknown'),
                isbn_13=isbn if len(isbn) == 13 else None,
                isbn_10=isbn if len(isbn) == 10 else None,
                confidence_score=0.9,
                source='google_books'
            )
        except Exception as e:
            logging.error(f"Google Books API error: {str(e)}")
            return None

    def fetch_google_books_br(self, isbn: str) -> Optional[BookMetadata]:
        """Busca na API do Google Books com filtro para Brasil."""
        try:
            url = f"https://www.googleapis.com/books/v1/volumes"
            params = {
                'q': f'isbn:{isbn}',
                'country': 'BR',
                'langRestrict': 'pt'
            }
            
            response = self.session.get(url, params=params, timeout=10)
            data = response.json()
            
            if 'items' not in data:
                return None
                
            book_info = data['items'][0]['volumeInfo']
            
            return BookMetadata(
                title=book_info.get('title', 'Unknown'),
                authors=book_info.get('authors', ['Unknown']),
                publisher=book_info.get('publisher', 'Unknown'),
                published_date=book_info.get('publishedDate', 'Unknown'),
                isbn_13=isbn if len(isbn) == 13 else None,
                isbn_10=isbn if len(isbn) == 10 else None,
                confidence_score=0.9,
                source='google_books_br'
            )
        except Exception as e:
            logging.error(f"Google Books BR API error: {str(e)}")
            return None

    def fetch_openlibrary(self, isbn: str) -> Optional[BookMetadata]:
        try:
            url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
            response = self.session.get(url, timeout=10)
            data = response.json()
            
            if f"ISBN:{isbn}" not in data:
                return None
                
            book_info = data[f"ISBN:{isbn}"]
            
            return BookMetadata(
                title=book_info.get('title', 'Unknown'),
                authors=[author['name'] for author in book_info.get('authors', [])],
                publisher=book_info.get('publishers', [{'name': 'Unknown'}])[0]['name'],
                published_date=book_info.get('publish_date', 'Unknown'),
                isbn_13=isbn if len(isbn) == 13 else None,
                isbn_10=isbn if len(isbn) == 10 else None,
                confidence_score=0.8,
                source='openlibrary'
            )
        except Exception as e:
            logging.error(f"Open Library API error: {str(e)}")
            return None

    def fetch_worldcat(self, isbn: str) -> Optional[BookMetadata]:
        """Busca metadados do WorldCat com melhor tratamento de erros."""
        try:
            urls = [
                f"https://classify.oclc.org/classify2/Classify?isbn={isbn}&summary=true",
                f"http://classify.oclc.org/classify2/Classify?isbn={isbn}&summary=true"
            ]
            
            response = None
            for url in urls:
                try:
                    response = self.session.get(url, timeout=15)
                    if response.status_code == 200:
                        break
                except:
                    continue
            
            if not response or response.status_code != 200:
                return None
                
            root = ET.fromstring(response.content)
            work = root.find('.//work')
            
            if work is None:
                return None
                
            authors = []
            author_element = work.get('author', '')
            if ' and ' in author_element:
                authors = [a.strip() for a in author_element.split(' and ')]
            elif ';' in author_element:
                authors = [a.strip() for a in author_element.split(';')]
            else:
                authors = [author_element]
                
            return BookMetadata(
                title=work.get('title', 'Unknown'),
                authors=authors,
                publisher=work.get('publisher', 'Unknown'),
                published_date=work.get('publishDate', 'Unknown'),
                isbn_13=isbn if len(isbn) == 13 else None,
                isbn_10=isbn if len(isbn) == 10 else None,
                confidence_score=0.75,
                source='worldcat'
            )
        except Exception as e:
            logging.error(f"WorldCat API error for ISBN {isbn}: {str(e)}")
            return None

    def fetch_mercado_editorial(self, isbn: str) -> Optional[BookMetadata]:
        """Busca na API do Mercado Editorial Brasileiro."""
        try:
            url = f"https://api.mercadoeditorial.org/api/v1.2/book?isbn={isbn}"
            response = self.session.get(url, timeout=10)
            
            if response.status_code != 200:
                return None
                
            data = response.json()
            if not data.get('books'):
                return None
                
            book = data['books'][0]
            
            return BookMetadata(
                title=book.get('title', 'Unknown'),
                authors=book.get('authors', []),
                publisher=book.get('publisher', 'Unknown'),
                published_date=book.get('published_date', 'Unknown'),
                isbn_13=isbn if len(isbn) == 13 else None,
                isbn_10=isbn if len(isbn) == 10 else None,
                confidence_score=0.85,
                source='mercado_editorial'
            )
        except Exception as e:
            logging.error(f"Mercado Editorial API error: {str(e)}")
            return None

    def fetch_metadata(self, isbn: str) -> Optional[BookMetadata]:
        """Busca metadados usando múltiplas fontes com lógica melhorada."""
        # Verifica cache
        cached = self.cache.get(isbn)
        if cached:
            return BookMetadata(**cached)
        
        # Detecta se é ISBN brasileiro
        is_brazilian = any(isbn.startswith(prefix) for prefix in ['97865', '97885', '65', '85'])
        
        # Define ordem das APIs baseado na origem do ISBN
        fetchers = []
        if is_brazilian:
            fetchers.extend([
                (self.fetch_google_books_br, 10),
                (self.fetch_mercado_editorial, 9)
            ])
            
        # Adiciona APIs internacionais
        fetchers.extend([
            (self.fetch_google_books, 7),
            (self.fetch_openlibrary, 6),
            (self.fetch_worldcat, 5)
        ])
        
        best_metadata = None
        highest_confidence = 0
        errors = []
        
        for fetcher, priority in fetchers:
            try:
                metadata = fetcher(isbn)
                if metadata:
                    # Ajusta confiança baseado na prioridade
                    metadata.confidence_score *= (priority / 10)
                    
                    if metadata.confidence_score > highest_confidence:
                        best_metadata = metadata
                        highest_confidence = metadata.confidence_score
                        
                        # Se encontrou com alta confiança, para
                        if highest_confidence > 0.9:
                            break
            except Exception as e:
                errors.append(f"{fetcher.__name__}: {str(e)}")
                continue
        
        if best_metadata:
            self.cache.set(isbn, asdict(best_metadata))
            
        return best_metadata
    
class PDFProcessor:
    def __init__(self):
        self.isbn_extractor = ISBNExtractor()
        
    def extract_text_from_pdf(self, pdf_path: str, max_pages: int = 10) -> str:
        """Extrai texto das primeiras páginas do PDF."""
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                pages_to_check = min(max_pages, len(reader.pages))
                
                text = ""
                for page_num in range(pages_to_check):
                    text += reader.pages[page_num].extract_text() + "\n"
                    
                return text
        except Exception as e:
            logging.error(f"Error extracting text from PDF {pdf_path}: {str(e)}")
            return ""

    def extract_metadata_from_pdf(self, pdf_path: str) -> Dict:
        """Extrai metadados internos do PDF."""
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                return reader.metadata if reader.metadata else {}
        except Exception as e:
            logging.error(f"Error extracting PDF metadata from {pdf_path}: {str(e)}")
            return {}

class BookMetadataExtractor:
    def __init__(self, isbndb_api_key: Optional[str] = None):
        self.isbn_extractor = ISBNExtractor()
        self.metadata_fetcher = MetadataFetcher(isbndb_api_key=isbndb_api_key)
        self.pdf_processor = PDFProcessor()
        
        # Configuração de logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('book_metadata.log')
            ]
        )

    def process_single_file(self, pdf_path: str, runtime_stats: Dict) -> Optional[BookMetadata]:
        """Processa um único arquivo PDF com estatísticas."""
        start_time = time.time()
        logging.info(f"Processing: {pdf_path}")
        
        runtime_stats['processed_files'].append(pdf_path)
        
        # Extrai texto do PDF
        text = self.pdf_processor.extract_text_from_pdf(pdf_path)
        
        # Extrai metadados internos do PDF
        pdf_metadata = self.pdf_processor.extract_metadata_from_pdf(pdf_path)
        
        # Encontra todos os ISBNs possíveis
        isbns = self.isbn_extractor.extract_from_text(text)
        
        # Adiciona ISBNs dos metadados do PDF se existirem
        if pdf_metadata.get('ISBN'):
            isbns.add(self.isbn_extractor.normalize_isbn(pdf_metadata['ISBN']))
            
        if not isbns:
            logging.warning(f"No ISBN found in: {pdf_path}")
            runtime_stats['isbn_not_found'].append(pdf_path)
            return None
            
        # Tenta obter metadados para cada ISBN encontrado
        best_metadata = None
        highest_confidence = 0
        runtime_stats['api_attempts'][pdf_path] = []
        runtime_stats['api_errors'][pdf_path] = []
        
        for isbn in isbns:
            try:
                metadata = self.metadata_fetcher.fetch_metadata(isbn)
                if metadata:
                    runtime_stats['api_attempts'][pdf_path].append(metadata.source)
                    if metadata.confidence_score > highest_confidence:
                        metadata.file_path = str(pdf_path)
                        best_metadata = metadata
                        highest_confidence = metadata.confidence_score
            except Exception as e:
                runtime_stats['api_errors'][pdf_path].append(str(e))
                runtime_stats['api_failures'].append(pdf_path)
                
        runtime_stats['processing_times'].append(time.time() - start_time)
        return best_metadata

    def print_detailed_report(self, results: List[BookMetadata], runtime_stats: Dict):
        """Imprime um relatório detalhado dos resultados."""
        total_files = len(runtime_stats['processed_files'])
        successful = len([r for r in results if r is not None])
        failed = total_files - successful
        
        print("\n" + "="*80)
        print("RELATÓRIO DE PROCESSAMENTO DE PDFs")
        print("="*80)
        
        # Estatísticas gerais
        print("\n1. ESTATÍSTICAS GERAIS")
        print("-"*40)
        print(f"Total de arquivos processados: {total_files}")
        print(f"Extrações bem-sucedidas: {successful} ({(successful/total_files*100):.1f}%)")
        print(f"Extrações falhas: {failed} ({(failed/total_files*100):.1f}%)")
        
        # Estatísticas por API
        print("\n2. RESULTADOS POR SERVIÇO")
        print("-"*40)
        api_stats = Counter(r.source for r in results if r is not None)
        total_successful = sum(api_stats.values())
        for api, count in api_stats.most_common():
            print(f"{api:15}: {count:3} sucessos ({count/total_successful*100:.1f}%)")
        
        # Detalhes das falhas
        print("\n3. ANÁLISE DE FALHAS")
        print("-"*40)
        isbn_not_found = len(runtime_stats.get('isbn_not_found', []))
        api_failures = len(runtime_stats.get('api_failures', []))
        print(f"ISBNs não encontrados: {isbn_not_found}")
        print(f"Falhas de API: {api_failures}")
        
        # Tempos de processamento
        print("\n4. PERFORMANCE")
        print("-"*40)
        if 'processing_times' in runtime_stats:
            times = runtime_stats['processing_times']
            print(f"Tempo médio por arquivo: {sum(times)/len(times):.2f}s")
            print(f"Arquivo mais rápido: {min(times):.2f}s")
            print(f"Arquivo mais lento: {max(times):.2f}s")
        
        # Livros processados com sucesso
        print("\n5. LIVROS PROCESSADOS COM SUCESSO")
        print("-"*40)
        for idx, book in enumerate(results, 1):
            if book:
                api_attempts = runtime_stats['api_attempts'].get(book.file_path, [])
                print(f"\n{idx}. {book.title}")
                print(f"   Autores: {', '.join(book.authors)}")
                print(f"   Editora: {book.publisher}")
                print(f"   Data: {book.published_date}")
                print(f"   ISBN-10: {book.isbn_10 or 'N/A'}")
                print(f"   ISBN-13: {book.isbn_13 or 'N/A'}")
                print(f"   Confiança: {book.confidence_score:.2f}")
                print(f"   Fonte: {book.source}")
                print(f"   Tentativas de API: {len(api_attempts)}")
                if api_attempts:
                    print(f"   Ordem de tentativas: {' -> '.join(api_attempts)}")
                print(f"   Arquivo: {Path(book.file_path).name}")
        
        # Arquivos que falharam
        print("\n6. ARQUIVOS COM FALHA")
        print("-"*40)
        failed_files = set(runtime_stats['processed_files']) - set(b.file_path for b in results if b)
        for failed in failed_files:
            print(f"✗ {Path(failed).name}")
            if failed in runtime_stats.get('isbn_not_found', []):
                print("  Motivo: ISBN não encontrado")
            elif failed in runtime_stats.get('api_failures', []):
                print("  Motivo: Falhas nas APIs")
                if failed in runtime_stats['api_errors']:
                    print(f"  Erros: {runtime_stats['api_errors'][failed]}")
        
        print("\n" + "="*80)

    def process_directory(self, directory_path: str, subdirs: Optional[List[str]] = None, 
                         recursive: bool = False, max_workers: int = 4) -> List[BookMetadata]:
        """Processa PDFs em um diretório com estatísticas detalhadas."""
        directory = Path(directory_path)
        pdf_files = []
        
        # Inicializa estatísticas de runtime
        runtime_stats = {
            'processed_files': [],
            'isbn_not_found': [],
            'api_failures': [],
            'processing_times': [],
            'api_attempts': {},
            'api_errors': {}
        }
        
        if subdirs:
            # Processa apenas os subdiretórios especificados
            for subdir in subdirs:
                subdir_path = directory / subdir
                if subdir_path.exists():
                    pdf_files.extend(subdir_path.glob('*.pdf'))
                else:
                    logging.warning(f"Subdiretório não encontrado: {subdir_path}")
        elif recursive:
            # Processa recursivamente
            pdf_files = list(directory.glob('**/*.pdf'))
        else:
            # Processa apenas o diretório atual
            pdf_files = list(directory.glob('*.pdf'))
        
        logging.info(f"Encontrados {len(pdf_files)} arquivos PDF para processar")
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_pdf = {
                executor.submit(self.process_single_file, str(pdf_path), runtime_stats): pdf_path
                for pdf_path in pdf_files
            }
            
            with tqdm(total=len(pdf_files), desc="Processando PDFs") as pbar:
                for future in futures.as_completed(future_to_pdf):
                    pdf_path = future_to_pdf[future]
                    try:
                        metadata = future.result()
                        if metadata:
                            results.append(metadata)
                            logging.info(f"Sucesso: {pdf_path}")
                        else:
                            logging.warning(f"Sem metadados: {pdf_path}")
                    except Exception as e:
                        logging.error(f"Erro processando {pdf_path}: {str(e)}")
                    finally:
                        pbar.update(1)
        
        # Imprime relatório detalhado
        self.print_detailed_report(results, runtime_stats)
                    
        return results
    
def main():
    parser = argparse.ArgumentParser(
        description='Extrai metadados de livros PDF e opcionalmente renomeia os arquivos',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  # Processar apenas o diretório atual:
  %(prog)s "/Users/menon/Downloads"
  
  # Processar diretório e subdiretórios:
  %(prog)s "/Users/menon/Downloads" -r
  
  # Processar e renomear arquivos:
  %(prog)s "/Users/menon/Downloads" --rename
  
  # Processar com mais threads e detalhes:
  %(prog)s "/Users/menon/Downloads" -t 8 -v
  
  # Processar diretórios específicos:
  %(prog)s "/Users/menon/Downloads" --subdirs "Machine Learning,Python Books"
  
  # Comando completo:
  %(prog)s "/Users/menon/Downloads" -r -t 8 --rename -v -k "sua_chave_isbndb" -o "relatorio.json"
  
  # Exemplos com diretórios reais:
  %(prog)s "/Users/menon/Downloads/LEARN YOU SOME CODE BY NO STARCH"
  %(prog)s "/Users/menon/Downloads/machine Learning Oreilly"

Observações:
  - Por padrão, processa apenas o diretório especificado (sem subdiretórios)
  - Use -r para processar todos os subdiretórios
  - Use --subdirs para processar apenas subdiretórios específicos
  - A chave ISBNdb é opcional e pode ser colocada em qualquer posição do comando
""")
    
    parser.add_argument('directory', 
                       help='Diretório contendo os arquivos PDF')
    parser.add_argument('-r', '--recursive',
                       action='store_true',
                       help='Processa subdiretórios recursivamente')
    parser.add_argument('--subdirs',
                       help='Lista de subdiretórios específicos (separados por vírgula)')
    parser.add_argument('-o', '--output',
                       default='book_metadata_report.json',
                       help='Arquivo JSON de saída (padrão: %(default)s)')
    parser.add_argument('-t', '--threads',
                       type=int,
                       default=4,
                       help='Número de threads para processamento (padrão: %(default)s)')
    parser.add_argument('--rename',
                       action='store_true',
                       help='Renomeia arquivos com base nos metadados')
    parser.add_argument('-v', '--verbose',
                       action='store_true',
                       help='Mostra informações detalhadas')
    parser.add_argument('--log-file',
                       default='book_metadata.log',
                       help='Arquivo de log (padrão: %(default)s)')
    parser.add_argument('-k', '--isbndb-key',
                       help='Chave da API ISBNdb (opcional)')
    
    # Se nenhum argumento foi fornecido, mostra a ajuda
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()
    
    # Configuração de logging
    log_handlers = [
        logging.StreamHandler(),
        logging.FileHandler(args.log_file)
    ]
    
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=log_handlers
    )
    
    # Converte subdiretórios em lista se especificados
    subdirs = args.subdirs.split(',') if args.subdirs else None
    
    try:
        # Inicializa o extrator
        extractor = BookMetadataExtractor(isbndb_api_key=args.isbndb_key)
        
        print(f"\nProcessando PDFs em: {args.directory}")
        if args.recursive:
            print("Modo recursivo: processando todos os subdiretórios")
        elif subdirs:
            print(f"Processando subdiretórios específicos: {', '.join(subdirs)}")
        else:
            print("Modo não-recursivo: processando apenas o diretório principal")
        
        # Processa os arquivos
        results = extractor.process_directory(
            args.directory,
            subdirs=subdirs,
            recursive=args.recursive,
            max_workers=args.threads
        )
        
        # Gera relatório JSON
        if results:
            report = {
                'summary': {
                    'total_processed': len(results),
                    'successful': len([r for r in results if r is not None]),
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                },
                'books': [asdict(r) for r in results if r is not None]
            }
            
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            print(f"\nRelatório JSON salvo em: {args.output}")
        
        # Renomeia arquivos se solicitado
        if args.rename and results:
            print("\nRenomeando arquivos...")
            for metadata in results:
                if metadata and metadata.file_path:
                    old_path = Path(metadata.file_path)
                    new_name = extractor.suggest_filename(metadata)
                    new_path = old_path.parent / new_name
                    
                    try:
                        if new_path.exists():
                            print(f"Arquivo já existe, pulando: {new_name}")
                            continue
                            
                        old_path.rename(new_path)
                        print(f"Renomeado: {old_path.name} -> {new_name}")
                    except Exception as e:
                        print(f"Erro ao renomear {old_path.name}: {str(e)}")
        
        print(f"\nLog salvo em: {args.log_file}")
        
    except KeyboardInterrupt:
        print("\nProcessamento interrompido pelo usuário.")
        sys.exit(1)
    except Exception as e:
        print(f"\nErro durante o processamento: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()