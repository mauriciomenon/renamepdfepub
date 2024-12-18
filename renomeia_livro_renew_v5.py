# TO DO Remover estas importações
# from pdfminer.high_level import extract_text as pdfminer_extract
# import pytesseract
# from pdf2image import convert_from_path

# Standard Library Imports
import argparse
import functools
import json
import textwrap
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
import logging
import os
import re
import shutil
import sqlite3
import statistics
import sys
import time
import traceback
import unicodedata
import warnings
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from rich.progress import (
    Progress,
    TextColumn,
    BarColumn,
    SpinnerColumn,
    TimeElapsedColumn,
)
from concurrent import futures
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from urllib.parse import quote

# Third-party Imports: HTTP and API Related
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tqdm import tqdm

# Third-party Imports: PDF Processing
import PyPDF2
import pdfplumber
from pdf2image import convert_from_path
from pdfminer.high_level import extract_text as pdfminer_extract
import pytesseract

# Third-party Imports: E-book Processing
from bs4 import BeautifulSoup
from ebooklib import epub, ITEM_DOCUMENT
import mobi

# Third-party Imports: Data Visualization
import plotly.graph_objects as go

# Configure warnings
warnings.filterwarnings("ignore", category=UserWarning, module="ebooklib.epub")


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
            self.logger.debug("pdfplumber não está instalado. Usando alternativas.")

        # Verifica pdfminer
        try:
            from pdfminer.high_level import extract_text
            self.available_extractors['pdfminer'] = True
        except ImportError:
            self.logger.debug("pdfminer.six não está instalado. Usando alternativas.")

        # Verifica Tesseract
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            self.available_extractors['tesseract'] = True
        except:
            self.logger.debug("Tesseract OCR não está instalado/configurado.")

        # Verifica pdf2image
        try:
            import pdf2image
            self.available_extractors['pdf2image'] = True
        except ImportError:
            self.logger.debug("pdf2image não está instalado.")

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

NORMALIZED_PUBLISHERS = {
    # O'Reilly variants
    "O'REILLY": "OReilly",
    "O'REILLY MEDIA": "OReilly",
    "O'REILLY PUBLISHING": "OReilly",
    "OREILLY": "OReilly",
    
    # Manning variants
    "MANNING PUBLICATIONS": "Manning",
    "MANNING PRESS": "Manning",
    
    # Packt variants
    "PACKT PUBLISHING": "Packt",
    "PACKT PUB": "Packt",
    
    # Brazilian publishers
    "CASA DO CÓDIGO": "Casa do Codigo",
    "CDC": "Casa do Codigo",
    "CASADOCODIGO": "Casa do Codigo",
    
    "NOVATEC EDITORA": "Novatec",
    "EDITORA NOVATEC": "Novatec",
    
    "ALTA BOOKS EDITORA": "Alta Books",
    "ALTABOOKS": "Alta Books"
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
    file_paths: Optional[List[str]] = None  # Nova propriedade para múltiplos arquivos
    formats: Optional[List[str]] = None     # Nova propriedade para formatos
    
class MetadataCache:
    """
    Maintains a SQLite cache for book metadata with proper schema management 
    and error handling.
    """
    def __init__(self, db_path: str = "metadata_cache.db"):
        """
        Initialize metadata cache with database connection.
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_logging() 
        
        # If database exists and has issues, remove it
        if Path(db_path).exists():
            try:
                conn = sqlite3.connect(db_path)
                conn.execute("SELECT * FROM metadata_cache LIMIT 1")
                conn.close()
            except sqlite3.Error:
                self.logger.info(f"Removing corrupted database: {db_path}")
                os.remove(db_path)
        
        self._init_db()
        self._check_and_update_schema()

    def _init_logging(self):
        """Initialize logging configuration."""
        self.logger = logging.getLogger('metadata_cache')  # Use o nome específico da classe
        self.logger.setLevel(logging.DEBUG)  # Nível detalhado para o arquivo
        
        if not self.logger.handlers:
            # File handler - captura tudo para o arquivo
            file_handler = logging.FileHandler('metadata_cache.log')
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            ))
            file_handler.setLevel(logging.DEBUG)
            
            # Console handler - apenas warnings e erros
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(
                '%(levelname)s - %(message)s'
            ))
            console_handler.setLevel(logging.WARNING)
            
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)

    def _init_db(self):
        """Initialize database with required schema."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Create base table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS metadata_cache (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        isbn_10 TEXT,
                        isbn_13 TEXT,
                        title TEXT NOT NULL,
                        authors TEXT NOT NULL,
                        publisher TEXT,
                        published_date TEXT,
                        confidence_score REAL DEFAULT 0.0,
                        source TEXT,
                        file_path TEXT,
                        raw_json TEXT,
                        timestamp INTEGER DEFAULT (strftime('%s', 'now'))
                    )
                """)
                
                # Verify table exists and has correct structure
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(metadata_cache)")
                columns = [row[1] for row in cursor.fetchall()]
                
                if 'isbn_10' not in columns or 'isbn_13' not in columns:
                    raise sqlite3.Error("Table creation failed - missing required columns")

                # Only create indices if columns exist
                if 'isbn_10' in columns and 'isbn_13' in columns:
                    conn.execute("DROP INDEX IF EXISTS idx_isbn")  # Remove old index if exists
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_isbn_10 ON metadata_cache(isbn_10)")
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_isbn_13 ON metadata_cache(isbn_13)")

                self.logger.info("Database initialized successfully with schema verified")
                
        except sqlite3.Error as e:
            self.logger.error(f"Database initialization error: {str(e)}")
            # Delete database if initialization fails
            if Path(self.db_path).exists():
                os.remove(self.db_path)
            raise

    def _check_and_update_schema(self):
        """Check for missing columns and add them if necessary."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Verify table exists
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='metadata_cache'")
                if not cursor.fetchone():
                    raise sqlite3.Error("metadata_cache table does not exist")

                # Get current columns
                cursor.execute("PRAGMA table_info(metadata_cache)")
                columns = {row[1] for row in cursor.fetchall()}

                # Add missing columns
                if 'error_count' not in columns:
                    conn.execute("ALTER TABLE metadata_cache ADD COLUMN error_count INTEGER DEFAULT 0")
                if 'last_error' not in columns:
                    conn.execute("ALTER TABLE metadata_cache ADD COLUMN last_error TEXT")
                
                self.logger.info("Schema verification completed successfully")
        except sqlite3.Error as e:
            self.logger.error(f"Schema verification error: {str(e)}")
            raise
        
    def get_all(self) -> List[Dict]:
        """Return all records from cache."""
        try:
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
                
        except sqlite3.Error as e:
            self.logger.error(f"Error retrieving all metadata: {str(e)}")
            return []

    def get(self, isbn: str) -> Optional[Dict]:
        """
        Get metadata from cache with improved error handling.
        
        Args:
            isbn: ISBN to look up (ISBN-10 or ISBN-13)
            
        Returns:
            Dict with metadata if found, None otherwise
        """
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
                            self.logger.warning(f"Invalid JSON in cache for ISBN {isbn}")
                    
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
            self.logger.error(f"Cache retrieval error for ISBN {isbn}: {str(e)}")
            return None
            
        return None


    def set(self, metadata: Dict):
        """
        Save metadata to cache with validation.
        
        Args:
            metadata: Dictionary containing book metadata
        """
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
            self.logger.error(f"Cache storage error: {str(e)}")
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
                    self.logger.error(f"Erro ao atualizar metadados para ISBN {isbn}: {str(e)}")
                    continue
            
            self.logger.info(f"Rescan concluído. {updated_count} registros atualizados.")
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
            self.logger.error(f"Error updating error count for ISBN {isbn}: {str(e)}")


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

    def get_connection():
        """Get SQLite connection with optimal settings."""
        conn = sqlite3.connect("metadata_cache.db")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

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
        self._init_logging()
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

    def _init_logging(self):
        """Initialize logging configuration."""
        self.logger = logging.getLogger('api_handler')  # Use o nome específico da classe
        self.logger.setLevel(logging.DEBUG)  # Nível detalhado para o arquivo
        
        if not self.logger.handlers:
            # File handler - captura tudo para o arquivo
            file_handler = logging.FileHandler('api_handler.log')
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            ))
            file_handler.setLevel(logging.DEBUG)
            
            # Console handler - apenas warnings e erros
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(
                '%(levelname)s - %(message)s'
            ))
            console_handler.setLevel(logging.WARNING)
            
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)

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
        self._init_logging()
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

    def _init_logging(self):
        """Initialize logging configuration."""
        self.logger = logging.getLogger('isbn_extractor')  # Use o nome específico da classe
        self.logger.setLevel(logging.DEBUG)  # Nível detalhado para o arquivo
        
        if not self.logger.handlers:
            # File handler - captura tudo para o arquivo
            file_handler = logging.FileHandler('isbn_extractor.log')
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            ))
            file_handler.setLevel(logging.DEBUG)
            
            # Console handler - apenas warnings e erros
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(
                '%(levelname)s - %(message)s'
            ))
            console_handler.setLevel(logging.WARNING)
            
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)

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

    def _extract_info_from_epub(self, epub_path: str) -> Dict:
        """Extração mais robusta de metadados EPUB."""
        try:
            book = epub.read_epub(epub_path)
            metadata = {
                "Year": str(book.get_metadata("DC", "date")[0][0])[:4] if book.get_metadata("DC", "date") else "Unknown",
                "ISBN": str(book.get_metadata("DC", "identifier")[0][0]) if book.get_metadata("DC", "identifier") else "Unknown",
                "Author": ", ".join([str(author[0]) for author in book.get_metadata("DC", "creator")]) if book.get_metadata("DC", "creator") else "Unknown",
                "Publisher": str(book.get_metadata("DC", "publisher")[0][0]) if book.get_metadata("DC", "publisher") else "Unknown",
                "Title": str(book.get_metadata("DC", "title")[0][0]) if book.get_metadata("DC", "title") else "Unknown",
            }
            return metadata
        except Exception as e:
            self.logger.debug(f"Erro ao extrair metadados EPUB: {str(e)}")
            return {}

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
            self.logger.debug(f"Erro ao extrair metadados do PDF: {str(e)}")
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
                        self.logger.debug(f"Erro ao processar match: {str(e)}")
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
                self.logger.error(f"Erro ao extrair texto de PDF Packt: {str(e)}")
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
        self._init_logging()
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

    def _init_logging(self):
        """Initialize logging configuration."""
        self.logger = logging.getLogger('metadata_fetcher')  # Use o nome específico da classe
        self.logger.setLevel(logging.DEBUG)  # Nível detalhado para o arquivo
        
        if not self.logger.handlers:
            # File handler - captura tudo para o arquivo
            file_handler = logging.FileHandler('metadata_fetcher.log')
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            ))
            file_handler.setLevel(logging.DEBUG)
            
            # Console handler - apenas warnings e erros
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(
                '%(levelname)s - %(message)s'
            ))
            console_handler.setLevel(logging.WARNING)
            
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)

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
        """
        Busca metadados de um livro usando múltiplas fontes com sistema otimizado 
        de retentativas e fallback.
        
        Args:
            isbn: ISBN do livro para buscar metadados
            
        Returns:
            BookMetadata opcional com os metadados encontrados
        """
        # Verifica cache primeiro
        cached = self.cache.get(isbn)
        if cached:
            return BookMetadata(**cached)

        # Configurações de retentativa
        base_timeout = 5  # Timeout inicial em segundos
        max_retries = 3   # Número máximo de tentativas por API
        backoff_factor = 1.5  # Fator de aumento do timeout entre tentativas
        
        # Define grupos de APIs por prioridade e confiabilidade
        api_groups = [
            {
                'name': 'primary',
                'apis': [
                    ('google_books', self.fetch_google_books),
                    ('isbnlib_desc', self.fetch_isbnlib_desc),
                    ('isbnlib_info', self.fetch_isbnlib_info)
                ],
                'min_confidence': 0.9,
                'timeout': base_timeout
            },
            {
                'name': 'secondary',
                'apis': [
                    ('isbnlib_goom', self.fetch_isbnlib_goom),
                    ('isbnlib_meta', self.fetch_isbnlib_meta),
                ],
                'min_confidence': 0.8,
                'timeout': base_timeout * 1.5
            },
            {
                'name': 'fallback',
                'apis': [
                    ('loc', self.fetch_loc),
                    ('isbnlib_default', self.fetch_isbnlib_default),
                    ('openlibrary', self.fetch_openlibrary),
                ],
                'min_confidence': 0.7,
                'timeout': base_timeout * 2
            }
        ]

        # Para editoras brasileiras, ajusta a ordem das APIs
        if isbn.startswith(('97865', '97885')):  # ISBNs brasileiros
            brazilian_apis = [
                ('mercado_editorial', self.fetch_mercado_editorial),
                ('google_books_br', self.fetch_google_books_br),    
                # ('cbl', self.fetch_cbl),
            ]
            api_groups[0]['apis'] = brazilian_apis + api_groups[0]['apis']

        all_results = []
        tried_apis = set()
        errors = defaultdict(list)

        for group in api_groups:
            group_results = []
            timeout = group['timeout']

            for api_name, api_method in group['apis']:
                if api_name in tried_apis:
                    continue

                tried_apis.add(api_name)
                retry_count = 0
                current_timeout = timeout

                while retry_count < max_retries:
                    try:
                        # Verifica rate limit
                        wait_time = self.rate_limiter.should_wait(api_name)
                        if wait_time > 0:
                            time.sleep(wait_time)

                        start_time = time.time()
                        metadata = api_method(isbn)
                        elapsed = time.time() - start_time

                        # Atualiza métricas
                        self.rate_limiter.update_stats(api_name, True, elapsed)
                        self.metrics.add_metric(api_name, elapsed, True)

                        if metadata:
                            # Ajusta confiança baseado no tempo de resposta
                            if elapsed < 1:
                                metadata.confidence_score += 0.05
                            
                            # Validação dos metadados
                            if not self.validator.validate_metadata(asdict(metadata), api_name, isbn):
                                retry_count += 1
                                continue

                            group_results.append(metadata)

                            # Se encontramos um resultado muito bom, retorna imediatamente
                            if metadata.confidence_score >= group['min_confidence']:
                                # Salva no cache antes de retornar
                                self.cache.set(asdict(metadata))
                                return metadata

                        break  # Sai do loop de retry se não houve erros

                    except requests.Timeout:
                        retry_count += 1
                        current_timeout *= backoff_factor
                        errors[api_name].append('timeout')
                        self.metrics.add_error(api_name, 'timeout')
                        if retry_count < max_retries:
                            self.logger.warning(f"{api_name} timeout for ISBN {isbn}, retry {retry_count}/{max_retries}")
                            time.sleep(retry_count)  # Backoff exponencial
                    
                    except requests.ConnectionError as e:
                        errors[api_name].append(f'connection: {str(e)}')
                        self.metrics.add_error(api_name, 'connection')
                        break  # Não retenta erros de conexão
                    
                    except Exception as e:
                        errors[api_name].append(f'unexpected: {str(e)}')
                        self.metrics.add_error(api_name, 'unexpected')
                        break

            all_results.extend(group_results)
            
            # Se temos resultados suficientemente bons deste grupo, não tentamos o próximo
            if len(group_results) > 0:
                best_result = max(group_results, key=lambda x: x.confidence_score)
                if best_result.confidence_score >= group['min_confidence']:
                    self.cache.set(asdict(best_result))
                    return best_result

        # Se chegamos aqui, tentamos combinar os melhores resultados
        if len(all_results) >= 2:
            merged = self._merge_metadata_results(
                sorted(all_results, key=lambda x: x.confidence_score, reverse=True)[:3]
            )
            if merged and merged.confidence_score >= 0.8:
                self.cache.set(asdict(merged))
                return merged

        # Se ainda temos algum resultado, retorna o melhor
        if all_results:
            best_result = max(all_results, key=lambda x: x.confidence_score)
            self.cache.set(asdict(best_result))
            return best_result

        # Registra falhas se nenhum resultado foi encontrado
        if errors:
            for api_name, api_errors in errors.items():
                self.logger.error(f"Failed to fetch metadata for ISBN {isbn}")
                for error in api_errors:
                    self.logger.error(f"{api_name}: {error}")
            self.cache.update_error_count(isbn, str(errors))

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
                    method = getattr(self, f'fetch_{api_name}')  # Removido underscore
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
                    self.logger.error(f"Error in {api_name} for ISBN {isbn}: {str(e)}")
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
                self.logger.error(f"All attempts failed for ISBN {isbn}")
                for error in api_errors:
                    self.logger.error(f"{api_name}: {error}")

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
        self.logger.info(f"Processing Casa do Código ISBN: {isbn}")
        
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
                self.logger.error(f"Error with {api_name} for ISBN {isbn}: {str(e)}")
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
                self.logger.warning(f"ISBNlib info: ISBN variant detected for {isbn}: {str(e)}")
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
                self.logger.warning(f"WorldCat: Access forbidden for ISBN {isbn}")
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
        """
        Fetch metadata using isbnlib.goom with proper error handling.
        
        Args:
            isbn: ISBN to look up
            
        Returns:
            BookMetadata if successful, None otherwise
        """
        try:
            import isbnlib
            metadata = isbnlib.goom(isbn)
            
            # goom can return a list - take first item if so
            if isinstance(metadata, list) and metadata:
                metadata = metadata[0]
            elif not metadata:
                return None
                
            if not isinstance(metadata, dict):
                return None
                
            return BookMetadata(
                title=metadata.get('Title', '').strip(),
                authors=[a.strip() for a in metadata.get('Authors', [])],
                publisher=metadata.get('Publisher', '').strip(),
                published_date=metadata.get('Year', 'Unknown'),
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
            
        self.logger.info(f"Processing {publisher_info['name']} ISBN: {isbn}")
        
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
                self.logger.error(f"Error with {api_name} for ISBN {isbn}: {str(e)}")
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
        """
        Enhanced API error handling with support for ISBN variants and complete metrics tracking.
        
        Args:
            api_name: Name of the API that generated the error
            error: The exception that occurred
            isbn: ISBN being processed when the error occurred
        """
        error_type = type(error).__name__
        error_msg = str(error)
        
        # Known ISBN variant mappings, especially for Packt books
        known_variants = {
            '9781789957648': ['9788445901854'],
            '9781801813785': ['9781801812436'],
            '9781800205697': ['9781801810074'],
            '9781800206540': ['9781801079341']
        }
        
        # Skip warnings for known ISBN variants
        if "isbn request != isbn response" in error_msg.lower():
            if hasattr(self, 'file_group') and isinstance(self.file_group, object):
                for primary, variants in known_variants.items():
                    if isbn in variants or primary in error_msg:
                        return  # Known variant, no need to log

        # Get main logger
        logger = logging.getLogger('metadata_fetcher')
        
        # Categorize and record error
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
        
        # Record metrics for the failure
        self._log_api_metrics(api_name, False, 0.0)
        
        # Update dynamic API adjustments based on performance
        stats = self.metrics.get_api_stats(api_name)
        if stats.get('success_rate', 0) < 30:  # If success rate is very low
            config = self.API_CONFIGS.get(api_name, {})
            # Increase retries and backoff for problematic APIs
            config['retries'] = min(5, config.get('retries', 2) + 1)
            config['backoff'] = min(4.0, config.get('backoff', 1.5) * 1.5)

        # Update error tracking in cache if available
        if hasattr(self, 'cache') and self.cache:
            self.cache.update_error_count(isbn, str(error))

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
            
            self.logger.warning(
                f'API call failed: {api_name}\n'
                f'Average response time: {avg_time:.2f}s\n'
                f'Success rate: {success_rate:.1f}%'
            )

    def _setup_logging(self):
        """Configura logging com níveis de detalhe diferentes."""
        # Logger principal
        logger = logging.getLogger('metadata_fetcher')
        logger.setLevel(self.logger.info)

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
                                self.logger.info(f"ISBN variant accepted: {isbn} -> {returned_isbn}")
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
            self.logger.warning(f"API {api_name} health check: Poor performance detected. "
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
            self.logger.warning(f"ISBN variant mismatch: requested {isbn}, got {returned_isbns}")
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
            self.logger.error(f"Error processing metadata from {source}: {str(e)}")
            return None

    def validate_isbn_variant(self, original: str, variant: str) -> bool:
        """Validação melhorada de variantes de ISBN."""
        # Normaliza os ISBNs
        original = self._normalize_isbn(original)
        variant = self._normalize_isbn(variant)
        
        # Verifica correspondência direta
        if original == variant:
            return True
            
        try:
            import isbnlib
            
            # Converte ambos para ISBN-13 para comparação
            isbn13_original = original if len(original) == 13 else isbnlib.to_isbn13(original)
            isbn13_variant = variant if len(variant) == 13 else isbnlib.to_isbn13(variant)
            
            if isbn13_original == isbn13_variant:
                return True
                
            # Verifica edições relacionadas
            related_isbns = isbnlib.editions(isbn13_original)
            if related_isbns and isbn13_variant in related_isbns:
                return True
                
        except Exception as e:
            self.logger.debug(f"Erro na validação de variante ISBN: {str(e)}")
            
            # Fallback: compara prefixos se a conversão falhar
            if len(original) == len(variant):
                # Compara os primeiros 9 dígitos (ignora dígito verificador)
                return original[:-1] == variant[:-1]
        
        return False

    def _get_api_error_rate(self, api_name: str) -> float:
        """Calcula taxa de erro da API nas últimas chamadas."""
        stats = self.metrics.get_api_stats(api_name)
        if not stats or stats.get('total_calls', 0) == 0:
            return 0.0
        return 1.0 - (stats.get('success_rate', 0) / 100.0)

    def _merge_metadata(self, results: List[BookMetadata]) -> Optional[BookMetadata]:
        """
        Combina resultados de múltiplas fontes para criar um registro mais completo.
        
        Args:
            results: Lista de resultados do BookMetadata ordenados por confiança
            
        Returns:
            BookMetadata combinado ou None se não for possível combinar
        """
        if not results:
            return None
            
        # Usa o melhor resultado como base
        best = results[0]
        merged = asdict(best)
        confidence_boost = 0
        
        # Combina informações de outras fontes
        for other in results[1:]:
            changes_made = 0  # Rastreia número de melhorias
            
            # Usa título mais longo se disponível e parece válido
            if (len(other.title) > len(merged['title']) and 
                self.validator.validate_title(other.title)):
                merged['title'] = other.title
                changes_made += 1
                
            # Combina autores únicos mantendo ordem significativa
            other_authors = [a for a in other.authors if a not in merged['authors']]
            if other_authors:
                merged['authors'].extend(other_authors)
                changes_made += 1
                
            # Usa data mais específica se válida
            if (len(other.published_date) > len(merged['published_date']) and 
                self.validator.validate_date(other.published_date)):
                merged['published_date'] = other.published_date
                changes_made += 1
                
            # Sistema de boost de confiança dinâmico
            confidence_boost += changes_made * 0.02  # Boost por cada melhoria
            
            # Boost adicional se fontes concordam em informações principais
            if other.title.lower() == best.title.lower():
                confidence_boost += 0.05  # Alto boost para título igual
            if set(other.authors) == set(best.authors):
                confidence_boost += 0.03  # Boost médio para autores iguais
                
        # Ajusta pontuação final de confiança
        merged['confidence_score'] = min(1.0, merged['confidence_score'] + confidence_boost)
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
        self._init_logging() 
        self.isbn_extractor = ISBNExtractor()
        self.dependency_manager = DependencyManager()
        self.logger.info(f"Extractores disponíveis: {', '.join(self.dependency_manager.get_available_extractors())}")
        if self.dependency_manager.has_ocr_support:
            self.logger.info("Suporte a OCR está disponível")

    def _init_logging(self):
        """Initialize logging configuration."""
        self.logger = logging.getLogger('pdf_processor')  # Use o nome específico da classe
        self.logger.setLevel(logging.DEBUG)  # Nível detalhado para o arquivo
        
        if not self.logger.handlers:
            # File handler - captura tudo para o arquivo
            file_handler = logging.FileHandler('pdf_processor.log')
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            ))
            file_handler.setLevel(logging.DEBUG)
            
            # Console handler - apenas warnings e erros
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(
                '%(levelname)s - %(message)s'
            ))
            console_handler.setLevel(logging.WARNING)
            
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)

    def extract_text_from_pdf(self, pdf_path: str, max_pages: int = 10) -> Tuple[str, List[str]]:
        """Extrai texto do PDF usando múltiplos métodos."""
        text = ""
        methods_tried = []
        methods_succeeded = []
        
        # 1. PyPDF2
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                methods_tried.append('PyPDF2')
                
                for page_num in range(min(max_pages, len(reader.pages))):
                    text += reader.pages[page_num].extract_text() + "\n"
                    
                if text.strip():
                    methods_succeeded.append('PyPDF2')
        except Exception as e:
            self.logger.debug(f"PyPDF2 extraction failed: {str(e)}")
        
        # 2. pdfplumber se PyPDF2 falhar
        if not text.strip() and 'pdfplumber' in self.dependency_manager.get_available_extractors():
            try:
                import pdfplumber
                methods_tried.append('pdfplumber')
                
                with pdfplumber.open(pdf_path) as pdf:
                    for page in pdf.pages[:max_pages]:
                        text += page.extract_text() + "\n"
                        
                    if text.strip():
                        methods_succeeded.append('pdfplumber')
            except Exception as e:
                self.logger.debug(f"pdfplumber extraction failed: {str(e)}")
        
        # 3. OCR se texto ainda não foi extraído
        if not text.strip() and self.dependency_manager.has_ocr_support:
            try:
                import pytesseract
                from pdf2image import convert_from_path
                methods_tried.append('OCR')
                
                images = convert_from_path(pdf_path, last_page=max_pages)
                ocr_text = ""
                
                for image in images:
                    ocr_text += pytesseract.image_to_string(image) + "\n"
                    
                if ocr_text.strip():
                    text = ocr_text
                    methods_succeeded.append('OCR')
            except Exception as e:
                self.logger.debug(f"OCR extraction failed: {str(e)}")
        
        return self._clean_text(text), methods_tried

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
        self.logger.info(f"Extraindo metadados de: {pdf_path}")
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                metadata = reader.metadata if reader.metadata else {}
                
                if 'ISBN' in metadata:
                    isbn = re.sub(r'[^0-9X]', '', metadata['ISBN'].upper())
                    if not (self.isbn_extractor.validate_isbn_10(isbn) or 
                           self.isbn_extractor.validate_isbn_13(isbn)):
                        self.logger.warning(f"ISBN inválido encontrado nos metadados: {isbn}")
                        del metadata['ISBN']
                    else:
                        self.logger.info(f"ISBN válido encontrado nos metadados: {isbn}")
                        
                return metadata
        except Exception as e:
            self.logger.error(f"Erro ao extrair metadados de {pdf_path}: {str(e)}")
            return {}
        
