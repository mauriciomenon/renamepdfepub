try:
    try:
        import pypdf as PyPDF2  # type: ignore
    except Exception:
        try:
            import PyPDF2  # type: ignore
        except Exception:
            PyPDF2 = None
except Exception:
    PyPDF2 = None
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
import pdfplumber
import pytesseract

class DependencyManager:
    def __init__(self):
        self.available_extractors = {
            'pypdf2': True,  # Já sabemos que está disponível pois é requisito
            'pdfplumber': False,
            'pdfminer': False,
            'tesseract': False,
            'pdf2image': False
        }
        self._check_dependencies()
    
    def _check_dependencies(self):
        """Verifica quais dependências estão disponíveis."""
        # Verifica pdfplumber
        try:
            import pdfplumber
            self.available_extractors['pdfplumber'] = True
        except ImportError:
            logging.debug("pdfplumber não está instalado. Usando alternativas.")

        # Verifica pdfminer
        try:
            from pdfminer.high_level import extract_text
            self.available_extractors['pdfminer'] = True
        except ImportError:
            logging.debug("pdfminer.six não está instalado. Usando alternativas.")

        # Verifica Tesseract
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            self.available_extractors['tesseract'] = True
        except:
            logging.debug("Tesseract OCR não está instalado/configurado.")

        # Verifica pdf2image
        try:
            import pdf2image
            self.available_extractors['pdf2image'] = True
        except ImportError:
            logging.debug("pdf2image não está instalado.")

    def get_available_extractors(self) -> List[str]:
        """Retorna lista de extractors disponíveis."""
        return [k for k, v in self.available_extractors.items() if v]

    @property
    def has_ocr_support(self) -> bool:
        """Verifica se o suporte a OCR está disponível."""
        return self.available_extractors['tesseract'] and self.available_extractors['pdf2image']

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
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    isbn_10 TEXT,
                    isbn_13 TEXT,
                    title TEXT,
                    authors TEXT,
                    publisher TEXT,
                    published_date TEXT,
                    confidence_score REAL,
                    source TEXT,
                    file_path TEXT,
                    raw_json TEXT, -- Campo para JSON bruto
                    timestamp INTEGER DEFAULT (strftime('%s', 'now'))
                )
            """)

    def get(self, isbn: str) -> Optional[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute("""
                SELECT isbn_10, isbn_13, title, authors, publisher, 
                       published_date, confidence_score, source, file_path, raw_json
                FROM metadata_cache
                WHERE (isbn_10 = ? OR isbn_13 = ?) 
                AND timestamp > ?
                """, 
                (isbn, isbn, int(time.time()) - 30*24*60*60)  # 30 dias de cache
            ).fetchone()
            
            if result:
                # Se temos JSON bruto, use-o preferencialmente
                if result[9]:  # raw_json
                    try:
                        return json.loads(result[9])
                    except:
                        pass
                
                # Caso contrário, use os campos individuais
                return {
                    'isbn_10': result[0],
                    'isbn_13': result[1],
                    'title': result[2],
                    'authors': result[3].split(', '),
                    'publisher': result[4],
                    'published_date': result[5],
                    'confidence_score': result[6],
                    'source': result[7],
                    'file_path': result[8]
                }
            return None

    def set(self, metadata: Dict):
        """
        Salva os metadados no cache.
        Args:
            metadata: Dicionário com os metadados do livro
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO metadata_cache (
                    isbn_10, isbn_13, title, authors, publisher, 
                    published_date, confidence_score, source, file_path, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    metadata.get('isbn_10'),
                    metadata.get('isbn_13'),
                    metadata.get('title'),
                    ', '.join(metadata.get('authors', [])),
                    metadata.get('publisher'),
                    metadata.get('published_date'),
                    metadata.get('confidence_score', 0.0),
                    metadata.get('source'),
                    metadata.get('file_path'),
                    json.dumps(metadata)  # Armazena JSON bruto
                )
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

        # Mapeamento para corrigir caracteres corrompidos
        self.char_corrections = {
            # Caracteres básicos corrompidos
            '+': 'H', '2': 'O', 'Q': 'O', 'd': 'cl', '11': 'll',
            '1': 'l', '0': 'o', '@': 'a', '#': 'B', '$': 'S',
            
            # Caracteres específicos do caso mencionado
            'dF': 'cf', 'WL': 'ti', 'QWH': 'nte', 'LJHQFH': 'ligence',
            'DQGV': 'ands', 'UWL': 'rti', 'FLDO': 'ficial',
            
            # Correções para números em ISBNs
            'O': '0', 'l': '1', 'I': '1', 'i': '1',
            'S': '5', 'Z': '2', 'B': '8', 'G': '6',
            'q': '9', 'g': '9', 'A': '4'
        }

    def _try_extract_with_pdfplumber(self, pdf_path: str, max_pages: int = 10) -> str:
        """Tenta extrair texto usando pdfplumber."""
        try:
            import pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                text = ""
                pages_to_check = min(max_pages, len(pdf.pages))
                for page in pdf.pages[:pages_to_check]:
                    text += page.extract_text() or ""
                return text
        except Exception as e:
            logging.debug(f"pdfplumber extraction failed: {str(e)}")
            return ""

    def _try_extract_with_tesseract(self, pdf_path: str, max_pages: int = 5) -> str:
        """Tenta extrair texto usando Tesseract OCR."""
        try:
            import pytesseract
            from pdf2image import convert_from_path
            
            images = convert_from_path(pdf_path, first_page=1, last_page=max_pages)
            text = ""
            for image in images:
                text += pytesseract.image_to_string(image) or ""
            return text
        except Exception as e:
            logging.debug(f"Tesseract OCR failed: {str(e)}")
            return ""

    def _clean_corrupted_text(self, text: str) -> str:
        """Limpa texto corrompido usando o mapeamento de caracteres."""
        # Primeira passada: correção de palavras comuns
        common_words = {
            'DQGV2Q': 'Hands-On',
            'UWLdFLDO': 'rtificial',
            ',QWH11LJHQFH': 'Intelligence',
            '1RU': 'for',
            '%DQNLQJ': 'Banking'
        }
        
        for corrupt, clean in common_words.items():
            text = text.replace(corrupt, clean)
        
        # Segunda passada: correção caractere por caractere
        for corrupt, clean in self.char_corrections.items():
            text = text.replace(corrupt, clean)
            
        return text

    def _is_text_corrupted(self, text: str) -> bool:
        """Verifica se o texto está corrompido."""
        if not text:
            return True
            
        # Verifica proporção de caracteres especiais
        special_chars = sum(1 for c in text if not c.isalnum() and not c.isspace())
        if len(text) > 0 and special_chars / len(text) > 0.3:
            return True
            
        # Verifica se tem muitas sequências maiúsculas incomuns
        uppercase_sequences = re.findall(r'[A-Z]{4,}', text)
        if len(uppercase_sequences) > len(text.split()) / 4:
            return True
            
        return False

    def extract_from_text(self, text: str, source_path: str = None) -> Set[str]:
        """Extrai todos os ISBNs possíveis do texto."""
        found_isbns = set()
        original_text = text
        
        # Identifica editora para ajustes específicos
        publisher, confidence_boost = self.identify_publisher(text)
        logging.debug(f"Identified publisher: {publisher}")
        
        # Se o texto parece corrompido, tenta limpá-lo
        if self._is_text_corrupted(text):
            logging.info("Texto corrompido detectado, aplicando limpeza...")
            text = self._clean_corrupted_text(text)
            
            # Se ainda não encontrou ISBNs e temos o caminho do arquivo, tenta métodos alternativos
            if source_path and not found_isbns:
                logging.info("Tentando métodos alternativos de extração...")
                
                # Tenta pdfplumber
                plumber_text = self._try_extract_with_pdfplumber(source_path)
                if plumber_text:
                    logging.info("Texto extraído com pdfplumber, procurando ISBNs...")
                    found_isbns.update(self._extract_with_patterns(plumber_text, publisher))
                
                # Se ainda não encontrou, tenta OCR
                if not found_isbns:
                    ocr_text = self._try_extract_with_tesseract(source_path)
                    if ocr_text:
                        logging.info("Texto extraído com OCR, procurando ISBNs...")
                        found_isbns.update(self._extract_with_patterns(ocr_text, publisher))
        
        # Busca ISBNs no texto (original ou limpo)
        found_isbns.update(self._extract_with_patterns(text, publisher))
        
        # Se encontrou ISBNs, registra sucesso
        if found_isbns:
            logging.info(f"ISBNs encontrados: {found_isbns}")
            return found_isbns
        
        # Se não encontrou nada, tenta extrações específicas por editora
        publisher_isbns = self.extract_publisher_specific(original_text, publisher)
        if publisher_isbns:
            logging.info(f"ISBNs encontrados usando extração específica da editora: {publisher_isbns}")
            found_isbns.update(publisher_isbns)
        
        return found_isbns

    def _extract_with_patterns(self, text: str, publisher: str) -> Set[str]:
        """Extrai ISBNs usando os padrões definidos."""
        found_isbns = set()
        
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
    
    def extract_publisher_specific(self, text: str, publisher: str) -> Set[str]:
        """Extrai ISBNs usando técnicas específicas por editora."""
        found_isbns = set()
        
        if publisher == 'casa do codigo':
            # Padrão específico para Casa do Código
            patterns = [
                r'ISBN[:\s]*(?:Impresso e PDF:|PDF:)?\s*(97[89][-\s]*(?:\d[-\s]*){9}\d)',
                r'ISBN[:\s]*(?:EPUB:|MOBI:)?\s*(97[89][-\s]*(?:\d[-\s]*){9}\d)'
            ]
        elif publisher == 'packt':
            # Padrão específico para Packt, incluindo caracteres corrompidos
            patterns = [
                r'ISBN[:\s]*[@>?]*(97[89][-\s]*(?:[\d@>?][-\s]*){9}[\d@>?])',
                r'ISBN[:\s]*([9@][7>][\d@>?]{11})'
            ]
        elif publisher == 'wiley':
            # Padrão específico para Wiley, pegando múltiplos ISBNs
            patterns = [
                r'ISBN:\s*(97[89][-\s]*(?:\d[-\s]*){9}\d)(?:\s*\(.*?\))?',
                r'ISBN-13:\s*(97[89][-\s]*(?:\d[-\s]*){9}\d)',
                r'Print ISBN:\s*(97[89][-\s]*(?:\d[-\s]*){9}\d)'
            ]
        else:
            # Padrões genéricos mais agressivos para outras editoras
            patterns = [
                r'(?:ISBN[-:]?)?\s*(97[89][-\s]*(?:\d[-\s]*){9}\d)',
                r'(?:ISBN[-:]?)?\s*([\dX][-\s]*){10,13}'
            ]
        
        for pattern in patterns:
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
        
        # Configuração de timeouts globais
        self.session.timeout = (3.05, 10)  # (connect timeout, read timeout)
        
        # Configuração de retry mais robusta
        retry_strategy = Retry(
            total=3,  # Reduzido para 3 tentativas
            backoff_factor=1.0,
            status_forcelist=[404, 429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"],
            respect_retry_after_header=True,  # Respeita header Retry-After
            raise_on_redirect=True,  # Levanta exceção em redirecionamentos
            raise_on_status=True  # Levanta exceção em status de erro
        )
        
        # Configuração do adapter
        adapter = HTTPAdapter(
            pool_connections=100,
            pool_maxsize=100,
            max_retries=retry_strategy,
            pool_block=False  # Não bloqueia quando pool está cheio
        )
        
        # Monta adapters
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Headers padrão
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; BookMetadataBot/1.0)',
            'Accept': 'text/html,application/json,application/xml;q=0.9',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive'
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
        try:
            base_url = "https://www.worldcat.org/isbn/" + isbn
            response = self.session.get(base_url, timeout=5)
            
            if response.status_code == 200:
                # Parse HTML response
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                
                title = soup.find('h1', {'class': 'title'})
                authors = soup.find_all('a', {'class': 'author'})
                publisher = soup.find('td', text='Publisher')
                
                return BookMetadata(
                    title=title.text if title else 'Unknown',
                    authors=[a.text for a in authors] if authors else ['Unknown'],
                    publisher=publisher.next_sibling.text if publisher else 'Unknown',
                    published_date='Unknown',
                    isbn_13=isbn if len(isbn) == 13 else None,
                    isbn_10=isbn if len(isbn) == 10 else None,
                    confidence_score=0.75,
                    source='worldcat'
                )
        except Exception as e:
            logging.error(f"WorldCat error: {str(e)}")
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

    def fetch_zbib(self, isbn: str) -> Optional[BookMetadata]:
        """Busca metadados na API da Zbib.org."""
        try:
            url = f"https://zbib.org/api/v1/search?q={isbn}"
            response = self.session.get(url, timeout=(2, 5))  # timeout mais curto
            data = response.json()
            
            if not data or 'items' not in data or not data['items']:
                return None
                
            item = data['items'][0]
            
            return BookMetadata(
                title=item.get('title', 'Unknown'),
                authors=item.get('authors', ['Unknown']),
                publisher=item.get('publisher', 'Unknown'),
                published_date=item.get('year', 'Unknown'),
                isbn_13=isbn if len(isbn) == 13 else None,
                isbn_10=isbn if len(isbn) == 10 else None,
                confidence_score=0.7,
                source='zbib'
            )
        except Exception as e:
            logging.error(f"Zbib API error: {str(e)}")
            return None

    def fetch_mybib(self, isbn: str) -> Optional[BookMetadata]:
        """Busca metadados na API da MyBib.com."""
        try:
            url = f"https://www.mybib.com/api/v1/references?q={isbn}"
            response = self.session.get(url, timeout=10)
            data = response.json()
            
            if not data or 'references' not in data or not data['references']:
                return None
                
            item = data['references'][0]
            
            return BookMetadata(
                title=item.get('title', 'Unknown'),
                authors=item.get('authors', ['Unknown']),
                publisher=item.get('publisher', 'Unknown'),
                published_date=item.get('year', 'Unknown'),
                isbn_13=isbn if len(isbn) == 13 else None,
                isbn_10=isbn if len(isbn) == 10 else None,
                confidence_score=0.7,
                source='mybib'
            )
        except Exception as e:
            logging.error(f"MyBib API error: {str(e)}")
            return None

    def fetch_ebook_de(self, isbn: str) -> Optional[BookMetadata]:
        """Busca metadados na ebook.de."""
        try:
            url = f"https://www.ebook.de/de/tools/isbn2bibtex/{isbn}"
            response = self.session.get(url, timeout=(2, 5))  # timeout mais curto
            
            if response.status_code != 200:
                logging.info("Ebook.de não retornou resultados")
                return None
                
            text = response.text
            
            # Extrai título
            title_match = re.search(r'title\s*=\s*{([^}]+)}', text)
            if not title_match:
                return None
            title = title_match.group(1)
            
            # Extrai autores
            authors_match = re.search(r'author\s*=\s*{([^}]+)}', text)
            authors = []
            if authors_match:
                authors = [a.strip() for a in authors_match.group(1).split(' and ')]
            
            # Extrai editora
            publisher_match = re.search(r'publisher\s*=\s*{([^}]+)}', text)
            publisher = publisher_match.group(1) if publisher_match else 'Unknown'
            
            # Extrai ano
            year_match = re.search(r'year\s*=\s*{(\d{4})}', text)
            year = year_match.group(1) if year_match else 'Unknown'
            
            return BookMetadata(
                title=title,
                authors=authors if authors else ['Unknown'],
                publisher=publisher,
                published_date=year,
                isbn_13=isbn if len(isbn) == 13 else None,
                isbn_10=isbn if len(isbn) == 10 else None,
                confidence_score=0.75,
                source='ebook_de'
            )
        except requests.Timeout:
            logging.info("Timeout ao acessar Ebook.de")
            return None
        except Exception as e:
            logging.error(f"Ebook.de API error: {str(e)}")
            return None
 
    def fetch_metadata(self, isbn: str) -> Optional[BookMetadata]:
        cached = self.cache.get(isbn)
        if cached:
            return BookMetadata(**cached)
            
        is_brazilian = any(isbn.startswith(prefix) for prefix in ['97865', '97885', '65', '85'])
        
        # Define ordem prioritária mas mantem única tentativa por serviço
        fetchers = []
        if is_brazilian:
            # Alta prioridade BR
            fetchers.extend([
                (self.fetch_mercado_editorial, 10),
                (self.fetch_google_books_br, 9),
            ])
        
        # Adiciona fetchers comuns
        fetchers.extend([
            (self.fetch_google_books, 8),
            (self.fetch_openlibrary, 7),
            (self.fetch_worldcat, 6),
            (self.fetch_zbib, 5),
            (self.fetch_mybib, 4)
        ])
        
        # Tenta cada fetcher uma única vez
        processed = set()
        for fetcher, priority in fetchers:
            if fetcher.__name__ not in processed:
                try:
                    metadata = fetcher(isbn)
                    if metadata:
                        metadata.confidence_score *= (priority / 10)
                        self.cache.set(asdict(metadata))
                        return metadata
                except Exception as e:
                    logging.error(f"Error with {fetcher.__name__}: {str(e)}")
                finally:
                    processed.add(fetcher.__name__)
                    
        return None

