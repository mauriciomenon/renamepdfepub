#!/usr/bin/env python3

import argparse
import json
import logging
import re
import sqlite3
import sys
import csv
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import warnings

import ebooklib
import isbnlib
import mobi
import requests
from bs4 import BeautifulSoup
from ebooklib import epub
from requests.adapters import HTTPAdapter
from tqdm import tqdm
from urllib3.util.retry import Retry

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('isbn_diagnostic.log')
    ]
)

# Suprimir avisos específicos
warnings.filterwarnings("ignore", category=UserWarning, module="ebooklib.epub")

@dataclass
class BookResult:
    """Estrutura de dados para resultado do processamento."""
    filename: str
    file_path: str
    format: str
    isbn: Optional[str] = None
    title: Optional[str] = None
    authors: List[str] = None
    publisher: Optional[str] = None
    validated_by: List[str] = None
    valid_isbn: bool = False
    size_kb: float = 0.0
    processing_time: float = 0.0

class ISBNCache:
    """Cache para resultados de API para evitar chamadas repetidas."""
    def __init__(self, cache_file: str = "isbn_cache.db"):
        self.cache_file = cache_file
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.cache_file) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS isbn_cache (
                    isbn TEXT PRIMARY KEY,
                    data TEXT,
                    timestamp INTEGER
                )
            """)

    def get(self, isbn: str) -> Optional[Dict]:
        with sqlite3.connect(self.cache_file) as conn:
            result = conn.execute(
                "SELECT data FROM isbn_cache WHERE isbn = ? AND timestamp > ?",
                (isbn, int(time.time()) - 86400 * 30)  # 30 dias de cache
            ).fetchone()
            if result:
                return json.loads(result[0])
        return None

    def set(self, isbn: str, data: Dict):
        with sqlite3.connect(self.cache_file) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO isbn_cache (isbn, data, timestamp) VALUES (?, ?, ?)",
                (isbn, json.dumps(data), int(time.time()))
            )

class APIClient:
    """Cliente HTTP com retry e rate limiting."""
    def __init__(self):
        self.session = requests.Session()
        retry_strategy = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.last_call = {}

    def get(self, url: str, api_name: str, timeout: int = 10) -> requests.Response:
        # Rate limiting
        if api_name in self.last_call:
            elapsed = time.time() - self.last_call[api_name]
            if elapsed < 1.0:  # 1 requisição por segundo
                time.sleep(1.0 - elapsed)
        
        try:
            response = self.session.get(url, timeout=timeout)
            self.last_call[api_name] = time.time()
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            logging.error(f"API error ({api_name}): {str(e)}")
            raise

class ISBNValidator:
    """Validação de ISBNs."""
    @staticmethod
    def validate_isbn_10(isbn: str) -> bool:
        if len(isbn) != 10:
            return False
        try:
            total = sum((10 - i) * (int(x) if x != 'X' else 10)
                        for i, x in enumerate(isbn))
            return total % 11 == 0
        except ValueError:
            return False

    @staticmethod
    def validate_isbn_13(isbn: str) -> bool:
        if len(isbn) != 13:
            return False
        try:
            total = sum((1 if i % 2 == 0 else 3) * int(x)
                        for i, x in enumerate(isbn[:12]))
            check = (10 - (total % 10)) % 10
            return check == int(isbn[-1])
        except ValueError:
            return False

    @classmethod
    def validate_isbn(cls, isbn: str) -> bool:
        isbn = isbn.replace('-', '').replace(' ', '').upper()
        if len(isbn) == 10:
            return cls.validate_isbn_10(isbn)
        elif len(isbn) == 13:
            return cls.validate_isbn_13(isbn)
        return False

def generate_report(results: List[BookResult], output_dir: Path) -> None:
    """
    Generate detailed reports for ISBN processing results.
    
    Args:
        results (List[BookResult]): List of processing results
        output_dir (Path): Directory where report files will be saved
    """
    # Ensure output directory exists
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate timestamp for unique filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save detailed JSON report
    json_path = output_dir / f"isbn_report_{timestamp}.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump([asdict(r) for r in results], f, indent=2, ensure_ascii=False)
    
    # Generate console report
    valid_results = [r for r in results if r.valid_isbn]
    
    print("\n" + "="*60)
    print("ISBN Processing Report")
    print("="*60)
    print(f"Total files processed: {len(results)}")
    print(f"Valid ISBNs found: {len(valid_results)}")
    print(f"Report saved to: {json_path}")
    
    if valid_results:
        print("\nValidated Books:")
        for r in valid_results:
            print("\n" + "-"*50)
            print(f"File: {r.filename}")
            print(f"Path: {r.file_path}")
            print(f"Format: {r.format.upper()}")
            print(f"Size: {r.size_kb:.1f} KB")
            print("\nMetadata:")
            print(f"  ISBN: {r.isbn}")
            print(f"  Title: {r.title}")
            print(f"  Authors: {', '.join(r.authors if r.authors else ['Unknown'])}")
            print(f"  Publisher: {r.publisher or 'Unknown'}")
            print(f"  Validated by: {', '.join(r.validated_by)}")
            print(f"Processing time: {r.processing_time:.2f} seconds")
    
    # Generate CSV report for easy importing
    csv_path = output_dir / f"isbn_report_{timestamp}.csv"
    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Filename', 'ISBN', 'Title', 'Authors', 'Publisher', 'Format', 'Size (KB)', 'Processing Time (s)'])
        for r in valid_results:
            writer.writerow([
                r.filename,
                r.isbn,
                r.title,
                '; '.join(r.authors if r.authors else []),
                r.publisher,
                r.format.upper(),
                f"{r.size_kb:.1f}",
                f"{r.processing_time:.2f}"
            ])
    
    print(f"\nCSV report saved to: {csv_path}")

def process_single_file(file_path: Path, processor: 'EbookProcessor') -> Optional[BookResult]:
    """
    Process a single ebook file and extract ISBN information.
    
    Args:
        file_path (Path): Path to the ebook file
        processor (EbookProcessor): Instance of EbookProcessor for ISBN validation
        
    Returns:
        Optional[BookResult]: Processing result containing ISBN and metadata if found
    """
    start_time = time.time()
    
    print(f"\nProcessando arquivo: {file_path.name}")
    print("-" * 50)
    
    result = BookResult(
        filename=file_path.name,
        file_path=str(file_path),
        format=file_path.suffix[1:],
        size_kb=file_path.stat().st_size / 1024
    )
    
    try:
        print(f"Extraindo ISBNs do arquivo {file_path.suffix}...")
        
        # Structure to store ISBNs with context and priority
        isbn_candidates = []
        
        if file_path.suffix.lower() == '.epub':
            print("Processando EPUB...")
            book = epub.read_epub(str(file_path))
            
            # 1. First check metadata
            for identifier in book.get_metadata('DC', 'identifier'):
                isbn_match = re.search(r'(?:97[89][-\s]*(?:\d[-\s]*){9}\d|(?:\d[-\s]*){9}[\dXx])', 
                                    str(identifier[0]))
                if isbn_match:
                    isbn = isbn_match.group().replace('-', '').replace(' ', '')
                    isbn_candidates.append({
                        'isbn': isbn,
                        'context': 'metadata',
                        'priority': 10
                    })

            # 2. Check priority files
            for item in book.get_items():
                if item.get_type() == ebooklib.ITEM_DOCUMENT:
                    content = item.get_content().decode('utf-8', errors='ignore')
                    soup = BeautifulSoup(content, 'html.parser')
                    text = soup.get_text()
                    
                    # Check for errata URLs first
                    errata_matches = re.finditer(r'errata\.csp\?isbn=(\d{13})', text)
                    for match in errata_matches:
                        isbn_candidates.append({
                            'isbn': match.group(1),
                            'context': 'errata_url',
                            'priority': 9
                        })
                    
                    # Check for other ISBNs
                    isbn_matches = re.finditer(
                        r'(?:ISBN[-: ]?(?:13)?[-: ]?)?(?:97[89][-\s]*(?:\d[-\s]*){9}\d)',
                        text
                    )
                    for match in isbn_matches:
                        isbn = match.group().replace('-', '').replace(' ', '')
                        if isbn.upper().startswith("ISBN"):
                            isbn = re.sub(r'^ISBN[-: ]*(?:13)?[-: ]*', '', isbn, flags=re.IGNORECASE)
                        start = max(0, match.start() - 100)
                        end = min(len(text), match.end() + 100)
                        context = text[start:end]
                        isbn_candidates.append({
                            'isbn': isbn,
                            'context': context,
                            'priority': 5
                        })
        
        else:  # MOBI
            print("Processando MOBI...")
            try:
                with open(file_path, 'rb') as f:
                    content = f.read().decode('utf-8', errors='ignore')
                    print(f"   Tamanho do conteúdo: {len(content)} bytes")
                    
                    # First check errata URLs
                    errata_matches = re.finditer(r'errata\.csp\?isbn=(\d{13})', content)
                    for match in errata_matches:
                        isbn_candidates.append({
                            'isbn': match.group(1),
                            'context': 'errata_url',
                            'priority': 9
                        })
                    
                    # Then check other ISBNs
                    isbn_matches = re.finditer(
                        r'(?:ISBN[-: ]?(?:13)?[-: ]?)?(?:97[89][-\s]*(?:\d[-\s]*){9}\d)',
                        content
                    )
                    for match in isbn_matches:
                        isbn = match.group().replace('-', '').replace(' ', '')
                        if isbn.upper().startswith("ISBN"):
                            isbn = re.sub(r'^ISBN[-: ]*(?:13)?[-: ]*', '', isbn, flags=re.IGNORECASE)
                        start = max(0, match.start() - 100)
                        end = min(len(content), match.end() + 100)
                        context = content[start:end]
                        isbn_candidates.append({
                            'isbn': isbn,
                            'context': context,
                            'priority': 5
                        })
            
            except Exception as e:
                print(f"   Erro na extração MOBI: {str(e)}")
        
        # Remove duplicates keeping highest priority
        seen_isbns = {}
        for candidate in isbn_candidates:
            isbn = candidate['isbn']
            priority = candidate['priority']
            if isbn not in seen_isbns or priority > seen_isbns[isbn]['priority']:
                seen_isbns[isbn] = candidate
        
        # Convert to list and sort by priority
        unique_candidates = list(seen_isbns.values())
        unique_candidates.sort(key=lambda x: x['priority'], reverse=True)
        
        # Validate ISBNs according to priority
        for candidate in unique_candidates:
            isbn = candidate['isbn']
            priority = candidate['priority']
            context = candidate['context']
            
            print(f"\nValidando ISBN: {isbn}")
            print("-" * 30)
            
            # If from errata URL or metadata, validate and use if found
            if context in ['errata_url', 'metadata']:
                metadata = processor.validate_with_apis(isbn)
                if metadata and metadata.get('publisher', '').lower().find('reilly') != -1:
                    result.isbn = isbn
                    result.title = metadata['title']
                    result.authors = metadata['authors']
                    result.publisher = metadata['publisher']
                    result.validated_by = [metadata['source']]
                    result.valid_isbn = True
                    print(f"ISBN validado com alta prioridade: {isbn}")
                    break
            
            # If not high priority, only validate if no valid ISBN found yet
            elif not result.valid_isbn:
                metadata = processor.validate_with_apis(isbn)
                if metadata and metadata.get('publisher', '').lower().find('reilly') != -1:
                    result.isbn = isbn
                    result.title = metadata['title']
                    result.authors = metadata['authors']
                    result.publisher = metadata['publisher']
                    result.validated_by = [metadata['source']]
                    result.valid_isbn = True
        
    except Exception as e:
        print(f"Erro processando arquivo: {str(e)}")
        logging.error(f"Error processing {file_path.name}: {str(e)}")
        
    result.processing_time = time.time() - start_time
    return result

def process_directory(directory: str, max_workers: int = 4) -> List[BookResult]:
    """
    Process a directory of ebooks.
    
    Args:
        directory (str): Path to directory containing ebooks
        max_workers (int): Number of parallel workers
        
    Returns:
        List[BookResult]: List of processing results
    """
    processor = EbookProcessor()
    results = []
    
    # Find all epub/mobi files
    path = Path(directory)
    files = []
    files.extend(path.glob("**/*.epub"))
    files.extend(path.glob("**/*.mobi"))
    
    print(f"\nEncontramos {len(files)} arquivos para processar")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for file_path in files:
            futures.append(executor.submit(process_single_file, file_path, processor))
            
        for future in tqdm(futures, desc="Processando arquivos"):
            try:
                result = future.result()
                if result:
                    results.append(result)
            except Exception as e:
                logging.error(f"Error processing file: {str(e)}")
                
    return results

class EbookProcessor:
    """Handles ebook processing and ISBN validation."""
    
    def __init__(self):
        self.validator = ISBNValidator()
        self.api_client = APIClient()
        self.cache = ISBNCache()

    def validate_with_apis(self, isbn: str) -> Optional[Dict]:
        """
        Validate ISBN with multiple APIs.
        
        Args:
            isbn (str): ISBN to validate
            
        Returns:
            Optional[Dict]: Validation result with metadata if successful
        """
        cached = self.cache.get(isbn)
        if cached:
            return cached

        results = []
        
        # Google Books API
        try:
            response = self.api_client.get(
                f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}",
                "google_books"
            )
            if response.status_code == 200:
                data = response.json()
                if 'items' in data:
                    book = data['items'][0]['volumeInfo']
                    results.append({
                        'title': book.get('title'),
                        'authors': book.get('authors', []),
                        'publisher': book.get('publisher'),
                        'source': 'google_books'
                    })
        except Exception as e:
            logging.debug(f"Google Books API error: {str(e)}")

        # Add other API validations here...

        if len(results) >= 2:
            best_result = max(results, key=lambda x: len(x.get('authors', [])))
            self.cache.set(isbn, best_result)
            return best_result

        return None
    
    
def main():
    parser = argparse.ArgumentParser(description="ISBN Diagnostic Tool for Ebooks")
    parser.add_argument("path", help="Path to ebook file or directory")
    parser.add_argument("-w", "--workers", type=int, default=4, 
                       help="Number of worker threads for directory processing")
    parser.add_argument("-v", "--verbose", action="store_true", 
                       help="Enable verbose logging")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    path = Path(args.path)
    if not path.exists():
        print(f"Error: Path does not exist: {path}")
        sys.exit(1)

    try:
        if path.is_file():
            if path.suffix.lower() not in ['.epub', '.mobi']:
                print("Error: File must be EPUB or MOBI format")
                sys.exit(1)
            processor = EbookProcessor()
            result = process_single_file(path, processor)
            if result:
                generate_report([result], path.parent)
            
        elif path.is_dir():
            results = process_directory(str(path), max_workers=args.workers)
            generate_report(results, path)
            
    except KeyboardInterrupt:
        print("\nProcesso interrompido pelo usuário.")
        sys.exit(1)
    except Exception as e:
        print(f"\nErro durante o processamento: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()