class BookMetadataExtractor:
    def __init__(self, isbndb_api_key: Optional[str] = None):
        """
        Initialize the extractor with required components.
        
        Args:
            isbndb_api_key: Optional API key for ISBNdb service
        """
        # Set up reports directory first
        self.reports_dir = Path("reports")
        self.reports_dir.mkdir(exist_ok=True)
        
        # Initialize logging before other components
        self._setup_logging()
        
        # Initialize core components
        
        self.isbn_extractor = ISBNExtractor()
        self.metadata_fetcher = MetadataFetcher(isbndb_api_key=isbndb_api_key)
        self.pdf_processor = PDFProcessor()
        self.ebook_processor = EbookProcessor()
        self.cache = MetadataCache()
        self.api = APIHandler()
        self.packt_processor = PacktBookProcessor()
        self.session = requests.Session()
        self.isbndb_api_key = isbndb_api_key
        self.file_naming_pattern = "{title} - {author} - {year} - {ISBN}"  # Default pattern
        
        # Initialize file grouping support
        self.file_group = BookFileGroup()

    def _setup_logging(self):
        """Initialize logging with correct file location."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = self.reports_dir / f"report_{timestamp}_metadata.log"
        
        # Create logger
        self.logger = logging.getLogger('book_metadata')
        self.logger.setLevel(logging.INFO)
        
        # Create handlers
        file_handler = logging.FileHandler(str(log_path))
        console_handler = logging.StreamHandler()
        
        # Create formatters and add it to handlers
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers to the logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def _add_publisher_stats(self, metadata: Dict, runtime_stats: Dict):
        """Adiciona estatísticas por editora aos runtime stats sem modificar estrutura existente."""
        if not metadata or 'publisher' not in metadata:
            return
            
        if 'publisher_stats' not in runtime_stats:
            runtime_stats['publisher_stats'] = defaultdict(lambda: {'total': 0, 'success': 0, 'failed': 0})
            
        publisher = metadata.get('publisher', 'Unknown').strip()
        format_ext = Path(metadata.get('file_path', '')).suffix.lower()[1:]
        
        stats = runtime_stats['publisher_stats'][publisher]
        stats['total'] += 1
        stats['success'] += 1
        stats[f'{format_ext}_success'] = stats.get(f'{format_ext}_success', 0) + 1


    def _clean_filename(self, filename: str) -> str:
        """
        Limpa e normaliza um nome de arquivo removendo caracteres inválidos e 
        normalizando Unicode.

        Args:
            filename: String com o nome do arquivo para limpar

        Returns:
            str: Nome do arquivo limpo e seguro para uso em sistemas de arquivos

        Examples:
            >>> self._clean_filename('File: "Test" /> .pdf')
            'File Test.pdf'
            >>> self._clean_filename('áéíóú.pdf')
            'aeiou.pdf'
        """
        if not filename:
            return ""
        
        try:
            # Remove caracteres inválidos para sistemas de arquivos
            filename = re.sub(r'[<>:"/\\|?*]', '', filename)
            
            # Normaliza caracteres Unicode (converte acentos e caracteres especiais)
            filename = unicodedata.normalize('NFKD', filename)
            filename = filename.encode('ASCII', 'ignore').decode('ASCII')
            
            # Remove espaços duplicados e normaliza espaços
            filename = ' '.join(filename.split())
            
            # Limita tamanho para evitar problemas com sistemas de arquivos
            max_length = 200
            if len(filename) > max_length:
                # Preserva extensão ao truncar
                name, ext = os.path.splitext(filename)
                trunc_length = max_length - len(ext) - 3  # -3 para '...'
                filename = name[:trunc_length] + '...' + ext
                
            return filename.strip()
            
        except Exception as e:
            self.logger.error(f"Erro ao limpar nome de arquivo: {str(e)}")
            return "unnamed_file"  # Nome seguro em caso de erro
            

    def preview_new_name(self, metadata: Dict) -> str:
        """Gera preview do novo nome do arquivo."""
        elements = []
        
        # Adiciona elementos na ordem desejada
        if metadata.get('title'):
            elements.append(metadata['title'][:50])
            
        if metadata.get('authors'):
            authors = ', '.join(metadata['authors'][:2])  # Limita a 2 autores
            elements.append(authors[:30])
            
        if metadata.get('published_date'):
            year = metadata['published_date'].split('-')[0] if '-' in metadata['published_date'] else metadata['published_date']
            elements.append(year)
            
        if metadata.get('isbn_13'):
            elements.append(metadata['isbn_13'])
        elif metadata.get('isbn_10'):
            elements.append(metadata['isbn_10'])
        
        # Junta elementos e limpa o nome
        return self._clean_filename(' - '.join(elements))

    def log_file_operation(self, old_path: str, new_path: str, operation: str):
        """Log detalhado de operações com arquivos."""
        try:
            old_size = Path(old_path).stat().st_size / (1024*1024)  # Tamanho em MB
            old_name = Path(old_path).name
            new_name = Path(new_path).name
            
            self.logger.info(f"File operation: {operation}")
            self.logger.info(f"  Original filename: {old_name}")
            self.logger.info(f"  New filename: {new_name}")
            self.logger.info(f"  Size: {old_size:.2f}MB")
            self.logger.info(f"  Original path: {old_path}")
            self.logger.info(f"  New path: {new_path}")
            
            # Adiciona logs de validação
            if operation == "rename":
                if Path(new_path).exists():
                    self.logger.warning(f"  Target file already exists: {new_path}")
                if not Path(old_path).exists():
                    self.logger.error(f"  Source file not found: {old_path}")
                    
        except Exception as e:
            self.logger.error(f"Error logging file operation: {str(e)}")

    def rename_file(self, metadata: Union[Dict, BookMetadata], simulate: bool = True) -> bool:
        """
        Renomeia arquivos de forma segura para compatibilidade entre sistemas operacionais.
        
        Args:
            metadata: Metadados do livro (dict ou BookMetadata)
            simulate: Se True, apenas simula a renomeação
        
        Returns:
            bool: True se operação foi bem sucedida
        """
        try:
            if not metadata:
                return False
                
            if isinstance(metadata, BookMetadata):
                metadata = asdict(metadata)

            def clean_name_part(text: str) -> str:
                """Limpa parte do nome do arquivo para compatibilidade."""
                if not text:
                    return ""
                # Remove caracteres especiais e espaços extras
                text = text.strip()
                # Substitui vírgulas por hífen
                text = text.replace(',', '-')
                # Substitui espaços em branco por underscore
                text = text.replace(' ', '_')
                # Remove outros caracteres problemáticos
                text = re.sub(r'[<>:"/\\|?*]', '', text)
                return text
                
            # Extrai e limpa campos
            publisher = clean_name_part(self.normalize_publisher(metadata.get('publisher', 'Unknown')))
            year = metadata.get('published_date', 'Unknown').split('-')[0]
            title = clean_name_part(metadata.get('title', 'Unknown'))[:50]
            authors = metadata.get('authors', [])
            author = clean_name_part(', '.join(authors[:2])) if authors else ''
            isbn = metadata.get('isbn_13') or metadata.get('isbn_10', '')
            
            # Monta as partes do nome
            name_parts = []
            
            if publisher and publisher != 'Unknown':
                name_parts.append(publisher)
                
            if year and year != 'Unknown':
                name_parts.append(year)
                
            if title:
                name_parts.append(title)
                
            if author:
                name_parts.append(author)
                
            if isbn:
                name_parts.append(isbn)
                
            # Une as partes com underscore
            base_name = '_'.join(filter(None, name_parts))
            
            # Processa arquivos
            files_to_rename = []
            if metadata.get('file_paths'):
                files_to_rename = metadata['file_paths']
            elif metadata.get('file_path'):
                files_to_rename = [metadata['file_path']]
                
            if not files_to_rename:
                return False
                
            success = True
            renames = []
            
            for old_path in files_to_rename:
                old_path = Path(old_path)
                if not old_path.exists():
                    self.logger.error(f"Arquivo não encontrado: {old_path}")
                    success = False
                    continue
                    
                new_name = f"{base_name}{old_path.suffix}"
                new_path = old_path.parent / new_name
                
                # Log da operação
                self.log_file_operation(
                    str(old_path),
                    str(new_path),
                    "preview" if simulate else "rename"
                )
                
                if not simulate:
                    if new_path.exists():
                        self.logger.error(f"Arquivo já existe: {new_path}")
                        success = False
                        continue
                        
                    renames.append((old_path, new_path))
            
            # Executa renomeações
            if not simulate and success and renames:
                for old_path, new_path in renames:
                    old_path.rename(new_path)
                    self.logger.info(f"Arquivo renomeado: {new_path}")
                    
            return success
            
        except Exception as e:
            self.logger.error(f"Erro ao renomear arquivos: {str(e)}")
            return False

    def process_single_file(self, file_path: str, runtime_stats: Dict) -> Optional[BookMetadata]:
        """
        Processa um único arquivo extraindo metadados com tratamento especial para Casa do Código e Packt.
        """
        start_time = time.time()
        file_ext = Path(file_path).suffix.lower()[1:]
        self.logger.info(f" {file_path}")
        
        try:
            # Extrai texto baseado no tipo de arquivo
            if file_ext == 'pdf':
                text, methods = self.pdf_processor.extract_text_from_pdf(file_path)
                file_metadata = self.pdf_processor.extract_metadata_from_pdf(file_path)
            elif file_ext in ('epub', 'mobi'):
                if file_ext == 'epub':
                    text, methods = self.ebook_processor.extract_text_from_epub(file_path)
                else:
                    text, methods = self.ebook_processor.extract_text_from_mobi(file_path)
                file_metadata = self.ebook_processor.extract_metadata(file_path)

                # Se encontrou metadados válidos da Casa do Código, retorna imediatamente
                if file_metadata and file_metadata.get('isbn', '').startswith('978855519'):
                    if all(file_metadata.get(field) for field in ['title', 'creator', 'isbn']):
                        metadata = BookMetadata(
                            title=file_metadata['title'],
                            authors=[file_metadata['creator']],
                            publisher='Casa do Código',
                            published_date=file_metadata.get('date', 'Unknown'),
                            isbn_13=file_metadata['isbn'],
                            isbn_10=None,
                            confidence_score=0.95,
                            source='epub_metadata',
                            file_path=str(file_path)
                        )
                        runtime_stats['successful_files'].append(file_path)
                        return metadata
                        
                # Se for livro Packt, tenta processar com tratamento especial
                if file_ext == 'epub' and self.packt_processor.is_packt_book(file_path):
                    enhanced_metadata = self.packt_processor.enhance_metadata(file_metadata, text)
                    if enhanced_metadata and enhanced_metadata.get('isbn'):
                        metadata = BookMetadata(
                            title=enhanced_metadata.get('title', ''),
                            authors=[enhanced_metadata.get('creator')] if 'creator' in enhanced_metadata 
                                else enhanced_metadata.get('authors', []),
                            publisher='Packt Publishing',
                            published_date=enhanced_metadata.get('date', 'Unknown'),
                            isbn_13=enhanced_metadata.get('isbn'),
                            isbn_10=None,
                            confidence_score=0.95,
                            source='packt_processor',
                            file_path=str(file_path)
                        )
                        runtime_stats['successful_files'].append(file_path)
                        self._add_publisher_stats(asdict(metadata), runtime_stats)
                        return metadata
            else:
                runtime_stats['failure_details'][file_path] = {
                    'error': 'unsupported_format',
                    'format': file_ext
                }
                return None

            if not text:
                runtime_stats['failure_details'][file_path] = {
                    'error': 'text_extraction_failed',
                    'methods_tried': methods
                }
                return None

            # Extrai ISBNs
            isbns = self.isbn_extractor.extract_from_text(text, source_path=file_path)
            if file_metadata and 'isbn' in file_metadata:
                isbns.add(file_metadata['isbn'])

            if not isbns:
                runtime_stats['failure_details'][file_path] = {
                    'error': 'no_isbn_found',
                    'text_sample': text[:500]
                }
                return None

            # Tenta cada ISBN encontrado
            for isbn in sorted(isbns):
                try:
                    metadata = self.metadata_fetcher.fetch_metadata(isbn)
                    if metadata:
                        metadata.file_path = str(file_path)
                        runtime_stats['successful_files'].append(file_path)
                        # Adiciona estatística por editora
                        publisher = metadata.publisher or 'Unknown'
                        if 'publisher_stats' not in runtime_stats:
                            runtime_stats['publisher_stats'] = defaultdict(lambda: {'total': 0, 'success': 0})
                        stats = runtime_stats['publisher_stats'][publisher]
                        stats['total'] += 1
                        stats['success'] += 1
                        ext = Path(file_path).suffix.lower()[1:]
                        stats[f'{ext}_success'] = stats.get(f'{ext}_success', 0) + 1
                        return metadata
                except Exception as e:
                    runtime_stats['api_errors'][file_path].append(f"ISBN {isbn}: {str(e)}")

            runtime_stats['failure_details'][file_path] = {
                'error': 'metadata_fetch_failed',
                'isbns_found': list(isbns)
            }
            return None

        except Exception as e:
            runtime_stats['failure_details'][file_path] = {
                'error': str(e),
                'traceback': traceback.format_exc()
            }
            self.logger.error(f"Error processing {file_path}: {str(e)}")
            return None
        finally:
            runtime_stats['processing_times'][file_path] = time.time() - start_time

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
        self.logger.info(f"Detected Casa do Código ISBN: {isbn}")
        
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
            self.logger.error(error_msg)
        
        return None

    def _fetch_with_publisher_priority(self, isbn: str, publisher_info: Dict) -> Optional[BookMetadata]:
        """Busca metadados usando prioridade específica da editora."""
        self.logger.info(f"Tentando busca prioritária para ISBN {isbn} da editora {publisher_info['name']}")
        
        errors = []
        for api_name in publisher_info['api_priority']:
            try:
                self.logger.info(f"Tentando API {api_name}")
                
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
                self.logger.error(error_msg)
                errors.append(error_msg)
                continue
                
        self.logger.error(f"Falha em todas as APIs para ISBN {isbn}:\n" + "\n".join(errors))
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

    def _prepare_report_data(self, runtime_stats: Dict) -> Dict:
        """
        Prepara dados consistentes para ambos os relatórios HTML e JSON.
        """
        successful_results = runtime_stats.get('successful_results', [])
        processed_files = runtime_stats.get('processed_files', [])
        
        total_files = len(processed_files)
        successful = len(successful_results)
        failed = total_files - successful if total_files >= successful else 0
        
        success_rate = (successful / total_files * 100) if total_files > 0 else 0.0
        processing_times = list(runtime_stats.get('processing_times', {}).values())
        avg_time = statistics.mean(processing_times) if processing_times else 0.0
        
        return {
            'summary': {
                'total_files': total_files,
                'successful': successful,
                'failed': failed,
                'success_rate': success_rate,
                'average_time': avg_time,
                'timestamp': datetime.now().isoformat()
            },
            'details': {
                'successful': [asdict(r) for r in successful_results],
                'failures': runtime_stats.get('failure_details', {}),
                'format_stats': runtime_stats.get('format_stats', {}),
                'api_stats': runtime_stats.get('api_stats', {})
            }
        }

    def _generate_html_report(self, data: Dict, output_file: Path):
        """
        Gera relatório HTML com visualizações e estatísticas detalhadas.
        Todo o template HTML está contido neste método para evitar dependências externas.
        """
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Book Metadata Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }
                .card { background: #fff; padding: 20px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
                table { width: 100%; border-collapse: collapse; margin: 10px 0; }
                th, td { padding: 12px 8px; text-align: left; border-bottom: 1px solid #ddd; }
                th { background-color: #f5f5f5; font-weight: bold; }
                .success { color: #28a745; font-weight: bold; }
                .failure { color: #dc3545; font-weight: bold; }
                .warning { color: #ffc107; font-weight: bold; }
                .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
                .error-details { background-color: #fff8f8; padding: 10px; border-left: 4px solid #dc3545; margin: 5px 0; }
                h1, h2, h3 { color: #2c3e50; }
                .progress-bar { 
                    background-color: #f0f0f0; 
                    border-radius: 4px; 
                    padding: 3px;
                    margin: 5px 0;
                }
                .progress-bar > div {
                    background-color: #4CAF50;
                    height: 20px;
                    border-radius: 2px;
                    transition: width 0.5s;
                }
            </style>
        </head>
        <body>
            <h1>Book Metadata Report</h1>
            
            <div class="card">
                <h2>Summary</h2>
                <div class="stats-grid">
                    <div>
                        <h3>General Statistics</h3>
                        <table>
                            <tr><th>Total Files</th><td>{total_files}</td></tr>
                            <tr><th>Successful</th><td class="success">{successful}</td></tr>
                            <tr><th>Failed</th><td class="failure">{failed}</td></tr>
                            <tr><th>Success Rate</th><td>
                                <div class="progress-bar">
                                    <div style="width: {success_rate}%"></div>
                                </div>
                                {success_rate:.1f}%
                            </td></tr>
                            <tr><th>Average Time</th><td>{avg_time:.2f}s</td></tr>
                        </table>
                    </div>
                    
                    <div>
                        <h3>Format Statistics</h3>
                        <table>
                            <tr>
                                <th>Format</th>
                                <th>Total</th>
                                <th>Success</th>
                                <th>Failed</th>
                                <th>Rate</th>
                            </tr>
                            {format_stats}
                        </table>
                    </div>
                </div>
            </div>

            <div class="card">
                <h2>Successful Extractions</h2>
                <table>
                    <tr>
                        <th>File</th>
                        <th>Title</th>
                        <th>Authors</th>
                        <th>Publisher</th>
                        <th>ISBN</th>
                        <th>Source</th>
                        <th>Confidence</th>
                    </tr>
                    {success_rows}
                </table>
            </div>

            <div class="card">
                <h2>Failure Analysis</h2>
                <table>
                    <tr>
                        <th>File</th>
                        <th>Error Type</th>
                        <th>Details</th>
                    </tr>
                    {error_rows}
                </table>
            </div>

            <footer class="card">
                <p>Generated at: {timestamp}</p>
            </footer>
        </body>
        </html>
        """

        # Gera estatísticas por formato
        format_stats_rows = []
        for fmt, stats in data['details'].get('format_stats', {}).items():
            success_rate = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
            format_stats_rows.append(f"""
                <tr>
                    <td>{fmt.upper()}</td>
                    <td>{stats['total']}</td>
                    <td class="success">{stats['success']}</td>
                    <td class="failure">{stats['failed']}</td>
                    <td>
                        <div class="progress-bar">
                            <div style="width: {success_rate}%"></div>
                        </div>
                        {success_rate:.1f}%
                    </td>
                </tr>
            """)

        # Gera linhas de sucessos
        success_rows = []
        for book in sorted(data['details']['successful'], key=lambda x: x['confidence_score'], reverse=True):
            success_rows.append(f"""
                <tr>
                    <td>{Path(book['file_path']).name}</td>
                    <td>{book['title']}</td>
                    <td>{', '.join(book['authors'])}</td>
                    <td>{book['publisher']}</td>
                    <td>{book['isbn_13'] or book['isbn_10']}</td>
                    <td>{book['source']}</td>
                    <td>{book['confidence_score']:.2f}</td>
                </tr>
            """)

        # Gera linhas de erros
        error_rows = []
        for file_path, error in data['details']['failures'].items():
            error_type = error.get('error', 'Unknown error')
            details = ', '.join(str(v) for k, v in error.items() if k != 'error' and v)
            error_rows.append(f"""
                <tr>
                    <td>{Path(file_path).name}</td>
                    <td class="failure">{error_type}</td>
                    <td class="error-details">{details}</td>
                </tr>
            """)

        # Monta HTML final
        html_content = html_template.format(
            total_files=data['summary']['total_files'],
            successful=data['summary']['successful'],
            failed=data['summary']['failed'],
            success_rate=data['summary']['success_rate'],
            avg_time=data['summary']['average_time'],
            timestamp=data['summary']['timestamp'],
            format_stats='\n'.join(format_stats_rows),
            success_rows='\n'.join(success_rows) if success_rows else '<tr><td colspan="7">No successful extractions</td></tr>',
            error_rows='\n'.join(error_rows) if error_rows else '<tr><td colspan="3">No errors reported</td></tr>'
        )

        # Salva o arquivo
        output_file.write_text(html_content, encoding='utf-8')

    def _generate_json_report(self, data: Dict, output_file: Path):
        """
        Generates a comprehensive JSON report of the metadata extraction process.
        
        This method takes the processed data, prepares it in a structured format,
        and saves it as a JSON file. The report includes detailed statistics,
        successful extractions, and error information.
        """
        try:
            # Prepare the JSON data with our structured format
            json_data = self._prepare_json_data(data)
            
            # Write the JSON file with proper formatting and encoding
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
                
            self.logger.info(f"JSON report successfully generated: {output_file}")
            
        except Exception as e:
            self.logger.error(f"Error generating JSON report: {str(e)}")
            self.logger.error(traceback.format_exc())
            raise

    def suggest_filename(self, metadata: Dict) -> str:
        """
        Sugere nome de arquivo baseado nos metadados usando o padrão definido.
        
        Args:
            metadata: Dicionário com metadados do livro
            
        Returns:
            str: Nome de arquivo sugerido com extensão apropriada
        """
        # Extrai e limpa os valores
        title = self._clean_filename(metadata.get('title', 'Unknown Title'))[:50]
        authors = metadata.get('authors', ['Unknown Author'])
        author = self._clean_filename(', '.join(authors[:2]))[:30]
        year = metadata.get('published_date', 'Unknown').split('-')[0]
        publisher = self._clean_filename(self.normalize_publisher(metadata.get('publisher', '')))
        isbn = metadata.get('isbn_13') or metadata.get('isbn_10') or ''

        # Gera nome base usando o padrão
        base_name = self.file_naming_pattern.format(
            title=title,
            author=author,
            year=year,
            publisher=publisher,
            isbn=isbn
        )
        
        # Limpa o nome final
        base_name = self._clean_filename(base_name)
        
        # Gera nomes para múltiplos formatos se necessário
        if metadata.get('formats'):
            return {fmt: f"{base_name}.{fmt}" for fmt in metadata['formats']}
        
        # Ou retorna nome único com extensão original
        ext = Path(metadata['file_path']).suffix.lower()[1:]
        return f"{base_name}.{ext}"

    def normalize_publisher(self, publisher: str) -> str:
        """
        Normaliza o nome da editora para um formato padrão.

        Args:
            publisher: Nome original da editora

        Returns:
            str: Nome normalizado da editora
        """
        if not publisher:
            return "Unknown"
        
        # Converte para maiúsculas para comparação
        publisher_upper = publisher.upper()
        
        # Verifica variações conhecidas
        for variant, normalized in NORMALIZED_PUBLISHERS.items():
            if variant in publisher_upper:
                return normalized
        
        return publisher.strip()

    def set_naming_pattern(self, pattern: str):
        """
        Define o padrão para nomeação de arquivos.
        
        Args:
            pattern: Padrão usando placeholders {title}, {author}, {year}, {publisher}, {isbn}
        """
        self.file_naming_pattern = pattern
      
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
            self.logger.error(f"Erro ao gerar relatório: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())

    def process_directory(self, directory_path: str, subdirs: Optional[List[str]] = None, 
                         recursive: bool = False, max_workers: int = 4) -> List[BookMetadata]:
        """
        Process a directory containing book files.
        
        Args:
            directory_path: Path to directory containing book files
            subdirs: Optional list of specific subdirectories to process
            recursive: Whether to process subdirectories recursively
            max_workers: Number of concurrent worker threads
            
        Returns:
            List[BookMetadata]: List of successfully processed book metadata
        """
        directory = Path(directory_path)
        console = Console()
        
        # Initialize runtime stats
        runtime_stats = {
            'processed_files': [],
            'successful_files': [],
            'successful_results': [],
            'failure_details': {},
            'api_errors': defaultdict(list),
            'processing_times': {},
            'format_stats': defaultdict(lambda: {'total': 0, 'success': 0, 'failed': 0}),
            'start_time': time.time()
        }

        # Find and group files
        file_groups = self._collect_files(directory, subdirs, recursive, runtime_stats)
        if not file_groups:
            self.logger.warning(f"No files found in {directory_path}")
            return []

        # Process files with progress display
        results = self._process_with_progress(file_groups, runtime_stats, max_workers)
        
        # Generate final reports
        self.print_final_summary(runtime_stats)
        return results

    def _collect_files(self, directory: Path, subdirs: Optional[List[str]], 
                      recursive: bool, runtime_stats: Dict) -> Dict[str, List[str]]:
        """
        Collect and group files from the specified directory.
        
        Args:
            directory: Base directory path
            subdirs: Optional list of subdirectories to process
            recursive: Whether to process recursively
            runtime_stats: Dictionary to store runtime statistics
            
        Returns:
            Dictionary mapping base names to lists of related files
        """
        all_files = []
        extensions = {'pdf', 'epub', 'mobi'}
        
        self.logger.debug("Scanning for files...")
        
        if recursive:
            for ext in extensions:
                files = list(directory.rglob(f"*.{ext}"))
                all_files.extend(files)
                runtime_stats['format_stats'][ext]['total'] += len(files)
        else:
            if subdirs:
                for subdir in subdirs:
                    subdir_path = directory / subdir
                    if subdir_path.exists():
                        for ext in extensions:
                            files = list(subdir_path.glob(f"*.{ext}"))
                            all_files.extend(files)
                            runtime_stats['format_stats'][ext]['total'] += len(files)
            else:
                for ext in extensions:
                    files = list(directory.glob(f"*.{ext}"))
                    all_files.extend(files)
                    runtime_stats['format_stats'][ext]['total'] += len(files)

        runtime_stats['processed_files'] = [str(f) for f in all_files]
        return self.file_group.group_files([str(f) for f in all_files])

    def _process_with_progress(self, file_groups: Dict[str, List[str]], 
                             runtime_stats: Dict, max_workers: int) -> List[BookMetadata]:
        """
        Process files with progress display using rich progress bar.
        
        Args:
            file_groups: Dictionary of file groups to process
            runtime_stats: Dictionary to store runtime statistics
            max_workers: Number of concurrent worker threads
            
        Returns:
            List of successfully processed BookMetadata objects
        """
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=Console(),
            transient=True
        ) as progress:
            task = progress.add_task(
                f"Processing {len(file_groups)} files...",
                total=len(file_groups)
            )

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = []

                # Submit all tasks
                for base_name, group_files in file_groups.items():
                    best_source = self.file_group.find_best_isbn_source(group_files)
                    if best_source:
                        future = executor.submit(
                            self.process_single_file,
                            best_source,
                            runtime_stats
                        )
                        futures.append((future, group_files))

                # Process results
                for future, group_files in futures:
                    try:
                        metadata = future.result()
                        if metadata:
                            runtime_stats['successful_results'].append(metadata)
                            ext = Path(group_files[0]).suffix.lower()[1:]
                            runtime_stats['format_stats'][ext]['success'] += 1
                        else:
                            ext = Path(group_files[0]).suffix.lower()[1:]
                            runtime_stats['format_stats'][ext]['failed'] += 1
                    except Exception as e:
                        self.logger.debug(f"Error processing {group_files[0]}: {str(e)}")
                    finally:
                        progress.advance(task)

        return runtime_stats['successful_results']

    def _print_summary(self, runtime_stats: Dict):
        """
        Print final processing summary with clean formatting.
        
        Args:
            runtime_stats: Dictionary containing runtime statistics
        """
        total_files = len(runtime_stats['processed_files'])
        successful = len(runtime_stats['successful_results'])
        failed = total_files - successful
        success_rate = (successful / total_files * 100) if total_files > 0 else 0

        table = Table(title="Processing Summary")
        table.add_column("Category", style="blue")
        table.add_column("Count", justify="right")
        table.add_column("Percentage", justify="right")

        table.add_row(
            "Total Files",
            str(total_files),
            "100%"
        )
        table.add_row(
            "Successful",
            str(successful),
            f"{success_rate:.1f}%"
        )
        table.add_row(
            "Failed",
            str(failed),
            f"{(100 - success_rate):.1f}%"
        )

        print("\nFormat Statistics:")
        format_table = Table()
        format_table.add_column("Format")
        format_table.add_column("Total")
        format_table.add_column("Success")
        format_table.add_column("Failed")
        format_table.add_column("Success Rate")

        for fmt, stats in runtime_stats['format_stats'].items():
            if stats['total'] > 0:
                success_rate = (stats['success'] / stats['total'] * 100)
                format_table.add_row(
                    fmt.upper(),
                    str(stats['total']),
                    str(stats['success']),
                    str(stats['failed']),
                    f"{success_rate:.1f}%"
                )

        Console().print(table)
        Console().print(format_table)



    '''
    def print_final_summary(self, runtime_stats):
        """Imprime um resumo final com proteção total contra divisão por zero e valores nulos."""
        
        # Verifica se runtime_stats existe
        if not runtime_stats:
            print("\nErro: Nenhuma estatística disponível")
            return
            
        try:
            # Inicializa contadores com valores seguros
            extension_stats = defaultdict(lambda: {'total': 0, 'success': 0, 'failed': 0, 'success_rate': 0.0})
            total_files = 0
            total_success = 0
            
            # Conta total de arquivos por extensão com verificações de segurança
            processed_files = runtime_stats.get('processed_files', [])
            if processed_files:
                for file_path in processed_files:
                    if not file_path:  # Pula entradas vazias
                        continue
                    try:
                        if isinstance(file_path, str):
                            ext = Path(file_path).suffix.lower()[1:]
                            if ext in {'pdf', 'epub', 'mobi'}:
                                extension_stats[ext]['total'] += 1
                                total_files += 1
                    except Exception as e:
                        self.logger.debug(f"Ignorando arquivo inválido: {str(e)}")
                        continue
            
            # Conta sucessos por extensão com verificações de segurança
            successful_results = runtime_stats.get('successful_results', [])
            if successful_results:
                for result in successful_results:
                    if not result or not hasattr(result, 'file_path') or not result.file_path:
                        continue
                    try:
                        ext = Path(result.file_path).suffix.lower()[1:]
                        if ext in extension_stats:
                            extension_stats[ext]['success'] += 1
                            total_success += 1
                    except Exception as e:
                        self.logger.debug(f"Ignorando resultado inválido: {str(e)}")
                        continue
            
            # Calcula estatísticas com proteção contra divisão por zero
            for ext in extension_stats:
                stats = extension_stats[ext]
                stats['failed'] = stats['total'] - stats['success']
                try:
                    if stats['total'] > 0:
                        stats['success_rate'] = (stats['success'] / stats['total']) * 100
                except Exception:
                    stats['success_rate'] = 0.0
            
            # Calcula taxa geral de sucesso com proteção
            try:
                overall_rate = (total_success / total_files * 100) if total_files > 0 else 0.0
            except Exception:
                overall_rate = 0.0
            
            # Imprime o relatório
            print("\n" + "=" * 60)
            print(f"{'RESUMO DO PROCESSAMENTO':^60}")
            print("=" * 60)
            
            # Estatísticas gerais
            print("\nEstatísticas Gerais:")
            print("-" * 40)
            print(f"Total de arquivos processados: {total_files}")
            print(f"Total de sucessos: {total_success}")
            print(f"Total de falhas: {total_files - total_success}")
            print(f"Taxa de sucesso geral: {overall_rate:.1f}%")
            
            # Estatísticas por tipo de arquivo
            if any(stats['total'] > 0 for stats in extension_stats.values()):
                print("\nEstatísticas por tipo de arquivo:")
                print("-" * 40)
                
                for ext in sorted(extension_stats.keys()):
                    stats = extension_stats[ext]
                    if stats['total'] > 0:  # Só mostra extensões com arquivos
                        print(f"\n{ext.upper()}:")
                        print(f"  Total: {stats['total']}")
                        print(f"  Sucessos: {stats['success']}")
                        print(f"  Falhas: {stats['failed']}")
                        print(f"  Taxa de Sucesso: {stats['success_rate']:.1f}%")
            
            if 'publisher_stats' in runtime_stats:
                print("\nEstatísticas por Editora:")
                for publisher, stats in runtime_stats['publisher_stats'].items():
                    print(f"{publisher}: {stats['success']}/{stats['total']} sucessos")
            
            # Arquivos gerados
            try:
                print("\nArquivos Gerados:")
                print("-" * 40)
                
                report_files = {
                    'HTML': next((r.get('path', '') for r in runtime_stats.get('generated_reports', []) 
                                if r.get('type') == 'HTML'), None),
                    'JSON': next((r.get('path', '') for r in runtime_stats.get('generated_reports', []) 
                                if r.get('type') == 'JSON'), None),
                    'Log': runtime_stats.get('log_file', '')
                }
                
                for report_type, path in report_files.items():
                    if path:
                        print(f"{report_type + ':':5} {path}")
            except Exception as e:
                self.logger.error(f"Erro ao processar informações de arquivos gerados: {str(e)}")
            
            print("\n" + "=" * 60)
            
        except Exception as e:
            print(f"\nErro ao gerar resumo: {str(e)}")
            self.logger.error(f"Erro ao gerar resumo: {str(e)}")
            import traceback
            self.logger.debug(traceback.format_exc())
    '''


    def print_final_summary(self, runtime_stats: Dict) -> None:
        """
        Main entry point for printing summary information. 
        Maintains backward compatibility while using new modular approach.
        
        Args:
            runtime_stats: Dictionary containing all processing statistics and results
        """
        if not runtime_stats:
            self.logger.warning("No runtime statistics available for summary")
            return
            
        try:
            self._print_full_summary(runtime_stats)
        except Exception as e:
            self.logger.error(f"Error printing summary: {str(e)}")
            # Fallback to original format if available
            self._print_legacy_summary(runtime_stats)

    def _print_full_summary(self, runtime_stats: Dict) -> None:
        """
        Orchestrates the display of all summary tables and statistics in new format.
        
        Args:
            runtime_stats: Dictionary containing processing statistics and results
        """
        # Print each section using modular methods
        self._print_processing_summary_table(runtime_stats)
        self._print_format_statistics_table(runtime_stats)
        self._print_file_processing_results(runtime_stats)
        self._print_report_paths()

    def _print_legacy_summary(self, runtime_stats: Dict) -> None:
        """
        Fallback method using original summary format if needed.
        
        Args:
            runtime_stats: Dictionary containing processing statistics and results
        """
        total_files = len(runtime_stats.get('processed_files', []))
        successful = len(runtime_stats.get('successful_results', []))
        
        print("\nProcessing Summary:")
        print(f"Total Files: {total_files}")
        print(f"Successful: {successful}")
        print(f"Failed: {total_files - successful}")

    def _print_processing_summary_table(self, runtime_stats: Dict) -> None:
        """
        Displays the main processing summary table showing total files and success rates.
        
        Args:
            runtime_stats: Dictionary containing runtime statistics including processed files and results
        """
        total_files = len(runtime_stats['processed_files'])
        successful = len(runtime_stats['successful_results'])
        failed = total_files - successful

        # Create and configure the main summary table
        table = Table(title="Processing Summary")
        table.add_column("Category")
        table.add_column("Count", justify="right")
        table.add_column("Percentage", justify="right")

        # Calculate percentages
        success_rate = (successful / total_files * 100) if total_files > 0 else 0
        failure_rate = (failed / total_files * 100) if total_files > 0 else 0

        # Add rows with proper styling
        table.add_row("Total Files", str(total_files), "100%", style="bright_blue")
        table.add_row("Successful", str(successful), f"{success_rate:.1f}%", style="bright_blue")
        table.add_row("Failed", str(failed), f"{failure_rate:.1f}%", style="bright_blue")

        Console().print("\nFormat Statistics:")
        Console().print(table)

    def _print_format_statistics_table(self, runtime_stats: Dict) -> None:
        """
        Displays detailed statistics breakdown by file format.
        
        Args:
            runtime_stats: Dictionary containing format-specific statistics
        """
        table = Table()
        table.add_column("Format")
        table.add_column("Total", justify="center")
        table.add_column("Success", justify="center")
        table.add_column("Failed", justify="center")
        table.add_column("Success Rate", justify="center")

        format_stats = runtime_stats.get('format_stats', defaultdict(lambda: {'total': 0, 'success': 0, 'failed': 0}))
        
        # Add rows for each format
        for fmt in ['MOBI', 'EPUB', 'PDF']:
            stats = format_stats.get(fmt.lower(), {'total': 0, 'success': 0, 'failed': 0})
            success_rate = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
            
            table.add_row(
                fmt,
                str(stats['total']),
                str(stats['success']),
                str(stats['failed']),
                f"{success_rate:.1f}%"
            )

        Console().print(table)
        Console().print()

    def _print_file_processing_results(self, runtime_stats: Dict) -> None:
        """
        Displays detailed results table for each processed file.
        
        Args:
            runtime_stats: Dictionary containing per-file processing results and metadata
        """
        table = Table(show_header=True, title="Sumário de Processamento")
        table.add_column("Arquivo", no_wrap=True)
        table.add_column("Status", justify="center")
        table.add_column("Tempo", justify="right")
        table.add_column("Detalhes")

        # Process each file result
        for file_path in runtime_stats['processed_files']:
            file_name = Path(file_path).name
            time_taken = runtime_stats['processing_times'].get(file_path, 0.0)
            
            # Determine status and details
            success = any(result.file_path == file_path for result in runtime_stats['successful_results'])
            
            if success:
                status = "[green]✓ success[/green]"
                for result in runtime_stats['successful_results']:
                    if result.file_path == file_path:
                        details = f"ISBN: {result.isbn_13 or result.isbn_10}"
                        break
            else:
                status = "[red]✗ failed[/red]"
                details = "ISBN: Not found"

            table.add_row(
                file_name,
                status,
                f"{time_taken:.2f}s",
                details
            )

        Console().print(table)

    def _print_report_paths(self) -> None:
        """
        Displays paths to generated report files.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_path = f"reports/report_{timestamp}"
        
        for report_type in ["HTML", "JSON", "LOG"]:
            suffix = "_metadata.log" if report_type == "LOG" else f".{report_type.lower()}"
            path = f"{base_path}{suffix}"
            Console().print(f"{report_type:<4} {path}")

    def print_final_summary(self, runtime_stats: Dict) -> None:
        """
        Orchestrates the display of all summary tables and statistics.
        
        Args:
            runtime_stats: Dictionary containing all processing statistics and results
        """
        self._print_processing_summary_table(runtime_stats)
        self._print_format_statistics_table(runtime_stats)
        self._print_file_processing_results(runtime_stats)
        self._print_report_paths()

    def _calculate_metadata_completeness(self, metadata: BookMetadata) -> float:
        """
        Calcula a porcentagem de campos preenchidos nos metadados.
        """
        fields = ['title', 'authors', 'publisher', 'published_date', 'isbn_13', 'isbn_10']
        filled = sum(1 for field in fields if getattr(metadata, field) and getattr(metadata, field) != "Unknown")
        return (filled / len(fields)) * 100

    def _calculate_advanced_statistics(self, runtime_stats: Dict, results: List[BookMetadata]):
        """
        Calcula estatísticas avançadas sobre os metadados.
        """
        if not results:
            return
            
        stats = runtime_stats.setdefault('advanced_stats', {})
        
        # Estatísticas de qualidade
        quality_scores = runtime_stats['quality_scores']
        stats['quality'] = {
            'mean': statistics.mean(quality_scores),
            'median': statistics.median(quality_scores),
            'std_dev': statistics.stdev(quality_scores) if len(quality_scores) > 1 else 0,
            'min': min(quality_scores),
            'max': max(quality_scores)
        }
        
        # Estatísticas de completude
        completeness = runtime_stats['metadata_completeness']
        stats['completeness'] = {
            'mean': statistics.mean(completeness),
            'median': statistics.median(completeness),
            'std_dev': statistics.stdev(completeness) if len(completeness) > 1 else 0,
            'min': min(completeness),
            'max': max(completeness)
        }
        
        # Estatísticas por fonte
        sources = Counter(r.source for r in results)
        stats['sources'] = dict(sources)
        
        # Estatísticas por editora
        publishers = Counter(r.publisher for r in results)
        stats['publishers'] = dict(publishers)
        
        # Estatísticas por ano
        years = Counter(r.published_date.split('-')[0] for r in results 
                    if r.published_date and r.published_date != "Unknown")
        stats['years'] = dict(years)

    def _calculate_metadata_quality(self, metadata: BookMetadata) -> float:
        """
        Calcula uma pontuação de qualidade para os metadados.
        """
        score = 0.0
        total_weight = 0.0
        
        # Título (peso 2.0)
        if metadata.title and metadata.title != "Unknown":
            score += 2.0 * min(1.0, len(metadata.title) / 50)
        total_weight += 2.0
        
        # Autores (peso 1.5)
        if metadata.authors and metadata.authors != ["Unknown"]:
            score += 1.5 * min(1.0, len(metadata.authors) / 3)
        total_weight += 1.5
        
        # Editora (peso 1.0)
        if metadata.publisher and metadata.publisher != "Unknown":
            score += 1.0
        total_weight += 1.0
        
        # Data de publicação (peso 1.0)
        if metadata.published_date and metadata.published_date != "Unknown":
            score += 1.0
        total_weight += 1.0
        
        # ISBN (peso 2.0)
        if metadata.isbn_13:
            score += 2.0
        elif metadata.isbn_10:
            score += 1.5
        total_weight += 2.0
        
        # Múltiplos formatos (peso 0.5)
        if metadata.file_paths and len(metadata.file_paths) > 1:
            score += 0.5
        total_weight += 0.5
        
        return (score / total_weight) * 100

    def fetch_isbnlib_info(self, isbn: str) -> Optional[BookMetadata]:
        """Fetch usando isbnlib com melhor suporte a variantes."""
        try:
            import isbnlib
            
            # Validação inicial
            if not (isbnlib.is_isbn13(isbn) or isbnlib.is_isbn10(isbn)):
                return None
                
            # Tenta diferentes serviços do isbnlib
            services = ['default', 'goob', 'merge']
            metadata = None
            
            for service in services:
                try:
                    metadata = isbnlib.meta(isbn, service=service)
                    if metadata:
                        break
                except:
                    continue
                    
            if not metadata:
                return None
                
            return BookMetadata(
                title=metadata.get('Title', '').strip(),
                authors=[a.strip() for a in metadata.get('Authors', [])],
                publisher=metadata.get('Publisher', '').strip(),
                published_date=metadata.get('Year', 'Unknown'),
                isbn_13=isbn if len(isbn) == 13 else isbnlib.to_isbn13(isbn),
                isbn_10=isbn if len(isbn) == 10 else isbnlib.to_isbn10(isbn),
                confidence_score=self.confidence_adjustments['isbnlib_info'],
                source='isbnlib_info'
            )
        except Exception as e:
            self._handle_api_error('isbnlib_info', e, isbn)
            return None

    def fetch_crossref(self, isbn: str) -> Optional[BookMetadata]:
        """Fetch from CrossRef API com validação aprimorada."""
        try:
            url = "https://api.crossref.org/works"
            params = {
                'filter': f'isbn:{isbn}',
                'select': 'title,author,published-print,publisher'
            }
            
            response = self._make_request('crossref', url, params=params)
            data = response.json()
            
            if not data['message']['items']:
                return None
                
            item = data['message']['items'][0]
            
            return BookMetadata(
                title=item['title'][0] if item.get('title') else '',
                authors=[
                    f"{a.get('given', '')} {a.get('family', '')}".strip()
                    for a in item.get('author', [])
                ],
                publisher=item.get('publisher', ''),
                published_date=str(item.get('published-print', {})
                                .get('date-parts', [['']])[0][0]),
                isbn_13=isbn if len(isbn) == 13 else None,
                isbn_10=isbn if len(isbn) == 10 else None,
                confidence_score=self.confidence_adjustments['crossref'],
                source='crossref'
            )
        except Exception as e:
            self._handle_api_error('crossref', e, isbn)
            return None

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

    def _process_file_group(self, files: List[Path], runtime_stats: Dict) -> Optional[BookMetadata]:
        """Processa grupo de arquivos com mesmo nome base."""
        metadata = None
        combined_isbns = set()
        
        # Tenta cada arquivo do grupo
        for file_path in sorted(files):  # Ordena para tentar PDF primeiro
            ext = file_path.suffix.lower()
            
            try:
                if ext == '.pdf':
                    metadata = self.process_single_file(str(file_path), runtime_stats)
                elif ext in {'.epub', '.mobi'}:
                    # Usa o EbookProcessor
                    text, methods = self.ebook_processor.extract_text_from_epub(str(file_path)) \
                                if ext == '.epub' else \
                                self.ebook_processor.extract_text_from_mobi(str(file_path))
                                
                    ebook_metadata = self.ebook_processor.extract_metadata(str(file_path))
                    if ebook_metadata.get('isbn'):
                        combined_isbns.add(ebook_metadata['isbn'])
                        
                    isbns = self.isbn_extractor.extract_from_text(text)
                    combined_isbns.update(isbns)
            except Exception as e:
                self.logger.error(f"Erro processando {file_path}: {str(e)}")
                continue
        
        # Se encontrou ISBNs em qualquer arquivo do grupo
        if combined_isbns:
            for isbn in sorted(combined_isbns):
                try:
                    metadata = self.metadata_fetcher.fetch_metadata(isbn)
                    if metadata:
                        # Atualiza file_path para incluir todos os arquivos do grupo
                        metadata.file_paths = [str(f) for f in files]
                        return metadata
                except Exception as e:
                    self.logger.error(f"Erro obtendo metadados para ISBN {isbn}: {str(e)}")
                    
        return metadata

    def _generate_html_report(self, results, source_stats, publisher_stats, 
                            runtime_stats, total_files, successful, failed, avg_time, output_file):
        """Gera relatório HTML completo com visualizações."""
        
        # CSS personalizado para o relatório
        css = """
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .card { background: #fff; padding: 20px; margin: 10px 0; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
            table { width: 100%; border-collapse: collapse; margin: 10px 0; }
            th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
            .success { color: #28a745; }
            .failure { color: #dc3545; }
            .chart-container { height: 400px; margin: 20px 0; }
            .tab-content { display: none; }
            .tab-content.active { display: block; }
            .nav-tabs { margin-bottom: 20px; }
            .nav-tabs button { padding: 10px 20px; margin-right: 5px; border: none; background: #f8f9fa; cursor: pointer; }
            .nav-tabs button.active { background: #007bff; color: white; }
        </style>
        """

        # JavaScript para interatividade
        javascript = """
        <script>
            function showTab(tabId) {
                document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
                document.querySelectorAll('.nav-tabs button').forEach(btn => btn.classList.remove('active'));
                document.getElementById(tabId).classList.add('active');
                document.querySelector(`button[data-tab="${tabId}"]`).classList.add('active');
            }
        </script>
        """

        # Adiciona contagem por extensão
        extension_stats = defaultdict(lambda: {'total': 0, 'success': 0, 'failed': 0})
        
        # Processa estatísticas por extensão
        for file_path in runtime_stats['processed_files']:
            ext = Path(file_path).suffix.lower()[1:]
            extension_stats[ext]['total'] += 1
        
        for result in results:
            if result and result.file_path:
                ext = Path(result.file_path).suffix.lower()[1:]
                extension_stats[ext]['success'] += 1
        
        for ext in extension_stats:
            extension_stats[ext]['failed'] = (
                extension_stats[ext]['total'] - extension_stats[ext]['success']
            )

        # Gera o HTML
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Book Metadata Report</title>
            {css}
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        </head>
        <body>
            <h1>Book Metadata Report</h1>
            
            <div class="nav-tabs">
                <button onclick="showTab('overview')" data-tab="overview" class="active">Overview</button>
                <button onclick="showTab('details')" data-tab="details">Details</button>
                <button onclick="showTab('failures')" data-tab="failures">Failures</button>
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

                    <h3>Statistics by File Type</h3>
                    <table>
                        <tr>
                            <th>Extension</th>
                            <th>Total</th>
                            <th>Successful</th>
                            <th>Failed</th>
                            <th>Success Rate</th>
                        </tr>
                        {self._generate_extension_rows(extension_stats)}
                    </table>
                    <div id="extensionChart" class="chart-container"></div>
                </div>
            </div>

            <div id="details" class="tab-content">
                <div class="card">
                    <h2>Successful Extractions</h2>
                    <table>
                        <tr>
                            <th>File</th>
                            <th>Title</th>
                            <th>Authors</th>
                            <th>ISBN</th>
                            <th>Publisher</th>
                            <th>Source</th>
                        </tr>
                        {self._generate_success_rows(results)}
                    </table>
                </div>
            </div>

            <div id="failures" class="tab-content">
                <div class="card">
                    <h2>Failed Extractions</h2>
                    <table>
                        <tr>
                            <th>File</th>
                            <th>Error</th>
                            <th>Details</th>
                        </tr>
                        {self._generate_failure_rows(runtime_stats)}
                    </table>
                </div>
            </div>

            {javascript}
            
            <script>
                // Gráfico de estatísticas por extensão
                const extensionData = {self._generate_extension_chart_data(extension_stats)};
                Plotly.newPlot('extensionChart', extensionData, {
                    'title': 'Success Rate by File Type',
                    'barmode': 'stack',
                    'showlegend': true
                });
            </script>
        </body>
        </html>
        """

        # Salva o arquivo HTML
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
            
    # Atualiza o relatório JSON também
    def _generate_json_report(self, results, source_stats, publisher_stats, 
                            runtime_stats, total_files, successful, failed, avg_time, output_file):
        """Gera relatório JSON detalhado."""
        # Calcula estatísticas por extensão
        extension_stats = defaultdict(lambda: {'total': 0, 'success': 0, 'failed': 0})
        
        for file_path in runtime_stats['processed_files']:
            ext = Path(file_path).suffix.lower()[1:]
            extension_stats[ext]['total'] += 1
        
        for result in results:
            if result and result.file_path:
                ext = Path(result.file_path).suffix.lower()[1:]
                extension_stats[ext]['success'] += 1
        
        for ext in extension_stats:
            extension_stats[ext]['failed'] = (
                extension_stats[ext]['total'] - extension_stats[ext]['success']
            )

        report_data = {
            'summary': {
                'total_files': total_files,
                'successful': successful,
                'failed': failed,
                'success_rate': (successful/total_files*100) if total_files > 0 else 0,
                'average_processing_time': avg_time,
                'by_extension': dict(extension_stats),  # Adiciona estatísticas por extensão
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
            'results': [asdict(r) for r in results if r is not None]
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

    def _generate_extension_rows(self, extension_stats: Dict) -> str:
        """Gera as linhas da tabela de estatísticas por extensão."""
        rows = []
        for ext, stats in extension_stats.items():
            success_rate = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
            rows.append(f"""
                <tr>
                    <td>{ext.upper()}</td>
                    <td>{stats['total']}</td>
                    <td class="success">{stats['success']}</td>
                    <td class="failure">{stats['failed']}</td>
                    <td>{success_rate:.1f}%</td>
                </tr>
            """)
        return '\n'.join(rows)

    def _generate_success_rows(self, results: List[BookMetadata]) -> str:
        """Gera as linhas da tabela de extrações bem-sucedidas."""
        rows = []
        for result in results:
            if result:
                rows.append(f"""
                    <tr>
                        <td>{Path(result.file_path).name}</td>
                        <td>{result.title}</td>
                        <td>{', '.join(result.authors)}</td>
                        <td>{result.isbn_13 or result.isbn_10 or 'N/A'}</td>
                        <td>{result.publisher}</td>
                        <td>{result.source}</td>
                    </tr>
                """)
        return '\n'.join(rows)

    def _generate_failure_rows(self, runtime_stats: Dict) -> str:
        """Gera as linhas da tabela de falhas."""
        rows = []
        for file_path, details in runtime_stats['failure_details'].items():
            if details.get('status') != 'Success':
                rows.append(f"""
                    <tr>
                        <td>{Path(file_path).name}</td>
                        <td>{details.get('error', 'Unknown error')}</td>
                        <td>{self._format_failure_details(details)}</td>
                    </tr>
                """)
        return '\n'.join(rows)

    def _format_failure_details(self, details: Dict) -> str:
        """Formata os detalhes da falha para exibição."""
        formatted = []
        if details.get('methods_tried'):
            formatted.append(f"Methods tried: {', '.join(details['methods_tried'])}")
        if details.get('found_isbns'):
            formatted.append(f"ISBNs found: {', '.join(details['found_isbns'])}")
        if details.get('api_attempts'):
            formatted.append(f"APIs attempted: {', '.join(details['api_attempts'])}")
        return '<br>'.join(formatted)

    def _generate_extension_chart_data(self, extension_stats: Dict) -> str:
        """Gera dados para o gráfico de estatísticas por extensão."""
        extensions = list(extension_stats.keys())
        successful = [stats['success'] for stats in extension_stats.values()]
        failed = [stats['failed'] for stats in extension_stats.values()]
        
        return f"""[
            {{
                x: {extensions},
                y: {successful},
                name: 'Successful',
                type: 'bar',
                marker: {{color: '#28a745'}}
            }},
            {{
                x: {extensions},
                y: {failed},
                name: 'Failed',
                type: 'bar',
                marker: {{color: '#dc3545'}}
            }}
        ]"""

    def _generate_reports(self, runtime_stats: Dict):
        """
        Generate all reports (HTML, JSON, and log) in the reports directory with consistent naming.
        
        Args:
            runtime_stats: Dictionary containing runtime statistics
            
        Generates:
            - HTML report
            - JSON report with full metadata
            - Log file
        All files use consistent timestamp and are stored in reports directory.
        """
        if not runtime_stats:
            self.logger.error("Invalid runtime_stats data")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            # Ensure reports directory exists
            self.reports_dir.mkdir(exist_ok=True)
            
            # Define consistent file paths
            html_path = self.reports_dir / f"report_{timestamp}.html"
            json_path = self.reports_dir / f"report_{timestamp}.json"
            log_path = self.reports_dir / f"report_{timestamp}_metadata.log"
            
            # Generate reports
            report_data = self._prepare_report_data(runtime_stats)
            
            # Generate HTML report
            self._generate_html_report(report_data, html_path)
            
            # Generate JSON report (combined format)
            json_data = {
                "report_metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "total_files_processed": len(runtime_stats['processed_files']),
                    "successful_extractions": len(runtime_stats['successful_results']),
                    "failed_extractions": len(runtime_stats['failure_details'])
                },
                "summary_statistics": report_data['summary'],
                "format_statistics": report_data['details']['format_stats'],
                "successful_extractions": report_data['details']['successful'],
                "failed_extractions": runtime_stats['failure_details']
            }
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
                
            # Move log file to reports directory
            log_file = Path("book_metadata.log")
            if log_file.exists():
                shutil.move(log_file, log_path)
                
            # Update runtime stats with file locations
            runtime_stats['generated_reports'] = [
                {'type': 'HTML', 'path': str(html_path)},
                {'type': 'JSON', 'path': str(json_path)},
                {'type': 'LOG', 'path': str(log_path)}
            ]
            
            self.logger.info(f"Reports generated successfully in {self.reports_dir}")
            # Print report locations
            print("\nArquivos Gerados:")
            print("-" * 40)
            print(f"HTML {html_path}")
            print(f"JSON {json_path}") 
            print(f"LOG  {log_path}")
                        
        except Exception as e:
            self.logger.error(f"Error generating reports: {str(e)}")
            self.logger.error(traceback.format_exc())

    def _init_logging(self):
        """Initialize logging configuration."""
        self.logger = logging.getLogger('book_metadata_extractor')  # Use o nome específico da classe
        self.logger.setLevel(logging.DEBUG)  # Nível detalhado para o arquivo
        
        if not self.logger.handlers:
            # File handler - captura tudo para o arquivo
            file_handler = logging.FileHandler('book_metadata_extractor.log')
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            ))
            file_handler.setLevel(logging.DEBUG)
            
            # Console handler - apenas warnings e erros
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(
                '%(levelname)s - %(message)s'
            ))
            console_handler.setLevel(logging.WARNING)
            
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)
    
    def _generate_html_report(self, data: Dict, output_file: Path):
        """Gera relatório HTML usando nomes de parâmetros consistentes."""
        # O resto do método permanece o mesmo, apenas mudando html_path para output_file
        html_content = self._generate_html_content(data)
        output_file.write_text(html_content)

    def _generate_html_content(self, data: Dict) -> str:
        """
        Generates HTML content for the report using a safer approach to string formatting.
        The HTML and CSS are defined as raw strings to prevent formatting conflicts.
        """
        # Define the CSS as a raw string to preserve formatting exactly
        css = r"""
            body { font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }
            .card { background: #fff; padding: 20px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
            table { width: 100%; border-collapse: collapse; margin: 10px 0; }
            th, td { padding: 12px 8px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background-color: #f5f5f5; }
            .success { color: #28a745; }
            .failure { color: #dc3545; }
            .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        """

        # First, let's create our dynamic content sections
        format_stats_rows = []
        for fmt, stats in data['details']['format_stats'].items():
            success_rate = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
            row = f"""
                <tr>
                    <td>{fmt.upper()}</td>
                    <td>{stats['total']}</td>
                    <td class="success">{stats['success']}</td>
                    <td class="failure">{stats['failed']}</td>
                    <td>{success_rate:.1f}%</td>
                </tr>"""
            format_stats_rows.append(row)

        success_rows = []
        for book in data['details']['successful']:
            row = f"""
                <tr>
                    <td>{Path(book['file_path']).name}</td>
                    <td>{book['title']}</td>
                    <td>{', '.join(book['authors'])}</td>
                    <td>{book['isbn_13'] or book['isbn_10'] or 'N/A'}</td>
                    <td>{book['source']}</td>
                </tr>"""
            success_rows.append(row)

        failure_rows = []
        for file_path, error in data['details']['failures'].items():
            row = f"""
                <tr>
                    <td>{Path(file_path).name}</td>
                    <td>{error.get('error', 'Unknown error')}</td>
                    <td>{error.get('details', '')}</td>
                </tr>"""
            failure_rows.append(row)

        # Now construct the complete HTML using string concatenation instead of format()
        html = f"""<!DOCTYPE html>
        <html>
        <head>
            <title>Book Metadata Report</title>
            <style>
                {css}
            </style>
        </head>
        <body>
            <h1>Book Metadata Report</h1>
            
            <div class="card">
                <h2>Summary</h2>
                <div class="stats-grid">
                    <table>
                        <tr><th>Total Files</th><td>{data['summary']['total_files']}</td></tr>
                        <tr><th>Successful</th><td class="success">{data['summary']['successful']}</td></tr>
                        <tr><th>Failed</th><td class="failure">{data['summary']['failed']}</td></tr>
                        <tr><th>Success Rate</th><td>{data['summary']['success_rate']:.1f}%</td></tr>
                        <tr><th>Average Time</th><td>{data['summary']['average_time']:.2f}s</td></tr>
                    </table>
                </div>
            </div>

            <div class="card">
                <h2>Format Statistics</h2>
                <table>
                    <tr>
                        <th>Format</th>
                        <th>Total</th>
                        <th>Success</th>
                        <th>Failed</th>
                        <th>Success Rate</th>
                    </tr>
                    {''.join(format_stats_rows)}
                </table>
            </div>

            <div class="card">
                <h2>Successful Extractions</h2>
                <table>
                    <tr>
                        <th>File</th>
                        <th>Title</th>
                        <th>Authors</th>
                        <th>ISBN</th>
                        <th>Source</th>
                    </tr>
                    {''.join(success_rows)}
                </table>
            </div>

            <div class="card">
                <h2>Failed Extractions</h2>
                <table>
                    <tr>
                        <th>File</th>
                        <th>Error</th>
                        <th>Details</th>
                    </tr>
                    {''.join(failure_rows)}
                </table>
            </div>
        </body>
        </html>"""

        return html

    def _generate_json_report(self, data: Dict, output_file: Path):
        """Gera relatório JSON usando nomes de parâmetros consistentes."""
        # O resto do método permanece o mesmo, apenas mudando json_path para output_file
        json_data = self._prepare_json_data(data)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
            
    def _calculate_format_stats(self, runtime_stats: Dict) -> Dict[str, Dict[str, int]]:
        """
        Calcula estatísticas por formato de arquivo.
        
        Args:
            runtime_stats: Dicionário com estatísticas de execução
            
        Returns:
            Dicionário com estatísticas por formato
        """
        format_stats = defaultdict(lambda: {'total': 0, 'success': 0, 'failed': 0})
        
        # Conta totais por formato
        for file_path in runtime_stats['processed_files']:
            ext = Path(file_path).suffix.lower()[1:]
            format_stats[ext]['total'] += 1
        
        # Conta sucessos por formato
        for result in runtime_stats['successful_results']:
            if result and result.file_path:
                ext = Path(result.file_path).suffix.lower()[1:]
                format_stats[ext]['success'] += 1
        
        # Calcula falhas
        for fmt in format_stats:
            format_stats[fmt]['failed'] = (
                format_stats[fmt]['total'] - format_stats[fmt]['success']
            )
            
        return dict(format_stats)

    def _prepare_json_data(self, data: Dict) -> Dict:
        """
        Prepares data for JSON report by organizing and structuring the information.
        
        This method transforms the raw processing data into a well-organized JSON structure
        that's both readable and useful for later analysis.
        """
        # Get basic statistics
        successful_results = data['details']['successful']
        format_stats = data['details']['format_stats']
        
        # Calculate additional metrics
        api_usage = Counter(result['source'] for result in successful_results)
        publishers = Counter(result['publisher'] for result in successful_results)
        
        # Organize data into a structured format
        json_data = {
            "report_metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_files_processed": data['summary']['total_files'],
                "processing_duration": f"{data['summary']['average_time']:.2f}s"
            },
            "summary_statistics": {
                "total_files": data['summary']['total_files'],
                "successful_extractions": data['summary']['successful'],
                "failed_extractions": data['summary']['failed'],
                "success_rate_percentage": round(data['summary']['success_rate'], 2),
                "average_processing_time": round(data['summary']['average_time'], 2)
            },
            "format_statistics": {
                fmt: {
                    "total": stats["total"],
                    "successful": stats["success"],
                    "failed": stats["failed"],
                    "success_rate_percentage": round((stats["success"] / stats["total"] * 100) if stats["total"] > 0 else 0, 2)
                } for fmt, stats in format_stats.items()
            },
            "api_statistics": {
                "sources_used": dict(api_usage),
                "most_successful_source": api_usage.most_common(1)[0][0] if api_usage else "None"
            },
            "publisher_statistics": {
                "total_publishers": len(publishers),
                "publisher_distribution": dict(publishers)
            },
            "successful_extractions": [
                {
                    "filename": Path(result["file_path"]).name,
                    "title": result["title"],
                    "authors": result["authors"],
                    "publisher": result["publisher"],
                    "isbn": result["isbn_13"] or result["isbn_10"] or "N/A",
                    "source": result["source"],
                    "confidence_score": round(result["confidence_score"], 2)
                } for result in successful_results
            ],
            "failed_extractions": [
                {
                    "filename": Path(file_path).name,
                    "error_type": error.get("error", "Unknown error"),
                    "error_details": error.get("details", "No details available")
                } for file_path, error in data["details"]["failures"].items()
            ]
        }
        
        return json_data

    def _generate_format_stats_rows(self, format_stats: Dict) -> str:
        """Gera linhas HTML para estatísticas de formato."""
        rows = []
        for fmt, stats in format_stats.items():
            rows.append(f"""
                <tr>
                    <td>{fmt.upper()}</td>
                    <td>{stats['total']}</td>
                    <td class="success">{stats['success']}</td>
                    <td class="failure">{stats['failed']}</td>
                </tr>
            """)
        return '\n'.join(rows)

    def _generate_publisher_stats_rows(self, publisher_stats: Dict) -> str:
        """Gera linhas HTML para estatísticas de editora."""
        return '\n'.join(
            f"""
            <tr>
                <td>{publisher}</td>
                <td>{count}</td>
            </tr>
            """
            for publisher, count in sorted(publisher_stats.items(), 
                                        key=lambda x: x[1], 
                                        reverse=True)
        )

    def _generate_success_rows(self, successful_books: List[Dict]) -> str:
        """Gera linhas HTML para livros processados com sucesso."""
        return '\n'.join(
            f"""
            <tr>
                <td>{Path(book['file_path']).name}</td>
                <td>{book['title']}</td>
                <td>{', '.join(book['authors'])}</td>
                <td>{book['publisher']}</td>
                <td>{book['isbn_13'] or book['isbn_10']}</td>
                <td>{book['source']}</td>
            </tr>
            """
            for book in successful_books
        )

    def _generate_failure_rows(self, failures: Dict) -> str:
        """Gera linhas HTML para falhas de processamento."""
        return '\n'.join(
            f"""
            <tr>
                <td>{Path(file_path).name}</td>
                <td>{error.get('error', 'Unknown error')}</td>
                <td>{', '.join(str(detail) for detail in error.values() if detail != error.get('error'))}</td>
            </tr>
            """
            for file_path, error in failures.items()
        )

    def suggest_filename(self, metadata: BookMetadata) -> str:
            """
            Sugere um nome de arquivo baseado nos metadados do livro.
            
            Args:
                metadata: Objeto BookMetadata contendo os metadados do livro
                
            Returns:
                String com o nome de arquivo sugerido, incluindo extensão
                
            O nome do arquivo é gerado seguindo o padrão:
            titulo-autores-ano.extensao
            
            Onde:
            - título é limitado a 50 caracteres
            - autores são os dois primeiros autores separados por vírgula
            - ano é extraído da data de publicação
            - extensão é mantida do arquivo original
            """
            def clean_string(s: str) -> str:
                """Limpa uma string para uso em nome de arquivo."""
                # Normaliza caracteres Unicode
                s = unicodedata.normalize('NFKD', s)
                # Remove caracteres acentuados
                s = s.encode('ASCII', 'ignore').decode('ASCII')
                # Mantém apenas caracteres alfanuméricos e alguns separadores
                s = re.sub(r'[^\w\s-]', '', s)
                # Substitui espaços por underscores e remove espaços extras
                return s.strip().replace(' ', '_')
            
            # Limpa e limita o título
            title = clean_string(metadata.title)
            max_title_length = 50
            if len(title) > max_title_length:
                # Se precisar truncar, tenta não cortar no meio de uma palavra
                title = title[:max_title_length].rsplit('_', 1)[0] + '...'
            
            # Pega no máximo os dois primeiros autores
            authors = clean_string(', '.join(metadata.authors[:2]))
            
            # Extrai o ano da data de publicação
            if metadata.published_date and '-' in metadata.published_date:
                year = metadata.published_date.split('-')[0]
            else:
                year = metadata.published_date or 'unknown_year'
            
            # Monta o nome base do arquivo
            base_name = f"{title}-{authors}-{year}"

            # Se o livro tem múltiplos formatos
            if hasattr(metadata, 'formats') and metadata.formats:
                # Retorna um dicionário com um nome para cada formato
                return {fmt: f"{base_name}.{fmt}" for fmt in metadata.formats}
            
            # Se não, usa a extensão do arquivo original
            ext = Path(metadata.file_path).suffix.lower()[1:]
            return f"{base_name}.{ext}"

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
        self._init_logging()
        self.publisher_patterns = {
            'springer': [r'springer', r'apress'],
            'oreilly': [r"o'reilly", r'oreilly'],
            'packt': [r'packt'],
            'manning': [r'manning'],
            'casa_do_codigo': [r'casa\s+do\s+c[oó]digo'],
            'novatec': [r'novatec'],
            'alta_books': [r'alta\s+books']
        }

    def _init_logging(self):
        """Initialize logging configuration."""
        self.logger = logging.getLogger('metadata_validator')  # Use o nome específico da classe
        self.logger.setLevel(logging.DEBUG)  # Nível detalhado para o arquivo
        
        if not self.logger.handlers:
            # File handler - captura tudo para o arquivo
            file_handler = logging.FileHandler('metadata_validator.log')
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            ))
            file_handler.setLevel(logging.DEBUG)
            
            # Console handler - apenas warnings e erros
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(
                '%(levelname)s - %(message)s'
            ))
            console_handler.setLevel(logging.WARNING)
            
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)

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
        self._init_logging()
        self.error_counts = defaultdict(Counter)
        self.last_errors = defaultdict(dict)
        self.error_thresholds = {
            'timeout': 3,
            'connection': 5,
            'api': 3,
            'validation': 2
        }

    def _init_logging(self):
        """Initialize logging configuration."""
        self.logger = logging.getLogger('error_handler')  # Use o nome específico da classe
        self.logger.setLevel(logging.DEBUG)  # Nível detalhado para o arquivo
        
        if not self.logger.handlers:
            # File handler - captura tudo para o arquivo
            file_handler = logging.FileHandler('error_handler.log')
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            ))
            file_handler.setLevel(logging.DEBUG)
            
            # Console handler - apenas warnings e erros
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(
                '%(levelname)s - %(message)s'
            ))
            console_handler.setLevel(logging.WARNING)
            
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)

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
        self.logger.error(
            f"API Error in {api_name} for ISBN {isbn}\n"
            f"Category: {category}\n"
            f"Error: {error_msg}\n"
            f"Count: {self.error_counts[api_name][category]}"
        )

        # Check if should retry based on error category and count
        threshold = self.error_thresholds.get(category, 3)
        if self.error_counts[api_name][category] >= threshold:
            self.logger.warning(
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
            self.logger.warning(f"API {api_name} shows poor health. Consider alternative.")
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
        self._init_logging()
        self.metrics = defaultdict(list)
        self.errors = defaultdict(Counter)
        
    def add_metric(self, api_name: str, response_time: float, success: bool):
        self.metrics[api_name].append({
            'timestamp': time.time(),
            'response_time': response_time,
            'success': success
        })

    def _init_logging(self):
        """Initialize logging configuration."""
        self.logger = logging.getLogger('metrics_collector')  # Use o nome específico da classe
        self.logger.setLevel(logging.DEBUG)  # Nível detalhado para o arquivo
        
        if not self.logger.handlers:
            # File handler - captura tudo para o arquivo
            file_handler = logging.FileHandler('metrics_collector.lower.log')
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            ))
            file_handler.setLevel(logging.DEBUG)
            
            # Console handler - apenas warnings e erros
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(
                '%(levelname)s - %(message)s'
            ))
            console_handler.setLevel(logging.WARNING)
            
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)

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