class PDFProcessor:
    def __init__(self):
        self.isbn_extractor = ISBNExtractor()
        self.dependency_manager = DependencyManager()
        logging.info(f"Extractores disponíveis: {', '.join(self.dependency_manager.get_available_extractors())}")
        if self.dependency_manager.has_ocr_support:
            logging.info("Suporte a OCR está disponível")
        
    def extract_text_from_pdf(self, pdf_path: str, max_pages: int = 10) -> Tuple[str, List[str]]:
        """Extrai texto das primeiras páginas do PDF."""
        logging.info(f"Iniciando extração de texto de: {pdf_path}")
        text = ""
        methods_tried = []
        methods_succeeded = []
        
        # Sequência original de tentativas
        
        # Tenta PyPDF2 primeiro (método original)
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                pages_to_check = min(max_pages, len(reader.pages))
                methods_tried.append("PyPDF2")
                for page_num in range(pages_to_check):
                    text += reader.pages[page_num].extract_text() + "\n"
                if text.strip():
                    methods_succeeded.append("PyPDF2")
        except Exception as e:
            logging.debug(f"Erro na extração com PyPDF2: {str(e)}")

        # Se não conseguiu texto suficiente, tenta pdfplumber (se disponível)
        if (not text or len(text.strip()) < 100) and 'pdfplumber' in self.dependency_manager.get_available_extractors():
            try:
                import pdfplumber
                methods_tried.append("pdfplumber")
                with pdfplumber.open(pdf_path) as pdf:
                    pages_to_check = min(max_pages, len(pdf.pages))
                    plumber_text = ""
                    for page in pdf.pages[:pages_to_check]:
                        plumber_text += page.extract_text() + "\n"
                    if plumber_text.strip():
                        text = plumber_text
                        methods_succeeded.append("pdfplumber")
            except Exception as e:
                logging.debug(f"Erro na extração com pdfplumber: {str(e)}")

        # Se ainda não tem texto suficiente, tenta pdfminer (se disponível)
        if (not text or len(text.strip()) < 100) and 'pdfminer' in self.dependency_manager.get_available_extractors():
            try:
                from pdfminer.high_level import extract_text as pdfminer_extract
                methods_tried.append("pdfminer")
                miner_text = pdfminer_extract(pdf_path, maxpages=max_pages)
                if miner_text.strip():
                    text = miner_text
                    methods_succeeded.append("pdfminer")
            except Exception as e:
                logging.debug(f"Erro na extração com pdfminer: {str(e)}")

        # Se ainda não tem texto e OCR está disponível, tenta Tesseract
        if (not text or len(text.strip()) < 100) and self.dependency_manager.has_ocr_support:
            try:
                import pytesseract
                from pdf2image import convert_from_path
                methods_tried.append("OCR (Tesseract)")
                
                images = convert_from_path(pdf_path, last_page=max_pages)
                ocr_text = ""
                for image in images:
                    ocr_text += pytesseract.image_to_string(image) + "\n"
                    
                if ocr_text.strip():
                    text = ocr_text
                    methods_succeeded.append("OCR (Tesseract)")
            except Exception as e:
                logging.debug(f"Erro na extração com OCR: {str(e)}")

        # Se após todas as tentativas ainda não tiver texto adequado, usa o AdvancedTextExtractor
        if not text or len(text.strip()) < 100:
            logging.info("Tentando extração avançada após falha dos métodos convencionais")
            advanced_extractor = AdvancedTextExtractor()
            advanced_text, is_manual = advanced_extractor.extract_text(pdf_path, max_pages)
            
            if is_manual:
                logging.info(f"Arquivo identificado como manual/documentação via extração avançada: {pdf_path}")
                return "", methods_tried + ["advanced_extraction"]
                
            if advanced_text:
                text = advanced_text
                methods_tried.append("advanced_extraction")
                methods_succeeded.append("advanced_extraction")

        # Limpa o texto
        text = self._clean_text(text)
        
        # Verifica se é um manual
        if self._is_manual_or_documentation(text):
            logging.info(f"Arquivo identificado como manual/documentação: {pdf_path}")
            return "", methods_tried
            
        logging.info(f"Métodos tentados: {', '.join(methods_tried)}")
        logging.info(f"Métodos bem-sucedidos: {', '.join(methods_succeeded)}")
        
        return text, methods_tried

    def _clean_text(self, text: str) -> str:
        """Limpa e normaliza o texto extraído."""
        if not text:
            return ""
            
        # Remove caracteres de controle
        text = ''.join(char for char in text if unicodedata.category(char)[0] != 'C')
        
        # Normaliza espaços
        text = re.sub(r'\s+', ' ', text)
        
        # Correções mais abrangentes para OCR e texto corrompido
        ocr_replacements = {
            'l': '1', 'I': '1', 'O': '0', 'o': '0',
            'S': '5', 'Z': '2', 'B': '8', 'G': '6',
            '+': '7', '@': '9', '>': '7', '?': '8',
            'd': 'fi', '00': '11', '#': '8'
        }
        
        def replace_in_numbers(match):
            number = match.group()
            for old, new in ocr_replacements.items():
                number = number.replace(old, new)
            return number
        
        # Aplica correções em potenciais ISBNs
        text = re.sub(r'(?:ISBN[-:]?\s*)?(?:[0-9A-Za-z-]{10,})', replace_in_numbers, text)
        
        return text.strip()

    def _is_manual_or_documentation(self, text: str) -> bool:
        """Verifica se o texto parece ser de um manual."""
        patterns = [
            r'manual\s+de\s+\w+',
            r'student\s+guide',
            r'lab\s+guide',
            r'training\s+manual',
            r'documentation',
            r'confidential\s+and\s+proprietary',
            r'©.*training',
            r'course\s+materials?',
            r'trellix.*student\s+guide',
            r'trellix.*lab\s+guide',
            r'education\s+services',
            r'trellix.*documentation',
            r'student\s+workbook',
            r'training\s+kit'
        ]
        
        text_lower = text.lower()
        
        # Verifica o nome do arquivo também
        if any(x in text_lower for x in ['_sg.pdf', '_lg.pdf']):
            return True
        
        # Se encontrar 2 ou mais padrões, considera como manual
        matches = sum(1 for pattern in patterns if re.search(pattern, text_lower))
        return matches >= 2

    def extract_metadata_from_pdf(self, pdf_path: str) -> Dict:
        """Extrai metadados internos do PDF."""
        logging.info(f"Extraindo metadados de: {pdf_path}")
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                metadata = reader.metadata if reader.metadata else {}
                
                if 'ISBN' in metadata:
                    isbn = re.sub(r'[^0-9X]', '', metadata['ISBN'].upper())
                    if not (self.isbn_extractor.validate_isbn_10(isbn) or 
                           self.isbn_extractor.validate_isbn_13(isbn)):
                        logging.warning(f"ISBN inválido encontrado nos metadados: {isbn}")
                        del metadata['ISBN']
                    else:
                        logging.info(f"ISBN válido encontrado nos metadados: {isbn}")
                        
                return metadata
        except Exception as e:
            logging.error(f"Erro ao extrair metadados de {pdf_path}: {str(e)}")
            return {}

