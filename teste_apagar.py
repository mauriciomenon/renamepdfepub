# TO DO Remover estas importações
# from pdfminer.high_level import extract_text as pdfminer_extract
# import pytesseract
# from pdf2image import convert_from_path

# Bibliotecas padrão do Python
import argparse
import json
import logging
import re
import sqlite3
import sys
import time
import unicodedata
from collections import Counter
from concurrent import futures
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import quote

# Bibliotecas de terceiros - HTTP/API
import requests
import xml.etree.ElementTree as ET
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tqdm import tqdm

# Bibliotecas de terceiros - Processamento de PDF
import PyPDF2
import pdfplumber
from pdfminer.high_level import extract_text as pdfminer_extract
import pytesseract
from pdf2image import convert_from_path

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

    def get_all(self) -> List[Dict]:
        """Retorna todos os registros do cache."""
        with sqlite3.connect(self.db_path) as conn:
            results = conn.execute("""
                SELECT isbn_10, isbn_13, title, authors, publisher, 
                    published_date, confidence_score, source, file_path, raw_json
                FROM metadata_cache
                """).fetchall()
            
            if not results:
                return []
                
            return [
                {
                    'isbn_10': r[0],
                    'isbn_13': r[1],
                    'title': r[2], 
                    'authors': r[3].split(', '),
                    'publisher': r[4],
                    'published_date': r[5],
                    'confidence_score': r[6],
                    'source': r[7],
                    'file_path': r[8]
                } for r in results
            ]

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

class APIHandler:
    def __init__(self):
        self.session = requests.Session()
        
        # Configuração mais robusta de retry
        retry_strategy = Retry(
            total=5,
            backoff_factor=1,  # Aumentado para dar mais tempo entre tentativas
            status_forcelist=[404, 429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"],
            respect_retry_after_header=True
        )
        
        adapter = HTTPAdapter(
            pool_connections=100,
            pool_maxsize=100,
            max_retries=retry_strategy,
            pool_block=False
        )
        
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Headers mais robustos
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
            'Accept': 'application/json,application/xml,text/html,application/xhtml+xml,*/*;q=0.9',
            'Accept-Language': 'en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache'
        })

    def get(self, url: str, params: Dict = None, timeout: int = 10, verify: bool = True) -> requests.Response:
        """GET request com melhor tratamento de erros."""
        try:
            response = self.session.get(
                url,
                params=params,
                timeout=timeout,
                verify=verify
            )
            response.raise_for_status()
            return response
        except requests.exceptions.SSLError:
            # Tenta novamente sem verificação SSL se falhar
            return self.session.get(url, params=params, timeout=timeout, verify=False)
        except requests.exceptions.ConnectionError as e:
            if "ProxyError" in str(e):
                # Tenta sem proxy
                self.session.trust_env = False
                return self.session.get(url, params=params, timeout=timeout, verify=verify)
            raise
            
    def post(self, url: str, data: Dict = None, json: Dict = None, timeout: int = 10) -> requests.Response:
        """POST request com melhor tratamento de erros."""
        try:
            response = self.session.post(
                url,
                data=data,
                json=json,
                timeout=timeout
            )
            response.raise_for_status()
            return response
        except requests.exceptions.SSLError:
            return self.session.post(url, data=data, json=json, timeout=timeout, verify=False)