class EbookProcessor:
    """Enhanced processor for ebook files (EPUB and MOBI) with working implementation from isbn_diagnostic."""
    
    def __init__(self):
        """Initialize the ebook processor with logging support."""
        self._init_logging()
        
        # ISBN patterns ordered by reliability and specificity
        self.isbn_patterns = [
            # Casa do Código specific patterns (highest priority)
            r'Impresso:\s*(978-85-5519-[0-9]{3}-[0-9])',  # Matches exactly CDC pattern
            r'Digital:\s*(978-85-5519-[0-9]{3}-[0-9])',   # Matches exactly CDC pattern
            
            # O'Reilly patterns
            r'O\'Reilly\s+(?:Media|Publishing).*?ISBN[:\s-]*(97[89]\d{10})',
            r'(?:Print|eBook|Digital)\s+ISBN[:\s-]*(97[89]\d{10})',
            r'oreilly\.com/catalog/[^/]+/?ISBN[:\s-]*(97[89]\d{10})',
            r'shop\.oreilly\.com/product/[^/]+/?ISBN[:\s-]*(97[89]\d{10})',
            
            # Brazilian publishers with specific prefixes
            r'(?:Casa do Código|CDC|casadocodigo)[^\n]*?ISBN[:\s-]*(978-85-5519-[0-9]{3}-[0-9])',
            r'(?:Novatec)[^\n]*?ISBN[:\s-]*(978-85-7522-[0-9]{3}-[0-9])',
            r'(?:Alta Books)[^\n]*?ISBN[:\s-]*(978-85-508-[0-9]{3}-[0-9])',
            
            # Standard ISBN formats
            r'ISBN-13[:\s-]*(97[89]\d{10})',
            r'ISBN[:\s-]*(97[89]\d{10})',
            
            # Generic formats with context
            r'(?:Impresso|Digital|Print|eBook)[:\s]+([0-9-]+)',
            r'ISBN(?:-1[03])?[:\s]+([0-9-]+)',
            
            # Fallback patterns
            r'(?:Casa do Código|CDC)[^\n]*?([0-9]{3}[- ]?[0-9]+[- ]?[0-9]+[- ]?[0-9]+[- ]?[0-9])',
            r'97[89](?:[- ]?\d){10}',
            r'\d{9}[\dXx]'
        ]
        
        # Add publisher identifier prefixes
        self.publisher_prefixes = {
            'casa_do_codigo': '978855519',
            'novatec': '9788575',
            'alta_books': '978855508'
        }
        
        # Add publisher validation patterns
        self.publisher_markers = {
            'casa_do_codigo': [
                r'Casa do Código',
                r'casadocodigo\.com\.br',
                r'erratas\.casadocodigo\.com\.br'
            ],
            'novatec': [
                r'Novatec Editora',
                r'novatec\.com\.br'
            ],
            'alta_books': [
                r'Alta Books',
                r'altabooks\.com\.br'
            ]
        }

    def _init_logging(self):
        """Initialize logging configuration."""
        self.logger = logging.getLogger('ebook_processor')  # Use o nome específico da classe
        self.logger.setLevel(logging.DEBUG)  # Nível detalhado para o arquivo
        
        if not self.logger.handlers:
            # File handler - captura tudo para o arquivo
            file_handler = logging.FileHandler('ebook_processor.log')
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            ))
            file_handler.setLevel(logging.DEBUG)
            
            # Console handler - apenas warnings e erros
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(
                '%(levelname)s - %(message)s'
            ))
            console_handler.setLevel(logging.WARNING)
            
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)

    def extract_text_from_epub(self, epub_path: str) -> Tuple[str, List[str]]:
        """
        Extract text content from EPUB files with enhanced ISBN detection and logging.

        Args:
            epub_path: Path to the EPUB file

        Returns:
            Tuple containing extracted text and list of methods attempted
        """
        methods_tried = ["ebooklib"]
        text_sections = []
        found_isbns = set()
        
        self.logger.info(f"Processing EPUB file: {epub_path}")
        
        try:
            book = epub.read_epub(epub_path)
            
            # Log metadata availability
            self.logger.debug("Checking Dublin Core metadata...")
            dc_identifiers = book.get_metadata('DC', 'identifier')
            if dc_identifiers:
                self.logger.debug(f"Found {len(dc_identifiers)} DC identifiers")
                
                for ident in dc_identifiers:
                    self.logger.debug(f"Processing identifier: {ident}")
                    isbn_match = re.search(r'(?:97[89]\d{10})|(?:\d{9}[\dXx])', str(ident[0]))
                    if isbn_match:
                        isbn = isbn_match.group(0)
                        found_isbns.add(isbn)
                        text_sections.append(f"ISBN: {isbn}")
                        self.logger.info(f"Found ISBN in DC metadata: {isbn}")

            # Process document items
            self.logger.debug("Processing EPUB content...")
            items_processed = 0
            for item in book.get_items():
                if item.get_type() == ITEM_DOCUMENT:
                    items_processed += 1
                    try:
                        content = item.get_content().decode('utf-8', errors='ignore')
                        soup = BeautifulSoup(content, 'html.parser')
                        text = soup.get_text()
                        
                        # Log content length for debugging
                        self.logger.debug(f"Processing item {items_processed}: {len(text)} characters")
                        
                        # Look for ISBNs using all patterns
                        for pattern in self.isbn_patterns:
                            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
                            for match in matches:
                                # Extract and clean ISBN
                                isbn_raw = match.group(1) if match.groups() else match.group(0)
                                isbn = re.sub(r'[^0-9X]', '', isbn_raw.upper())
                                
                                # Validate ISBN format
                                if len(isbn) == 13 and isbn.startswith(('978', '979')):
                                    found_isbns.add(isbn)
                                    text_sections.append(f"ISBN: {isbn}")
                                    self.logger.info(f"Found ISBN-13 in content: {isbn}")
                                elif len(isbn) == 10:
                                    found_isbns.add(isbn)
                                    text_sections.append(f"ISBN: {isbn}")
                                    self.logger.info(f"Found ISBN-10 in content: {isbn}")
                        
                        # Add context for ISBN sections
                        if re.search(r'ISBN|97[89]|Casa do Código', text, re.IGNORECASE):
                            self.logger.debug("Found ISBN-related content, adding context")
                            text_sections.insert(0, text)
                        
                    except Exception as e:
                        self.logger.error(f"Error processing item {items_processed}: {str(e)}")
                        continue

            # Final logging
            self.logger.info(f"Processed {items_processed} items")
            self.logger.info(f"Found {len(found_isbns)} unique ISBNs: {sorted(found_isbns)}")
            
            if not found_isbns:
                self.logger.warning(f"No ISBNs found in {epub_path}")
                # Log a sample of the content for debugging
                if text_sections:
                    sample = text_sections[0][:500]
                    self.logger.debug(f"Content sample: {sample}")

            return "\n\n".join(text_sections), methods_tried
            
        except Exception as e:
            self.logger.error(f"EPUB extraction error in {epub_path}: {str(e)}")
            self.logger.error(traceback.format_exc())
            return "", methods_tried

    def _extract_title_from_metadata(self, metadata: Dict) -> Optional[str]:
        """
        Extract and clean book title from metadata, prioritizing main title over subtitle.
        
        Args:
            metadata: Raw metadata dictionary from any source
            
        Returns:
            str: Clean main title or None if not found
        """
        if not metadata:
            return None

        # Extract raw title
        raw_title = None
        if 'title' in metadata:
            raw_title = metadata['title']
        elif 'Title' in metadata:
            raw_title = metadata['Title']
        elif 'volumeInfo' in metadata and 'title' in metadata['volumeInfo']:
            raw_title = metadata['volumeInfo']['title']

        if not raw_title:
            return None

        # Clean and split title
        title_parts = raw_title.split(':')
        main_title = title_parts[0].strip()
        
        # Validate main title is meaningful
        if len(main_title) < 3 or main_title.lower() in ['untitled', 'unknown']:
            return None
            
        return main_title

    def extract_text_from_mobi(self, mobi_path: str) -> Tuple[str, List[str]]:
        """Extract text content from MOBI files."""
        methods_tried = ["mobi-raw"]
        text_sections = []

        try:
            with open(mobi_path, 'rb') as file:
                # Tenta múltiplos encodings comuns em MOBIs
                for encoding in ['utf-8', 'cp1252', 'latin1', 'iso-8859-1']:
                    try:
                        content = file.read().decode(encoding, errors='ignore')
                        file.seek(0)  # Reset para próxima tentativa
                        
                        # Procura primeiro por seção de copyright que geralmente tem ISBN
                        copyright_match = re.search(
                            r'(?:Copyright|\u00A9|©).{0,500}?(?=\n\n|\Z)',
                            content,
                            re.IGNORECASE | re.DOTALL
                        )
                        if copyright_match:
                            text_sections.append(copyright_match.group(0))
                            break
                    except:
                        continue

            # Processamento existente como fallback
            if not text_sections:
                methods_tried.append("mobi-structured")
                try:
                    book = mobi.Mobi(file)
                    book.parse()
                    if hasattr(book, 'book_header'):
                        if hasattr(book.book_header, 'title'):
                            text_sections.append(
                                book.book_header.title.decode('utf-8', errors='ignore')
                            )
                except:
                    pass

        except Exception as e:
            self.logger.error(f"MOBI extraction failed for {mobi_path}: {str(e)}")
        
        return "\n\n".join(text_sections), methods_tried

    def _normalize_text(self, text: str) -> str:
        """
        Normaliza texto removendo acentos e caracteres especiais do português.
        
        Args:
            text: Texto original, possivelmente com acentos e caracteres especiais
            
        Returns:
            str: Texto normalizado sem acentos e caracteres especiais
        """
        if not text:
            return ""
            
        try:
            # Primeiro converte para Unicode NFKD para separar os caracteres base dos acentos
            normalized = unicodedata.normalize('NFKD', text)
            
            # Remove os caracteres não-ASCII (acentos e outros diacríticos)
            ascii_text = normalized.encode('ASCII', 'ignore').decode('ASCII')
            
            # Substitui caracteres específicos do português
            replacements = {
                'Ã¡': 'a', 'Ã ': 'a', 'Ã¢': 'a', 'Ã£': 'a',
                'Ã©': 'e', 'Ãª': 'e',
                'Ã­': 'i',
                'Ã³': 'o', 'Ã´': 'o', 'Ãµ': 'o',
                'Ãº': 'u', 'Ã¼': 'u',
                'Ã§': 'c',
                'Ã': 'A', 'Ã': 'E', 'Ã': 'I', 'Ã': 'O', 'Ã': 'U',
                'Ã': 'A', 'Ã': 'E', 'Ã': 'I', 'Ã': 'O', 'Ã': 'U',
                'Ã': 'A', 'Ã': 'E', 'Ã': 'I', 'Ã': 'O', 'Ã': 'U'
            }
            
            for old, new in replacements.items():
                ascii_text = ascii_text.replace(old, new)
                
            return ascii_text
            
        except Exception as e:
            self.logger.error(f"Erro ao normalizar texto: {str(e)}")
            return text  # Retorna o texto original em caso de erro

    def extract_metadata(self, file_path: str) -> Dict[str, Union[str, List[str], None]]:
        """
        Extract and validate metadata with enhanced support for Brazilian publishers.
        """
        metadata: Dict[str, Union[str, List[str], None]] = {}
        ext = Path(file_path).suffix.lower()
        
        self.logger.info(f"Extracting metadata from: {file_path}")
        
        try:
            if ext == '.epub':
                book = epub.read_epub(file_path)
                
                # Extract Dublin Core metadata first
                self.logger.debug("Checking Dublin Core metadata...")
                
                # Get all DC metadata
                dc_metadata_found = False
                for field in ['title', 'creator', 'publisher', 'date', 'identifier']:
                    field_data = book.get_metadata('DC', field)
                    if field_data:
                        value = str(field_data[0][0])
                        if field == 'identifier':
                            isbn_match = re.search(
                                r'(?:97[89]\d{10})|(?:\d{9}[\dXx])',
                                value
                            )
                            if isbn_match:
                                metadata['isbn'] = isbn_match.group(0)
                                self.logger.info(f"Found ISBN in DC metadata: {metadata['isbn']}")
                                dc_metadata_found = True
                        else:
                            # Aplica a normalização aqui
                            metadata[field] = self._normalize_text(value)
                            self.logger.debug(f"Found {field}: {metadata[field]}")
                
                # If no ISBN in DC metadata, try content scanning
                if 'isbn' not in metadata:
                    self.logger.debug("No ISBN in DC metadata, scanning content...")
                    text, _ = self.extract_text_from_epub(file_path)
                    if text:
                        # Try Casa do Código patterns first if filename suggests it
                        is_casa_codigo = any(marker in file_path.lower() for marker in ['casa', 'codigo', 'cdc'])
                        if is_casa_codigo:
                            for pattern in [
                                r'Impresso:\s*(978-85-5519-[0-9]{3}-[0-9])',
                                r'Digital:\s*(978-85-5519-[0-9]{3}-[0-9])'
                            ]:
                                matches = re.finditer(pattern, text, re.IGNORECASE)
                                for match in matches:
                                    isbn = re.sub(r'[^0-9]', '', match.group(1))
                                    if len(isbn) == 13 and isbn.startswith('97885'):
                                        metadata['isbn'] = isbn
                                        metadata['publisher'] = 'Casa do Código'
                                        self.logger.info(f"Found Casa do Código ISBN: {isbn}")
                                        break
                                if 'isbn' in metadata:
                                    break
                        
                        # If still no ISBN, try all patterns
                        if 'isbn' not in metadata:
                            for pattern in self.isbn_patterns:
                                matches = re.finditer(pattern, text, re.IGNORECASE)
                                for match in matches:
                                    isbn_raw = match.group(1) if match.groups() else match.group(0)
                                    isbn = re.sub(r'[^0-9X]', '', isbn_raw.upper())
                                    
                                    # Validate ISBN format
                                    if len(isbn) == 13 and isbn.startswith(('978', '979')):
                                        metadata['isbn'] = isbn
                                        
                                        # Check for Brazilian publishers
                                        if isbn.startswith('97885'):
                                            if '855519' in isbn:
                                                metadata['publisher'] = 'Casa do Código'
                                            elif '857522' in isbn:
                                                metadata['publisher'] = 'Novatec'
                                            elif '85508' in isbn:
                                                metadata['publisher'] = 'Alta Books'
                                        
                                        self.logger.info(f"Found ISBN in content: {isbn}")
                                        break
                                if 'isbn' in metadata:
                                    break

                # Validate required fields
                required_fields = {
                    'isbn': metadata.get('isbn'),
                    'title': metadata.get('title') or metadata.get('creator'),
                    'creator': metadata.get('creator') or metadata.get('authors', [])
                }

                # Special handling for Casa do Código
                if metadata.get('isbn', '').startswith('978855519'):
                    metadata['publisher'] = 'Casa do Código'
                    # Casa do Código books always pass validation if ISBN is correct
                    if all(required_fields.values()):
                        # Aplica a normalização antes de retornar
                        if metadata.get('title'):
                            metadata['title'] = self._normalize_text(metadata['title'])
                        if metadata.get('creator'):
                            metadata['creator'] = self._normalize_text(metadata['creator'])
                        self.logger.info(f"Successfully extracted metadata: {metadata}")
                        return metadata

                # General validation for other publishers
                if all(required_fields.values()):
                    # Aplica a normalização antes de retornar
                    if metadata.get('title'):
                        metadata['title'] = self._normalize_text(metadata['title'])
                    if metadata.get('creator'):
                        metadata['creator'] = self._normalize_text(metadata['creator'])
                    self.logger.info(f"Successfully extracted metadata: {metadata}")
                    return metadata
                
                self.logger.warning(f"Incomplete metadata found in {file_path}: {metadata}")
                return metadata  # Return partial metadata instead of empty dict
                
            elif ext == '.mobi':
                # [MOBI processing code remains the same]
                pass
                
        except Exception as e:
            self.logger.error(f"Metadata extraction failed for {file_path}: {str(e)}")
            self.logger.error(traceback.format_exc())
            
        return metadata  # Return whatever metadata was found, even if incomplete

    def _clean_isbn(self, isbn: str) -> str:
        """
        Clean and normalize ISBN string.
        
        Args:
            isbn: Raw ISBN string
            
        Returns:
            str: Cleaned ISBN string without hyphens or spaces
        """
        return re.sub(r'[^0-9X]', '', isbn.upper())

    def _validate_isbn_13(self, isbn: str) -> bool:
        """
        Validate ISBN-13 checksum according to standard.
        
        Args:
            isbn: ISBN-13 string to validate
            
        Returns:
            bool: True if valid ISBN-13
        """
        if len(isbn) != 13 or not isbn.startswith(('978', '979')):
            return False
        try:
            total = sum(int(num) * (1 if i % 2 == 0 else 3) 
                    for i, num in enumerate(isbn[:12]))
            check = (10 - (total % 10)) % 10
            return check == int(isbn[-1])
        except ValueError:
            return False

    def _validate_isbn_10(self, isbn: str) -> bool:
        """
        Validate ISBN-10 checksum according to standard.
        
        Args:
            isbn: ISBN-10 string to validate
            
        Returns:
            bool: True if valid ISBN-10
        """
        if len(isbn) != 10:
            return False
        try:
            total = sum((10 - i) * (int(num) if num != 'X' else 10)
                    for i, num in enumerate(isbn))
            return total % 11 == 0
        except ValueError:
            return False

    def _validate_oreilly_metadata(self, metadata: Dict, isbn: str) -> bool:
        """
        Validate metadata matches O'Reilly book characteristics.
        
        Args:
            metadata: Metadata dictionary to validate
            isbn: ISBN being validated
            
        Returns:
            bool: True if metadata appears valid for O'Reilly book
        """
        if not metadata or not isbn:
            return False

        # ISBN format validation
        if not self._validate_isbn_13(isbn):
            return False

        # Publisher validation
        publisher = metadata.get('publisher', '') or metadata.get('Publisher', '')
        if not publisher:
            return False
            
        if not any(name.lower() in publisher.lower() 
                for name in ["o'reilly", "oreilly", "o'reilly media"]):
            return False

        # Title validation
        title = self._extract_title_from_metadata(metadata)
        if not title:
            return False

        return True

    def _handle_api_response(self, api_response: Dict, isbn: str, source: str) -> Optional[Dict]:
        """
        Process and validate API response data.
        
        Args:
            api_response: Raw API response data
            isbn: ISBN being validated
            source: Name of API source
            
        Returns:
            Optional[Dict]: Processed metadata if valid, None otherwise
        """
        try:
            # Extract core metadata
            metadata = {
                'title': self._extract_title_from_metadata(api_response),
                'authors': api_response.get('authors', []) or api_response.get('Authors', []),
                'publisher': api_response.get('publisher') or api_response.get('Publisher', ''),
                'isbn': isbn,
                'source': source
            }

            # Validate required fields
            if not metadata['title'] or not metadata['authors'] or not metadata['publisher']:
                self.logger.debug(f"Incomplete metadata from {source} for ISBN {isbn}")
                return None

            # Validate O'Reilly specific fields
            if not self._validate_oreilly_metadata(metadata, isbn):
                self.logger.debug(f"Non-O'Reilly metadata from {source} for ISBN {isbn}")
                return None

            return metadata

        except Exception as e:
            self.logger.debug(f"Error processing {source} response for ISBN {isbn}: {str(e)}")
            return None

    def _handle_isbn_variant(self, isbn: str, variant_data: Dict) -> Optional[str]:
        """
        Handle ISBN variants and inconsistencies.
        
        Args:
            isbn: Original ISBN
            variant_data: Data containing potential variant ISBNs
            
        Returns:
            Optional[str]: Valid ISBN variant or None
        """
        if not variant_data:
            return None

        # Extract potential variants
        variants = []
        if 'identifier' in variant_data:
            if isinstance(variant_data['identifier'], list):
                variants.extend(id_obj.get('identifier') for id_obj in variant_data['identifier']
                            if isinstance(id_obj, dict) and 'identifier' in id_obj)
            else:
                variants.append(variant_data['identifier'])

        # Validate each variant
        for variant in variants:
            if self._validate_isbn_13(variant):
                # Only accept variant if it's clearly related (same publisher prefix)
                if variant[:7] == isbn[:7]:
                    return variant

        return None

    def _convert_isbn_10_to_13(self, isbn10: str) -> Optional[str]:
        """
        Convert valid ISBN-10 to ISBN-13.
        
        Args:
            isbn10: Valid ISBN-10 string
            
        Returns:
            Optional[str]: Converted ISBN-13 or None if conversion fails
        """
        if not self._validate_isbn_10(isbn10):
            return None
            
        isbn13 = f"978{isbn10[:-1]}"
        total = sum(int(num) * (1 if i % 2 == 0 else 3) 
                for i, num in enumerate(isbn13))
        check = (10 - (total % 10)) % 10
        return f"{isbn13}{check}"

    def _extract_copyright_section(self, text: str) -> Optional[str]:
        """
        Extract copyright section from text content.
        
        Args:
            text: Text content to search
            
        Returns:
            Optional[str]: Copyright section if found
        """
        copyright_match = re.search(
            r'(?:Copyright|\u00A9|©).*?(?=\n\n|\Z)',
            text,
            re.IGNORECASE | re.DOTALL
        )
        return copyright_match.group(0) if copyright_match else None

    def _check_oreilly_context(self, text: str, isbn_pos: int, context_size: int = 100) -> bool:
        """
        Check if ISBN appears in O'Reilly context.
        
        Args:
            text: Full text content
            isbn_pos: Position of ISBN match
            context_size: Size of context window to check
            
        Returns:
            bool: True if ISBN appears in O'Reilly context
        """
        start = max(0, isbn_pos - context_size)
        end = min(len(text), isbn_pos + context_size)
        context = text[start:end].lower()
        return 'reilly' in context or "o'reilly" in context

    def _validate_casa_codigo_metadata(self, metadata: Dict) -> bool:
        """Validação específica para livros da Casa do Código."""
        # ISBN deve começar com 978-85 (prefixo brasileiro)
        if 'isbn' in metadata:
            isbn = re.sub(r'[^0-9]', '', metadata['isbn'])
            if not isbn.startswith('97885'):
                return False

        # Deve ter título
        if not metadata.get('title'):
            return False

        # Deve ter pelo menos um autor
        if not metadata.get('creator') and not metadata.get('authors'):
            return False

        # Define publisher como Casa do Código se detectado
        if self._is_casa_codigo_book(metadata):
            metadata['publisher'] = 'Casa do Código'
            return True

        return False

    def _is_casa_codigo_book(self, metadata: Dict) -> bool:
        """Verifica se é um livro da Casa do Código."""
        # Verifica ISBN
        if 'isbn' in metadata:
            isbn = re.sub(r'[^0-9]', '', metadata['isbn'])
            if isbn.startswith('97885'):
                # Verifica se é do range da Casa do Código (85-5519)
                if '855519' in isbn:
                    return True

        # Verifica publisher existente
        publisher = metadata.get('publisher', '').lower()
        if any(marker.lower() in publisher for marker in ['casa do código', 'casadocodigo']):
            return True

        return False


