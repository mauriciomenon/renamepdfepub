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
                    timestamp INTEGER
                )
            """)

    def get(self, isbn: str) -> Optional[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute(
                "SELECT metadata_json FROM metadata_cache WHERE isbn = ?", 
                (isbn,)
            ).fetchone()
            return json.loads(result[0]) if result else None

    def set(self, isbn: str, metadata: Dict):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO metadata_cache (isbn, metadata_json, timestamp) VALUES (?, ?, ?)",
                (isbn, json.dumps(metadata), int(time.time()))
            )

class ISBNExtractor:
    def __init__(self):
        self.isbn_patterns = [
            # Padrões comuns de ISBN
            r'ISBN(?:-13)?:?\s*(978[\d-]+)',
            r'ISBN(?:-10)?:?\s*([\dX-]{10,})',
            r'978[\d-]{10,}',
            r'[\dX-]{10,13}',
            # Padrões específicos por editora
            r'O\'Reilly Media(?:.*?)ISBN(?:[^0-9]*)([\dX-]{10,})',
            r'Apress(?:.*?)ISBN(?:[^0-9]*)([\dX-]{10,})',
            r'No Starch Press(?:.*?)ISBN(?:[^0-9]*)([\dX-]{10,})',
            r'Pearson(?:.*?)ISBN(?:[^0-9]*)([\dX-]{10,})',
            r'Wiley(?:.*?)ISBN(?:[^0-9]*)([\dX-]{10,})',
            # Padrões mais agressivos
            r'97[89][\d-]{10,}',
            r'\b[\dX]{10}\b',
            r'\b97[89]\d{10}\b'
        ]
        
    def normalize_isbn(self, isbn: str) -> str:
        return re.sub(r'[^0-9X]', '', isbn.upper())

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
        found_isbns = set()
        
        for pattern in self.isbn_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                isbn = match.group(1) if '(' in pattern else match.group()
                isbn = self.normalize_isbn(isbn)
                
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
        self.isbndb_api_key = isbndb_api_key  # Opcional
        
        # Configuração de retry
        retry_strategy = Retry(
            total=5,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=100, pool_maxsize=100)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; BookMetadataBot/1.0)'
        })

        # Lista das APIs disponíveis e seus requisitos
        self.api_info = {
            'google_books': {
                'requires_auth': False,
                'is_active': True,
                'base_url': 'https://www.googleapis.com/books/v1'
            },
            'openlibrary': {
                'requires_auth': False,
                'is_active': True,
                'base_url': 'https://openlibrary.org/api'
            },
            'worldcat_classify': {  # API gratuita do WorldCat
                'requires_auth': False,
                'is_active': True,
                'base_url': 'https://classify.oclc.org/classify2'
            },
            'isbndb': {
                'requires_auth': True,
                'is_active': bool(isbndb_api_key),
                'base_url': 'https://api2.isbndb.com'
            }
        }

    def fetch_google_books(self, isbn: str) -> Optional[BookMetadata]:
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
            # Tenta primeiro HTTPS
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
                
            # Extrai mais dados quando disponíveis
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

    def fetch_metadata(self, isbn: str) -> Optional[BookMetadata]:
        """Busca metadados usando múltiplas fontes com fallback inteligente."""
        cached = self.cache.get(isbn)
        if cached:
            return BookMetadata(**cached)
            
        # Define os fetchers ativos e suas prioridades
        fetchers = []
        if self.api_info['google_books']['is_active']:
            fetchers.append((self.fetch_google_books, 10))
        if self.api_info['openlibrary']['is_active']:
            fetchers.append((self.fetch_openlibrary, 8))
        if self.api_info['worldcat_classify']['is_active']:
            fetchers.append((self.fetch_worldcat, 15))
        if self.api_info['isbndb']['is_active']:
            fetchers.append((self.fetch_isbndb, 10))
        
        best_metadata = None
        highest_confidence = 0
        errors = []
        
        for fetcher, timeout in fetchers:
            try:
                metadata = fetcher(isbn)
                if metadata and metadata.confidence_score > highest_confidence:
                    best_metadata = metadata
                    highest_confidence = metadata.confidence_score
                    if highest_confidence > 0.9:
                        break
            except Exception as e:
                errors.append(f"{fetcher.__name__}: {str(e)}")
                continue
        
        if not best_metadata and errors:
            logging.warning(f"Falha em todas as APIs para ISBN {isbn}. Erros: {'; '.join(errors)}")
        
        if best_metadata:
            self.cache.set(isbn, asdict(best_metadata))
            
        return best_metadata

class PDFProcessor:
    def __init__(self):
        self.isbn_extractor = ISBNExtractor()
        
    def extract_text_from_pdf(self, pdf_path: str, max_pages: int = 10) -> str:
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
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                return reader.metadata if reader.metadata else {}
        except Exception as e:
            logging.error(f"Error extracting PDF metadata from {pdf_path}: {str(e)}")
            return {}
        
class BookMetadataExtractor:
    def __init__(self, isbndb_api_key: Optional[str] = None):
        # Inicialização dos componentes principais
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

    def generate_report(self, results: List[BookMetadata], output_file: str) -> Dict:
        """Gera um relatório detalhado em JSON com os resultados."""
        report = {
            'summary': {
                'total_files_processed': len(results),
                'successful_extractions': sum(1 for r in results if r is not None),
                'failed_extractions': sum(1 for r in results if r is None),
                'sources_used': dict(Counter(r.source for r in results if r is not None)),
                'average_confidence': sum(r.confidence_score for r in results if r is not None) / 
                                   len([r for r in results if r is not None]) if results else 0,
                'publishers': dict(Counter(r.publisher for r in results if r is not None))
            },
            'books': [asdict(r) for r in results if r is not None]
        }
        
        # Adiciona estatísticas por editora
        publishers_stats = {}
        for r in results:
            if r and r.publisher not in ['Unknown', '']:
                if r.publisher not in publishers_stats:
                    publishers_stats[r.publisher] = {
                        'count': 0,
                        'avg_confidence': 0,
                        'successful_extractions': 0
                    }
                stats = publishers_stats[r.publisher]
                stats['count'] += 1
                stats['avg_confidence'] += r.confidence_score
                stats['successful_extractions'] += 1
        
        # Calcula médias
        for pub_stats in publishers_stats.values():
            if pub_stats['count'] > 0:
                pub_stats['avg_confidence'] /= pub_stats['count']
        
        report['summary']['publisher_stats'] = publishers_stats
        
        # Salva o relatório
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            
        return report

    def suggest_filename(self, metadata: BookMetadata) -> str:
        """Sugere um nome de arquivo baseado nos metadados."""
        def clean_string(s: str) -> str:
            # Remove caracteres inválidos para nome de arquivo
            s = unicodedata.normalize('NFKD', s)
            s = s.encode('ASCII', 'ignore').decode('ASCII')
            s = re.sub(r'[^\w\s-]', '', s)
            return s.strip()
        
        title = clean_string(metadata.title)
        # Limita a 2 autores para o nome do arquivo
        authors = clean_string(', '.join(metadata.authors[:2]))
        # Extrai o ano da data de publicação
        year = metadata.published_date.split('-')[0] if '-' in metadata.published_date else metadata.published_date
        
        # Limita o tamanho do nome do arquivo
        max_title_length = 50
        if len(title) > max_title_length:
            title = title[:max_title_length] + '...'
        
        return f"{title} - {authors} ({year}).pdf"

def main():
    parser = argparse.ArgumentParser(
        description='Extrai metadados de livros PDF e opcionalmente renomeia os arquivos',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  # Processar apenas o diretório atual:
  %(prog)s "/Users/menon/Downloads"
  
  # Processar incluindo subdiretórios:
  %(prog)s "/Users/menon/Downloads" -r
  
  # Processar e renomear arquivos:
  %(prog)s "/Users/menon/Downloads" --rename
  
  # Processar com mais threads e verbose:
  %(prog)s "/Users/menon/Downloads" -t 8 -v
  
  # Processar subdiretórios específicos:
  %(prog)s "/Users/menon/Downloads" --subdirs "Machine Learning,Python Books"
  
  # Exemplo completo com todas as opções:
  %(prog)s "/Users/menon/Downloads" -r -t 8 --rename -v -o "relatorio.json"
""")
    
    parser.add_argument('directory', 
                       help='Diretório contendo os arquivos PDF (ex: /Users/menon/Downloads)')
    parser.add_argument('-r', '--recursive',
                       action='store_true',
                       help='Processa subdiretórios recursivamente')
    parser.add_argument('--subdirs',
                       help='Lista de subdiretórios específicos separados por vírgula')
    parser.add_argument('-o', '--output',
                       default='book_metadata_report.json',
                       help='Arquivo JSON de saída para resultados (padrão: %(default)s)')
    parser.add_argument('-t', '--threads',
                       type=int,
                       default=4,
                       help='Número de threads para processamento paralelo (padrão: %(default)s)')
    parser.add_argument('--rename',
                       action='store_true',
                       help='Renomeia arquivos baseado nos metadados encontrados')
    parser.add_argument('-v', '--verbose',
                       action='store_true',
                       help='Mostra informações detalhadas durante o processamento')
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
    
    # Inicializa o extrator com configurações opcionais
    extractor = BookMetadataExtractor(isbndb_api_key=args.isbndb_key)
    
    print(f"\nProcessando PDFs em: {args.directory}")
    
    # Modifica a lógica de subdiretórios
    subdirs = None
    if args.subdirs:
        subdirs = args.subdirs.split(',')
        print(f"Subdiretórios específicos: {', '.join(subdirs)}")
    elif args.recursive:
        print("Modo recursivo: processando todos os subdiretórios")
    else:
        print("Modo não-recursivo: processando apenas o diretório principal")
    
    results = extractor.process_directory(
        args.directory,
        subdirs=subdirs,
        recursive=args.recursive,
        max_workers=args.threads
    )

if __name__ == "__main__":
    main()