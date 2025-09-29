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
from collections import Counter, defaultdict
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
import pdfplumber
from pdfminer.high_level import extract_text as pdfminer_extract
import pytesseract
from pdf2image import convert_from_path

import plotly.graph_objects as go
from datetime import datetime
from pathlib import Path
import json
from typing import Dict, List, Optional
from collections import Counter, defaultdict


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

    def rescan_and_update(self):
        """
        Verifica todos os registros no cache e atualiza aqueles com pontuação de confiança inferior.
        """
        with sqlite3.connect(self.db_path) as conn:
            # Obtém todos os registros atuais
            results = conn.execute("""
                SELECT isbn_10, isbn_13, confidence_score
                FROM metadata_cache
            """).fetchall()
            
            updated_count = 0
            for isbn_10, isbn_13, current_score in results:
                isbn = isbn_13 or isbn_10  # Usa ISBN-13 preferencialmente
                try:
                    # Tenta obter novos metadados
                    metadata = self.metadata_fetcher.fetch_metadata(isbn)
                    
                    if metadata and metadata.confidence_score > current_score:
                        # Atualiza o registro se encontrou dados melhores
                        conn.execute("""
                            UPDATE metadata_cache
                            SET title = ?, authors = ?, publisher = ?, 
                                published_date = ?, confidence_score = ?,
                                source = ?, raw_json = ?, timestamp = ?
                            WHERE isbn_10 = ? OR isbn_13 = ?
                        """, (
                            metadata.title,
                            ', '.join(metadata.authors),
                            metadata.publisher,
                            metadata.published_date,
                            metadata.confidence_score,
                            metadata.source,
                            json.dumps(asdict(metadata)),
                            int(time.time()),
                            isbn_10,
                            isbn_13
                        ))
                        updated_count += 1
                except Exception as e:
                    logging.error(f"Erro ao atualizar metadados para ISBN {isbn}: {str(e)}")
                    continue
            
            logging.info(f"Rescan concluído. {updated_count} registros atualizados.")
            return updated_count

    def update(self, metadata: Dict):
            """
            Atualiza um registro existente no cache.
            """
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE metadata_cache
                    SET title = ?, authors = ?, publisher = ?, 
                        published_date = ?, confidence_score = ?,
                        source = ?, raw_json = ?, timestamp = ?
                    WHERE isbn_10 = ? OR isbn_13 = ?
                """, (
                    metadata.get('title'),
                    ', '.join(metadata.get('authors', [])),
                    metadata.get('publisher'),
                    metadata.get('published_date'),
                    metadata.get('confidence_score', 0.0),
                    metadata.get('source'),
                    json.dumps(metadata),
                    int(time.time()),
                    metadata.get('isbn_10'),
                    metadata.get('isbn_13')
                ))

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
        
        # Contadores persistentes para estatísticas
        self.api_success = Counter()
        self.api_total = Counter()
        self.api_times = defaultdict(list)
        
        # Configuração de timeouts e retries
        self.session.timeout = (5, 15)
        
        retry_strategy = Retry(
            total=5,  
            backoff_factor=0.5,
            status_forcelist=[404, 429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"],
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
        
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json,text/html,application/xhtml+xml',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive'
        })

    def print_current_stats(self):
        """Imprime estatísticas atuais das APIs."""
        print("\nEstatísticas em tempo real:")
        print("-" * 40)
        for api, total in sorted(self.api_total.items()):
            if total > 0:
                success = self.api_success[api]
                success_rate = (success / total * 100)
                avg_time = sum(self.api_times[api]) / len(self.api_times[api]) if self.api_times[api] else 0
                print(f"{api:15}: {success}/{total} ({success_rate:.1f}%) - {avg_time:.2f}s")
        print("-" * 40)

    def reset_stats(self):
        """Reseta os contadores de estatísticas."""
        self.api_success.clear()
        self.api_total.clear()
        self.api_times.clear()


    def fetch_metadata(self, isbn: str) -> Optional[BookMetadata]:
        """Método principal para buscar metadados."""
        # Verifica cache primeiro
        cached = self.cache.get(isbn)
        if cached:
            return BookMetadata(**cached)

        # Lista de fetchers 
        fetchers = [
            # Tier 1: APIs mais rápidas e confiáveis
            (self.fetch_openlibrary, 9.9),     # 100% sucesso, 2.20s
            (self.fetch_loc, 9.8),             # Rápido (0.49s) mas precisa fix XML
            
            # Tier 2: ISBNlib com boa performance
            (self.fetch_isbnlib_info, 9.5),    # 54.5% sucesso, 3.16s
            (self.fetch_isbnlib_mask, 9.4),    # 54.5% sucesso, 3.95s
            
            # Tier 3: APIs com performance média
            (self.fetch_google_books, 8.5),     # Rápido (0.60s) mas baixo sucesso
            (self.fetch_internet_archive, 8.0), # 1.13s
            
            # Tier 4: Fallbacks lentos
            (self.fetch_isbnlib_editions, 7.0), # Muito lento (6.85s)
            (self.fetch_isbnlib_default, 6.5),  # Lento (4.01s)
        ]
        # No método fetch_metadata da classe MetadataFetcher
        confidence_adjustments = {
            # ISBNlib - Tier 1 (rápidos e 100% confiáveis)
            'isbnlib_mask': 0.99,      # 100% sucesso, 0.000s
            'isbnlib_info': 0.98,      # 100% sucesso, 0.000s
            'isbnlib_isbn10': 0.97,    # 100% sucesso, 0.000s
            'isbnlib_isbn13': 0.97,    # 100% sucesso, 0.000s
            
            # ISBNlib - Tier 2 (confiáveis mas mais lentos)
            'isbnlib_desc': 0.95,      # 100% sucesso, 0.712s
            'isbnlib_goom': 0.90,      # 90% sucesso, 0.847s
            
            # ISBNlib - Tier 3 (mais lentos)
            'isbnlib_editions': 0.85,  # 100% sucesso, 4.045s
            'isbnlib_default': 0.60,   # 60% sucesso, 1.432s
            
            # APIs Externas - Performance Real
            'openlibrary': 0.60,       # 60% sucesso, 4.620s
            'loc': 0.556,             # 55.6% sucesso, 1.804s
            'google_books': 0.50,      # 50% sucesso, 0.541s
            'internet_archive': 0.33,  # 33.3% sucesso, 0.668s
            'google_books_br': 0.11,   # 11.1% sucesso, 0.417s
            
            # APIs com dados insuficientes mantém baixa confiança até termos métricas
            'worldcat': 0.30,         # Necessita validação melhor
            'mercado_editorial': 0.20, # Necessita validação
            'springer': 0.20,         # Necessita validação
            'oreilly': 0.20,          # Necessita validação
            'zbib': 0.20,             # Necessita validação
            'mybib': 0.20,            # Necessita validação
            'ebook_de': 0.20          # Necessita validação
        }

        all_results = []
        processed = set()
        last_error = None
        
        retry_configs = {
            'high_priority': {
                'max_retries': 3,    
                'backoff_factor': 1.5,
                'retry_delay': 2
            },
            'medium_priority': {
                'max_retries': 2,    
                'backoff_factor': 1,
                'retry_delay': 1
            },
            'low_priority': {
                'max_retries': 1,    
                'backoff_factor': 0.5,
                'retry_delay': 0.5
            }
        }

        for fetcher, priority in fetchers:
            if fetcher.__name__ not in processed:
                # Determina a configuração de retry baseada na prioridade
                start_time = time.time()
                self.api_total[fetcher.__name__] += 1

                if priority >= 8:
                    retry_config = retry_configs['high_priority']
                elif priority >= 6:
                    retry_config = retry_configs['medium_priority']
                else:
                    retry_config = retry_configs['low_priority']

                for attempt in range(retry_config['max_retries']):
                    try:
                        metadata = fetcher(isbn)
                        elapsed = time.time() - start_time
                        self.api_times[fetcher.__name__].append(elapsed)
                        
                        if metadata:
                            # Ajusta score baseado no desempenho real da API
                            self.api_success[fetcher.__name__] += 1
                            base_score = priority / 10
                            adjustment = confidence_adjustments.get(metadata.source, 0.5)
                            metadata.confidence_score = min(1.0, base_score * adjustment)
                            
                            # Adiciona ISBN-10/13 se não existir
                            if len(isbn) == 10 and not metadata.isbn_10:
                                metadata.isbn_10 = isbn
                            elif len(isbn) == 13 and not metadata.isbn_13:
                                metadata.isbn_13 = isbn
                                
                            all_results.append(metadata)
                            
                            if metadata.confidence_score > 0.85:
                                break
                    except Exception as e:
                        elapsed = time.time() - start_time
                        self.api_times[fetcher.__name__].append(elapsed)
                        last_error = e
                        self._handle_api_error(fetcher.__name__, e, isbn)
                        
                        if attempt < retry_config['max_retries'] - 1:
                            sleep_time = retry_config['retry_delay'] * (retry_config['backoff_factor'] ** attempt)
                            time.sleep(sleep_time)
                            
                processed.add(fetcher.__name__)

                # Imprime estatísticas a cada 5 APIs processadas
                if len(processed) % 5 == 0:
                    self.print_current_stats()

                # Se já tem resultados suficientes com boa confiança, pode parar
                if len(all_results) >= 2 and any(r.confidence_score > 0.80 for r in all_results):
                    break

        # Escolhe o melhor resultado baseado na pontuação de confiança
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

    def fetch_isbnlib_mask(self, isbn: str) -> Optional[BookMetadata]:
        """Busca usando isbnlib.mask() - formatação canônica do ISBN."""
        try:
            import isbnlib
            if not isbnlib.is_isbn13(isbn) and not isbnlib.is_isbn10(isbn):
                return None
                
            # Formata o ISBN no formato canônico
            masked_isbn = isbnlib.mask(isbn)
            if not masked_isbn:
                return None
                
            # Busca metadados usando o ISBN formatado
            metadata = isbnlib.meta(masked_isbn)
            if not metadata:
                return None
                
            return BookMetadata(
                title=metadata.get('Title', '').strip(),
                authors=[a.strip() for a in metadata.get('Authors', [])],
                publisher=metadata.get('Publisher', '').strip(),
                published_date=metadata.get('Year', 'Unknown'),
                isbn_13=isbn if len(isbn) == 13 else None,
                isbn_10=isbn if len(isbn) == 10 else None,
                confidence_score=0.99,  # 100% success rate
                source='isbnlib_mask'
            )
        except Exception as e:
            logging.error(f"ISBNlib mask error for ISBN {isbn}: {str(e)}")
            return None

    def fetch_loc(self, isbn: str) -> Optional[BookMetadata]:
        """Busca na API da Library of Congress."""
        try:
            # URL da API da LoC
            url = f"https://lccn.loc.gov/{isbn}/marc21.xml"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                # Parse do XML
                root = ET.fromstring(response.content)
                
                # Busca os campos MARC relevantes
                title = None
                authors = []
                publisher = None
                published_date = None
                
                # Procura no XML os campos MARC21
                for field in root.findall(".//marc:datafield", {'marc': 'http://www.loc.gov/MARC21/slim'}):
                    tag = field.get('tag')
                    
                    if tag == '245':  # Título
                        title = ' '.join(subfield.text for subfield in field.findall(".//marc:subfield[@code='a']", {'marc': 'http://www.loc.gov/MARC21/slim'}))
                        
                    elif tag == '100':  # Autor principal
                        author = ' '.join(subfield.text for subfield in field.findall(".//marc:subfield[@code='a']", {'marc': 'http://www.loc.gov/MARC21/slim'}))
                        if author:
                            authors.append(author)
                            
                    elif tag == '700':  # Autores adicionais
                        author = ' '.join(subfield.text for subfield in field.findall(".//marc:subfield[@code='a']", {'marc': 'http://www.loc.gov/MARC21/slim'}))
                        if author:
                            authors.append(author)
                            
                    elif tag == '260' or tag == '264':  # Publicação
                        publisher = ' '.join(subfield.text for subfield in field.findall(".//marc:subfield[@code='b']", {'marc': 'http://www.loc.gov/MARC21/slim'}))
                        published_date = ' '.join(subfield.text for subfield in field.findall(".//marc:subfield[@code='c']", {'marc': 'http://www.loc.gov/MARC21/slim'}))
                
                # Validação mais rigorosa dos dados
                if not title or not authors or not publisher:
                    logging.warning(f"LoC: Dados incompletos para ISBN {isbn}")
                    return None
                    
                # Remove pontuação extra e limpa os dados
                if title:
                    title = title.strip(' /.,')
                if publisher:
                    publisher = publisher.strip(' /.,')
                if published_date:
                    published_date = re.sub(r'[^\d]', '', published_date)
                    
                return BookMetadata(
                    title=title,
                    authors=[a.strip(' /.,') for a in authors],
                    publisher=publisher,
                    published_date=published_date or 'Unknown',
                    isbn_13=isbn if len(isbn) == 13 else None,
                    isbn_10=isbn if len(isbn) == 10 else None,
                    confidence_score=0.556,  # 55.6% success rate
                    source='loc'
                )
        except Exception as e:
            logging.error(f"Library of Congress API error for ISBN {isbn}: {str(e)}")
            return None

    def fetch_isbnlib_info(self, isbn: str) -> Optional[BookMetadata]:
        """Busca usando isbnlib.info() - informações básicas do ISBN."""
        try:
            import isbnlib
            if not isbnlib.is_isbn13(isbn) and not isbnlib.is_isbn10(isbn):
                return None
                
            # Obtém informações básicas do ISBN
            info = isbnlib.info(isbn)
            if not info:
                return None
                
            # Usa o info para buscar metadados completos
            metadata = isbnlib.meta(isbn)
            if not metadata:
                return None
                
            return BookMetadata(
                title=metadata.get('Title', '').strip(),
                authors=[a.strip() for a in metadata.get('Authors', [])],
                publisher=metadata.get('Publisher', '').strip(),
                published_date=metadata.get('Year', 'Unknown'),
                isbn_13=isbn if len(isbn) == 13 else None,
                isbn_10=isbn if len(isbn) == 10 else None,
                confidence_score=0.98,  # 100% success rate
                source='isbnlib_info'
            )
        except Exception as e:
            logging.error(f"ISBNlib info error for ISBN {isbn}: {str(e)}")
            return None

    def fetch_isbnlib_desc(self, isbn: str) -> Optional[BookMetadata]:
        """Busca usando isbnlib.desc() - descrição detalhada."""
        try:
            import isbnlib
            if not isbnlib.is_isbn13(isbn) and not isbnlib.is_isbn10(isbn):
                return None
                
            # Obtém descrição detalhada
            desc = isbnlib.desc(isbn)
            if not desc:
                return None
                
            # Busca metadados completos
            metadata = isbnlib.meta(isbn)
            if not metadata:
                return None
                
            return BookMetadata(
                title=metadata.get('Title', '').strip(),
                authors=[a.strip() for a in metadata.get('Authors', [])],
                publisher=metadata.get('Publisher', '').strip(),
                published_date=metadata.get('Year', 'Unknown'),
                isbn_13=isbn if len(isbn) == 13 else None,
                isbn_10=isbn if len(isbn) == 10 else None,
                confidence_score=0.95,  # 100% success rate, but slower
                source='isbnlib_desc'
            )
        except Exception as e:
            logging.error(f"ISBNlib desc error for ISBN {isbn}: {str(e)}")
            return None

    def fetch_isbnlib_editions(self, isbn: str) -> Optional[BookMetadata]:
        """Busca usando isbnlib.editions() - todas as edições do livro."""
        try:
            import isbnlib
            if not isbnlib.is_isbn13(isbn) and not isbnlib.is_isbn10(isbn):
                return None
                
            # Obtém todas as edições
            editions = isbnlib.editions(isbn)
            if not editions:
                return None
                
            # Usa o ISBN original para buscar metadados
            metadata = isbnlib.meta(isbn)
            if not metadata:
                return None
                
            return BookMetadata(
                title=metadata.get('Title', '').strip(),
                authors=[a.strip() for a in metadata.get('Authors', [])],
                publisher=metadata.get('Publisher', '').strip(),
                published_date=metadata.get('Year', 'Unknown'),
                isbn_13=isbn if len(isbn) == 13 else None,
                isbn_10=isbn if len(isbn) == 10 else None,
                confidence_score=0.85,  # 100% success rate, but slowest
                source='isbnlib_editions'
            )
        except Exception as e:
            logging.error(f"ISBNlib editions error for ISBN {isbn}: {str(e)}")
            return None

    def fetch_isbnlib_isbn10(self, isbn: str) -> Optional[BookMetadata]:
        """Busca usando isbnlib para ISBN-10."""
        try:
            import isbnlib
            if not isbnlib.is_isbn13(isbn) and not isbnlib.is_isbn10(isbn):
                return None
                
            # Converte para ISBN-10 se necessário
            isbn10 = isbnlib.to_isbn10(isbn) if len(isbn) == 13 else isbn
            if not isbn10:
                return None
                
            # Busca metadados usando ISBN-10
            metadata = isbnlib.meta(isbn10)
            if not metadata:
                return None
                
            return BookMetadata(
                title=metadata.get('Title', '').strip(),
                authors=[a.strip() for a in metadata.get('Authors', [])],
                publisher=metadata.get('Publisher', '').strip(),
                published_date=metadata.get('Year', 'Unknown'),
                isbn_13=None,
                isbn_10=isbn10,
                confidence_score=0.97,  # 100% success rate
                source='isbnlib_isbn10'
            )
        except Exception as e:
            logging.error(f"ISBNlib ISBN-10 error for ISBN {isbn}: {str(e)}")
            return None

    def fetch_isbnlib_isbn13(self, isbn: str) -> Optional[BookMetadata]:
        """Busca usando isbnlib para ISBN-13."""
        try:
            import isbnlib
            if not isbnlib.is_isbn13(isbn) and not isbnlib.is_isbn10(isbn):
                return None
                
            # Converte para ISBN-13 se necessário
            isbn13 = isbnlib.to_isbn13(isbn) if len(isbn) == 10 else isbn
            if not isbn13:
                return None
                
            # Busca metadados usando ISBN-13
            metadata = isbnlib.meta(isbn13)
            if not metadata:
                return None
                
            return BookMetadata(
                title=metadata.get('Title', '').strip(),
                authors=[a.strip() for a in metadata.get('Authors', [])],
                publisher=metadata.get('Publisher', '').strip(),
                published_date=metadata.get('Year', 'Unknown'),
                isbn_13=isbn13,
                isbn_10=None,
                confidence_score=0.97,  # 100% success rate
                source='isbnlib_isbn13'
            )
        except Exception as e:
            logging.error(f"ISBNlib ISBN-13 error for ISBN {isbn}: {str(e)}")
            return None


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

    def fetch_isbnlib_default(self, isbn: str) -> Optional[BookMetadata]:
        """Busca usando o serviço padrão do isbnlib."""
        try:
            import isbnlib
            if not isbnlib.is_isbn13(isbn) and not isbnlib.is_isbn10(isbn):
                return None
                
            # Usa o serviço padrão do isbnlib
            metadata = isbnlib.meta(isbn, service='default')
            if not metadata:
                return None
                
            return BookMetadata(
                title=metadata.get('Title', '').strip(),
                authors=[a.strip() for a in metadata.get('Authors', [])],
                publisher=metadata.get('Publisher', '').strip(),
                published_date=metadata.get('Year', 'Unknown'),
                isbn_13=isbn if len(isbn) == 13 else None,
                isbn_10=isbn if len(isbn) == 10 else None,
                confidence_score=0.80,  # 60% success rate
                source='isbnlib_default'
            )
        except Exception as e:
            logging.error(f"ISBNlib default error for ISBN {isbn}: {str(e)}")
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
        """Busca na API do Google Books com validação melhorada."""
        try:
            url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
            response = self.session.get(url, timeout=10)
            data = response.json()
            
            if 'items' not in data:
                return None
                
            book_info = data['items'][0]['volumeInfo']
            
            # Validação mais rigorosa
            if (not book_info.get('title') or 
                not book_info.get('authors') or 
                not book_info.get('publisher')):
                logging.warning(f"Google Books: Dados incompletos para ISBN {isbn}")
                return None
                
            # Se publisher for Unknown, tenta próxima API
            if book_info.get('publisher', 'Unknown') == 'Unknown':
                logging.warning(f"Google Books: Publisher desconhecido para ISBN {isbn}")
                return None
            
            # Validação adicional dos autores
            authors = book_info.get('authors', [])
            if not authors or any(not author.strip() for author in authors):
                logging.warning(f"Google Books: Dados de autores inválidos para ISBN {isbn}")
                return None
            
            return BookMetadata(
                title=book_info.get('title', 'Unknown'),
                authors=authors,
                publisher=book_info.get('publisher', 'Unknown'),
                published_date=book_info.get('publishedDate', 'Unknown'),
                isbn_13=isbn if len(isbn) == 13 else None,
                isbn_10=isbn if len(isbn) == 10 else None,
                confidence_score=0.85,
                source='google_books'
            )
        except Exception as e:
            logging.error(f"Google Books API error for ISBN {isbn}: {str(e)}")
            return None

    def fetch_isbnlib_meta(self, isbn: str) -> Optional[BookMetadata]:
        """Busca metadados usando isbnlib.meta()"""
        try:
            import isbnlib
            metadata = isbnlib.meta(isbn)
            if metadata:
                return BookMetadata(
                    title=metadata.get('Title', 'Unknown'),
                    authors=metadata.get('Authors', ['Unknown']),
                    publisher=metadata.get('Publisher', 'Unknown'),
                    published_date=metadata.get('Year', 'Unknown'),
                    isbn_13=isbn if len(isbn) == 13 else None,
                    isbn_10=isbn if len(isbn) == 10 else None,
                    confidence_score=0.95,
                    source='isbnlib_meta'
                )
        except Exception as e:
            logging.error(f"ISBNlib meta error: {str(e)}")
            return None

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

    def fetch_isbnlib_goom(self, isbn: str) -> Optional[BookMetadata]:
        """Busca metadados usando isbnlib.goom() - otimizado para Google Books."""
        try:
            import isbnlib
            if not isbnlib.is_isbn13(isbn) and not isbnlib.is_isbn10(isbn):
                logging.warning(f"ISBNlib: ISBN inválido {isbn}")
                return None
                
            metadata = isbnlib.goom(isbn)
            if not metadata:
                return None
                
            # Validação mais rigorosa dos dados
            if (not metadata.get('Title') or 
                not metadata.get('Authors') or 
                not metadata.get('Publisher')):
                logging.warning(f"ISBNlib goom: Dados incompletos para ISBN {isbn}")
                return None
                
            # Validação de dados inválidos/unknown
            if any(v.strip() == 'Unknown' for v in [
                metadata.get('Title', ''),
                metadata.get('Publisher', ''),
                *metadata.get('Authors', [])
            ]):
                logging.warning(f"ISBNlib goom: Dados inválidos para ISBN {isbn}")
                return None
            
            return BookMetadata(
                title=metadata['Title'].strip(),
                authors=[author.strip() for author in metadata['Authors']],
                publisher=metadata['Publisher'].strip(),
                published_date=metadata.get('Year', 'Unknown'),
                isbn_13=isbn if len(isbn) == 13 else None,
                isbn_10=isbn if len(isbn) == 10 else None,
                confidence_score=0.90,  # Alta confiança devido à validação rigorosa
                source='isbnlib_goom'
            )
        except Exception as e:
            logging.error(f"ISBNlib goom error for ISBN {isbn}: {str(e)}")
            return None

    def fetch_worldcat(self, isbn: str) -> Optional[BookMetadata]:
        """Busca no WorldCat com validação melhorada."""
        try:
            base_url = "https://www.worldcat.org/isbn/" + isbn
            response = self.session.get(base_url, timeout=5)
            
            if response.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                
                title = soup.find('h1', {'class': 'title'})
                authors = soup.find_all('a', {'class': 'author'})
                publisher = soup.find('td', string='Publisher')
                published_date = soup.find('td', string='Date')
                
                # Validação mais rigorosa
                if not title or not authors or not publisher:
                    logging.warning(f"WorldCat: Dados incompletos para ISBN {isbn}")
                    return None
                    
                if any(x.strip() == 'Unknown' for x in [title.text, publisher.next_sibling.text]):
                    logging.warning(f"WorldCat: Dados inválidos para ISBN {isbn}")
                    return None
                
                return BookMetadata(
                    title=title.text.strip(),
                    authors=[a.text.strip() for a in authors if a.text.strip()],
                    publisher=publisher.next_sibling.text.strip(),
                    published_date=published_date.next_sibling.text.strip() if published_date else 'Unknown',
                    isbn_13=isbn if len(isbn) == 13 else None,
                    isbn_10=isbn if len(isbn) == 10 else None,
                    confidence_score=0.75,
                    source='worldcat'
                )
        except Exception as e:
            logging.error(f"WorldCat error for ISBN {isbn}: {str(e)}")
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

    def update_low_confidence_records(self, confidence_threshold: float = 0.7) -> int:
        """
        Atualiza registros do cache que têm pontuação de confiança abaixo do limiar.
        
        Args:
            confidence_threshold: Limite de confiança para atualização (default: 0.7)
            
        Returns:
            int: Número de registros atualizados
        """
        try:
            all_records = self.cache.get_all()
            updated_count = 0
            
            for record in all_records:
                # Verifica se o registro tem baixa confiança
                if record['confidence_score'] < confidence_threshold:
                    isbn = record['isbn_13'] or record['isbn_10']
                    logging.info(f"Tentando atualizar registro de baixa confiança: {isbn}")
                    
                    try:
                        # Tenta obter novos metadados
                        new_metadata = self.fetch_metadata(isbn)
                        
                        # Atualiza apenas se encontrou dados melhores
                        if new_metadata and new_metadata.confidence_score > record['confidence_score']:
                            self.cache.update(asdict(new_metadata))
                            updated_count += 1
                            logging.info(f"Atualizado ISBN {isbn}: {record['confidence_score']} -> {new_metadata.confidence_score}")
                    except Exception as e:
                        logging.error(f"Erro ao atualizar ISBN {isbn}: {str(e)}")
                        continue
                        
            return updated_count
            
        except Exception as e:
            logging.error(f"Erro ao atualizar registros: {str(e)}")
            return 0

    def rescan_cache(self) -> int:
        """
        Reprocessa todos os registros do cache, independente da pontuação de confiança.
        
        Returns:
            int: Número de registros atualizados
        """
        try:
            all_records = self.cache.get_all()
            updated_count = 0
            
            for record in all_records:
                isbn = record['isbn_13'] or record['isbn_10']
                logging.info(f"Rescaneando registro: {isbn}")
                
                try:
                    # Tenta obter novos metadados
                    new_metadata = self.fetch_metadata(isbn)
                    
                    # Atualiza se encontrou dados novos
                    if new_metadata:
                        if new_metadata.confidence_score > record['confidence_score']:
                            self.cache.update(asdict(new_metadata))
                            updated_count += 1
                            logging.info(f"Atualizado ISBN {isbn}: {record['confidence_score']} -> {new_metadata.confidence_score}")
                        else:
                            logging.info(f"Mantido ISBN {isbn}: dados existentes são melhores")
                except Exception as e:
                    logging.error(f"Erro ao processar ISBN {isbn}: {str(e)}")
                    continue
                    
            return updated_count
            
        except Exception as e:
            logging.error(f"Erro ao rescanear cache: {str(e)}")
            return 0
            
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
        
        # Configura diretório de relatórios
        self.reports_dir = Path("reports")
        self.reports_dir.mkdir(exist_ok=True)
        
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
        
        # Gera relatórios aprimorados
        self._generate_enhanced_report(results, runtime_stats)
        
        return results

    def _generate_enhanced_report(self, results: List[BookMetadata], runtime_stats: Dict):
        """Gera relatórios HTML e JSON aprimorados."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Prepara dados para o relatório
        successful_results = [r for r in results if r is not None]
        total_files = len(runtime_stats['processed_files'])
        successful = len(successful_results)
        failed = total_files - successful

        # Estatísticas por fonte
        source_stats = Counter(r.source for r in successful_results)
        
        # Estatísticas por editora
        publisher_stats = Counter(r.publisher for r in successful_results)
        
        # Análise de tempo de processamento
        processing_times = runtime_stats['processing_times']
        avg_time = sum(processing_times) / len(processing_times) if processing_times else 0
        
        # Gera relatório HTML
        html_file = self.reports_dir / f"metadata_report_{timestamp}.html"
        self._generate_html_report(
            successful_results,
            source_stats,
            publisher_stats,
            runtime_stats,
            total_files,
            successful,
            failed,
            avg_time,
            html_file
        )
        
        # Gera relatório JSON
        json_file = self.reports_dir / f"metadata_report_{timestamp}.json"
        self._generate_json_report(
            successful_results,
            source_stats,
            publisher_stats,
            runtime_stats,
            total_files,
            successful,
            failed,
            avg_time,
            json_file
        )
        
        print(f"\nRelatórios gerados:")
        print(f"HTML: {html_file}")
        print(f"JSON: {json_file}")

    def _generate_html_report(self, results, source_stats, publisher_stats, 
                            runtime_stats, total_files, successful, failed, avg_time, output_file):
        """Gera relatório HTML com visualizações aprimoradas e análise de falhas."""
        
        # Código existente para preparar dados permanece o mesmo
        source_keys = list(map(repr, source_stats.keys()))
        source_values = list(source_stats.values())
        publisher_keys = list(map(repr, publisher_stats.keys()))
        publisher_values = list(publisher_stats.values())

        # Código existente para gerar linhas das tabelas permanece o mesmo
        api_rows = ""
        for source, count in source_stats.items():
            success_rate = (count/successful*100) if successful > 0 else 0
            api_rows += f"""
            <tr>
                <td>{source}</td>
                <td>{count}</td>
                <td>{success_rate:.1f}%</td>
            </tr>
            """

        publisher_rows = ""
        for publisher, count in publisher_stats.items():
            percentage = (count/successful*100) if successful > 0 else 0
            publisher_rows += f"""
            <tr>
                <td>{publisher}</td>
                <td>{count}</td>
                <td>{percentage:.1f}%</td>
            </tr>
            """

        result_rows = ""
        for r in results:
            if r is not None:
                result_rows += f"""
                <tr>
                    <td>{r.title}</td>
                    <td>{', '.join(r.authors)}</td>
                    <td>{r.publisher}</td>
                    <td>{r.isbn_13 or r.isbn_10 or 'N/A'}</td>
                    <td>{r.confidence_score:.2f}</td>
                    <td>{r.source}</td>
                </tr>
                """

        # Nova seção: Gera linhas para arquivos que falharam
        failed_rows = ""
        failed_files = set(runtime_stats['processed_files']) - {r.file_path for r in results if r is not None}
        
        for file_path in sorted(failed_files):
            details = runtime_stats['failure_details'].get(file_path, {})
            methods = ', '.join(details.get('extraction_methods', ['None']))
            isbns = ', '.join(details.get('found_isbns', ['None']))
            status = details.get('status', 'Unknown error')
            publisher = details.get('detected_publisher', 'Unknown')
            errors = '<br>'.join(runtime_stats['api_errors'].get(file_path, ['None']))
            
            failed_rows += f"""
            <tr>
                <td class="file-path">{file_path}</td>
                <td>{status}</td>
                <td>{methods}</td>
                <td>{isbns}</td>
                <td>{publisher}</td>
                <td class="error-detail">{errors}</td>
            </tr>
            """

        # Template HTML com nova seção de Failed Files
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Book Metadata Extraction Report</title>
            <style>
                body {{
                    font-family: -apple-system, system-ui, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
                    line-height: 1.5;
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                    background: #f8f9fa;
                }}
                .card {{
                    background: white;
                    border-radius: 8px;
                    padding: 20px;
                    margin-bottom: 20px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 1em 0;
                }}
                th, td {{
                    padding: 12px;
                    border: 1px solid #dee2e6;
                    text-align: left;
                }}
                th {{ background: #f8f9fa; }}
                tr:hover {{ background: #f8f9fa; }}
                .success {{ color: #28a745; }}
                .warning {{ color: #ffc107; }}
                .failure {{ color: #dc3545; }}
                .chart-container {{
                    height: 400px;
                    margin: 20px 0;
                }}
                .file-path {{
                    font-family: monospace;
                    font-size: 0.9em;
                }}
                .error-detail {{
                    color: #dc3545;
                    font-size: 0.9em;
                }}
                .todo-note {{
                    background: #fff3cd;
                    border-left: 4px solid #ffc107;
                    padding: 15px;
                    margin: 20px 0;
                    border-radius: 4px;
                }}
                .tabs {{
                    display: flex;
                    margin-bottom: 20px;
                }}
                .tab {{
                    padding: 10px 20px;
                    cursor: pointer;
                    border: none;
                    background: #f8f9fa;
                    margin-right: 5px;
                    border-radius: 4px 4px 0 0;
                }}
                .tab.active {{
                    background: white;
                    border-bottom: 2px solid #007bff;
                }}
                .tab-content {{
                    display: none;
                }}
                .tab-content.active {{
                    display: block;
                }}
            </style>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        </head>
        <body>
            <h1>Book Metadata Extraction Report</h1>
            <p>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            
            <div class="tabs">
                <button class="tab active" onclick="openTab(event, 'overview')">Overview</button>
                <button class="tab" onclick="openTab(event, 'api-stats')">API Stats</button>
                <button class="tab" onclick="openTab(event, 'publishers')">Publishers</button>
                <button class="tab" onclick="openTab(event, 'results')">Results</button>
                <button class="tab" onclick="openTab(event, 'failures')">Failed Files</button>
            </div>

            <div id="overview" class="tab-content active">
                <div class="card">
                    <h2>Overview</h2>
                    <table>
                        <tr>
                            <th>Total Files Processed</th>
                            <td>{total_files}</td>
                        </tr>
                        <tr>
                            <th>Successful Extractions</th>
                            <td class="success">{successful}</td>
                        </tr>
                        <tr>
                            <th>Failed Extractions</th>
                            <td class="failure">{failed}</td>
                        </tr>
                        <tr>
                            <th>Success Rate</th>
                            <td>{(successful/total_files*100):.1f}%</td>
                        </tr>
                        <tr>
                            <th>Average Processing Time</th>
                            <td>{avg_time:.2f}s</td>
                        </tr>
                    </table>
                    <div id="summaryChart" class="chart-container"></div>
                </div>
            </div>

            <div id="api-stats" class="tab-content">
                <div class="card">
                    <h2>API Performance</h2>
                    <div id="apiChart" class="chart-container"></div>
                    <table>
                        <tr>
                            <th>API Source</th>
                            <th>Successful Extractions</th>
                            <th>Success Rate</th>
                        </tr>
                        {api_rows}
                    </table>
                </div>
            </div>

            <div id="publishers" class="tab-content">
                <div class="card">
                    <h2>Publisher Statistics</h2>
                    <div id="publisherChart" class="chart-container"></div>
                    <table>
                        <tr>
                            <th>Publisher</th>
                            <th>Books</th>
                            <th>Percentage</th>
                        </tr>
                        {publisher_rows}
                    </table>
                </div>
            </div>

            <div id="results" class="tab-content">
                <div class="card">
                    <h2>Successful Results</h2>
                    <table>
                        <tr>
                            <th>Title</th>
                            <th>Authors</th>
                            <th>Publisher</th>
                            <th>ISBN</th>
                            <th>Confidence</th>
                            <th>Source</th>
                        </tr>
                        {result_rows}
                    </table>
                </div>
            </div>

            <div id="failures" class="tab-content">
                <div class="card">
                    <h2>Failed Files Analysis</h2>
                    <div class="todo-note">
                        <strong>TO DO:</strong> Implement aggressive detection methods for these files
                    </div>
                    <table>
                        <tr>
                            <th>File Path</th>
                            <th>Status</th>
                            <th>Extraction Methods</th>
                            <th>Found ISBNs</th>
                            <th>Publisher</th>
                            <th>Errors</th>
                        </tr>
                        {failed_rows}
                    </table>
                </div>
            </div>

            <script>
            function openTab(evt, tabName) {{
                var i, tabcontent, tablinks;
                tabcontent = document.getElementsByClassName("tab-content");
                for (i = 0; i < tabcontent.length; i++) {{
                    tabcontent[i].className = tabcontent[i].className.replace(" active", "");
                }}
                tablinks = document.getElementsByClassName("tab");
                for (i = 0; i < tablinks.length; i++) {{
                    tablinks[i].className = tablinks[i].className.replace(" active", "");
                }}
                document.getElementById(tabName).className += " active";
                evt.currentTarget.className += " active";
                
                // Reflow charts when tab is shown
                if (tabName === 'overview') {{
                    Plotly.relayout('summaryChart', {{}});
                }} else if (tabName === 'api-stats') {{
                    Plotly.relayout('apiChart', {{}});
                }} else if (tabName === 'publishers') {{
                    Plotly.relayout('publisherChart', {{}});
                }}
            }}

            // Summary Chart
            const summaryData = [{{
                values: [{successful}, {failed}],
                labels: ['Successful', 'Failed'],
                type: 'pie',
                marker: {{
                    colors: ['#28a745', '#dc3545']
                }}
            }}];
            Plotly.newPlot('summaryChart', summaryData);

            // API Performance Chart
            const apiData = [{{
                x: {source_keys},
                y: {source_values},
                type: 'bar',
                marker: {{
                    color: '#17a2b8'
                }}
            }}];
            const apiLayout = {{
                title: 'Successful Extractions by API',
                xaxis: {{ tickangle: -45 }}
            }};
            Plotly.newPlot('apiChart', apiData, apiLayout);

            // Publisher Chart
            const publisherData = [{{
                labels: {publisher_keys},
                values: {publisher_values},
                type: 'pie'
            }}];
            Plotly.newPlot('publisherChart', publisherData);
            </script>
        </body>
        </html>
        """
        
        # Salva o relatório HTML
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

    def _generate_json_report(self, results, source_stats, publisher_stats, 
                            runtime_stats, total_files, successful, failed, avg_time, output_file):
        """Gera relatório JSON detalhado."""
        report_data = {
            'summary': {
                'total_files': total_files,
                'successful': successful,
                'failed': failed,
                'success_rate': (successful/total_files*100) if total_files > 0 else 0,
                'average_processing_time': avg_time,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            'api_stats': dict(source_stats),
            'publisher_stats': dict(publisher_stats),
            'failure_details': runtime_stats['failure_details'],
            'api_errors': runtime_stats['api_errors'],
            'processing_times': {
                'average': avg_time,
                'min': min(runtime_stats['processing_times']) if runtime_stats['processing_times'] else 0,
                'max': max(runtime_stats['processing_times']) if runtime_stats['processing_times'] else 0
            },
            'results': [asdict(r) for r in results]
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

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
  
  # Atualizar cache com dados melhores:
  %(prog)s --update-cache
  
  # Reprocessar cache existente:
  %(prog)s --rescan-cache

Observações:
  - Por padrão, processa apenas o diretório especificado (sem subdiretórios)
  - Use -r para processar todos os subdiretórios
  - Use --subdirs para processar apenas subdiretórios específicos
  - A chave ISBNdb é opcional e pode ser colocada em qualquer posição do comando
  - Use --rescan-cache para reprocessar todo o cache em busca de dados melhores
  - Use --update-cache para atualizar apenas registros com baixa confiança
""")
    
    parser.add_argument('directory', 
                       nargs='?',
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
    parser.add_argument('--rescan-cache',
                       action='store_true',
                       help='Reprocessa todo o cache em busca de dados melhores')
    parser.add_argument('--update-cache',
                       action='store_true',
                       help='Atualiza registros com baixa confiança')
    parser.add_argument('--confidence-threshold',
                       type=float,
                       default=0.7,
                       help='Limite de confiança para atualização (padrão: 0.7)')
    
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
    
    try:
        # Inicializa o extrator
        extractor = BookMetadataExtractor(isbndb_api_key=args.isbndb_key)
        
        # Verifica se é para atualizar o cache
        if args.rescan_cache:
            print("\nReprocessando todo o cache...")
            updated = extractor.metadata_fetcher.rescan_cache()
            print(f"Atualizados {updated} registros no cache")
            return
            
        if args.update_cache:
            print(f"\nAtualizando registros com confiança menor que {args.confidence_threshold}...")
            updated = extractor.metadata_fetcher.update_low_confidence_records(
                confidence_threshold=args.confidence_threshold
            )
            print(f"Atualizados {updated} registros no cache")
            return
            
        # Verifica se foi fornecido um diretório
        if not args.directory:
            parser.print_help()
            print("\nERRO: É necessário fornecer um diretório ou usar --rescan-cache/--update-cache")
            sys.exit(1)
        
        # Converte subdiretórios em lista se especificados
        subdirs = args.subdirs.split(',') if args.subdirs else None
        
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