class PacktBookProcessor:
    """Processador especializado para livros da Packt."""
    
    def __init__(self):
        self._init_logging()
        # Padrões específicos da Packt para complementar a extração existente
        self.packt_patterns = {
            'isbn': [
                r'eBook:\s*ISBN[:\s-]*(97[89][-\s]*(?:\d[-\s]*){9}\d)',
                r'Print\s+ISBN[:\s-]*(97[89][-\s]*(?:\d[-\s]*){9}\d)',
                r'ISBN\s+13:[:\s-]*(97[89][-\s]*(?:\d[-\s]*){9}\d)'
            ]
        }
        
        self.packt_char_fixes = {
            '@': '9',
            '>': '7',
            '?': '8',
            '_': '-'
        }

    def _init_logging(self):
        """Initialize logging configuration."""
        self.logger = logging.getLogger('packt_processor')  # Use o nome específico da classe
        self.logger.setLevel(logging.DEBUG)  # Nível detalhado para o arquivo
        
        if not self.logger.handlers:
            # File handler - captura tudo para o arquivo
            file_handler = logging.FileHandler('packt_processor.log')
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            ))
            file_handler.setLevel(logging.DEBUG)
            
            # Console handler - apenas warnings e erros
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(
                '%(levelname)s - %(message)s'
            ))
            console_handler.setLevel(logging.WARNING)
            
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)

    def enhance_metadata(self, file_metadata: Dict, text: str) -> Dict:
        """
        Aprimora os metadados existentes com informações específicas da Packt.
        Não substitui o processamento padrão, apenas complementa.
        """
        if not isinstance(file_metadata, dict):
            file_metadata = {}
            
        # Se já temos ISBN, apenas corrige caracteres Packt
        if 'isbn' in file_metadata:
            isbn = file_metadata['isbn']
            for old, new in self.packt_char_fixes.items():
                isbn = isbn.replace(old, new)
            file_metadata['isbn'] = isbn
            return file_metadata
            
        # Procura ISBN no texto com padrões Packt
        for pattern in self.packt_patterns['isbn']:
            matches = re.finditer(pattern, text)
            for match in matches:
                isbn = match.group(1)
                # Aplica correções Packt
                for old, new in self.packt_char_fixes.items():
                    isbn = isbn.replace(old, new)
                isbn = re.sub(r'[^0-9X]', '', isbn)
                if len(isbn) == 13 and isbn.startswith('978'):
                    file_metadata['isbn'] = isbn
                    break
                    
        return file_metadata

    def is_packt_book(self, file_path: str) -> bool:
        """Verifica se é um livro da Packt."""
        return ('packt' in file_path.lower() or 
                'hands-on' in file_path.lower())

