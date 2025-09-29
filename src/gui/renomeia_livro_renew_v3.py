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
import statistics
from collections import Counter, defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, asdict

# Bibliotecas de terceiros - HTTP/API
import requests
import xml.etree.ElementTree as ET
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tqdm import tqdm

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import xml.etree.ElementTree as ET

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
    """Classe para armazenar metadados de livros."""
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
        self._check_and_update_schema()  # Adicionado método para verificar e atualizar schema


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
        """Initialize database with basic schema."""
        try:
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
                        raw_json TEXT,
                        timestamp INTEGER DEFAULT (strftime('%s', 'now'))
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_isbn ON metadata_cache(isbn_10, isbn_13)")
        except sqlite3.Error as e:
            logging.error(f"Database initialization error: {str(e)}")
            raise

    def _check_and_update_schema(self):
        """Check for missing columns and add them if necessary."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get current columns
                cursor = conn.execute("PRAGMA table_info(metadata_cache)")
                columns = {row[1] for row in cursor.fetchall()}

                # Add missing columns
                if 'error_count' not in columns:
                    conn.execute("ALTER TABLE metadata_cache ADD COLUMN error_count INTEGER DEFAULT 0")
                if 'last_error' not in columns:
                    conn.execute("ALTER TABLE metadata_cache ADD COLUMN last_error TEXT")
                
                logging.info("Database schema updated successfully")
        except sqlite3.Error as e:
            logging.error(f"Schema update error: {str(e)}")
            raise

    def get(self, isbn: str) -> Optional[Dict]:
        """Get metadata from cache with improved error handling."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                result = conn.execute("""
                    SELECT isbn_10, isbn_13, title, authors, publisher, 
                           published_date, confidence_score, source, file_path, raw_json
                    FROM metadata_cache
                    WHERE (isbn_10 = ? OR isbn_13 = ?) 
                    AND timestamp > ?
                    """, 
                    (isbn, isbn, int(time.time()) - 30*24*60*60)  # 30 days cache
                ).fetchone()
                
                if result:
                    # Try to use raw JSON first
                    if result[9]:  # raw_json
                        try:
                            return json.loads(result[9])
                        except json.JSONDecodeError:
                            logging.warning(f"Invalid JSON in cache for ISBN {isbn}")
                    
                    # Fallback to structured data
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
        except sqlite3.Error as e:
            logging.error(f"Cache retrieval error for ISBN {isbn}: {str(e)}")
            return None
        return None

    def set(self, metadata: Dict):
        """Save metadata to cache with error handling."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO metadata_cache (
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
                        json.dumps(metadata)
                    )
                )
        except sqlite3.Error as e:
            logging.error(f"Cache storage error: {str(e)}")
            raise

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

    def update_error_count(self, isbn: str, error: str):
        """Track API errors for each ISBN."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE metadata_cache 
                    SET error_count = error_count + 1,
                        last_error = ?
                    WHERE isbn_10 = ? OR isbn_13 = ?
                """, (error, isbn, isbn))
        except sqlite3.Error as e:
            logging.error(f"Error updating error count for ISBN {isbn}: {str(e)}")

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

class ApiStatistics:
    """Classe para coletar e analisar estatísticas de APIs."""
    def __init__(self):
        self.total_calls = 0
        self.successful_calls = 0
        self.response_times = []
        self.errors = Counter()
        
    def add_call(self, success: bool, response_time: float):
        self.total_calls += 1
        if success:
            self.successful_calls += 1
        self.response_times.append(response_time)
        
    def add_error(self, error_type: str):
        self.errors[error_type] += 1
        
    def get_stats(self) -> Dict[str, Any]:
        if not self.total_calls:
            return {
                'success_rate': 0.0,
                'avg_response_time': 0.0,
                'total_calls': 0,
                'errors': {}
            }
            
        return {
            'success_rate': (self.successful_calls / self.total_calls) * 100,
            'avg_response_time': sum(self.response_times) / len(self.response_times),
            'total_calls': self.total_calls,
            'errors': dict(self.errors)
        }

class ApiMonitor:
    """Monitor de APIs com limite de rate e métricas."""
    def __init__(self):
        self.stats = defaultdict(ApiStatistics)
        self.last_calls = defaultdict(float)
        
    def should_wait(self, api_name: str, rate_limit: Dict) -> float:
        now = time.time()
        last_call = self.last_calls.get(api_name, 0)
        
        if rate_limit['calls'] == 0:
            return 0
            
        wait_time = max(0, (last_call + rate_limit['period']) - now)
        return wait_time
        
    def update_stats(self, api_name: str, success: bool, response_time: float):
        self.stats[api_name].add_call(success, response_time)
        self.last_calls[api_name] = time.time()
        
    def get_api_stats(self, api_name: str) -> Dict[str, Any]:
        return self.stats[api_name].get_stats()
        
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        return {name: stats.get_stats() for name, stats in self.stats.items()}