class BookMetadataExtractor:
    def __init__(self, isbndb_api_key: Optional[str] = None):
        self.isbn_extractor = ISBNExtractor()
        self.metadata_fetcher = MetadataFetcher(isbndb_api_key=isbndb_api_key)
        self.pdf_processor = PDFProcessor()
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('book_metadata.log')
            ]
        )

    def process_single_file(self, pdf_path: str, runtime_stats: Dict) -> Optional[BookMetadata]:
        start_time = time.time()
        logging.info(f"Processing: {pdf_path}")
        
        runtime_stats['processed_files'].append(pdf_path)
        runtime_stats['failure_details'][pdf_path] = {}
        runtime_stats['api_errors'][pdf_path] = []  # Inicializa lista de erros
        details = runtime_stats['failure_details'][pdf_path]
        
        try:
            # Extrai texto do PDF
            text, extraction_methods = self.pdf_processor.extract_text_from_pdf(pdf_path)
            details['extraction_methods'] = extraction_methods
            
            # Se não conseguiu extrair texto
            if not text:
                runtime_stats['isbn_extraction_failed'].append(pdf_path)
                details['status'] = 'Falha na extração de texto'
                return None
            
            # Limpa o texto para amostra
            clean_text = re.sub(r'\n\s*\n', '\n', text[:500])
            details['extracted_text_sample'] = clean_text
            
            # Detecta editora
            publisher, confidence = self.isbn_extractor.identify_publisher(text)
            details['detected_publisher'] = publisher
            
            # Extrai metadados internos do PDF
            pdf_metadata = self.pdf_processor.extract_metadata_from_pdf(pdf_path)
            
            # Encontra ISBNs
            isbns = self.isbn_extractor.extract_from_text(text)
            if pdf_metadata.get('ISBN'):
                isbns.add(self.isbn_extractor.normalize_isbn(pdf_metadata['ISBN']))
            
            if not isbns:
                runtime_stats['isbn_extraction_failed'].append(pdf_path)
                details['status'] = 'ISBN não encontrado no arquivo'
                details['extraction_attempts'] = extraction_methods
                return None
            
            details['found_isbns'] = list(isbns)
            details['status'] = 'ISBNs encontrados mas falha na busca online'
            details['api_attempts'] = []
            
            # Tenta obter metadados usando o primeiro ISBN válido que corresponder
            for isbn in isbns:
                try:
                    metadata = self.metadata_fetcher.fetch_metadata(isbn)
                    if metadata:
                        details['api_attempts'].append(metadata.source)
                        if publisher != "unknown" and publisher.lower() in metadata.publisher.lower():
                            metadata.confidence_score += 0.1
                        metadata.file_path = str(pdf_path)
                        runtime_stats['processing_times'].append(time.time() - start_time)
                        details['status'] = 'Sucesso'
                        return metadata
                except Exception as e:
                    error_msg = f"ISBN {isbn}: {str(e)}"
                    runtime_stats['api_errors'][pdf_path].append(error_msg)
                    logging.error(error_msg)
                    continue
            
            runtime_stats['processing_times'].append(time.time() - start_time)
            runtime_stats['api_failures'].append(pdf_path)
            return None
            
        except Exception as e:
            error_msg = f"{pdf_path}: {str(e)}"
            runtime_stats['api_errors'][pdf_path].append(error_msg)
            logging.error(error_msg)
            details['status'] = f'Erro: {str(e)}'
            runtime_stats['processing_times'].append(time.time() - start_time)
            return None

    
    def generate_report(self, results: List[BookMetadata], output_file: str) -> Dict:
            """Gera um relatório detalhado em JSON com os resultados."""
            report = {
                'summary': {
                    'total_files_processed': len(results),
                    'successful_extractions': sum(1 for r in results if r is not None),
                    'failed_extractions': sum(1 for r in results if r is None),
                    'sources_used': dict(Counter(r.source for r in results if r is not None)),
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'publishers': dict(Counter(r.publisher for r in results if r is not None))
                },
                'books': [asdict(r) for r in results if r is not None]
            }
            
            # Salva o relatório
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
                
            return report

    def suggest_filename(self, metadata: BookMetadata) -> str:
        """Sugere um nome de arquivo baseado nos metadados."""
        def clean_string(s: str) -> str:
            s = unicodedata.normalize('NFKD', s)
            s = s.encode('ASCII', 'ignore').decode('ASCII')
            s = re.sub(r'[^\w\s-]', '', s)
            return s.strip()
        
        title = clean_string(metadata.title)
        authors = clean_string(', '.join(metadata.authors[:2]))
        year = metadata.published_date.split('-')[0] if '-' in metadata.published_date else metadata.published_date
        
        max_title_length = 50
        if len(title) > max_title_length:
            title = title[:max_title_length] + '...'
        
        return f"{title} - {authors} ({year}).pdf"

    def print_detailed_report(self, results: List[BookMetadata], runtime_stats: Dict):
        """Imprime um relatório detalhado dos resultados."""
        try:
            total_files = len(runtime_stats['processed_files'])
            successful_results = [r for r in results if r is not None]
            successful = len(successful_results)
            failed = total_files - successful

            print("\n" + "="*80)
            print("RELATÓRIO DE PROCESSAMENTO DE PDFs")
            print("="*80)
            
            # Análise detalhada de falhas (primeiro por ser mais importante)
            print("\n1. ANÁLISE DETALHADA DE FALHAS")
            print("-"*40)
            failed_files = set(runtime_stats['processed_files']) - set(b.file_path for b in successful_results)
            
            if failed_files:
                for failed_file in sorted(failed_files):
                    filename = Path(failed_file).name
                    details = runtime_stats['failure_details'].get(failed_file, {})
                    print(f"\n✗ {filename}")
                    
                    # Métodos de extração tentados
                    if 'extraction_methods' in details:
                        print(f"  Métodos de extração tentados: {', '.join(details['extraction_methods'])}")
                    
                    # ISBNs encontrados
                    if 'found_isbns' in details and details['found_isbns']:
                        print(f"  ISBNs encontrados: {', '.join(details['found_isbns'])}")
                    
                    # APIs tentadas
                    if 'api_attempts' in details:
                        print(f"  APIs tentadas: {', '.join(details['api_attempts'])}")
                    
                    # Erros de API detalhados
                    if failed_file in runtime_stats.get('api_failures', []):
                        errors = runtime_stats['api_errors'].get(failed_file, [])
                        if errors:
                            print("  Erros detalhados:")
                            for error in errors:
                                print(f"    - {error}")
                    
                    # Status de falha
                    if failed_file in runtime_stats.get('isbn_extraction_failed', []):
                        print("  Status: ISBN não encontrado no arquivo")
                        if 'extracted_text_sample' in details:
                            cleaned_sample = details['extracted_text_sample'].strip()
                            if cleaned_sample:
                                print(f"  Amostra do texto: {cleaned_sample}")
                    
                    # Editora detectada
                    publisher = details.get('detected_publisher')
                    if publisher and publisher != 'unknown':
                        print(f"  Editora detectada: {publisher}")
                        print("  FALHA CRÍTICA: Editora conhecida sem metadados")
            else:
                print("\nNenhuma falha encontrada!")
            
            # Resto do relatório (mantido igual)
            print("\n2. LIVROS PROCESSADOS COM SUCESSO")
            print("-"*40)
            if successful > 0:
                for idx, book in enumerate(sorted(successful_results, key=lambda x: x.file_path), 1):
                    print(f"\n{idx}. {book.title}")
                    print(f"   Arquivo: {Path(book.file_path).name}")
                    print(f"   Autores: {', '.join(book.authors)}")
                    print(f"   Editora: {book.publisher}")
                    print(f"   Data: {book.published_date}")
                    print(f"   ISBN-13: {book.isbn_13 or 'N/A'}")
                    print(f"   ISBN-10: {book.isbn_10 or 'N/A'}")
                    print(f"   Confiança: {book.confidence_score:.2f}")
                    print(f"   Fonte: {book.source}")
            else:
                print("\nNenhum livro processado com sucesso.")

            print("\n3. ESTATÍSTICAS GERAIS")
            print("-"*40)
            
            success_rate = (successful / total_files * 100) if total_files > 0 else 0
            failure_rate = (failed / total_files * 100) if total_files > 0 else 0
            
            print(f"Total de arquivos processados: {total_files}")
            print(f"Extrações bem-sucedidas: {successful} ({success_rate:.1f}%)")
            print(f"Extrações falhas: {failed} ({failure_rate:.1f}%)")
            
            if successful > 0:
                print("\n4. ESTATÍSTICAS POR SERVIÇO")
                print("-"*40)
                api_stats = Counter(r.source for r in successful_results)
                for api, count in api_stats.most_common():
                    service_rate = (count / successful * 100)
                    print(f"{api:15}: {count:3} sucessos ({service_rate:.1f}%)")
                
                if runtime_stats['processing_times']:
                    print("\n5. PERFORMANCE")
                    print("-"*40)
                    times = runtime_stats['processing_times']
                    avg_time = sum(times) / len(times)
                    print(f"Tempo médio por arquivo: {avg_time:.2f}s")
                    print(f"Arquivo mais rápido: {min(times):.2f}s")
                    print(f"Arquivo mais lento: {max(times):.2f}s")
            
            print("\n" + "="*80)

        except Exception as e:
            logging.error(f"Erro ao gerar relatório: {str(e)}")
            import traceback
            logging.error(traceback.format_exc())

    def process_directory(self, directory_path: str, subdirs: Optional[List[str]] = None, 
                         recursive: bool = False, max_workers: int = 4) -> List[BookMetadata]:
        directory = Path(directory_path)
        pdf_files = []
        
        runtime_stats = {
            'processed_files': [],
            'isbn_not_found': [],
            'isbn_extraction_failed': [],
            'api_failures': [],
            'processing_times': [],
            'api_attempts': {},
            'api_errors': {},
            'failure_details': {}
        }
        
        if subdirs:
            for subdir in subdirs:
                subdir_path = directory / subdir
                if subdir_path.exists():
                    pdf_files.extend(subdir_path.glob('*.pdf'))
                else:
                    logging.warning(f"Subdiretório não encontrado: {subdir_path}")
        elif recursive:
            pdf_files = list(directory.glob('**/*.pdf'))
        else:
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
        
        try:
            self.print_detailed_report(results, runtime_stats)
        except Exception as e:
            logging.error(f"Erro ao gerar relatório: {str(e)}")
            
        return results
    