class BookFileGroup:
    """Handles groups of related book files and ISBN variants."""
    def __init__(self):
        self._init_logging()
        self.base_patterns = [
            r'_Code\.zip$',
            r'\s+PDF$',
            r'\s+EPUB$',
            r'\.pdf$',
            r'\.epub$',
            r'\.mobi$',
            r'\.zip$'
        ]
        
        # Known ISBN variant mappings, especially for Packt books
        self.isbn_variants = {
            '9781789957648': ['9788445901854'],
            '9781801813785': ['9781801812436'],
            '9781800205697': ['9781801810074'],
            '9781800206540': ['9781801079341']
        }

    def _init_logging(self):
        """Initialize logging configuration."""
        self.logger = logging.getLogger('book_file_group')  # Use o nome específico da classe
        self.logger.setLevel(logging.DEBUG)  # Nível detalhado para o arquivo
        
        if not self.logger.handlers:
            # File handler - captura tudo para o arquivo
            file_handler = logging.FileHandler('book_file_group.log')
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            ))
            file_handler.setLevel(logging.DEBUG)
            
            # Console handler - apenas warnings e erros
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(
                '%(levelname)s - %(message)s'
            ))
            console_handler.setLevel(logging.WARNING)
            
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)

    def get_base_name(self, filename: str) -> str:
        """
        Extract base name from filename by removing format-specific suffixes.
        
        Args:
            filename: Original filename
            
        Returns:
            Base name without format suffixes
        """
        base = filename
        for pattern in self.base_patterns:
            base = re.sub(pattern, '', base, flags=re.IGNORECASE)
        return base.strip()

    def group_files(self, file_paths: List[str]) -> Dict[str, List[str]]:
        """
        Group files that represent the same book in different formats.
        
        Args:
            file_paths: List of file paths to process
            
        Returns:
            Dictionary mapping base names to lists of related files
        """
        groups = defaultdict(list)
        
        for file_path in file_paths:
            base_name = self.get_base_name(Path(file_path).name)
            groups[base_name].append(file_path)
            
        return dict(groups)

    def find_best_isbn_source(self, group_files: List[str]) -> Optional[str]:
        """
        Find the best file to extract ISBN from within a group.
        Prioritizes PDFs as they often have more reliable metadata.
        
        Args:
            group_files: List of files in the same group
            
        Returns:
            Path to best source file or None
        """
        # First try PDF files
        pdf_files = [f for f in group_files if f.lower().endswith('.pdf')]
        if pdf_files:
            return pdf_files[0]
            
        # Then try EPUB files
        epub_files = [f for f in group_files if f.lower().endswith('.epub')]
        if epub_files:
            return epub_files[0]
            
        # Finally try MOBI files
        mobi_files = [f for f in group_files if f.lower().endswith('.mobi')]
        if mobi_files:
            return mobi_files[0]
            
        return group_files[0] if group_files else None

    def validate_isbn_variant(self, original: str, variant: str) -> bool:
        """
        Validate if an ISBN variant is known and valid.
        
        Args:
            original: Original ISBN
            variant: Variant ISBN to validate
            
        Returns:
            True if variant is valid
        """
        # Check direct mapping
        if original in self.isbn_variants:
            return variant in self.isbn_variants[original]
            
        # Check reverse mapping
        for known_isbn, variants in self.isbn_variants.items():
            if variant == known_isbn and original in variants:
                return True
                
        return False