class ISBNExtractor:
    def __init__(self):
        # Padrões de ISBN
        self.isbn_patterns = [
            # ISBN-13 com prefixo
            r'ISBN[:\s-]*(97[89](?:[- ]?\d){10})',
            r'ISBN-13[:\s-]*(97[89](?:[- ]?\d){10})',
            
            # ISBN-10 com prefixo
            r'ISBN[:\s-]*(\d{9}[\dXx])',
            r'ISBN-10[:\s-]*(\d{9}[\dXx])',
            
            # Padrões sem prefixo
            r'(?<!\d)(97[89](?:\d[-\s]?){10})(?!\d)',
            r'(?<!\d)(\d{9}[0-9Xx])(?!\d)',
            
            # Padrões brasileiros
            r'ISBN[:\s-]*(978(?:65|85)\d{10})',
            r'EAN[:\s-]*(978(?:65|85)\d{10})',
            
            # Padrões com pontuação
            r'ISBN[:\s]*([0-9]{3}[-\s]?[0-9]{10})',
            r'ISBN[:\s]*([0-9]{9}[0-9Xx])',

            # Padrões sem espaço após ISBN
            r'ISBN:(97[89]\d{10})',
            r'ISBN:(\d{9}[\dXx])',
            
            # Padrões para ISBNs com múltiplos hífens
            r'ISBN:\s*([0-9]{3}[- ]*[0-9][- ]*[0-9]{3}[- ]*[0-9]{5}[- ]*[0-9X])',
            r'ISBN:\s*([0-9]{3}[- ]*[0-9][- ]*[0-9]{3}[- ]*[0-9]{5}[- ]*[0-9X])\s*\((?:ebk|ebook|pdf|digital)\)',
            
            # Padrões para capturar sequências específicas do exemplo
            r'978[- ]*1[- ]*394[- ]*\d{5}[- ]*[0-9X]',
            r'979[- ]*1[- ]*394[- ]*\d{5}[- ]*[0-9X]',
            
            # Padrões básicos existentes
            r'ISBN[:\s-]*(97[89]\d{10})',
            r'ISBN[:\s-]*([\dX]{10})',
            r'ISBN-13[:\s-]*(97[89]\d{10})',
            r'ISBN-10[:\s-]*([\dX]{10})',
            
            # Padrões mais flexíveis para hifenização
            r'ISBN[:\s]*(\d{3}[-\s]*\d{1,5}[-\s]*\d{1,7}[-\s]*\d{1,6}[-\s]*[\dX])',
            r'(?:ISBN[:\s]*)?(\d{3}[-\s]*\d{1,5}[-\s]*\d{1,7}[-\s]*\d{1,6}[-\s]*[\dX])',
            
            # Padrões específicos para formatos digitais
            r'ISBN[:\s]*([0-9-]{13,17})[\s]*\((?:ebk|ebook|pdf|digital)\)',
            r'(?:E-?book|Digital)\s+ISBN[:\s]*([0-9-]{13,17})',
            
            r'ISBN:\s*(\d{3}[-\s]+\d[-\s]+\d{3}[-\s]+\d{5}[-\s]*\d)',  # matches: 978- 1- 394- 15848- 5
            r'ISBN:\s*(\d{3}[-\s]+\d[-\s]+\d{3}[-\s]+\d{5}[-\s]*\d)(?:\s*\([^)]*\))?',  # matches com (ebk)
            
            # Backup patterns para o mesmo formato
            r'978[-\s]+1[-\s]+394[-\s]+\d{5}[-\s]*\d',
            r'979[-\s]+1[-\s]+394[-\s]+\d{5}[-\s]*\d', 
            
            r'ISBN:\s*(\d{3}[-\s]+\d[-\s]+\d{3}[-\s]+\d{5}[-\s]*\d)',  # matches: 978- 1- 394- 15848- 5
            r'ISBN:\s*(\d{3}[-\s]+\d[-\s]+\d{3}[-\s]+\d{5}[-\s]*\d)(?:\s*\([^)]*\))?',  # matches com (ebk)
            
            # Padrões específicos para formatos como no seu exemplo
            r'978[-\s]+1[-\s]+394[-\s]+\d{5}[-\s]*\d',
            r'979[-\s]+1[-\s]+394[-\s]+\d{5}[-\s]*\d',
            
            # Padrões originais
            r'ISBN[:\s-]*(97[89]\d{10})',
            r'ISBN[:\s-]*([\dX]{10})',
            r'ISBN-13[:\s-]*(97[89]\d{10})',
            r'ISBN-10[:\s-]*([\dX]{10})',
            
            # Padrões mais flexíveis
            r'ISBN[:\s]*(\d{3}[-\s]*\d{1,5}[-\s]*\d{1,7}[-\s]*\d{1,6}[-\s]*[\dX])',
            r'(?:ISBN[:\s]*)?(\d{3}[-\s]*\d{1,5}[-\s]*\d{1,7}[-\s]*\d{1,6}[-\s]*[\dX])',
            
            # Padrões para formatos digitais
            r'ISBN[:\s]*([0-9-]{13,17})[\s]*\((?:ebk|ebook|pdf|digital)\)',
            r'(?:E-?book|Digital)\s+ISBN[:\s]*([0-9-]{13,17})',
        ]

        # Editoras brasileiras
        self.BRAZILIAN_PUBLISHERS = {
            'casa do codigo': {
                'pattern': r'(?:Casa\s+do\s+[cC]ódigo|CASA\s+DO\s+CÓDIGO)',
                'prefixes': ['97865']
            },
            'novatec': {
                'pattern': r'(?:Novatec|NOVATEC)',
                'prefixes': ['97885']
            },
            'alta books': {
                'pattern': r'(?:Alta\s+Books|ALTA\s+BOOKS)',
                'prefixes': ['97885']
            }
        }

        # Editoras internacionais
        self.INTERNATIONAL_PUBLISHERS = {
            'oreilly': {
                'pattern': r"(?:O'Reilly|OREILLY)",
                'prefixes': ['97814']
            },
            'packt': {
                'pattern': r'(?:Packt|PACKT)',
                'prefixes': ['97817']
            },
            'apress': {
                'pattern': r'(?:Apress|APRESS)',
                'prefixes': ['97814']
            },
            'manning': {
                'pattern': r'(?:Manning|MANNING)',
                'prefixes': ['97816']
            },
            'wiley': {
                'pattern': r'(?:Wiley|WILEY)',
                'prefixes': ['97811']
            }
        }

        # Correção de caracteres
        self.char_corrections = {
            'O': '0', 'o': '0', 'Q': '0', 'D': '0',
            'I': '1', 'l': '1', 'i': '1',
            'Z': '2', 'z': '2',
            'E': '3',
            'h': '4', 'A': '4',
            'S': '5', 's': '5',
            'G': '6', 'b': '6',
            'T': '7',
            'B': '8',
            'g': '9', 'q': '9',
            'º': '0', '°': '0',
            '@': '9',
            '|': '1'
        }

    def identify_publisher(self, text: str) -> Tuple[str, float]:
        """Identifica a editora no texto."""
        text = text.lower()
        confidence_boost = 0.1

        # Verifica editoras brasileiras primeiro
        for publisher, info in self.BRAZILIAN_PUBLISHERS.items():
            if re.search(info['pattern'], text, re.IGNORECASE):
                return publisher, confidence_boost

        # Depois verifica editoras internacionais
        for publisher, info in self.INTERNATIONAL_PUBLISHERS.items():
            if re.search(info['pattern'], text, re.IGNORECASE):
                return publisher, confidence_boost

        return "unknown", 0.0

    def _clean_text_for_isbn(self, text: str) -> str:
        """Limpa texto especificamente para encontrar ISBNs."""
        # Primeiro normaliza os hífens e espaços
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'-+', '-', text)
        
        # Corrige casos específicos de OCR mal feito
        replacements = {
            '7ran': 'Tran',
            '50c1': 'Soci',
            '51mu1': 'simul',
            'tane0u51y': 'taneously',
            'pu611cat10n': 'publication',
            'repr0f1ucef1': 'reproduced',
            'tran5m1ttef1': 'transmitted'
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
            
        # Normaliza formatos de ISBN
        text = re.sub(r'ISBN[:\s]*', 'ISBN: ', text, flags=re.IGNORECASE)
        text = re.sub(r'\s+', ' ', text)
    
        # Remove espaços extras ao redor de hífens em números
        text = re.sub(r'(\d)\s*-\s*(\d)', r'\1-\2', text)
        
        return text

    def _normalize_ocr_text(self, text: str) -> str:
        """Normaliza texto com problemas comuns de OCR."""
        replacements = {
            # Números e letras comumente confundidos
            '0': ['O', 'o', 'Q', 'D', 'U'],
            '1': ['I', 'l', 'i', '|', 'L'],
            '2': ['Z', 'z'],
            '3': ['E', 'B'],
            '4': ['h', 'A', 'H'],
            '5': ['S', 's', '§'],
            '6': ['G', 'b'],
            '7': ['T', '+', 'Y'],
            '8': ['B', 'R'],
            '9': ['g', 'q', '@', 'P'],
            
            # Sequências específicas
            'ISBN': ['IS8N', 'IS3N', 'ISEN', '1SBN', 'iSBN'],
            '-': ['_', '—', '–', '='],
        }
        
        # Aplica as substituições
        normalized = text
        for correct, wrong_chars in replacements.items():
            for wrong in wrong_chars:
                normalized = normalized.replace(wrong, correct)
        
        return normalized

    def _extract_digital_isbns(self, text: str) -> Set[str]:
        """Extrai ISBNs específicos de formatos digitais."""
        digital_patterns = [
            r'(?:E-?book|Digital|PDF|EPUB)\s+ISBN[:\s]*([0-9-]{13,17})',
            r'ISBN[:\s]*([0-9-]{13,17})\s*\((?:ebk|ebook|pdf|epub|digital)\)',
            r'Electronic\s+ISBN[:\s]*([0-9-]{13,17})',
        ]
        
        found_isbns = set()
        for pattern in digital_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                isbn = self._normalize_isbn(match.group(1))
                if self._validate_isbn(isbn):
                    found_isbns.add(isbn)
        
        return found_isbns

    def _extract_from_pdf_metadata(self, pdf_path: str) -> Set[str]:
        """Extrai ISBNs dos metadados do PDF."""
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                metadata = reader.metadata if reader.metadata else {}
                
                found_isbns = set()
                
                # Procura em campos comuns de metadados
                fields_to_check = ['ISBN', 'Subject', 'Keywords', 'Title', 'Description']
                for field in fields_to_check:
                    if field in metadata:
                        # Procura por padrões de ISBN no valor do campo
                        text = str(metadata[field])
                        for pattern in self.isbn_patterns:
                            matches = re.finditer(pattern, text, re.IGNORECASE)
                            for match in matches:
                                isbn = self._normalize_isbn(match.group(1))
                                if self._validate_isbn(isbn):
                                    found_isbns.add(isbn)
                
                return found_isbns
        except Exception as e:
            logging.debug(f"Erro ao extrair metadados do PDF: {str(e)}")
            return set()

    def extract_from_text(self, text: str, source_path: str = None) -> Set[str]:
        """
        Extrai ISBNs do texto usando uma combinação de abordagem simples e robusta.
        """
        # Se não tem texto mas tem caminho, tenta extrair do PDF
        if not text and source_path:
            text = self._extract_from_pdf(source_path)
        
        if not text:
            return set()

        found_isbns = set()
        original_text = text
        
        # Lista simplificada de versões do texto
        text_versions = [
            text,                                      # Original
            text.replace('-', '').replace(' ', ''),    # Remove separadores
            self._clean_text_for_isbn(text),           # Limpeza específica para ISBN
            self._normalize_ocr_text(text),            # Correção de OCR
        ]
        
        # Processa cada versão do texto
        for cleaned_text in text_versions:
            for pattern in self.isbn_patterns:
                matches = re.finditer(pattern, cleaned_text, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    try:
                        # Se tem grupos, pega o primeiro grupo, senão pega o match inteiro
                        isbn = match.group(1) if match.groups() else match.group()
                        
                        # Limpa o ISBN (remove tudo exceto números)
                        isbn = self._normalize_isbn(isbn)
                        
                        # Validação básica de tamanho e prefixo
                        if len(isbn) == 13 and isbn.startswith(('978', '979')):
                            if self._validate_isbn_13_checksum(isbn):
                                found_isbns.add(isbn)
                        elif len(isbn) == 10:
                            if self._validate_isbn_10_checksum(isbn):
                                found_isbns.add(isbn)
                                # Adiciona também a versão ISBN-13
                                isbn13 = self._isbn_10_to_13(isbn)
                                if isbn13:
                                    found_isbns.add(isbn13)
                    except Exception as e:
                        logging.debug(f"Erro ao processar match: {str(e)}")
                        continue
            
            # Se encontrou ISBNs válidos, não precisa tentar outras versões do texto
            if found_isbns:
                break
        
        # Se não encontrou nada ainda, tenta métodos alternativos
        if not found_isbns:
            # Tenta encontrar padrões específicos de ISBN digital
            digital_isbns = self._extract_digital_isbns(original_text)
            found_isbns.update(digital_isbns)
            
            # Tenta encontrar ISBNs em metadados do PDF
            if source_path:
                metadata_isbns = self._extract_from_pdf_metadata(source_path)
                found_isbns.update(metadata_isbns)
        
        return found_isbns

    def _extract_from_pdf(self, pdf_path: str, max_pages: int = 30) -> str:
        """Extrai texto do PDF."""
        try:
            text = ""
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                # Verifica primeiras e últimas páginas
                priority_pages = [0, 1, 2, -1, -2]
                for page_num in priority_pages:
                    if abs(page_num) < len(reader.pages):
                        idx = page_num if page_num >= 0 else len(reader.pages) + page_num
                        text += reader.pages[idx].extract_text() + "\n"
                
                # Se não encontrou ISBN, verifica mais páginas
                if not any(p in text.lower() for p in ['isbn', '978', '979']):
                    for i in range(3, min(max_pages, len(reader.pages))):
                        text += reader.pages[i].extract_text() + "\n"
            return text
        except Exception as e:
            logging.error(f"Erro ao extrair texto do PDF: {str(e)}")
            return ""

    def _clean_text_basic(self, text: str) -> str:
        """Limpeza básica do texto."""
        text = ''.join(char if char.isprintable() or char.isspace() else ' ' for char in text)
        text = ' '.join(text.split())
        for old, new in self.char_corrections.items():
            text = text.replace(old, new)
        return text

    def _clean_text_aggressive(self, text: str) -> str:
        """Limpeza agressiva do texto."""
        text = re.sub(r'[^0-9X\s-]', '', text.upper())
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'-+', '-', text)
        return text.strip()

    def _normalize_isbn(self, isbn: str) -> str:
        """Normaliza ISBN removendo todos os caracteres não numéricos."""
        # Remove tudo exceto números e X
        isbn = ''.join(c for c in isbn.upper() if c.isdigit() or c == 'X')
        
        # Se o ISBN está em um formato válido após limpeza
        if len(isbn) in (10, 13):
            return isbn
            
        # Se ainda tem caracteres demais, tenta limpar mais agressivamente
        isbn = re.sub(r'[^0-9X]', '', isbn.upper())
        return isbn

    def _validate_isbn(self, isbn: str) -> bool:
        """Validação melhorada de ISBN."""
        # Remove caracteres não numéricos exceto X
        isbn = ''.join(c for c in isbn.upper() if c.isdigit() or c == 'X')
        
        if len(isbn) == 13:
            return (
                isbn.startswith(('978', '979')) and 
                isbn.isdigit() and
                self._validate_isbn_13_checksum(isbn)
            )
        elif len(isbn) == 10:
            return (
                isbn[:9].isdigit() and
                (isbn[9].isdigit() or isbn[9] == 'X') and
                self._validate_isbn_10_checksum(isbn)
            )
        return False

    def _validate_isbn_13_checksum(self, isbn: str) -> bool:
        """Valida checksum de ISBN-13."""
        try:
            total = sum((1 if i % 2 == 0 else 3) * int(digit)
                       for i, digit in enumerate(isbn[:12]))
            check = (10 - (total % 10)) % 10
            return check == int(isbn[-1])
        except ValueError:
            return False

    def _validate_isbn_10_checksum(self, isbn: str) -> bool:
        """Valida checksum de ISBN-10."""
        try:
            total = sum((10 - i) * (int(digit) if digit != 'X' else 10)
                       for i, digit in enumerate(isbn))
            return total % 11 == 0
        except ValueError:
            return False

    def _validate_isbn_10(self, isbn: str) -> bool:
        """Valida ISBN-10."""
        if not (len(isbn) == 10 and isbn[:9].isdigit() and 
               (isbn[9].isdigit() or isbn[9] == 'X')):
            return False

        try:
            total = sum((10 - i) * (int(num) if num != 'X' else 10)
                       for i, num in enumerate(isbn))
            return total % 11 == 0
        except:
            return False

    def _validate_isbn_13(self, isbn: str) -> bool:
        """Validação melhorada de ISBN-13."""
        if len(isbn) != 13 or not isbn.isdigit() or not isbn.startswith(('978', '979')):
            return False

        # Calcula checksum
        total = 0
        for i in range(12):
            if i % 2 == 0:
                total += int(isbn[i])
            else:
                total += int(isbn[i]) * 3
        
        check = (10 - (total % 10)) % 10
        return check == int(isbn[-1])

class MetadataFetcher:
    def __init__(self, isbndb_api_key: Optional[str] = None):
        self.cache = MetadataCache()
        self.api = APIHandler()
        self.session = requests.Session()
        self.isbndb_api_key = isbndb_api_key
        
        # Configuração de timeouts e retries mais robusta
        self.session.timeout = (5, 15)  # (connect timeout, read timeout)
        
        # Configuração de retry mais robusta
        retry_strategy = Retry(
            total=5,  
            backoff_factor=0.5,
            status_forcelist=[404, 429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"],
            respect_retry_after_header=True
        )
        
        # Configuração do adapter
        adapter = HTTPAdapter(
            pool_connections=100,
            pool_maxsize=100,
            max_retries=retry_strategy,
            pool_block=False
        )
        
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Headers atualizados
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json,text/html,application/xhtml+xml',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive'
        })

    def fetch_metadata(self, isbn: str) -> Optional[BookMetadata]:
            """Método principal para buscar metadados."""
            # Verifica cache primeiro
            cached = self.cache.get(isbn)
            if cached:
                return BookMetadata(**cached)

            # Todas as fontes em ordem de prioridade com scores atualizados baseados no relatório
            fetchers = [
                # APIs primárias - melhor desempenho comprovado
                (self.fetch_google_books, 9),      # 50% sucesso - mantida como primária
                (self.fetch_openlibrary, 8.5),     # 60% sucesso - melhor desempenho geral
                (self.fetch_worldcat, 7.5),        # 55.6% sucesso - bom desempenho
                
                # APIs secundárias - desempenho moderado
                (self.fetch_internet_archive, 7),   # 33.3% sucesso
                (self.fetch_crossref, 6.5),        # Taxa moderada de sucesso
                (self.fetch_google_books_br, 6),    # 11.1% sucesso mas útil para livros BR
                (self.fetch_mercado_editorial, 5.5),# 11.1% sucesso mas mantida para BR
                
                # APIs com baixo desempenho mas mantidas para casos específicos
                (self.fetch_zbib, 5),              # Baixo sucesso mas mantida como fallback
                (self.fetch_cbl, 5),               # Mantida para livros brasileiros
                
                # APIs desabilitadas temporariamente - 0% sucesso nos testes
                # (self.fetch_oreilly, 9),         # 0% sucesso - desabilitada
                # (self.fetch_springer, 8.5),      # 0% sucesso - desabilitada
                # (self.fetch_mybib, 5),           # 0% sucesso - desabilitada
                # (self.fetch_ebook_de, 5),        # 0% sucesso - desabilitada
                # (self.fetch_deutsche_national, 5),# 0% sucesso - desabilitada
                # (self.fetch_british_library, 5),  # 0% sucesso - desabilitada
                # (self.fetch_hathitrust, 5),      # 0% sucesso - desabilitada
                # (self.fetch_apress, 5),          # 0% sucesso - desabilitada
                # (self.fetch_manning, 5),         # 0% sucesso - desabilitada
                # (self.fetch_packt, 5),           # 0% sucesso - desabilitada
            ]

            # Ajusta scores de confiança baseados no desempenho real
            confidence_adjustments = {
                'google_books': 0.50,    # 50% taxa de sucesso
                'openlibrary': 0.60,     # 60% taxa de sucesso
                'worldcat': 0.55,        # ~55% taxa de sucesso
                'internet_archive': 0.33, # 33.3% taxa de sucesso
                'google_books_br': 0.11,  # 11.1% taxa de sucesso
                'mercado_editorial': 0.11 # 11.1% taxa de sucesso
            }

            all_results = []
            processed = set()
            last_error = None
            
            # Configurações de retry otimizadas baseadas no desempenho
            retry_configs = {
                'high_priority': {
                    'max_retries': 3,    # Reduzido de 5 para 3
                    'backoff_factor': 1.5,
                    'retry_delay': 2
                },
                'medium_priority': {
                    'max_retries': 2,    # Reduzido para 2
                    'backoff_factor': 1,
                    'retry_delay': 1
                },
                'low_priority': {
                    'max_retries': 1,    # Apenas 1 tentativa
                    'backoff_factor': 0.5,
                    'retry_delay': 0.5
                }
            }

            for fetcher, priority in fetchers:
                if fetcher.__name__ not in processed:
                    # Determina a configuração de retry baseada na prioridade
                    if priority >= 8:
                        retry_config = retry_configs['high_priority']
                    elif priority >= 6:
                        retry_config = retry_configs['medium_priority']
                    else:
                        retry_config = retry_configs['low_priority']

                    for attempt in range(retry_config['max_retries']):
                        try:
                            metadata = fetcher(isbn)
                            if metadata:
                                # Ajusta score baseado no desempenho real da API
                                base_score = priority / 10
                                adjustment = confidence_adjustments.get(metadata.source, 0.5)
                                metadata.confidence_score = min(1.0, base_score * adjustment)
                                
                                # Adiciona ISBN-10/13 se não existir
                                if len(isbn) == 10 and not metadata.isbn_10:
                                    metadata.isbn_10 = isbn
                                elif len(isbn) == 13 and not metadata.isbn_13:
                                    metadata.isbn_13 = isbn
                                    
                                all_results.append(metadata)
                                
                                # Se encontrou com alta confiança (>0.85), pode parar
                                if metadata.confidence_score > 0.85:
                                    break
                        except Exception as e:
                            last_error = e
                            self._handle_api_error(fetcher.__name__, e, isbn)
                            
                            if attempt < retry_config['max_retries'] - 1:
                                sleep_time = retry_config['retry_delay'] * (retry_config['backoff_factor'] ** attempt)
                                time.sleep(sleep_time)
                                
                    processed.add(fetcher.__name__)

                    # Se já tem resultados suficientes com boa confiança, pode parar
                    if len(all_results) >= 2 and any(r.confidence_score > 0.80 for r in all_results):
                        break

            # Escolhe o melhor resultado baseado na pontuação de confiança ajustada
            if all_results:
                return max(all_results, key=lambda x: x.confidence_score)
                
            return self._create_fallback_metadata(isbn, last_error)

    def _results_match(self, result1: BookMetadata, result2: BookMetadata) -> bool:
        """Compara dois resultados para ver se são similares."""
        # Função de similaridade de strings
        def similar(a: str, b: str) -> bool:
            a = a.lower().strip()
            b = b.lower().strip()
            return (
                a == b or
                a in b or b in a or
                self._levenshtein_distance(a, b) / max(len(a), len(b)) < 0.3
            )
        
        # Compara título e autores
        title_match = similar(result1.title, result2.title)
        authors_match = any(
            any(similar(a1, a2) for a2 in result2.authors)
            for a1 in result1.authors
        )
        
        return title_match and authors_match

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calcula a distância de Levenshtein entre duas strings."""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    def fetch_cbl(self, isbn: str) -> Optional[BookMetadata]:
        """Busca na API da Câmara Brasileira do Livro."""
        try:
            url = f"https://isbn.cbl.org.br/api/isbn/{isbn}"
            response = self.session.get(url, timeout=10)
            
            if response.status_code != 200:
                return None
                
            data = response.json()
            
            return BookMetadata(
                title=data.get('title', 'Unknown'),
                authors=data.get('authors', ['Unknown']),
                publisher=data.get('publisher', 'Unknown'),
                published_date=data.get('published_date', 'Unknown'),
                isbn_13=isbn if len(isbn) == 13 else None,
                isbn_10=isbn if len(isbn) == 10 else None,
                confidence_score=0.95,  # Alta confiança para CBL
                source='cbl'
            )
        except Exception as e:
            logging.error(f"CBL API error: {str(e)}")
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
                authors=book.get('authors', ['Unknown']),
                publisher=book.get('publisher', 'Unknown'),
                published_date=book.get('published_date', 'Unknown'),
                isbn_13=isbn if len(isbn) == 13 else None,
                isbn_10=isbn if len(isbn) == 10 else None,
                confidence_score=0.9,  # Alta confiança para Mercado Editorial
                source='mercado_editorial'
            )
        except Exception as e:
            logging.error(f"Mercado Editorial API error: {str(e)}")
            return None

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
                confidence_score=0.85,
                source='google_books'
            )
        except Exception as e:
            logging.error(f"Google Books API error: {str(e)}")
            raise

    def fetch_google_books_br(self, isbn: str) -> Optional[BookMetadata]:
        """Busca na API do Google Books com filtro para Brasil."""
        try:
            url = "https://www.googleapis.com/books/v1/volumes"
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
                confidence_score=0.85,
                source='google_books_br'
            )
        except Exception as e:
            logging.error(f"Google Books BR API error: {str(e)}")
            raise

    def fetch_openlibrary(self, isbn: str) -> Optional[BookMetadata]:
        """Busca na Open Library API."""
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
            raise

    def fetch_worldcat(self, isbn: str) -> Optional[BookMetadata]:
        """Busca no WorldCat."""
        try:
            base_url = "https://www.worldcat.org/isbn/" + isbn
            response = self.session.get(base_url, timeout=5)
            
            if response.status_code == 200:
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

    def fetch_zbib(self, isbn: str) -> Optional[BookMetadata]:
        try:
            url = f"https://api.zbib.org/v1/search?q=isbn:{isbn}"
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if not data or not data.get('items'):
                    return None
                    
                item = data['items'][0]
                return BookMetadata(
                    title=item.get('title', 'Unknown'),
                    authors=item.get('authors', []),
                    publisher=item.get('publisher', 'Unknown'),
                    published_date=str(item.get('year', 'Unknown')),
                    isbn_13=isbn if len(isbn) == 13 else None,
                    isbn_10=isbn if len(isbn) == 10 else None,
                    confidence_score=0.7,
                    source='zbib'
                )
        except Exception as e:
            logging.error(f"Zbib error: {e}")
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

    def fetch_springer(self, isbn: str) -> Optional[BookMetadata]:
        """Busca na Springer Nature API."""
        try:
            url = f"https://api.springernature.com/metadata/books/isbn/{isbn}"
            response = self.api.get(url)
            
            if response.status_code == 200:
                data = response.json()
                return BookMetadata(
                    title=data.get('title', 'Unknown'),
                    authors=data.get('creators', []),
                    publisher="Springer",
                    published_date=data.get('publicationDate', 'Unknown'),
                    isbn_13=isbn if len(isbn) == 13 else None,
                    isbn_10=isbn if len(isbn) == 10 else None,
                    confidence_score=0.9,
                    source='springer'
                )
        except Exception as e:
            logging.error(f"Springer API error: {str(e)}")
            return None

    def fetch_oreilly(self, isbn: str) -> Optional[BookMetadata]:
        """Busca na O'Reilly Atlas API."""
        try:
            url = f"https://learning.oreilly.com/api/v2/book/isbn/{isbn}/"
            response = self.api.get(url)
            
            if response.status_code == 200:
                data = response.json()
                return BookMetadata(
                    title=data.get('title', 'Unknown'),
                    authors=data.get('authors', []),
                    publisher="O'Reilly Media",
                    published_date=data.get('issued', 'Unknown'),
                    isbn_13=isbn if len(isbn) == 13 else None,
                    isbn_10=isbn if len(isbn) == 10 else None,
                    confidence_score=0.95,
                    source='oreilly'
                )
        except Exception as e:
            logging.error(f"O'Reilly API error: {str(e)}")
            return None

    def fetch_crossref(self, isbn: str) -> Optional[BookMetadata]:
        """Busca na CrossRef API."""
        try:
            url = "https://api.crossref.org/works"
            params = {
                'query.bibliographic': isbn,
                'filter': 'type:book',
                'select': 'title,author,published-print,publisher'
            }
            response = self.api.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if data['message']['items']:
                    item = data['message']['items'][0]
                    return BookMetadata(
                        title=item.get('title', ['Unknown'])[0],
                        authors=[a.get('given', '') + ' ' + a.get('family', '') 
                                for a in item.get('author', [])],
                        publisher=item.get('publisher', 'Unknown'),
                        published_date=str(item.get('published-print', {}).get('date-parts', [[0]])[0][0]),
                        isbn_13=isbn if len(isbn) == 13 else None,
                        isbn_10=isbn if len(isbn) == 10 else None,
                        confidence_score=0.85,
                        source='crossref'
                    )
        except Exception as e:
            logging.error(f"CrossRef API error: {str(e)}")
            return None

    def fetch_internet_archive(self, isbn: str) -> Optional[BookMetadata]:
        """Busca no Internet Archive Books API."""
        try:
            url = f"https://archive.org/advancedsearch.php"
            params = {
                'q': f'isbn:{isbn}',
                'output': 'json',
                'rows': 1,
                'fl[]': ['title', 'creator', 'publisher', 'date']
            }
            response = self.api.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if data['response']['docs']:
                    doc = data['response']['docs'][0]
                    return BookMetadata(
                        title=doc.get('title', 'Unknown'),
                        authors=[doc.get('creator', 'Unknown')],
                        publisher=doc.get('publisher', 'Unknown'),
                        published_date=doc.get('date', 'Unknown'),
                        isbn_13=isbn if len(isbn) == 13 else None,
                        isbn_10=isbn if len(isbn) == 10 else None,
                        confidence_score=0.8,
                        source='internet_archive'
                    )
        except Exception as e:
            logging.error(f"Internet Archive API error: {str(e)}")
            return None


    def fetch_ebook_de(self, isbn: str) -> Optional[BookMetadata]:
        """Busca metadados na ebook.de."""
        try:
            url = f"https://www.ebook.de/de/tools/isbn2bibtex/{isbn}"
            response = self.session.get(url, timeout=(2, 5))
            
            if response.status_code != 200:
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

    def _create_fallback_metadata(self, isbn: str, error: Optional[Exception] = None) -> Optional[BookMetadata]:
        """Cria metadados básicos de fallback para quando todas as APIs falham."""
        try:
            # Para ISBNs brasileiros, tenta extrair informações do próprio ISBN
            publisher_prefix = isbn[3:7] if len(isbn) == 13 else None
            
            publisher_map = {
                '6586': 'Casa do Código',
                '8575': 'Novatec',
                '8550': 'Alta Books',
                '8536': 'Érica',
                '8521': 'Atlas',
                '8535': 'Campus',
                '8539': 'Saraiva'
            }
            
            publisher = publisher_map.get(publisher_prefix, 'Unknown')
            
            basic_metadata = BookMetadata(
                title=f"ISBN {isbn}",
                authors=["Unknown"],
                publisher=publisher,
                published_date="Unknown",
                isbn_13=isbn if len(isbn) == 13 else None,
                isbn_10=isbn if len(isbn) == 10 else None,
                confidence_score=0.3,  # Baixa confiança
                source="fallback"
            )
            
            return basic_metadata
        except Exception as e:
            logging.error(f"Fallback creation failed: {str(e)}")
            return None

    def _handle_api_error(self, api_name: str, error: Exception, isbn: str) -> None:
        """Trata erros de API de forma consistente."""
        if api_name == 'cbl':
            if 'Connection Error' in str(error):  # 88.9% dos erros
                logging.warning(f"CBL API connection error for ISBN {isbn}")
                return
        elif api_name == 'zbib':
            if 'Connection Error' in str(error):  # 88.9% dos erros
                logging.warning(f"ZBib connection error for ISBN {isbn}")
                return
        elif api_name == 'springer':
            if 'Server Error' in str(error):  # 10% dos erros
                logging.warning(f"Springer server error for ISBN {isbn}")
                return
        error_msg = f"{api_name} API error for ISBN {isbn}: {str(error)}"
        # Log genérico para outros erros
        logging.error(f"{api_name} API error for ISBN {isbn}: {str(error)}")
        
        if isinstance(error, requests.exceptions.Timeout):
            logging.warning(f"Timeout accessing {api_name}")
        elif isinstance(error, requests.exceptions.RequestException):
            if "Max retries exceeded" in str(error):
                logging.error(f"Connection problems with {api_name}")
            elif "timeout" in str(error).lower():
                logging.error(f"Timeout while accessing {api_name}")
            else:
                logging.error(f"Network error with {api_name}: {str(error)}")
        else:
            logging.error(error_msg)

    def _clean_metadata(self, metadata: BookMetadata) -> BookMetadata:
        """Limpa e normaliza os metadados."""
        if not metadata:
            return metadata
            
        if metadata.title:
            metadata.title = re.sub(r'\s+', ' ', metadata.title).strip()
            
        if metadata.authors:
            cleaned_authors = []
            for author in metadata.authors:
                if author and author.lower() != 'unknown':
                    author = re.sub(r'\s+', ' ', author).strip()
                    cleaned_authors.append(author)
            metadata.authors = cleaned_authors if cleaned_authors else ['Unknown']
            
        if metadata.publisher:
            metadata.publisher = re.sub(r'\s+', ' ', metadata.publisher).strip()
            
        if metadata.published_date:
            year_match = re.search(r'\b\d{4}\b', metadata.published_date)
            if year_match:
                metadata.published_date = year_match.group(0)
                
        return metadata

    def update_cache(self, isbn: str, force: bool = False) -> None:
        """Atualiza o cache para um ISBN específico."""
        if force or not self.cache.get(isbn):
            metadata = self.fetch_metadata(isbn)
            if metadata:
                self.cache.set(asdict(metadata))

    def rescan_cache(self) -> None:
        """Verifica todos os registros no cache e atualiza aqueles com pontuação de confiança inferior."""
        all_metadata = self.cache.get_all()
        for metadata in all_metadata:
            # Consulta os metadados usando o ISBN
            new_metadata = self.fetch_metadata(metadata['isbn_10'] or metadata['isbn_13'])
            
            # Atualiza o registro apenas se a nova pontuação de confiança for maior
            if new_metadata and new_metadata.confidence_score > metadata['confidence_score']:
                self.cache.update(asdict(new_metadata))
            
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

        # Se não conseguiu texto suficiente, tenta pdfplumber
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

        # Se ainda não tem texto suficiente, tenta pdfminer
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

        # Limpa o texto
        text = self._clean_text(text)
        
        # Verifica se é um manual
        if self._is_manual_or_documentation(text):
            logging.info(f"Arquivo identificado como manual/documentação: {pdf_path}")
            return "", methods_tried
            
        logging.info(f"Métodos tentados: {', '.join(methods_tried)}")
        logging.info(f"Métodos bem-sucedidos: {', '.join(methods_succeeded)}")
        
        return text, methods_tried

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
            
        # Verifica padrões de corrupção específicos observados
        corruption_patterns = [
            r'[0-9](?=[A-Za-z])|[A-Za-z](?=[0-9])',  # Números misturados com letras
            r'[A-Z]{2,}[a-z]{1,2}[A-Z]{2,}',         # Padrões estranhos de maiúsculas/minúsculas
            r'\d+[A-Za-z]+\d+',                       # Números intercalados com letras
            r'[A-Z]{5,}',                             # Sequências muito longas de maiúsculas
            r'[^a-zA-Z0-9\s,.!?()-]{3,}'             # Sequências de caracteres especiais
        ]
        
        for pattern in corruption_patterns:
            if len(re.findall(pattern, text)) > len(text.split()) / 10:  # mais de 10% das palavras
                return True
                
        # Verifica proporção de números no texto (exceto possíveis ISBNs)
        text_without_isbns = re.sub(r'(?:97[89][-\s]*(?:\d[-\s]*){9}\d|(?:\d[-\s]*){9}[\dXx])', '', text)
        numbers = sum(1 for c in text_without_isbns if c.isdigit())
        if len(text_without_isbns) > 0 and numbers / len(text_without_isbns) > 0.15:  # mais de 15% são números
            return True
                
        return False

    def _clean_text(self, text: str) -> str:
        """Limpa e normaliza o texto extraído com melhor tratamento de caracteres."""
        if not text:
            return ""

        # Mapeamento expandido de caracteres para limpeza
        char_replacements = {
            # Caracteres de controle e espaços especiais
            '\x0c': ' ',  # Form feed
            '\xa0': ' ',  # Non-breaking space
            '\u200b': '',  # Zero-width space
            '\t': ' ',    # Tab
            '\v': ' ',    # Vertical tab
            '\f': ' ',    # Form feed
            '\r': ' ',    # Carriage return
            
            # Caracteres tipográficos comuns em PDFs
            ''': "'",
            ''': "'",
            '"': '"',
            '"': '"',
            '…': '...',
            '–': '-',
            '—': '-',
            '­': '',      # Soft hyphen
            
            # Caracteres acentuados comumente mal interpretados
            'à': 'a',
            'á': 'a',
            'ã': 'a',
            'â': 'a',
            'é': 'e',
            'ê': 'e',
            'í': 'i',
            'ó': 'o',
            'ô': 'o',
            'õ': 'o',
            'ú': 'u',
            'ü': 'u',
            'ç': 'c'
        }

        # Correções específicas para OCR em ISBNs
        isbn_ocr_replacements = {
            'l': '1', 'I': '1', 'O': '0', 'o': '0',
            'S': '5', 'Z': '2', 'B': '8', 'G': '6',
            '+': '7', '@': '9', '>': '7', '?': '8',
            'd': 'fi', '00': '11', '#': '8',
            'Q': '0', 'D': '0', 'U': '0',
            'i': '1', 'L': '1',
            'z': '2',
            'E': '3',
            'h': '4',
            's': '5',
            'b': '6', 'G': '6',
            'T': '7',
            'B': '8',
            'g': '9', 'q': '9'
        }

        # Primeira passada: limpeza básica
        text = ''.join(char_replacements.get(c, c) for c in text)
        
        # Remove caracteres de controle mantendo apenas printáveis e espaços
        text = ''.join(c if c.isprintable() or c.isspace() else ' ' for c in text)
        
        # Normaliza espaços
        text = ' '.join(text.split())

        # Função para substituir caracteres em números (especialmente ISBNs)
        def replace_in_numbers(match):
            number = match.group()
            # Aplica substituições apenas em sequências que parecem ISBNs
            if len(number) >= 10:
                for old, new in isbn_ocr_replacements.items():
                    number = number.replace(old, new)
            return number

        # Padrões expandidos para identificar potenciais ISBNs
        isbn_patterns = [
            r'(?:ISBN[-: ]?)?[0-9A-Za-z-]{10,13}',
            r'(?:ISBN)?[-: ]?(?:[0-9A-Za-z-]{9}[0-9X])',
            r'(?:ISBN)?[-: ]?(?:97[89][- ]?[0-9A-Za-z-]{10})'
        ]
        
        # Aplica correções específicas para ISBNs
        for pattern in isbn_patterns:
            text = re.sub(pattern, replace_in_numbers, text, flags=re.IGNORECASE)

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