class AdvancedTextExtractor:
    def __init__(self):
        self.dependency_manager = DependencyManager()
        self.manual_patterns = [
            'manual', 'guide', 'documentation', 'student guide',
            'workbook', 'handbook', 'reference', 'training',
            'lesson', 'tutorial', 'lab guide', 'exercise book',
            'student workbook', 'course material', 'training kit',
            'quick reference', 'user guide', 'getting started'
        ]
        
        # Padrões expandidos de ISBN
        self.expanded_isbn_patterns = [
            # Padrões para ISBN-13 em diferentes formatos
            r'ISBN(?:-13)?[:\s]*(?:97[89][-\s]*(?:\d[-\s]*){9}\d)',
            r'97[89](?:[-\s]*\d){10}',
            r'97[89]\d{10}',
            
            # Padrões para ISBN-10
            r'ISBN(?:-10)?[:\s]*(?:\d[-\s]*){9}[\dXx]',
            r'(?:\d[-\s]*){9}[\dXx]',
            
            # Padrões específicos para livros técnicos
            r'ISBN(?:[\s-]*(?:Print|eBook|Digital|Paperback|Hardcover)?:?)?\s*(97[89][-\s]*(?:\d[-\s]*){9}\d)',
            r'ISBN\s*(?:Number|No|#)?[:.]?\s*(97[89][-\s]*(?:\d[-\s]*){9}\d)',
            
            # Padrões para múltiplos formatos
            r'(?:Print(?:/|\\)?Digital)?\s*ISBN:\s*(97[89][-\s]*(?:\d[-\s]*){9}\d)',
            r'(?:eBook|Digital|Online)\s*ISBN:\s*(97[89][-\s]*(?:\d[-\s]*){9}\d)',
            
            # Padrões específicos de editoras
            r'Apress\s+ISBN[-:]?\s*(97[89][-\s]*(?:\d[-\s]*){9}\d)',
            r"O'Reilly\s+ISBN[-:]?\s*(97[89][-\s]*(?:\d[-\s]*){9}\d)",
            r'Packt\s+ISBN[-:]?\s*(97[89][-\s]*(?:\d[-\s]*){9}\d)',
            r'Manning\s+ISBN[-:]?\s*(97[89][-\s]*(?:\d[-\s]*){9}\d)',
            r'Wiley\s+ISBN[-:]?\s*(97[89][-\s]*(?:\d[-\s]*){9}\d)',
            
            # Padrões para casos especiais
            r'ISBN[-:]?\s*(?:book|print|ebook)?\s*(97[89]\d{10})',
            r'ISBN[-:]?\s*(?:book|print|ebook)?\s*(97[89][-\s]\d{1,5}[-\s]\d{1,7}[-\s]\d{1,6}[-\s]\d)',
        ]
        
        # Caracteres comumente confundidos em OCR
        self.ocr_replacements = {
            'l': '1', 'I': '1', 'O': '0', 'o': '0',
            'S': '5', 'Z': '2', 'B': '8', 'G': '6',
            'q': '9', 'g': '9', 'z': '2', 'A': '4',
            'T': '7', 'Y': '7', 'U': '0', 'D': '0'
        }

    def extract_text(self, pdf_path: str, max_pages: int = 10) -> Tuple[str, bool]:
        """
        Extrai texto do PDF usando múltiplos métodos disponíveis.
        Retorna uma tupla (texto, é_manual).
        """
        text = ""
        methods_tried = []
        extractors_available = self.dependency_manager.get_available_extractors()

        if not extractors_available:
            logging.error("Nenhum extrator de PDF disponível. Instale pelo menos uma biblioteca de extração.")
            return "", False

        # Primeira tentativa: PyPDF2
        if 'pypdf2' in extractors_available:
            try:
                with open(pdf_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    pages_to_check = min(max_pages, len(reader.pages))
                    
                    for page_num in range(pages_to_check):
                        text += reader.pages[page_num].extract_text() + "\n"
                        
                    if text.strip():
                        methods_tried.append('pypdf2')
                        
                    # Verifica qualidade do texto
                    if text and not self._is_text_garbage(text):
                        logging.info("Texto extraído com sucesso usando PyPDF2")
                        text = self._clean_text(text)
                        return text, self._is_manual_or_documentation(text)
            except Exception as e:
                logging.debug(f"PyPDF2 extraction failed: {str(e)}")

        # Segunda tentativa: pdfplumber
        if 'pdfplumber' in extractors_available:
            try:
                import pdfplumber
                with pdfplumber.open(pdf_path) as pdf:
                    pages_to_check = min(max_pages, len(pdf.pages))
                    text = ""
                    for page in pdf.pages[:pages_to_check]:
                        text += page.extract_text() + "\n"
                        
                    if text.strip():
                        methods_tried.append('pdfplumber')
                        
                    # Verifica qualidade do texto
                    if text and not self._is_text_garbage(text):
                        logging.info("Texto extraído com sucesso usando pdfplumber")
                        text = self._clean_text(text)
                        return text, self._is_manual_or_documentation(text)
            except Exception as e:
                logging.debug(f"pdfplumber extraction failed: {str(e)}")

        # Terceira tentativa: pdfminer
        if 'pdfminer' in extractors_available:
            try:
                from pdfminer.high_level import extract_text as pdfminer_extract
                text = pdfminer_extract(pdf_path, maxpages=max_pages)
                if text.strip():
                    methods_tried.append('pdfminer')
                    
                # Verifica qualidade do texto
                if text and not self._is_text_garbage(text):
                    logging.info("Texto extraído com sucesso usando pdfminer")
                    text = self._clean_text(text)
                    return text, self._is_manual_or_documentation(text)
            except Exception as e:
                logging.debug(f"pdfminer extraction failed: {str(e)}")

        # Última tentativa: OCR com Tesseract
        if self.dependency_manager.has_ocr_support:
            try:
                import pytesseract
                from pdf2image import convert_from_path
                
                images = convert_from_path(pdf_path, last_page=max_pages)
                text = ""
                for image in images:
                    text += pytesseract.image_to_string(image) + "\n"
                    
                if text.strip():
                    methods_tried.append('tesseract')
                    
                # Verifica qualidade do texto
                if text and not self._is_text_garbage(text):
                    logging.info("Texto extraído com sucesso usando Tesseract OCR")
                    text = self._clean_text(text)
                    return text, self._is_manual_or_documentation(text)
            except Exception as e:
                logging.debug(f"Tesseract OCR failed: {str(e)}")

        if not text.strip():
            logging.warning(f"Nenhum método de extração teve sucesso")
            if methods_tried:
                logging.info(f"Métodos tentados: {', '.join(methods_tried)}")
            return "", False

        # Se chegou aqui, usa o melhor texto que conseguiu
        text = self._clean_text(text)
        is_manual = self._is_manual_or_documentation(text)
        logging.info(f"Texto extraído usando: {', '.join(methods_tried)}")
        return text, is_manual

    def _is_text_garbage(self, text: str) -> bool:
        """
        Verifica se o texto extraído parece ser lixo ou está muito corrompido.
        """
        if not text:
            return True
            
        # Remove espaços em branco e caracteres especiais para análise
        clean_text = ''.join(c for c in text if c.isalnum())
        
        # Texto muito curto
        if len(clean_text) < 50:
            return True
            
        # Alta proporção de caracteres especiais
        special_chars = sum(1 for c in text if not c.isalnum() and not c.isspace())
        if len(text) > 0 and special_chars / len(text) > 0.4:
            return True
            
        # Sequências longas de caracteres idênticos
        if any(c * 8 in text for c in set(text)):
            return True
            
        # Baixa variabilidade de caracteres
        unique_chars = len(set(clean_text))
        if len(clean_text) > 0 and unique_chars / len(clean_text) < 0.1:
            return True
            
        return False

    def _clean_text(self, text: str) -> str:
        """Limpa e normaliza o texto extraído."""
        import unicodedata
        
        # Remove caracteres de controle
        text = ''.join(char for char in text if unicodedata.category(char)[0] != 'C')
        
        # Normaliza espaços e quebras de linha
        text = re.sub(r'\s+', ' ', text)
        
        # Aplica correções apenas em sequências que parecem números
        def replace_in_numbers(match):
            number = match.group()
            for old, new in self.ocr_replacements.items():
                if old in number:
                    number = number.replace(old, new)
            return number
            
        # Aplica correções apenas em potenciais ISBNs
        isbn_pattern = r'(?:ISBN[-:]?\s*)?(?:[0-9A-Za-z-]{10,})'
        text = re.sub(isbn_pattern, replace_in_numbers, text)
        
        return text.strip()
    
    def _is_manual_or_documentation(self, text: str) -> bool:
        """
        Verifica se o texto parece ser de um manual ou documentação.
        Retorna True se for manual/documentação, False caso contrário.
        """
        text_lower = text.lower()
        
        # Verifica padrões de manuais
        if any(pattern in text_lower for pattern in self.manual_patterns):
            # Verifica por indicadores adicionais
            if re.search(r'(chapter|lesson|module|training|exercise)\s+\d+', text_lower):
                return True
            if re.search(r'student\s+guide|instructor\s+manual|training\s+material', text_lower):
                return True
            if re.search(r'lab\s+\d+|appendix\s+[a-z]|unit\s+\d+', text_lower):
                return True
                
        # Verifica estrutura típica de manuais
        content_indicators = [
            r'table\s+of\s+contents',
            r'learning\s+objectives',
            r'course\s+overview',
            r'prerequisites',
            r'©\s*\d{4}.*\s+training',
            r'©\s*\d{4}.*\s+documentation',
            r'all\s+rights\s+reserved.*training',
            r'confidential\s+and\s+proprietary'
        ]
        
        if sum(1 for pattern in content_indicators if re.search(pattern, text_lower)) >= 2:
            return True
            
        return False

    def find_isbns(self, text: str) -> Set[str]:
        """Encontra ISBNs usando padrões expandidos."""
        isbns = set()
        
        for pattern in self.expanded_isbn_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                isbn = match.group(1) if '(' in pattern else match.group()
                isbn = re.sub(r'[^0-9X]', '', isbn.upper())
                
                if len(isbn) == 10:
                    if self._validate_isbn_10(isbn):
                        isbns.add(isbn)
                        isbn13 = self._convert_isbn10_to_13(isbn)
                        if isbn13:
                            isbns.add(isbn13)
                elif len(isbn) == 13:
                    if self._validate_isbn_13(isbn):
                        isbns.add(isbn)
                        
        return isbns
    
    def _validate_isbn_10(self, isbn: str) -> bool:
        """Valida ISBN-10."""
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
            
    def _validate_isbn_13(self, isbn: str) -> bool:
        """Valida ISBN-13."""
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
            
    def _convert_isbn10_to_13(self, isbn10: str) -> Optional[str]:
        """Converte ISBN-10 para ISBN-13."""
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
   
def rescan_and_update(self):
    """
    Verifica todos os registros no cache e atualiza aqueles com pontuação de confiança inferior.
    """
    all_metadata = self.get_all()
    for metadata in all_metadata:
        # Consulta os metadados usando o ISBN
        new_metadata = self.fetch_metadata(metadata['isbn_10'] or metadata['isbn_13'])
        
        # Atualiza o registro apenas se a nova pontuação de confiança for maior
        if new_metadata and new_metadata['confidence_score'] > metadata['confidence_score']:
            self.update(new_metadata)   
    
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
  %(prog)s "/Users/menon/Downloads" -r -t 8 --rename -v -k "sua_chave_isbndb" -o "relatorio.json" --rescan
  
  # Exemplos com diretórios reais:
  %(prog)s "/Users/menon/Downloads/LEARN YOU SOME CODE BY NO STARCH"
  %(prog)s "/Users/menon/Downloads/machine Learning Oreilly"

Observações:
  - Por padrão, processa apenas o diretório especificado (sem subdiretórios)
  - Use -r para processar todos os subdiretórios
  - Use --subdirs para processar apenas subdiretórios específicos
  - A chave ISBNdb é opcional e pode ser colocada em qualquer posição do comando
  - Use --rescan para forçar um rescaneamento e atualização do cache de metadados

Rescaneamento do cache de metadados:
  O programa possui a capacidade de rescanear periodicamente o cache de metadados e atualizar os registros com informações de
  melhor qualidade. Essa funcionalidade é ativada quando a opção --rescan é utilizada.

  Por exemplo, ao executar o comando:
  %(prog)s "/Users/menon/Downloads" --rescan

 O programa processará os arquivos PDF no diretório e também atualizará os registros existentes no cache caso
 sejam encontrados metadados mais confiáveis. Recomenda-se utilizar a opção --rescan periodicamente.
  
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