class APIHandler:
    """Handler para requisições HTTP."""
    def __init__(self):
        self.session = requests.Session()
        
        retry_strategy = Retry(
            total=5,
            backoff_factor=1,
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
        
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
            'Accept': 'application/json,application/xml,text/html',
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
    def _quick_isbn_validation(self, isbn: str) -> bool:
        """Validação rápida antes de chamar APIs."""
        if not isbn or not isinstance(isbn, str):
            return False
            
        # Remove caracteres não numéricos exceto X
        isbn = ''.join(c for c in isbn.upper() if c.isdigit() or c == 'X')
        
        # Verifica tamanho e prefixo básico
        if len(isbn) == 13:
            return isbn.startswith(('978', '979'))
        elif len(isbn) == 10:
            return isbn[:-1].isdigit() and (isbn[-1].isdigit() or isbn[-1] == 'X')
            
        return False
    
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
        Extrai ISBNs do texto usando uma combinação de abordagens, com suporte especial para editoras específicas.
        """
        # Se não tem texto mas tem caminho, tenta extrair do PDF
        if not text and source_path:
            text = self._extract_from_pdf(source_path)
        
        if not text:
            return set()

        found_isbns = set()
        original_text = text
        
        # Verifica se é um tipo de livro específico
        is_packt = source_path and ('hands-on' in source_path.lower() or 'packt' in source_path.lower())
        is_oreilly = source_path and ("oreilly" in source_path.lower() or "o'reilly" in source_path.lower())
        is_casa_codigo = source_path and ('casa' in source_path.lower() and 'codigo' in source_path.lower())
        
        # Lista simplificada de versões do texto
        text_versions = [
            text,                                      # Original
            text.replace('-', '').replace(' ', ''),    # Remove separadores
            self._clean_text_for_isbn(text),           # Limpeza específica para ISBN
            self._normalize_ocr_text(text),            # Correção de OCR
        ]
        
        # Se for livro da Packt, adiciona correções específicas
        if is_packt:
            packt_text = text.replace('@', '9').replace('>', '7').replace('?', '8')
            text_versions.append(packt_text)

        # Processa cada versão do texto
        for cleaned_text in text_versions:
            # Escolhe padrões apropriados baseado no tipo de livro
            patterns_to_use = []
            
            if is_packt:
                patterns_to_use.extend([
                    r'eBook:\s*ISBN[:\s-]*(97[89][-\s]*(?:\d[-\s]*){9}\d)',
                    r'Print\s+ISBN[:\s-]*(97[89][-\s]*(?:\d[-\s]*){9}\d)',
                    r'ISBN\s+13:[:\s-]*(97[89][-\s]*(?:\d[-\s]*){9}\d)',
                    r'ISBN[:\s-]*(@7[89][-\s]*(?:\d[-\s]*){9}\d)',
                    r'ISBN[:\s-]*(>7[89][-\s]*(?:\d[-\s]*){9}\d)',
                    r'ISBN[:\s-]*(\?7[89][-\s]*(?:\d[-\s]*){9}\d)'
                ])
            elif is_casa_codigo:
                patterns_to_use.extend([
                    r'ISBN[:\s-]*(97865[-\s]*(?:\d[-\s]*){7}\d)',
                    r'EAN[:\s-]*(97865[-\s]*(?:\d[-\s]*){7}\d)'
                ])
            
            # Adiciona padrões padrão
            patterns_to_use.extend([
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
            ])
            
            for pattern in patterns_to_use:
                matches = re.finditer(pattern, cleaned_text, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    try:
                        # Se tem grupos, pega o primeiro grupo, senão pega o match inteiro
                        isbn = match.group(1) if match.groups() else match.group()
                        
                        # Limpa o ISBN
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
            
            # Se encontrou ISBNs, não precisa tentar outras versões do texto
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

    def extract_from_pdf(self, pdf_path: str, max_pages: int = 10) -> str:
        """Extrai texto com foco em livros da Packt."""
        is_packt = 'hands-on' in pdf_path.lower() or 'packt' in pdf_path.lower()
        
        if is_packt:
            # Para Packt, verifica mais páginas e especialmente a página de copyright
            try:
                with open(pdf_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    text = ""
                    # Verifica páginas iniciais onde geralmente está o ISBN
                    for i in range(min(5, len(reader.pages))):
                        text += reader.pages[i].extract_text() + "\n"
                        
                    # Se não encontrou ISBN, procura na página de copyright
                    if not re.search(r'ISBN', text, re.IGNORECASE):
                        for i in range(5, min(15, len(reader.pages))):
                            page_text = reader.pages[i].extract_text()
                            if re.search(r'copyright|isbn', page_text, re.IGNORECASE):
                                text += page_text + "\n"
                                break
                    return text
            except Exception as e:
                logging.error(f"Erro ao extrair texto de PDF Packt: {str(e)}")
                return ""
                
        # Se não for Packt, usa extração normal
        return super().extract_from_pdf(pdf_path, max_pages)

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

    def _isbn_10_to_13(self, isbn10: str) -> Optional[str]:
        """Converte ISBN-10 para ISBN-13."""
        if len(isbn10) != 10:
            return None
            
        # Remove hífens e espaços
        isbn10 = ''.join(c for c in isbn10 if c.isdigit() or c in 'Xx')
        
        # Converte para ISBN-13
        isbn13 = '978' + isbn10[:-1]
        
        # Calcula dígito verificador
        total = 0
        for i in range(12):
            if i % 2 == 0:
                total += int(isbn13[i])
            else:
                total += int(isbn13[i]) * 3
                
        check = (10 - (total % 10)) % 10
        return isbn13 + str(check)

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
        
        # Initialize required components
        self.rate_limiter = RateLimitCache()
        self.validator = MetadataValidator()
        self.metrics = MetricsCollector()

        # Configure APIs and confidence scores
        self._configure_apis()
        self._configure_confidence_scores()

        # Brazilian publishers configuration
        self.BRAZILIAN_PUBLISHERS = {
            'casa_do_codigo': {
                'name': 'Casa do Código',
                'prefixes': ['97865'],
                'patterns': [r'casa\s+do\s+c[óo]digo', r'CDC', r'casadocodigo'],
                'api_priority': ['google_books', 'openlibrary', 'worldcat']
            },
            'novatec': {
                'name': 'Novatec',
                'prefixes': ['97885'],
                'patterns': [r'novatec'],
                'api_priority': ['google_books', 'openlibrary', 'worldcat']
            },
            'alta_books': {
                'name': 'Alta Books',
                'prefixes': ['97885'],
                'patterns': [r'alta\s+books'],
                'api_priority': ['google_books', 'openlibrary', 'worldcat']
            }
        }
        
        # API configurations
        self.API_CONFIGS = {
            'openlibrary': {'enabled': True, 'timeout': 5, 'retries': 3},
            'google_books': {'enabled': True, 'timeout': 5, 'retries': 3},
            'worldcat': {'enabled': True, 'timeout': 8, 'retries': 2},
            'isbnlib_info': {'enabled': True, 'timeout': 3, 'retries': 2},
            'crossref': {'enabled': True, 'timeout': 6, 'retries': 2},
        }

        # Confidence adjustments
        self.confidence_adjustments = {
            'openlibrary': 0.85,
            'google_books': 0.90,
            'worldcat': 0.80,
            'isbnlib_info': 0.95,
            'crossref': 0.80,
        } 

    def _make_request(self, api_name: str, url: str, **kwargs) -> requests.Response:
        """Make HTTP request with error handling and rate limiting."""
        if not self._check_api_health(api_name):
            raise Exception(f"API {api_name} is currently unhealthy")

        start_time = time.time()
        config = self.API_CONFIGS.get(api_name, {})
        
        # Rate limiting
        wait_time = self.rate_limiter.should_wait(api_name)
        if wait_time > 0:
            time.sleep(wait_time)
            
        try:
            # Dynamic timeout based on performance
            stats = self.metrics.get_api_stats(api_name)
            avg_time = stats.get('avg_response_time', 5.0)
            dynamic_timeout = min(max(avg_time * 2, config.get('timeout', 5)), 30)

            # Make request
            response = self.api.get(
                url,
                timeout=dynamic_timeout,
                **kwargs
            )
            
            elapsed = time.time() - start_time
            
            # Update statistics
            success = response.status_code == 200
            self.rate_limiter.update_stats(api_name, success, elapsed)
            self.metrics.add_metric(api_name, elapsed, success)
            
            response.raise_for_status()
            return response
            
        except Exception as e:
            elapsed = time.time() - start_time
            self.rate_limiter.update_stats(api_name, False, elapsed)
            self.metrics.add_metric(api_name, elapsed, False)
            self.metrics.add_error(api_name, type(e).__name__)
            raise       

    def _configure_apis(self):
        """Configure API settings and Brazilian publishers."""
        self.BRAZILIAN_PUBLISHERS = {
            'casa_do_codigo': {
                'name': 'Casa do Código',
                'prefixes': ['97865'],
                'patterns': [r'casa\s+do\s+c[óo]digo', r'CDC', r'casadocodigo'],
                'api_priority': ['google_books', 'openlibrary', 'worldcat']
            },
            'novatec': {
                'name': 'Novatec',
                'prefixes': ['97885'],
                'patterns': [r'novatec'],
                'api_priority': ['google_books', 'openlibrary', 'worldcat']
            },
            'alta_books': {
                'name': 'Alta Books',
                'prefixes': ['97885'],
                'patterns': [r'alta\s+books'],
                'api_priority': ['google_books', 'openlibrary', 'worldcat']
            }
        }
        
        self.API_CONFIGS = {
            'openlibrary': {'enabled': True, 'timeout': 5, 'retries': 3},
            'google_books': {'enabled': True, 'timeout': 5, 'retries': 3}, 
            'worldcat': {'enabled': True, 'timeout': 8, 'retries': 2},
            'isbnlib_info': {'enabled': True, 'timeout': 3, 'retries': 2},
            'crossref': {'enabled': True, 'timeout': 6, 'retries': 2}
        }

    def _configure_confidence_scores(self):
        """Configure confidence scores for different APIs."""
        self.confidence_adjustments = {
            'openlibrary': 0.85,
            'google_books': 0.90,
            'worldcat': 0.80,
            'isbnlib_info': 0.95,
            'crossref': 0.80,
        }

    def fetch_metadata(self, isbn: str) -> Optional[BookMetadata]:
        """Main method to fetch metadata with special handling for Casa do Código."""
        # Check cache first
        cached = self.cache.get(isbn)
        if cached:
            return BookMetadata(**cached)
            
        try:
            # Special handling for Casa do Código (prefix 97865)
            if isbn.startswith('97865'):
                metadata = self._fetch_casa_codigo_metadata(isbn)
                if metadata:
                    return metadata

            # Special handling for other Brazilian publishers (prefix 97885)
            if isbn.startswith('97885'):
                metadata = self._fetch_brazilian_metadata(isbn)
                if metadata:
                    return metadata

            # Try fetch with fallback system
            metadata = self._fetch_with_fallback(isbn)
            
            if metadata:
                # Final validation before caching
                metadata_dict = asdict(metadata)
                if self.validator.validate_metadata(metadata_dict, metadata.source, isbn):
                    self.cache.set(metadata_dict)
                    logging.info(f"Metadata found for ISBN {isbn} from {metadata.source}")
                    return metadata
            
            logging.warning(f"Failed to fetch metadata for ISBN {isbn}")
            return None
            
        except Exception as e:
            logging.error(f"Error fetching metadata for ISBN {isbn}: {str(e)}")
            return None

    def _fetch_with_fallback(self, isbn: str) -> Optional[BookMetadata]:
        """Enhanced fallback system with better error handling."""
        api_groups = [
            {
                'name': 'primary',
                'apis': ['isbnlib_info', 'google_books'],
                'min_confidence': 0.90,
                'required_success': 1
            },
            {
                'name': 'secondary',
                'apis': ['openlibrary', 'worldcat'],
                'min_confidence': 0.80,
                'required_success': 1
            },
            {
                'name': 'fallback',
                'apis': ['crossref'],
                'min_confidence': 0.70,
                'required_success': 1
            }
        ]

        all_results = []
        tried_apis = set()
        errors = defaultdict(list)

        for group in api_groups:
            group_results = []
            available_apis = [
                api for api in group['apis']
                if api not in tried_apis and
                self.API_CONFIGS.get(api, {}).get('enabled', True)
            ]

            if not available_apis:
                continue

            for api_name in available_apis:
                tried_apis.add(api_name)
                start_time = time.time()  # Inicializa start_time antes de qualquer possível exceção
                
                try:
                    # Check rate limiting
                    wait_time = self.rate_limiter.should_wait(api_name)
                    if wait_time > 0:
                        time.sleep(wait_time)

                    # Make API call with timing
                    method = getattr(self, f'_fetch_{api_name}')
                    metadata = method(isbn)
                    elapsed = time.time() - start_time

                    # Update rate limiting and metrics
                    self.rate_limiter.update_stats(api_name, True, elapsed)
                    self.metrics.add_metric(api_name, elapsed, True)

                    if metadata:
                        # Validate metadata
                        if self.validator.validate_metadata(asdict(metadata), api_name, isbn):
                            group_results.append(metadata)

                            # Return if we have good enough results
                            if (len(group_results) >= group['required_success'] and
                                any(r.confidence_score >= group['min_confidence'] 
                                    for r in group_results)):
                                return max(group_results, key=lambda x: x.confidence_score)

                except Exception as e:
                    elapsed = time.time() - start_time
                    self.rate_limiter.update_stats(api_name, False, elapsed)
                    self.metrics.add_metric(api_name, elapsed, False)
                    self.metrics.add_error(api_name, type(e).__name__)
                    errors[api_name].append(str(e))
                    logging.error(f"Error in {api_name} for ISBN {isbn}: {str(e)}")
                    continue

            all_results.extend(group_results)

            # Return if we have good enough results
            if all_results and any(
                r.confidence_score >= group['min_confidence'] 
                for r in all_results
            ):
                return max(all_results, key=lambda x: x.confidence_score)

        # Log all errors if no results found
        if not all_results:
            for api_name, api_errors in errors.items():
                logging.error(f"All attempts failed for ISBN {isbn}")
                for error in api_errors:
                    logging.error(f"{api_name}: {error}")

        return max(all_results, key=lambda x: x.confidence_score) if all_results else None

    def _fetch_google_books(self, isbn: str) -> Optional[BookMetadata]:
        """Fetch metadata from Google Books API."""
        try:
            url = "https://www.googleapis.com/books/v1/volumes"
            params = {'q': f'isbn:{isbn}', 'maxResults': 1}
            
            response = self._make_request('google_books', url, params=params)
            data = response.json()
            
            if 'items' not in data:
                return None
                
            book_info = data['items'][0]['volumeInfo']
            
            metadata_dict = {
                'title': book_info.get('title', ''),
                'authors': book_info.get('authors', []),
                'publisher': book_info.get('publisher', 'Unknown'),
                'published_date': book_info.get('publishedDate', 'Unknown'),
                'isbn_13': isbn if len(isbn) == 13 else None,
                'isbn_10': isbn if len(isbn) == 10 else None,
                'confidence_score': self.confidence_adjustments['google_books'],
                'source': 'google_books'
            }
            
            if not self.validator.validate_metadata(metadata_dict, 'google_books', isbn):
                return None
                
            return BookMetadata(**metadata_dict)
            
        except Exception as e:
            self._handle_api_error('google_books', e, isbn)
            return None

    def _fetch_openlibrary(self, isbn: str) -> Optional[BookMetadata]:
        """Fetch metadata from Open Library API."""
        try:
            url = "https://openlibrary.org/api/books"
            params = {
                'bibkeys': f'ISBN:{isbn}',
                'format': 'json',
                'jscmd': 'data'
            }
            
            response = self._make_request('openlibrary', url, params=params)
            data = response.json()
            
            if f"ISBN:{isbn}" not in data:
                return None
                
            book_info = data[f"ISBN:{isbn}"]
            
            metadata_dict = {
                'title': book_info.get('title', ''),
                'authors': [author['name'] for author in book_info.get('authors', [])],
                'publisher': book_info.get('publishers', [{'name': 'Unknown'}])[0]['name'],
                'published_date': book_info.get('publish_date', 'Unknown'),
                'isbn_13': isbn if len(isbn) == 13 else None,
                'isbn_10': isbn if len(isbn) == 10 else None,
                'confidence_score': self.confidence_adjustments['openlibrary'],
                'source': 'openlibrary'
            }
            
            if not self.validator.validate_metadata(metadata_dict, 'openlibrary', isbn):
                return None
                
            return BookMetadata(**metadata_dict)
            
        except Exception as e:
            self._handle_api_error('openlibrary', e, isbn)
            return None

    def _fetch_worldcat(self, isbn: str) -> Optional[BookMetadata]:
        """Fetch metadata from WorldCat."""
        try:
            url = f"https://www.worldcat.org/isbn/{isbn}"
            response = self._make_request('worldcat', url)
            
            if response.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                
                title = soup.find('h1', {'class': 'title'})
                authors = soup.find_all('a', {'class': 'author'})
                publisher = soup.find('td', string='Publisher')
                published_date = soup.find('td', string='Date')
                
                metadata_dict = {
                    'title': title.text.strip() if title else '',
                    'authors': [a.text.strip() for a in authors if a.text.strip()],
                    'publisher': publisher.next_sibling.text.strip() if publisher else 'Unknown',
                    'published_date': published_date.next_sibling.text.strip() if published_date else 'Unknown',
                    'isbn_13': isbn if len(isbn) == 13 else None,
                    'isbn_10': isbn if len(isbn) == 10 else None,
                    'confidence_score': self.confidence_adjustments['worldcat'],
                    'source': 'worldcat'
                }
                
                if not self.validator.validate_metadata(metadata_dict, 'worldcat', isbn):
                    return None
                    
                return BookMetadata(**metadata_dict)
                
        except Exception as e:
            self._handle_api_error('worldcat', e, isbn)
            return None

    def _fetch_casa_codigo_metadata(self, isbn: str) -> Optional[BookMetadata]:
        """Fetch metadata specifically for Casa do Código books."""
        logging.info(f"Processing Casa do Código ISBN: {isbn}")
        
        # Try APIs in priority order for Casa do Código
        for api_name in ['google_books', 'openlibrary', 'worldcat']:
            try:
                method = getattr(self, f'_fetch_{api_name}')
                metadata = method(isbn)
                
                if metadata:
                    # Force correct publisher and increase confidence
                    metadata.publisher = "Casa do Código"
                    metadata.confidence_score = 0.95
                    
                    # Validate and cache
                    metadata_dict = asdict(metadata)
                    if self.validator.validate_metadata(metadata_dict, metadata.source, isbn):
                        self.cache.set(metadata_dict)
                        return metadata
                        
            except Exception as e:
                logging.error(f"Error with {api_name} for ISBN {isbn}: {str(e)}")
                continue
                
        return None


    def fetch_openlibrary(self, isbn: str) -> Optional[BookMetadata]:
        """Fetch from Open Library API com rate limiting e métricas."""
        try:
            url = f"https://openlibrary.org/api/books"
            params = {
                'bibkeys': f'ISBN:{isbn}',
                'format': 'json',
                'jscmd': 'data'
            }
            
            response = self._make_request('openlibrary', url, params=params)
            data = response.json()
            
            if f"ISBN:{isbn}" not in data:
                return None
                
            book_info = data[f"ISBN:{isbn}"]
            
            # Preparação dos dados para validação
            metadata_dict = {
                'title': book_info.get('title', ''),
                'authors': [author['name'] for author in book_info.get('authors', [])],
                'publisher': book_info.get('publishers', [{'name': 'Unknown'}])[0]['name'],
                'published_date': book_info.get('publish_date', 'Unknown')
            }
            
            # Validação antes de criar o objeto
            if not self.validator.validate_metadata(metadata_dict, 'openlibrary', isbn=isbn):
                return None
                
            return BookMetadata(
                title=metadata_dict['title'],
                authors=metadata_dict['authors'],
                publisher=metadata_dict['publisher'],
                published_date=metadata_dict['published_date'],
                isbn_13=isbn if len(isbn) == 13 else None,
                isbn_10=isbn if len(isbn) == 10 else None,
                confidence_score=self.confidence_adjustments['openlibrary'],
                source='openlibrary'
            )
            
        except Exception as e:
            self._handle_api_error('openlibrary', e, isbn)
            return None

    def fetch_google_books(self, isbn: str, country: str = None, lang: str = None) -> Optional[BookMetadata]:
        """Versão melhorada do Google Books com suporte a regionalização."""
        try:
            url = "https://www.googleapis.com/books/v1/volumes"
            params = {
                'q': f'isbn:{isbn}',
                'maxResults': 1
            }
            
            # Adiciona parâmetros de regionalização
            if country:
                params['country'] = country
            if lang:
                params['langRestrict'] = lang
            
            response = self._make_request('google_books', url, params=params)
            data = response.json()
            
            if 'items' not in data:
                return None
                
            book_info = data['items'][0]['volumeInfo']
            
            metadata_dict = {
                'title': book_info.get('title', ''),
                'authors': book_info.get('authors', []),
                'publisher': book_info.get('publisher', 'Unknown'),
                'published_date': book_info.get('publishedDate', 'Unknown'),
                'isbn_13': isbn if len(isbn) == 13 else None,
                'isbn_10': isbn if len(isbn) == 10 else None,
                'confidence_score': self.confidence_adjustments['google_books'],
                'source': 'google_books'
            }
            
            # Validação
            if not self.validator.validate_metadata(metadata_dict, 'google_books', isbn):
                return None
                
            return BookMetadata(**metadata_dict)
            
        except Exception as e:
            self._handle_api_error('google_books', e, isbn)
            return None

    def fetch_loc(self, isbn: str) -> Optional[BookMetadata]:
            """Fetch from Library of Congress com melhor tratamento de XML."""
            try:
                url = f"https://lccn.loc.gov/{isbn}/marc21.xml"
                response = self._make_request('loc', url)
                
                if response.status_code == 200:
                    # Limpa o XML antes de processar
                    xml_text = response.text
                    xml_text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', xml_text)
                    xml_text = re.sub(r'<\?xml[^>]+\?>', '', xml_text)
                    
                    try:
                        # Tenta primeiro com namespace
                        root = ET.fromstring(xml_text)
                        ns = {'marc': 'http://www.loc.gov/MARC21/slim'}
                        
                        title = root.find('.//marc:datafield[@tag="245"]/marc:subfield[@code="a"]', ns)
                        authors = root.findall('.//marc:datafield[@tag="100"]/marc:subfield[@code="a"]', ns)
                        publisher = root.find('.//marc:datafield[@tag="260"]/marc:subfield[@code="b"]', ns)
                        date = root.find('.//marc:datafield[@tag="260"]/marc:subfield[@code="c"]', ns)
                        
                    except ET.ParseError:
                        try:
                            # Se falhar, tenta parsing mais tolerante
                            from bs4 import BeautifulSoup
                            soup = BeautifulSoup(xml_text, 'xml')
                            
                            title = soup.find('subfield', {'code': 'a', 'tag': '245'})
                            authors = soup.find_all('subfield', {'code': 'a', 'tag': '100'})
                            publisher = soup.find('subfield', {'code': 'b', 'tag': '260'})
                            date = soup.find('subfield', {'code': 'c', 'tag': '260'})
                        except:
                            return None
                    
                    metadata_dict = {
                        'title': title.text.strip() if title is not None else '',
                        'authors': [a.text.strip() for a in authors] if authors else ['Unknown'],
                        'publisher': publisher.text.strip() if publisher is not None else 'Unknown',
                        'published_date': date.text.strip() if date is not None else 'Unknown'
                    }
                    
                    if not self.validator.validate_metadata(metadata_dict, 'loc', isbn=isbn):
                        return None
                        
                    return BookMetadata(
                        title=metadata_dict['title'],
                        authors=metadata_dict['authors'],
                        publisher=metadata_dict['publisher'],
                        published_date=metadata_dict['published_date'],
                        isbn_13=isbn if len(isbn) == 13 else None,
                        isbn_10=isbn if len(isbn) == 10 else None,
                        confidence_score=self.confidence_adjustments['loc'],
                        source='loc'
                    )
                    
            except Exception as e:
                self._handle_api_error('loc', e, isbn)
                return None
 
    def fetch_isbnlib_info(self, isbn: str) -> Optional[BookMetadata]:
        """Fetch usando isbnlib.info() com melhor tratamento de variantes."""
        try:
            import isbnlib
            
            # Validação inicial do ISBN
            if not isbnlib.is_isbn13(isbn) and not isbnlib.is_isbn10(isbn):
                return None
                
            # Obtém informações básicas
            info = isbnlib.info(isbn)
            if not info:
                return None
                
            # Busca metadados completos
            metadata = isbnlib.meta(isbn)
            if not metadata:
                return None
                
            metadata_dict = {
                'title': metadata.get('Title', '').strip(),
                'authors': [a.strip() for a in metadata.get('Authors', [])],
                'publisher': metadata.get('Publisher', '').strip(),
                'published_date': metadata.get('Year', 'Unknown')
            }
            
            # Validação dos dados
            if not self.validator.validate_metadata(metadata_dict, 'isbnlib_info', isbn=isbn):
                return None
                
            return BookMetadata(
                title=metadata_dict['title'],
                authors=metadata_dict['authors'],
                publisher=metadata_dict['publisher'],
                published_date=metadata_dict['published_date'],
                isbn_13=isbn if len(isbn) == 13 else None,
                isbn_10=isbn if len(isbn) == 10 else None,
                confidence_score=self.confidence_adjustments['isbnlib_info'],
                source='isbnlib_info'
            )
            
        except Exception as e:
            if 'isbn request != isbn response' in str(e):
                logging.warning(f"ISBNlib info: ISBN variant detected for {isbn}: {str(e)}")
                return None
            self._handle_api_error('isbnlib_info', e, isbn)
            return None
        

    def fetch_cbl(self, isbn: str) -> Optional[BookMetadata]:
        """Busca na API da Câmara Brasileira do Livro com validação aprimorada."""
        try:
            url = f"https://isbn.cbl.org.br/api/isbn/{isbn}"
            response = self._make_request('cbl', url)
            
            if response.status_code != 200:
                return None
                
            data = response.json()
            
            metadata_dict = {
                'title': data.get('title', ''),
                'authors': data.get('authors', ['Unknown']),
                'publisher': data.get('publisher', 'Unknown'),
                'published_date': data.get('published_date', 'Unknown')
            }
            
            # Validação específica para CBL
            if not self.validator.validate_metadata(metadata_dict, 'cbl', isbn=isbn):
                return None
                
            return BookMetadata(
                title=metadata_dict['title'],
                authors=metadata_dict['authors'],
                publisher=metadata_dict['publisher'],
                published_date=metadata_dict['published_date'],
                isbn_13=isbn if len(isbn) == 13 else None,
                isbn_10=isbn if len(isbn) == 10 else None,
                confidence_score=self.confidence_adjustments['cbl'],
                source='cbl'
            )
        except Exception as e:
            self._handle_api_error('cbl', e, isbn)
            return None

    def fetch_mercado_editorial(self, isbn: str) -> Optional[BookMetadata]:
        """Busca na API do Mercado Editorial Brasileiro com validação aprimorada."""
        try:
            url = f"https://api.mercadoeditorial.org/api/v1.2/book?isbn={isbn}"
            response = self._make_request('mercado_editorial', url)
            
            data = response.json()
            if not data.get('books'):
                return None
                
            book = data['books'][0]
            
            metadata_dict = {
                'title': book.get('title', ''),
                'authors': book.get('authors', ['Unknown']),
                'publisher': book.get('publisher', 'Unknown'),
                'published_date': book.get('published_date', 'Unknown')
            }
            
            # Validação específica para Mercado Editorial
            if not self.validator.validate_metadata(metadata_dict, 'mercado_editorial', isbn=isbn):
                return None
                
            return BookMetadata(
                title=metadata_dict['title'],
                authors=metadata_dict['authors'],
                publisher=metadata_dict['publisher'],
                published_date=metadata_dict['published_date'],
                isbn_13=isbn if len(isbn) == 13 else None,
                isbn_10=isbn if len(isbn) == 10 else None,
                confidence_score=self.confidence_adjustments['mercado_editorial'],
                source='mercado_editorial'
            )
        except Exception as e:
            self._handle_api_error('mercado_editorial', e, isbn)
            return None

    def fetch_internet_archive(self, isbn: str) -> Optional[BookMetadata]:
        """Fetch from Internet Archive Books API com validação aprimorada."""
        try:
            url = f"https://archive.org/advancedsearch.php"
            params = {
                'q': f'isbn:{isbn}',
                'output': 'json',
                'rows': 1,
                'fl[]': ['title', 'creator', 'publisher', 'date']
            }
            
            response = self._make_request('internet_archive', url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if data['response']['docs']:
                    doc = data['response']['docs'][0]
                    
                    metadata_dict = {
                        'title': doc.get('title', ''),
                        'authors': [doc.get('creator', 'Unknown')],
                        'publisher': doc.get('publisher', 'Unknown'),
                        'published_date': doc.get('date', 'Unknown')
                    }
                    
                    # Validação
                    if not self.validator.validate_metadata(metadata_dict, 'internet_archive', isbn=isbn):
                        return None
                        
                    return BookMetadata(
                        title=metadata_dict['title'],
                        authors=metadata_dict['authors'],
                        publisher=metadata_dict['publisher'],
                        published_date=metadata_dict['published_date'],
                        isbn_13=isbn if len(isbn) == 13 else None,
                        isbn_10=isbn if len(isbn) == 10 else None,
                        confidence_score=self.confidence_adjustments['internet_archive'],
                        source='internet_archive'
                    )
                    
        except Exception as e:
            self._handle_api_error('internet_archive', e, isbn)
            return None

    def fetch_zbib(self, isbn: str) -> Optional[BookMetadata]:
        """Fetch from Zbib com validação aprimorada."""
        try:
            url = f"https://api.zbib.org/v1/search"
            params = {'q': f'isbn:{isbn}'}
            
            response = self._make_request('zbib', url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if not data or not data.get('items'):
                    return None
                    
                item = data['items'][0]
                
                metadata_dict = {
                    'title': item.get('title', ''),
                    'authors': item.get('authors', []),
                    'publisher': item.get('publisher', 'Unknown'),
                    'published_date': str(item.get('year', 'Unknown'))
                }
                
                # Validação
                if not self.validator.validate_metadata(metadata_dict, 'zbib', isbn=isbn):
                    return None
                    
                return BookMetadata(
                    title=metadata_dict['title'],
                    authors=metadata_dict['authors'],
                    publisher=metadata_dict['publisher'],
                    published_date=metadata_dict['published_date'],
                    isbn_13=isbn if len(isbn) == 13 else None,
                    isbn_10=isbn if len(isbn) == 10 else None,
                    confidence_score=self.confidence_adjustments['zbib'],
                    source='zbib'
                )
                
        except Exception as e:
            self._handle_api_error('zbib', e, isbn)
            return None

    def fetch_ebook_de(self, isbn: str) -> Optional[BookMetadata]:
        """Fetch from Ebook.de com validação aprimorada."""
        try:
            url = f"https://www.ebook.de/de/tools/isbn2bibtex/{isbn}"
            response = self._make_request('ebook_de', url)
            
            if response.status_code != 200:
                return None
                
            text = response.text
            
            # Parser melhorado para BibTeX
            def extract_field(field: str) -> Optional[str]:
                pattern = rf'{field}\s*=\s*{{([^}}]+)}}'
                match = re.search(pattern, text)
                return match.group(1).strip() if match else None
                
            metadata_dict = {
                'title': extract_field('title'),
                'authors': [a.strip() for a in (extract_field('author') or '').split(' and ')],
                'publisher': extract_field('publisher'),
                'published_date': extract_field('year')
            }
            
            # Validação
            if not self.validator.validate_metadata(metadata_dict, 'ebook_de', isbn=isbn):
                return None
                
            return BookMetadata(
                title=metadata_dict['title'],
                authors=metadata_dict['authors'] if metadata_dict['authors'] else ['Unknown'],
                publisher=metadata_dict['publisher'] or 'Unknown',
                published_date=metadata_dict['published_date'] or 'Unknown',
                isbn_13=isbn if len(isbn) == 13 else None,
                isbn_10=isbn if len(isbn) == 10 else None,
                confidence_score=self.confidence_adjustments['ebook_de'],
                source='ebook_de'
            )
            
        except Exception as e:
            self._handle_api_error('ebook_de', e, isbn)
            return None
        
    def fetch_crossref(self, isbn: str) -> Optional[BookMetadata]:
        """Fetch from CrossRef API com validação aprimorada."""
        try:
            url = "https://api.crossref.org/works"
            params = {
                'query.bibliographic': isbn,
                'filter': 'type:book',
                'select': 'title,author,published-print,publisher'
            }
            
            response = self._make_request('crossref', url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if data['message']['items']:
                    item = data['message']['items'][0]
                    
                    metadata_dict = {
                        'title': item.get('title', ['Unknown'])[0],
                        'authors': [
                            f"{a.get('given', '')} {a.get('family', '')}".strip()
                            for a in item.get('author', [])
                        ],
                        'publisher': item.get('publisher', 'Unknown'),
                        'published_date': str(
                            item.get('published-print', {})
                            .get('date-parts', [[0]])[0][0]
                        )
                    }
                    
                    # Validação
                    if not self.validator.validate_metadata(metadata_dict, 'crossref', isbn=isbn):
                        return None
                        
                    return BookMetadata(
                        title=metadata_dict['title'],
                        authors=metadata_dict['authors'],
                        publisher=metadata_dict['publisher'],
                        published_date=metadata_dict['published_date'],
                        isbn_13=isbn if len(isbn) == 13 else None,
                        isbn_10=isbn if len(isbn) == 10 else None,
                        confidence_score=self.confidence_adjustments['crossref'],
                        source='crossref'
                    )
                    
        except Exception as e:
            self._handle_api_error('crossref', e, isbn)
            return None

    def fetch_springer(self, isbn: str) -> Optional[BookMetadata]:
        """Fetch from Springer Nature API com validação aprimorada."""
        try:
            url = f"https://api.springernature.com/metadata/books/isbn/{isbn}"
            response = self._make_request('springer', url)
            
            if response.status_code == 200:
                data = response.json()
                
                metadata_dict = {
                    'title': data.get('title', ''),
                    'authors': data.get('creators', []),
                    'publisher': 'Springer',  # Sempre Springer
                    'published_date': data.get('publicationDate', 'Unknown')
                }
                
                # Validação específica para Springer
                if not self.validator.validate_metadata(metadata_dict, 'springer', isbn=isbn):
                    return None
                    
                return BookMetadata(
                    title=metadata_dict['title'],
                    authors=metadata_dict['authors'],
                    publisher=metadata_dict['publisher'],
                    published_date=metadata_dict['published_date'],
                    isbn_13=isbn if len(isbn) == 13 else None,
                    isbn_10=isbn if len(isbn) == 10 else None,
                    confidence_score=self.confidence_adjustments['springer'],
                    source='springer'
                )
                
        except Exception as e:
            self._handle_api_error('springer', e, isbn)
            return None

    def fetch_oreilly(self, isbn: str) -> Optional[BookMetadata]:
        """Fetch from O'Reilly API com validação aprimorada."""
        try:
            url = f"https://learning.oreilly.com/api/v2/book/isbn/{isbn}/"
            response = self._make_request('oreilly', url)
            
            if response.status_code == 200:
                data = response.json()
                
                metadata_dict = {
                    'title': data.get('title', ''),
                    'authors': data.get('authors', []),
                    'publisher': "O'Reilly Media",
                    'published_date': data.get('issued', 'Unknown')
                }
                
                # Validação específica para O'Reilly
                if not self.validator.validate_metadata(metadata_dict, 'oreilly', isbn=isbn):
                    return None
                    
                return BookMetadata(
                    title=metadata_dict['title'],
                    authors=metadata_dict['authors'],
                    publisher=metadata_dict['publisher'],
                    published_date=metadata_dict['published_date'],
                    isbn_13=isbn if len(isbn) == 13 else None,
                    isbn_10=isbn if len(isbn) == 10 else None,
                    confidence_score=self.confidence_adjustments['oreilly'],
                    source='oreilly'
                )
                
        except Exception as e:
            self._handle_api_error('oreilly', e, isbn)
            return None

    def fetch_worldcat(self, isbn: str) -> Optional[BookMetadata]:
        """Fetch from WorldCat com validação aprimorada."""
        try:
            url = f"https://www.worldcat.org/isbn/{isbn}"
            response = self._make_request('worldcat', url)
            
            if response.status_code == 403:
                logging.warning(f"WorldCat: Access forbidden for ISBN {isbn}")
                return None
                
            if response.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                
                title = soup.find('h1', {'class': 'title'})
                authors = soup.find_all('a', {'class': 'author'})
                publisher = soup.find('td', string='Publisher')
                published_date = soup.find('td', string='Date')
                
                metadata_dict = {
                    'title': title.text.strip() if title else '',
                    'authors': [a.text.strip() for a in authors if a.text.strip()],
                    'publisher': publisher.next_sibling.text.strip() if publisher else 'Unknown',
                    'published_date': published_date.next_sibling.text.strip() if published_date else 'Unknown'
                }
                
                # Validação
                if not self.validator.validate_metadata(metadata_dict, 'worldcat', isbn=isbn):
                    return None
                    
                return BookMetadata(
                    title=metadata_dict['title'],
                    authors=metadata_dict['authors'],
                    publisher=metadata_dict['publisher'],
                    published_date=metadata_dict['published_date'],
                    isbn_13=isbn if len(isbn) == 13 else None,
                    isbn_10=isbn if len(isbn) == 10 else None,
                    confidence_score=self.confidence_adjustments['worldcat'],
                    source='worldcat'
                )
                
        except Exception as e:
            self._handle_api_error('worldcat', e, isbn)
            return None

    def fetch_mybib(self, isbn: str) -> Optional[BookMetadata]:
        """Fetch from MyBib API com validação aprimorada."""
        try:
            url = f"https://www.mybib.com/api/v1/references"
            params = {'q': isbn}
            
            response = self._make_request('mybib', url, params=params)
            data = response.json()
            
            if not data or 'references' not in data or not data['references']:
                return None
                
            item = data['references'][0]
            
            metadata_dict = {
                'title': item.get('title', ''),
                'authors': item.get('authors', ['Unknown']),
                'publisher': item.get('publisher', 'Unknown'),
                'published_date': item.get('year', 'Unknown')
            }
            
            # Validação
            if not self.validator.validate_metadata(metadata_dict, 'mybib', isbn=isbn):
                return None
                
            return BookMetadata(
                title=metadata_dict['title'],
                authors=metadata_dict['authors'],
                publisher=metadata_dict['publisher'],
                published_date=metadata_dict['published_date'],
                isbn_13=isbn if len(isbn) == 13 else None,
                isbn_10=isbn if len(isbn) == 10 else None,
                confidence_score=self.confidence_adjustments['mybib'],
                source='mybib'
            )
            
        except Exception as e:
            self._handle_api_error('mybib', e, isbn)
            return None
        
        
    def fetch_isbnlib_mask(self, isbn: str) -> Optional[BookMetadata]:
        """Fetch usando isbnlib.mask() com validação aprimorada."""
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
                
            metadata_dict = {
                'title': metadata.get('Title', '').strip(),
                'authors': [a.strip() for a in metadata.get('Authors', [])],
                'publisher': metadata.get('Publisher', '').strip(),
                'published_date': metadata.get('Year', 'Unknown')
            }
            
            # Validação
            if not self.validator.validate_metadata(metadata_dict, 'isbnlib_mask', isbn=isbn):
                return None
                
            return BookMetadata(
                title=metadata_dict['title'],
                authors=metadata_dict['authors'],
                publisher=metadata_dict['publisher'],
                published_date=metadata_dict['published_date'],
                isbn_13=isbn if len(isbn) == 13 else None,
                isbn_10=isbn if len(isbn) == 10 else None,
                confidence_score=self.confidence_adjustments['isbnlib_mask'],
                source='isbnlib_mask'
            )
            
        except Exception as e:
            self._handle_api_error('isbnlib_mask', e, isbn)
            return None

    def fetch_isbnlib_desc(self, isbn: str) -> Optional[BookMetadata]:
        """Fetch usando isbnlib.desc() com validação aprimorada."""
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
                
            metadata_dict = {
                'title': metadata.get('Title', '').strip(),
                'authors': [a.strip() for a in metadata.get('Authors', [])],
                'publisher': metadata.get('Publisher', '').strip(),
                'published_date': metadata.get('Year', 'Unknown')
            }
            
            # Validação
            if not self.validator.validate_metadata(metadata_dict, 'isbnlib_desc', isbn=isbn):
                return None
                
            return BookMetadata(
                title=metadata_dict['title'],
                authors=metadata_dict['authors'],
                publisher=metadata_dict['publisher'],
                published_date=metadata_dict['published_date'],
                isbn_13=isbn if len(isbn) == 13 else None,
                isbn_10=isbn if len(isbn) == 10 else None,
                confidence_score=self.confidence_adjustments['isbnlib_desc'],
                source='isbnlib_desc'
            )
            
        except Exception as e:
            self._handle_api_error('isbnlib_desc', e, isbn)
            return None

    def fetch_isbnlib_editions(self, isbn: str) -> Optional[BookMetadata]:
        """Fetch usando isbnlib.editions() com validação aprimorada."""
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
                
            metadata_dict = {
                'title': metadata.get('Title', '').strip(),
                'authors': [a.strip() for a in metadata.get('Authors', [])],
                'publisher': metadata.get('Publisher', '').strip(),
                'published_date': metadata.get('Year', 'Unknown')
            }
            
            # Validação
            if not self.validator.validate_metadata(metadata_dict, 'isbnlib_editions', isbn=isbn):
                return None
                
            return BookMetadata(
                title=metadata_dict['title'],
                authors=metadata_dict['authors'],
                publisher=metadata_dict['publisher'],
                published_date=metadata_dict['published_date'],
                isbn_13=isbn if len(isbn) == 13 else None,
                isbn_10=isbn if len(isbn) == 10 else None,
                confidence_score=self.confidence_adjustments['isbnlib_editions'],
                source='isbnlib_editions'
            )
            
        except Exception as e:
            self._handle_api_error('isbnlib_editions', e, isbn)
            return None

    def fetch_isbnlib_isbn10(self, isbn: str) -> Optional[BookMetadata]:
        """Fetch usando isbnlib para ISBN-10 com validação aprimorada."""
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
                
            metadata_dict = {
                'title': metadata.get('Title', '').strip(),
                'authors': [a.strip() for a in metadata.get('Authors', [])],
                'publisher': metadata.get('Publisher', '').strip(),
                'published_date': metadata.get('Year', 'Unknown')
            }
            
            # Validação
            if not self.validator.validate_metadata(metadata_dict, 'isbnlib_isbn10', isbn=isbn):
                return None
                
            return BookMetadata(
                title=metadata_dict['title'],
                authors=metadata_dict['authors'],
                publisher=metadata_dict['publisher'],
                published_date=metadata_dict['published_date'],
                isbn_13=None,
                isbn_10=isbn10,
                confidence_score=self.confidence_adjustments['isbnlib_isbn10'],
                source='isbnlib_isbn10'
            )
            
        except Exception as e:
            self._handle_api_error('isbnlib_isbn10', e, isbn)
            return None

    def fetch_isbnlib_isbn13(self, isbn: str) -> Optional[BookMetadata]:
        """Fetch usando isbnlib para ISBN-13 com validação aprimorada."""
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
                
            metadata_dict = {
                'title': metadata.get('Title', '').strip(),
                'authors': [a.strip() for a in metadata.get('Authors', [])],
                'publisher': metadata.get('Publisher', '').strip(),
                'published_date': metadata.get('Year', 'Unknown')
            }
            
            # Validação
            if not self.validator.validate_metadata(metadata_dict, 'isbnlib_isbn13', isbn=isbn):
                return None
                
            return BookMetadata(
                title=metadata_dict['title'],
                authors=metadata_dict['authors'],
                publisher=metadata_dict['publisher'],
                published_date=metadata_dict['published_date'],
                isbn_13=isbn13,
                isbn_10=None,
                confidence_score=self.confidence_adjustments['isbnlib_isbn13'],
                source='isbnlib_isbn13'
            )
            
        except Exception as e:
            self._handle_api_error('isbnlib_isbn13', e, isbn)
            return None

    def fetch_isbnlib_default(self, isbn: str) -> Optional[BookMetadata]:
        """Fetch usando serviço padrão do isbnlib com validação aprimorada."""
        try:
            import isbnlib
            if not isbnlib.is_isbn13(isbn) and not isbnlib.is_isbn10(isbn):
                return None
                
            # Usa o serviço padrão do isbnlib
            metadata = isbnlib.meta(isbn, service='default')
            if not metadata:
                return None
                
            metadata_dict = {
                'title': metadata.get('Title', '').strip(),
                'authors': [a.strip() for a in metadata.get('Authors', [])],
                'publisher': metadata.get('Publisher', '').strip(),
                'published_date': metadata.get('Year', 'Unknown')
            }
            
            # Validação
            if not self.validator.validate_metadata(metadata_dict, 'isbnlib_default', isbn=isbn):
                return None
                
            return BookMetadata(
                title=metadata_dict['title'],
                authors=metadata_dict['authors'],
                publisher=metadata_dict['publisher'],
                published_date=metadata_dict['published_date'],
                isbn_13=isbn if len(isbn) == 13 else None,
                isbn_10=isbn if len(isbn) == 10 else None,
                confidence_score=self.confidence_adjustments['isbnlib_default'],
                source='isbnlib_default'
            )
            
        except Exception as e:
            self._handle_api_error('isbnlib_default', e, isbn)
            return None

    def fetch_isbnlib_goom(self, isbn: str) -> Optional[BookMetadata]:
        """Fetch usando isbnlib.goom() com validação aprimorada."""
        try:
            import isbnlib
            if not isbnlib.is_isbn13(isbn) and not isbnlib.is_isbn10(isbn):
                logging.warning(f"ISBNlib: ISBN inválido {isbn}")
                return None
                
            metadata = isbnlib.goom(isbn)
            if not metadata:
                return None
                
            metadata_dict = {
                'title': metadata.get('Title', '').strip(),
                'authors': [author.strip() for author in metadata.get('Authors', [])],
                'publisher': metadata.get('Publisher', '').strip(),
                'published_date': metadata.get('Year', 'Unknown')
            }
            
            # Validação específica para goom
            if not self.validator.validate_metadata(metadata_dict, 'isbnlib_goom', isbn=isbn):
                return None
                
            return BookMetadata(
                title=metadata_dict['title'],
                authors=metadata_dict['authors'],
                publisher=metadata_dict['publisher'],
                published_date=metadata_dict['published_date'],
                isbn_13=isbn if len(isbn) == 13 else None,
                isbn_10=isbn if len(isbn) == 10 else None,
                confidence_score=self.confidence_adjustments['isbnlib_goom'],
                source='isbnlib_goom'
            )
            
        except Exception as e:
            self._handle_api_error('isbnlib_goom', e, isbn)
            return None

    def _fetch_brazilian_metadata(self, isbn: str) -> Optional[BookMetadata]:
        """Fetch metadata for other Brazilian publishers."""
        # Detect publisher from ISBN prefix
        publisher_info = None
        for pub_info in self.BRAZILIAN_PUBLISHERS.values():
            if any(isbn.startswith(prefix) for prefix in pub_info['prefixes']):
                publisher_info = pub_info
                break
                
        if not publisher_info:
            return None
            
        logging.info(f"Processing {publisher_info['name']} ISBN: {isbn}")
        
        # Try APIs in priority order
        for api_name in publisher_info['api_priority']:
            try:
                method = getattr(self, f'_fetch_{api_name}')
                metadata = method(isbn)
                
                if metadata:
                    # Force correct publisher and adjust confidence
                    metadata.publisher = publisher_info['name']
                    metadata.confidence_score = 0.95
                    
                    # Validate and cache
                    metadata_dict = asdict(metadata)
                    if self.validator.validate_metadata(metadata_dict, metadata.source, isbn):
                        self.cache.set(metadata_dict)
                        return metadata
                        
            except Exception as e:
                logging.error(f"Error with {api_name} for ISBN {isbn}: {str(e)}")
                continue
                
        return None

    def fetch_isbnlib_meta(self, isbn: str) -> Optional[BookMetadata]:
        """Fetch usando isbnlib.meta() com validação aprimorada."""
        try:
            import isbnlib
            metadata = isbnlib.meta(isbn)
            if not metadata:
                return None
                
            metadata_dict = {
                'title': metadata.get('Title', '').strip(),
                'authors': [a.strip() for a in metadata.get('Authors', [])],
                'publisher': metadata.get('Publisher', '').strip(),
                'published_date': metadata.get('Year', 'Unknown')
            }
            
            # Validação
            if not self.validator.validate_metadata(metadata_dict, 'isbnlib_meta', isbn=isbn):
                return None
                
            return BookMetadata(
                title=metadata_dict['title'],
                authors=metadata_dict['authors'],
                publisher=metadata_dict['publisher'],
                published_date=metadata_dict['published_date'],
                isbn_13=isbn if len(isbn) == 13 else None,
                isbn_10=isbn if len(isbn) == 10 else None,
                confidence_score=self.confidence_adjustments['isbnlib_meta'],
                source='isbnlib_meta'
            )
            
        except Exception as e:
            self._handle_api_error('isbnlib_meta', e, isbn)
            return None

    def _handle_api_error(self, api_name: str, error: Exception, isbn: str) -> None:
        """Tratamento melhorado de erros de API."""
        error_type = type(error).__name__
        error_msg = str(error)
        
        logger = logging.getLogger('metadata_fetcher')
        
        # Categoriza e registra o erro
        if isinstance(error, requests.exceptions.Timeout):
            logger.warning(f"{api_name} timeout for ISBN {isbn}: {error_msg}")
            self.metrics.add_error(api_name, 'timeout')
        elif isinstance(error, requests.exceptions.ConnectionError):
            logger.error(f"{api_name} connection error for ISBN {isbn}: {error_msg}")
            self.metrics.add_error(api_name, 'connection')
        elif isinstance(error, requests.exceptions.HTTPError):
            logger.error(f"{api_name} HTTP error for ISBN {isbn}: {error_msg}")
            self.metrics.add_error(api_name, 'http')
        else:
            logger.error(f"{api_name} unexpected error for ISBN {isbn}: {error_type} - {error_msg}")
            self.metrics.add_error(api_name, 'unexpected')
        
        # Registra métricas da falha
        self._log_api_metrics(api_name, False, 0.0)
        
        # Atualiza estatísticas para ajuste dinâmico
        stats = self.metrics.get_api_stats(api_name)
        if stats.get('success_rate', 0) < 30:  # Se taxa de sucesso muito baixa
            config = self.API_CONFIGS.get(api_name, {})
            config['retries'] = min(5, config.get('retries', 2) + 1)  # Aumenta retries
            config['backoff'] = min(4.0, config.get('backoff', 1.5) * 1.5)  # Aumenta backoff

    def _get_api_success_rate(self, api_name: str) -> float:
        """Calcula taxa de sucesso da API."""
        stats = self.metrics.get_api_stats(api_name)
        return stats.get('success_rate', 0.0)

    def _get_avg_response_time(self, api_name: str) -> float:
        """Calcula tempo médio de resposta da API."""
        stats = self.metrics.get_api_stats(api_name)
        return stats.get('avg_response_time', 0.0)

    def _log_api_metrics(self, api_name: str, success: bool, response_time: float):
        """Registra métricas de API."""
        # Atualiza métricas em memória
        self.metrics.add_metric(api_name, response_time, success)
        
        # Atualiza estatísticas de rate limiting
        self.rate_limiter.update_stats(api_name, success, response_time)
        
        # Log em caso de falha
        if not success:
            avg_time = self._get_avg_response_time(api_name)
            success_rate = self._get_api_success_rate(api_name)
            
            logging.warning(
                f'API call failed: {api_name}\n'
                f'Average response time: {avg_time:.2f}s\n'
                f'Success rate: {success_rate:.1f}%'
            )

    def _setup_logging(self):
        """Configura logging com níveis de detalhe diferentes."""
        # Logger principal
        logger = logging.getLogger('metadata_fetcher')
        logger.setLevel(logging.INFO)

        # Handler para arquivo
        file_handler = logging.FileHandler('metadata_fetcher.log')
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(file_handler)

        # Handler para console
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(console_handler)

    def _advanced_fallback(self, isbn: str, file_path: str = None) -> Optional[BookMetadata]:
        """Sistema avançado de fallback com tratamento especial para editoras conhecidas."""
        # Define estratégias baseadas no tipo de ISBN e nome do arquivo
        if file_path and ('hands-on' in file_path.lower() or 'packt' in file_path.lower()):
            strategies = [
                {
                    'name': 'packt_primary',
                    'apis': ['google_books', 'isbnlib_info', 'openlibrary'],
                    'min_confidence': 0.85,
                    'required_success': 1
                }
            ]
        elif isbn.startswith('97865'):  # Casa do Código
            strategies = [
                {
                    'name': 'casa_codigo',
                    'apis': ['google_books', 'openlibrary', 'worldcat'],
                    'min_confidence': 0.90,
                    'required_success': 1
                }
            ]
        elif isbn.startswith('97885'):  # Outras editoras brasileiras
            strategies = [
                {
                    'name': 'brazilian_reliable',
                    'apis': ['isbnlib_info', 'openlibrary', 'google_books'],
                    'min_confidence': 0.85,
                    'required_success': 1
                },
                {
                    'name': 'brazilian_alternatives',
                    'apis': ['worldcat', 'isbnlib_meta', 'isbnlib_editions'],
                    'min_confidence': 0.80,
                    'required_success': 1
                }
            ]
        else:  # Editoras internacionais
            strategies = [
                {
                    'name': 'primary',
                    'apis': ['isbnlib_info', 'google_books', 'openlibrary'],
                    'min_confidence': 0.90,
                    'required_success': 1
                },
                {
                    'name': 'secondary',
                    'apis': ['worldcat', 'isbnlib_meta', 'isbnlib_editions'],
                    'min_confidence': 0.85,
                    'required_success': 1
                }
            ]

        all_results = []
        tried_apis = set()
        
        for strategy in strategies:
            strategy_results = []
            
            # Filtra APIs já tentadas e habilitadas
            available_apis = [
                api for api in strategy['apis']
                if api not in tried_apis and
                self.API_CONFIGS.get(api, {}).get('enabled', True)
            ]
            
            for api_name in available_apis:
                tried_apis.add(api_name)
                
                try:
                    fetcher = getattr(self, f'fetch_{api_name}')
                    start_time = time.time()
                    metadata = fetcher(isbn)
                    elapsed = time.time() - start_time
                    
                    # Se demorar muito, reduz prioridade da API
                    if elapsed > 5:
                        self.API_CONFIGS[api_name]['timeout'] *= 0.8
                    
                    if metadata:
                        # Ajustes especiais por editora
                        if file_path and 'hands-on' in file_path.lower():
                            metadata.publisher = "Packt Publishing"
                            metadata.confidence_score = 0.95
                            return metadata
                        elif isbn.startswith('97865'):
                            metadata.publisher = "Casa do Código"
                            metadata.confidence_score = 0.95
                            return metadata
                        
                        # Ajusta confiança baseado no tempo de resposta
                        if elapsed < 1:
                            metadata.confidence_score += 0.05
                            
                        # Verifica variantes de ISBN
                        returned_isbn = metadata.isbn_13 or metadata.isbn_10
                        if returned_isbn and returned_isbn != isbn:
                            if self._validate_isbn_variant(isbn, returned_isbn):
                                metadata.confidence_score += 0.1
                                logging.info(f"ISBN variant accepted: {isbn} -> {returned_isbn}")
                            else:
                                continue
                                
                        strategy_results.append(metadata)
                        
                        # Retorna imediatamente se encontrar resultado muito bom
                        if metadata.confidence_score >= 0.95:
                            return metadata
                            
                except Exception as e:
                    self._handle_api_error(api_name, e, isbn)
                    # Desabilita temporariamente API com muitos erros
                    if self._get_api_error_rate(api_name) > 0.5:
                        self.API_CONFIGS[api_name]['enabled'] = False
                    continue
                    
            all_results.extend(strategy_results)
            
            # Se tem resultados suficientes com boa confiança
            if len(strategy_results) >= strategy['required_success']:
                best_result = max(strategy_results, key=lambda x: x.confidence_score)
                if best_result.confidence_score >= strategy['min_confidence']:
                    return best_result
                    
        # Tenta merge apenas se necessário e não for Casa do Código
        if all_results and not isbn.startswith('97865'):
            merged = self._merge_metadata(sorted(all_results, 
                                            key=lambda x: x.confidence_score, 
                                            reverse=True)[:3])
            if merged and merged.confidence_score >= 0.8:
                return merged
                
        # Se tem algum resultado, retorna o melhor
        return max(all_results, key=lambda x: x.confidence_score) if all_results else None

    def _get_best_apis(self, isbn: str) -> List[str]:
        """
        Determina a melhor ordem de APIs para tentar baseado no ISBN
        e histórico de performance.
        """
        # Inicializa scores
        api_scores = {}
        
        for api_name, config in self.API_CONFIGS.items():
            if not config.get('enabled', True):
                continue
                
            # Score base da API
            base_score = self.confidence_adjustments.get(api_name, 0.5)
            
            # Ajusta score baseado em performance
            stats = self.metrics.get_api_stats(api_name)
            if stats:
                success_rate = stats.get('success_rate', 0) / 100
                avg_time = stats.get('avg_response_time', 5.0)
                score = base_score * success_rate * (1 / avg_time)
            else:
                score = base_score
                
            # Boost para APIs específicas por região/editora
            if isbn.startswith(('97865', '97885')):  # ISBN brasileiro
                if api_name in ['cbl', 'mercado_editorial']:
                    score *= 2.0
            
            api_scores[api_name] = score
            
        # Retorna APIs ordenadas por score
        return sorted(api_scores.keys(), key=lambda x: api_scores[x], reverse=True)

    def _check_api_health(self, api_name: str) -> bool:
        """Verifica saúde da API e ajusta configurações."""
        stats = self.metrics.get_api_stats(api_name)
        
        # Se não tem dados suficientes, considera saudável
        if not stats or stats.get('total_calls', 0) < 10:
            return True
            
        success_rate = stats.get('success_rate', 0)
        avg_time = stats.get('avg_response_time', 0)
        
        # Ajusta configurações baseado na performance
        config = self.API_CONFIGS.get(api_name, {})
        
        if success_rate < 50:  # API com problemas
            config['timeout'] = min(30, config.get('timeout', 5) * 1.5)
            config['retries'] += 1
            logging.warning(f"API {api_name} health check: Poor performance detected. "
                        f"Success rate: {success_rate:.1f}%, Avg time: {avg_time:.2f}s")
            return False
            
        elif success_rate > 90 and avg_time < 2:  # API saudável
            config['timeout'] = max(3, config.get('timeout', 5) * 0.8)
            config['retries'] = max(2, config['retries'] - 1)
            return True
            
        return True

    def _process_isbn_response(self, isbn: str, metadata: Dict, source: str) -> Optional[BookMetadata]:
        """Processa resposta de API com melhor tratamento de variantes."""
        if not metadata:
            return None
            
        # Verifica ISBNs retornados
        returned_isbns = []
        if 'industryIdentifiers' in metadata:
            for identifier in metadata['industryIdentifiers']:
                if identifier['type'] in ['ISBN_13', 'ISBN_10']:
                    returned_isbns.append(identifier['identifier'])
        elif 'isbn_13' in metadata:
            returned_isbns.append(metadata['isbn_13'])
        elif 'isbn_10' in metadata:
            returned_isbns.append(metadata['isbn_10'])
            
        # Se encontrou variante válida
        valid_variant = False
        for returned_isbn in returned_isbns:
            if self._validate_isbn_variant(isbn, returned_isbn):
                valid_variant = True
                break
                
        if not valid_variant and returned_isbns:
            logging.warning(f"ISBN variant mismatch: requested {isbn}, got {returned_isbns}")
            return None
            
        # Processa metadados
        try:
            metadata_dict = {
                'title': metadata.get('title', '').strip(),
                'authors': [a.strip() for a in metadata.get('authors', [])],
                'publisher': metadata.get('publisher', '').strip(),
                'published_date': metadata.get('published_date', 'Unknown'),
                'isbn_13': isbn if len(isbn) == 13 else None,
                'isbn_10': isbn if len(isbn) == 10 else None,
                'confidence_score': self.confidence_adjustments.get(source, 0.5),
                'source': source
            }
            
            # Validação final
            if not self.validator.validate_metadata(metadata_dict, source, isbn):
                return None
                
            return BookMetadata(**metadata_dict)
            
        except Exception as e:
            logging.error(f"Error processing metadata from {source}: {str(e)}")
            return None

    def _validate_isbn_variant(self, original_isbn: str, variant_isbn: str) -> bool:
        """Validação aprimorada de variantes de ISBN."""
        if not original_isbn or not variant_isbn:
            return False
            
        # Remove hífens e espaços
        original = ''.join(c for c in original_isbn if c.isdigit())
        variant = ''.join(c for c in variant_isbn if c.isdigit())
        
        # Se são idênticos
        if original == variant:
            return True
            
        try:
            import isbnlib
            
            # Converte ambos para ISBN-13 para comparação
            original_13 = isbnlib.to_isbn13(original) if len(original) == 10 else original
            variant_13 = isbnlib.to_isbn13(variant) if len(variant) == 10 else variant
            
            if original_13 == variant_13:
                return True
                
            # Verifica edições diferentes
            try:
                editions = isbnlib.editions(original_13) or []
                if variant_13 in editions:
                    return True
            except:
                pass
                
            # Compara prefixos (publisher)
            if original_13 and variant_13:
                # Verifica mais dígitos para maior precisão
                if original_13[:9] == variant_13[:9]:  # Compara até o nível da edição
                    return True
                    
        except Exception as e:
            logging.debug(f"Error in ISBN variant validation: {str(e)}")
            # Fallback para comparação básica se isbnlib falhar
            if original[:7] == variant[:7]:  # Mesmo prefixo de editora
                return True
                
        return False

    def _get_api_error_rate(self, api_name: str) -> float:
        """Calcula taxa de erro da API nas últimas chamadas."""
        stats = self.metrics.get_api_stats(api_name)
        if not stats or stats.get('total_calls', 0) == 0:
            return 0.0
        return 1.0 - (stats.get('success_rate', 0) / 100.0)

    def _merge_metadata(self, results: List[BookMetadata]) -> Optional[BookMetadata]:
        """Combina resultados de múltiplas fontes."""
        if not results:
            return None
            
        # Usa o melhor resultado como base
        best = results[0]
        merged = asdict(best)
        
        # Combina informações de outras fontes
        for other in results[1:]:
            # Usa título mais longo se disponível
            if len(other.title) > len(merged['title']):
                merged['title'] = other.title
                
            # Combina autores únicos
            merged['authors'] = list(set(merged['authors'] + other.authors))
            
            # Usa data mais específica
            if len(other.published_date) > len(merged['published_date']):
                merged['published_date'] = other.published_date
                
            # Aumenta confiança se fontes concordam
            if (other.title.lower() == best.title.lower() or 
                set(other.authors) == set(best.authors)):
                merged['confidence_score'] = min(1.0, 
                    merged['confidence_score'] + 0.05)
                
        merged['source'] = f"{best.source}+merged"
        return BookMetadata(**merged)

    def _update_api_priorities(self):
        """Atualiza prioridades das APIs baseado em performance."""
        api_scores = {}
        
        for api_name in self.API_CONFIGS:
            if not self.API_CONFIGS[api_name].get('enabled', True):
                continue
                
            stats = self.metrics.get_api_stats(api_name)
            if not stats:
                continue
                
            # Calcula score baseado em múltiplos fatores
            success_rate = stats.get('success_rate', 0)
            avg_time = stats.get('avg_response_time', float('inf'))
            error_rate = len(stats.get('error_types', {}))
            
            score = (success_rate / 100.0) * (1.0 / max(1, avg_time)) * (1.0 / (1 + error_rate))
            api_scores[api_name] = score
        
        # Atualiza ordem de tentativa das APIs
        self.api_priorities = sorted(
            api_scores.keys(),
            key=lambda x: api_scores[x],
            reverse=True
        )

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
        
        # Configure reports directory
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
        """Process single PDF file with proper statistics tracking."""
        start_time = time.time()
        logging.info(f"Processing: {pdf_path}")
        
        # Inicializa estruturas de estatísticas se não existirem
        if 'processed_files' not in runtime_stats:
            runtime_stats['processed_files'] = []
        if 'failure_details' not in runtime_stats:
            runtime_stats['failure_details'] = {}
        if 'api_errors' not in runtime_stats:
            runtime_stats['api_errors'] = {}
        if 'isbn_extraction_failed' not in runtime_stats:
            runtime_stats['isbn_extraction_failed'] = []
        if 'api_failures' not in runtime_stats:
            runtime_stats['api_failures'] = []
        if 'processing_times' not in runtime_stats:
            runtime_stats['processing_times'] = []
        
        # Registra arquivo processado
        runtime_stats['processed_files'].append(pdf_path)
        
        # Inicializa detalhes com todas as chaves necessárias
        runtime_stats['failure_details'][pdf_path] = {
            'api_attempts': [],        # Lista de APIs tentadas
            'status': '',             # Status atual do processamento
            'extraction_methods': [],  # Métodos de extração tentados
            'found_isbns': [],        # ISBNs encontrados
            'detected_publisher': '',  # Editora detectada
            'text_sample': '',        # Amostra do texto extraído
            'errors': []              # Erros encontrados
        }
        
        # Inicializa lista de erros de API para este arquivo
        runtime_stats['api_errors'][pdf_path] = []
        
        # Obtém referência para os detalhes deste arquivo
        details = runtime_stats['failure_details'][pdf_path]
        
        try:
            # Extract text from PDF
            text, extraction_methods = self.pdf_processor.extract_text_from_pdf(pdf_path)
            details['extraction_methods'] = extraction_methods
            
            if not text:
                runtime_stats['isbn_extraction_failed'].append(pdf_path)
                details['status'] = 'Failed to extract text'
                return None
            
            # Clean text for sample
            clean_text = re.sub(r'\n\s*\n', '\n', text[:500])
            details['text_sample'] = clean_text
            
            # Extract PDF metadata
            pdf_metadata = self.pdf_processor.extract_metadata_from_pdf(pdf_path)
            
            # Find ISBNs
            isbns = self.isbn_extractor.extract_from_text(text)
            if pdf_metadata and pdf_metadata.get('ISBN'):
                isbns.add(self.isbn_extractor._normalize_isbn(pdf_metadata['ISBN']))
            
            if not isbns:
                runtime_stats['isbn_extraction_failed'].append(pdf_path)
                details['status'] = 'No ISBN found in file'
                return None
            
            details['found_isbns'] = list(isbns)
            
            # Check for Casa do Código ISBNs
            casa_codigo_isbns = [isbn for isbn in isbns if isbn.startswith('97865')]
            if casa_codigo_isbns:
                details['detected_publisher'] = 'Casa do Código'
                primary_isbn = casa_codigo_isbns[0]
                logging.info(f"Using primary Casa do Código ISBN: {primary_isbn}")
                metadata = self._process_casa_codigo_isbn(primary_isbn, pdf_path, runtime_stats, details)
                if metadata:
                    runtime_stats['processing_times'].append(time.time() - start_time)
                    details['status'] = 'Success'
                    return metadata
            
            # Try each ISBN until success
            for isbn in sorted(isbns):
                try:
                    metadata = self.metadata_fetcher.fetch_metadata(isbn)
                    if metadata:
                        # Registra tentativa bem-sucedida
                        details['api_attempts'].append(metadata.source)
                        metadata.file_path = str(pdf_path)
                        
                        # Adjust metadata for specific publishers
                        metadata = self._adjust_publisher_metadata(metadata, pdf_path)
                        
                        runtime_stats['processing_times'].append(time.time() - start_time)
                        details['status'] = 'Success'
                        return metadata
                        
                except Exception as e:
                    error_msg = f"ISBN {isbn}: {str(e)}"
                    runtime_stats['api_errors'][pdf_path].append(error_msg)
                    details['errors'].append(error_msg)
                    logging.error(error_msg)
                    continue
            
            # Se chegou aqui, todas as tentativas falharam
            runtime_stats['api_failures'].append(pdf_path)
            details['status'] = 'All API attempts failed'
            runtime_stats['processing_times'].append(time.time() - start_time)
            return None
            
        except Exception as e:
            error_msg = f"{pdf_path}: {str(e)}"
            runtime_stats['api_errors'][pdf_path].append(error_msg)
            details['errors'].append(error_msg)
            details['status'] = f'Error: {str(e)}'
            logging.error(error_msg)
            runtime_stats['processing_times'].append(time.time() - start_time)
            return None

    def _adjust_publisher_metadata(self, metadata: BookMetadata, file_path: str) -> BookMetadata:
        """Adjust metadata based on publisher-specific rules."""
        file_lower = file_path.lower()
        
        if 'hands-on' in file_lower or 'packt' in file_lower:
            metadata.publisher = "Packt Publishing"
            metadata.confidence_score = 0.95
        elif metadata.isbn_13 and metadata.isbn_13.startswith('97865'):
            metadata.publisher = "Casa do Código"
            metadata.confidence_score = 0.95
        elif metadata.isbn_13 and metadata.isbn_13.startswith('97885'):
            # Check for other Brazilian publishers
            if any(term in file_lower for term in ['novatec', 'alta books']):
                publisher_map = {
                    'novatec': 'Novatec Editora',
                    'alta books': 'Alta Books'
                }
                for term, pub_name in publisher_map.items():
                    if term in file_lower:
                        metadata.publisher = pub_name
                        metadata.confidence_score = 0.95
                        break
        
        return metadata

    def _process_casa_codigo_isbn(self, isbn: str, pdf_path: str, runtime_stats: Dict, details: Dict) -> Optional[BookMetadata]:
        """Handle Casa do Código ISBN processing."""
        logging.info(f"Detected Casa do Código ISBN: {isbn}")
        
        try:
            metadata = self.metadata_fetcher.fetch_metadata(isbn)
            if metadata:
                details['api_attempts'].append(metadata.source)
                metadata.publisher = "Casa do Código"
                metadata.confidence_score = 0.95
                metadata.file_path = str(pdf_path)
                details['status'] = 'Success'
                return metadata
        except Exception as e:
            error_msg = f"ISBN {isbn}: {str(e)}"
            runtime_stats['api_errors'][pdf_path].append(error_msg)
            logging.error(error_msg)
        
        return None

    def _fetch_with_publisher_priority(self, isbn: str, publisher_info: Dict) -> Optional[BookMetadata]:
        """Busca metadados usando prioridade específica da editora."""
        logging.info(f"Tentando busca prioritária para ISBN {isbn} da editora {publisher_info['name']}")
        
        errors = []
        for api_name in publisher_info['api_priority']:
            try:
                logging.info(f"Tentando API {api_name}")
                
                if api_name == 'google_books_br':
                    metadata = self.fetch_google_books(isbn, country='BR', lang='pt-BR')
                else:
                    fetcher = getattr(self, f'fetch_{api_name}')
                    metadata = fetcher(isbn)
                
                if metadata:
                    # Verifica se é da editora esperada
                    if any(re.search(pattern, metadata.publisher.lower()) 
                        for pattern in publisher_info['patterns']):
                        metadata.confidence_score += 0.2
                        metadata.source = api_name
                        return metadata
                        
            except Exception as e:
                error_msg = f"Erro em {api_name}: {str(e)}"
                logging.error(error_msg)
                errors.append(error_msg)
                continue
                
        logging.error(f"Falha em todas as APIs para ISBN {isbn}:\n" + "\n".join(errors))
        return None

    def _detect_brazilian_publisher(self, isbn: str, text: str = None) -> Optional[Dict]:
        """Detecta editora brasileira baseado no ISBN e texto."""
        BRAZILIAN_PUBLISHERS = {
            'casa_do_codigo': {
                'name': 'Casa do Código',
                'prefixes': ['97865'],
                'patterns': [
                    r'casa\s+do\s+c[óo]digo',
                    r'CDC',
                    r'casadocodigo'
                ],
                'api_priority': ['cbl', 'mercado_editorial', 'google_books_br', 'openlibrary']
            },
            'novatec': {
                'name': 'Novatec',
                'prefixes': ['97885'],
                'patterns': [r'novatec'],
                'api_priority': ['cbl', 'mercado_editorial', 'google_books_br', 'openlibrary']
            },
            'alta_books': {
                'name': 'Alta Books',
                'prefixes': ['97885'],
                'patterns': [r'alta\s+books'],
                'api_priority': ['cbl', 'mercado_editorial', 'google_books_br', 'openlibrary']
            }
        }
        
        isbn_prefix = isbn[:5] if len(isbn) >= 5 else ''
        
        for pub_info in BRAZILIAN_PUBLISHERS.values():
            # Verifica prefixo ISBN
            if isbn_prefix in pub_info['prefixes']:
                return pub_info
                
            # Se tiver texto, verifica padrões
            if text:
                text_lower = text.lower()
                if any(re.search(pattern, text_lower) for pattern in pub_info['patterns']):
                    return pub_info
                    
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

class APIRateLimiter:
    def __init__(self):
        self.last_calls = defaultdict(float)
        self.limits = {
            'openlibrary': {'calls': 1, 'period': 1},
            'loc': {'calls': 2, 'period': 1},
            'google_books': {'calls': 5, 'period': 1},
            'internet_archive': {'calls': 1, 'period': 2},
            # Adiciona limites para as outras APIs
            'cbl': {'calls': 2, 'period': 1},
            'mercado_editorial': {'calls': 2, 'period': 1},
            'zbib': {'calls': 2, 'period': 1},
            'mybib': {'calls': 2, 'period': 1},
            'crossref': {'calls': 3, 'period': 1},
            'ebook_de': {'calls': 2, 'period': 1}
        }
        self.cache = {}

    def should_wait(self, api_name: str) -> float:
        """Returns wait time needed to respect rate limit."""
        if api_name not in self.limits:
            return 0
            
        now = time.time()
        last_call = self.last_calls.get(api_name, 0)
        limit = self.limits[api_name]
        
        wait_time = max(0, (last_call + limit['period']) - now)
        return wait_time
        
    def update_last_call(self, api_name: str):
        """Updates timestamp of last call."""
        self.last_calls[api_name] = time.time()

class RateLimitCache:
    """Cache com estatísticas de performance para rate limiting."""
    def __init__(self):
        self.cache = {}
        self.performance_stats = defaultdict(list)
        self.last_calls = defaultdict(float)
        
    def should_wait(self, api_name: str, base_delay: float = 1.0) -> float:
        """Determina tempo de espera baseado no histórico."""
        now = time.time()
        if api_name not in self.cache:
            return 0
            
        last_call, failures, avg_time = self.cache[api_name]
        dynamic_delay = base_delay * (1 + (failures * 0.5))
        
        wait_time = max(0, last_call + dynamic_delay - now)
        return wait_time
        
    def update_stats(self, api_name: str, success: bool, response_time: float):
        """Atualiza estatísticas de performance."""
        now = time.time()
        current_failures = self.cache.get(api_name, (0, 0, 0))[1]
        failures = current_failures if success else current_failures + 1
        
        self.performance_stats[api_name].append(response_time)
        # Mantém apenas últimas 100 medições
        if len(self.performance_stats[api_name]) > 100:
            self.performance_stats[api_name] = self.performance_stats[api_name][-100:]
            
        avg_time = statistics.mean(self.performance_stats[api_name][-10:])
        self.cache[api_name] = (now, failures, avg_time)
        self.last_calls[api_name] = now
        
    def get_performance_metrics(self, api_name: str) -> Dict[str, float]:
        """Retorna métricas de performance para uma API."""
        if api_name not in self.performance_stats:
            return {
                'avg_time': 0.0,
                'success_rate': 0.0,
                'error_rate': 0.0
            }
            
        stats = self.performance_stats[api_name]
        _, failures, _ = self.cache.get(api_name, (0, 0, 0))
        
        total_calls = len(stats)
        if total_calls == 0:
            return {
                'avg_time': 0.0,
                'success_rate': 0.0,
                'error_rate': 0.0
            }
            
        return {
            'avg_time': statistics.mean(stats),
            'success_rate': ((total_calls - failures) / total_calls) * 100,
            'error_rate': (failures / total_calls) * 100
        }

class MetadataValidator:
    """Validação centralizada de metadados."""
    def __init__(self):
        self.publisher_patterns = {
            'springer': [r'springer', r'apress'],
            'oreilly': [r"o'reilly", r'oreilly'],
            'packt': [r'packt'],
            'manning': [r'manning'],
            'casa_do_codigo': [r'casa\s+do\s+c[oó]digo'],
            'novatec': [r'novatec'],
            'alta_books': [r'alta\s+books']
        }
    

    def validate_metadata(self, metadata: Dict[str, Any], source: str, isbn: str = None, source_api: str = None) -> bool:
        """Validação centralizada de metadados."""
        # Valida campos obrigatórios
        if not all(metadata.get(field) for field in ['title', 'authors', 'publisher']):
            return False
                
        # Valida tamanho do título
        if len(metadata['title'].strip()) < 3:
            return False
                
        # Valida autores
        if not any(len(a.strip()) > 0 for a in metadata['authors']):
            return False
                
        # Valida editora
        if len(metadata['publisher'].strip()) < 2:
            return False
        
        # Valida data
        if metadata.get('published_date'):
            if not self._validate_date(metadata['published_date']):
                metadata['published_date'] = 'Unknown'

        # Se tiver source_api, valida específico da API
        if source_api:
            return self._validate_source_specific(metadata, source_api, isbn)
                
        return True

    def _validate_basic_fields(self, metadata: Dict) -> bool:
        """Validação de campos básicos."""
        required_fields = {'title', 'authors', 'publisher', 'published_date'}
        return all(metadata.get(field) for field in required_fields)
        
    def _validate_date(self, date: str) -> bool:
            """Validação aprimorada de datas."""
            if not date or date == 'Unknown':
                return False
                
            # Aceita anos (YYYY)
            if re.match(r'^\d{4}$', date):
                year = int(date)
                return 1900 <= year <= datetime.now().year
                
            # Aceita datas completas (YYYY-MM-DD)
            try:
                parsed_date = datetime.strptime(date, '%Y-%m-%d')
                return 1900 <= parsed_date.year <= datetime.now().year
            except ValueError:
                pass
                
            # Aceita mês/ano (YYYY-MM)
            try:
                parsed_date = datetime.strptime(date, '%Y-%m')
                return 1900 <= parsed_date.year <= datetime.now().year
            except ValueError:
                return False

    def _validate_publisher(self, publisher: str, source: str) -> bool:
        """Validação de editora."""
        if source in self.publisher_patterns:
            patterns = self.publisher_patterns[source]
            publisher_lower = publisher.lower()
            return any(re.search(pattern, publisher_lower) for pattern in patterns)
        return True
            
    def _validate_title_and_authors(self, title: str, authors: List[str]) -> bool:
        """Validação de título e autores."""
        if not title or len(title.strip()) < 3 or len(title) > 300:
            return False
            
        if not authors or all(not a.strip() for a in authors):
            return False
            
        return True
        
    def _validate_source_specific(self, metadata: Dict, source: str, isbn: str) -> bool:
        """Validação específica por fonte."""
        # Implementar validações específicas por fonte se necessário
        return True

class ErrorHandler:
    def __init__(self):
        self.error_counts = defaultdict(Counter)
        self.last_errors = defaultdict(dict)
        self.error_thresholds = {
            'timeout': 3,
            'connection': 5,
            'api': 3,
            'validation': 2
        }

    def handle_api_error(self, api_name: str, error: Exception, isbn: str) -> bool:
        """
        Handle API errors with sophisticated retry logic.
        Returns True if should retry, False otherwise.
        """
        error_type = type(error).__name__
        error_msg = str(error)
        
        # Categorize error
        if isinstance(error, requests.exceptions.Timeout):
            category = 'timeout'
        elif isinstance(error, requests.exceptions.ConnectionError):
            category = 'connection'
        elif isinstance(error, requests.exceptions.HTTPError):
            category = 'api'
        else:
            category = 'unknown'

        # Update error counts
        self.error_counts[api_name][category] += 1
        self.last_errors[api_name][isbn] = {
            'error': error_msg,
            'timestamp': time.time(),
            'category': category
        }

        # Log error with context
        logging.error(
            f"API Error in {api_name} for ISBN {isbn}\n"
            f"Category: {category}\n"
            f"Error: {error_msg}\n"
            f"Count: {self.error_counts[api_name][category]}"
        )

        # Check if should retry based on error category and count
        threshold = self.error_thresholds.get(category, 3)
        if self.error_counts[api_name][category] >= threshold:
            logging.warning(
                f"Error threshold reached for {api_name} ({category}). "
                f"Temporarily disabling API."
            )
            return False

        return True

    def check_api_health(self, api_name: str) -> bool:
        """Check if API is healthy enough to use."""
        total_errors = sum(self.error_counts[api_name].values())
        recent_errors = sum(
            1 for error in self.last_errors[api_name].values()
            if time.time() - error['timestamp'] < 300  # last 5 minutes
        )

        if total_errors > 10 or recent_errors > 5:
            logging.warning(f"API {api_name} shows poor health. Consider alternative.")
            return False
        return True

    def reset_error_counts(self, api_name: str = None):
        """Reset error counts for specific or all APIs."""
        if api_name:
            self.error_counts[api_name].clear()
            self.last_errors[api_name].clear()
        else:
            self.error_counts.clear()
            self.last_errors.clear()

    def get_api_status(self, api_name: str) -> Dict:
        """Get detailed API status."""
        return {
            'error_counts': dict(self.error_counts[api_name]),
            'recent_errors': sum(
                1 for error in self.last_errors[api_name].values()
                if time.time() - error['timestamp'] < 300
            ),
            'last_error': next(iter(self.last_errors[api_name].values()), None)
        }

class MetricsCollector:
    """Coleta e análise de métricas."""
    def __init__(self):
        self.metrics = defaultdict(list)
        self.errors = defaultdict(Counter)
        
    def add_metric(self, api_name: str, response_time: float, success: bool):
        self.metrics[api_name].append({
            'timestamp': time.time(),
            'response_time': response_time,
            'success': success
        })
        
    def add_error(self, api_name: str, error_type: str):
        self.errors[api_name][error_type] += 1
        
    def get_api_stats(self, api_name: str) -> Dict:
        """Retorna estatísticas para uma API."""
        if api_name not in self.metrics:
            return {}
            
        metrics = self.metrics[api_name]
        recent_metrics = [m for m in metrics if time.time() - m['timestamp'] < 3600]
        
        if not recent_metrics:
            return {}
            
        success_count = sum(1 for m in recent_metrics if m['success'])
        
        return {
            'total_calls': len(recent_metrics),
            'success_rate': (success_count / len(recent_metrics)) * 100,
            'avg_response_time': statistics.mean(m['response_time'] for m in recent_metrics),
            'error_types': dict(self.errors[api_name])
        }
        
    def get_overall_stats(self) -> Dict:
        """Retorna estatísticas gerais."""
        stats = {}
        for api_name in self.metrics:
            stats[api_name] = self.get_api_stats(api_name)
        return stats



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