def main():
    """Main function for book metadata extraction and renaming."""
    parser = argparse.ArgumentParser(
        description='Extrai metadados de livros PDF e opcionalmente renomeia os arquivos',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
            Exemplos de uso:
              # Processar apenas o diretório atual:
              %(prog)s "/Users/menon/Downloads"
              
              # Processar diretório e subdiretórios:
              %(prog)s "/Users/menon/Downloads" -r
              
              # Processar e renomear arquivos com padrão default:
              %(prog)s "/Users/menon/Downloads" --rename
              
              # Processar e renomear com padrão personalizado:
              %(prog)s "/Users/menon/Downloads" --rename --name-pattern "{publisher}_{year}_{title}"
              
              # Processar com mais threads e detalhes:
              %(prog)s "/Users/menon/Downloads" -t 8 -v
              
              # Processar diretórios específicos:
              %(prog)s "/Users/menon/Downloads" --subdirs "Machine Learning,Python Books"
              
              # Comando completo:
              %(prog)s "/Users/menon/Downloads" -r -t 8 --rename --name-pattern "{publisher}_{title}" -v -k "sua_chave_isbndb" -o "relatorio.json"
              
              # Atualizar cache com dados melhores:
              %(prog)s --update-cache
              
              # Reprocessar cache existente:
              %(prog)s --rescan-cache

            Observações:
              - Por padrão, processa apenas o diretório especificado (sem subdiretórios)
              - Use -r para processar todos os subdiretórios
              - Use --subdirs para processar apenas subdiretórios específicos
              - Use --name-pattern para definir o padrão de nomeação. Placeholders disponíveis:
                {title}, {author}, {year}, {publisher}, {isbn}
              - A chave ISBNdb é opcional e pode ser colocada em qualquer posição do comando
              - Use --rescan-cache para reprocessar todo o cache em busca de dados melhores
              - Use --update-cache para atualizar apenas registros com baixa confiança
            """)
    )
    
    # Argumentos básicos
    parser.add_argument('directory', 
                       nargs='?',
                       help='Diretório contendo os arquivos PDF')
    parser.add_argument('-r', '--recursive',
                       action='store_true',
                       help='Processa subdiretórios recursivamente')
    parser.add_argument('--subdirs',
                       help='Lista de subdiretórios específicos (separados por vírgula)')
                       
    # Argumentos de saída e logging
    parser.add_argument('-o', '--output',
                       default='report.json',
                       help='Arquivo JSON de saída (padrão: %(default)s)')
    parser.add_argument('-v', '--verbose',
                       action='store_true',
                       help='Mostra informações detalhadas')
                       
    # Argumentos de processamento
    parser.add_argument('-t', '--threads',
                       type=int,
                       default=4,
                       help='Número de threads para processamento (padrão: %(default)s)')
    parser.add_argument('-k', '--isbndb-key',
                       help='Chave da API ISBNdb (opcional)')
                       
    # Argumentos de cache
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
                       
    # Argumentos de renomeação
    parser.add_argument('--rename',
                       action='store_true',
                       help='Renomeia arquivos com base nos metadados')
    parser.add_argument('--name-pattern',
                       default="{title} - {author} - {year}",
                       help='Padrão para nomes de arquivo. Placeholders: {title}, {author}, {year}, {publisher}, {isbn}')
    
    args = parser.parse_args()
    
    try:
        # Inicializa o extrator
        extractor = BookMetadataExtractor(isbndb_api_key=args.isbndb_key)
        
        # Operações de cache
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
            
        # Verifica diretório
        if not args.directory:
            parser.print_help()
            print("\nERRO: É necessário fornecer um diretório ou usar --rescan-cache/--update-cache")
            sys.exit(1)
        
        # Prepara processamento
        subdirs = args.subdirs.split(',') if args.subdirs else None
        
        print(f"\nProcessando PDFs em: {args.directory}")
        if args.recursive:
            print("Modo recursivo: processando todos os subdiretórios")
        elif subdirs:
            print(f"Processando subdiretórios específicos: {', '.join(subdirs)}")
        else:
            print("Modo não-recursivo: processando apenas o diretório principal")
        
        # Configura padrão de nomeação se necessário
        if args.rename:
            extractor.set_naming_pattern(args.name_pattern)
            print(f"Usando padrão de nomeação: {args.name_pattern}")
        
        # Processa arquivos
        results = extractor.process_directory(
            args.directory,
            subdirs=subdirs,
            recursive=args.recursive,
            max_workers=args.threads
        )
        
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