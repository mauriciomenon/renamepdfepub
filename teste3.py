import logging
import time
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, asdict
import json
from datetime import datetime
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor, as_completed
import isbnlib
from pathlib import Path
import xml.etree.ElementTree as ET
from collections import Counter
import plotly.graph_objects as go
from bs4 import BeautifulSoup
import re
from tqdm import tqdm

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('isbn_api_tester.log')
    ]
)

# Configurações das APIs
API_REQUIREMENTS = {
    'google_books': {
        'name': 'Google Books',
        'requires_key': False,
        'free_tier': True,
        'rate_limit': '1000/day',
        'notes': 'Free API, no registration required'
    },
    'open_library': {
        'name': 'Open Library',
        'requires_key': False,
        'free_tier': True,
        'rate_limit': 'Unlimited',
        'notes': 'Free API, no registration required'
    },
    'isbndb': {
        'name': 'ISBNdb',
        'requires_key': True,
        'free_tier': True,
        'rate_limit': '1000/month',
        'notes': 'Registration required. Free tier available'
    },
    'springer': {
        'name': 'Springer Nature',
        'requires_key': True,
        'free_tier': True,
        'rate_limit': '5000/month',
        'notes': 'Good for technical books'
    },
    'oreilly': {
        'name': "O'Reilly Atlas",
        'requires_key': True,
        'free_tier': False,
        'rate_limit': 'Variable',
        'notes': 'Commercial API'
    },
    'crossref': {
        'name': 'CrossRef',
        'requires_key': False,
        'free_tier': True,
        'rate_limit': '50/sec',
        'notes': 'Free API, email registration recommended'
    },
    'worldcat': {
        'name': 'WorldCat',
        'requires_key': True,
        'free_tier': True,
        'rate_limit': '100/min',
        'notes': 'Basic API free, full version requires key'
    },
    'library_of_congress': {
        'name': 'Library of Congress',
        'requires_key': False,
        'free_tier': True,
        'rate_limit': '100/min',
        'notes': 'Free API'
    },
    'internet_archive': {
        'name': 'Internet Archive',
        'requires_key': False,
        'free_tier': True,
        'rate_limit': 'Variable',
        'notes': 'Free API'
    }
}

@dataclass
class APITestResult:
    """Resultados detalhados de testes de API"""
    api_name: str
    response_time: float
    success: bool
    metadata: Optional[Dict]
    error: Optional[str] = None
    http_status: Optional[int] = None
    requires_key: bool = False
    api_type: str = "unknown"
    retry_count: int = 0
    cache_hit: bool = False
    confidence_score: float = 0.0
    raw_response: Optional[Dict] = None
    rate_limit_info: Optional[Dict] = None
    response_headers: Optional[Dict] = None

class Cache:
    """Sistema de cache com TTL e persistência"""
    def __init__(self, cache_file: str = "isbn_cache.json", ttl: int = 86400):
        self.cache_file = Path(cache_file)
        self.ttl = ttl
        self.cache = self._load_cache()

    def _load_cache(self) -> Dict:
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    cache = json.load(f)
                # Remove entradas expiradas
                current_time = time.time()
                cache = {
                    k: v for k, v in cache.items()
                    if current_time - v.get('timestamp', 0) < self.ttl
                }
                return cache
            except:
                return {}
        return {}

    def _save_cache(self):
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f)

    def get(self, key: str) -> Optional[Dict]:
        if key in self.cache:
            entry = self.cache[key]
            if time.time() - entry['timestamp'] < self.ttl:
                return entry['data']
            del self.cache[key]
            self._save_cache()
        return None

    def set(self, key: str, value: Dict):
        self.cache[key] = {
            'data': value,
            'timestamp': time.time()
        }
        self._save_cache()

class HttpClient:
    """Cliente HTTP robusto com retry e timeouts"""
    def __init__(self):
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"]
        )
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=100,
            pool_maxsize=100
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        session.headers.update({
            'User-Agent': 'ISBN-API-Tester/1.0 (Academic Research Tool)',
            'Accept': 'application/json,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive'
        })
        
        return session

    def get(self, url: str, **kwargs) -> requests.Response:
        try:
            response = self.session.get(url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.SSLError:
            # Tenta novamente sem verificação SSL
            kwargs['verify'] = False
            return self.session.get(url, **kwargs)
        except requests.exceptions.ProxyError:
            # Tenta sem proxy
            self.session.trust_env = False
            return self.session.get(url, **kwargs)


class ISBNAPITester:
    def __init__(self, api_keys: Optional[Dict[str, str]] = None):
        self.http_client = HttpClient()
        self.api_keys = api_keys or {}
        self.cache = Cache()

    def test_google_books(self, isbn: str) -> APITestResult:
        """Testa a API do Google Books."""
        start_time = time.time()
        try:
            response = self.http_client.get(
                "https://www.googleapis.com/books/v1/volumes",
                params={'q': f'isbn:{isbn}'},
                timeout=10
            )
            data = response.json()

            if 'items' in data and data['items']:
                book = data['items'][0]['volumeInfo']
                metadata = {
                    'title': book.get('title'),
                    'authors': book.get('authors', []),
                    'publisher': book.get('publisher'),
                    'publishedDate': book.get('publishedDate'),
                    'isbn': isbn,
                    'language': book.get('language'),
                    'pageCount': book.get('pageCount'),
                    'categories': book.get('categories', [])
                }
                return APITestResult(
                    api_name="Google Books",
                    response_time=time.time() - start_time,
                    success=True,
                    metadata=metadata,
                    http_status=response.status_code,
                    raw_response=data,
                    response_headers=dict(response.headers)
                )

            return APITestResult(
                api_name="Google Books",
                response_time=time.time() - start_time,
                success=False,
                metadata=None,
                error="No results found",
                http_status=response.status_code
            )

        except Exception as e:
            return APITestResult(
                api_name="Google Books",
                response_time=time.time() - start_time,
                success=False,
                metadata=None,
                error=str(e)
            )

    def test_open_library(self, isbn: str) -> APITestResult:
        """Testa a API do Open Library."""
        start_time = time.time()
        try:
            response = self.http_client.get(
                "https://openlibrary.org/api/books",
                params={
                    'bibkeys': f"ISBN:{isbn}",
                    'format': 'json',
                    'jscmd': 'data'
                },
                timeout=10
            )
            data = response.json()

            if f"ISBN:{isbn}" in data:
                book = data[f"ISBN:{isbn}"]
                metadata = {
                    'title': book.get('title'),
                    'authors': [a.get('name') for a in book.get('authors', [])],
                    'publisher': book.get('publishers', [{}])[0].get('name'),
                    'publishedDate': book.get('publish_date'),
                    'isbn': isbn,
                    'pages': book.get('number_of_pages'),
                    'subjects': book.get('subjects', [])
                }
                return APITestResult(
                    api_name="Open Library",
                    response_time=time.time() - start_time,
                    success=True,
                    metadata=metadata,
                    http_status=response.status_code,
                    raw_response=data
                )

            return APITestResult(
                api_name="Open Library",
                response_time=time.time() - start_time,
                success=False,
                metadata=None,
                error="No results found",
                http_status=response.status_code
            )

        except Exception as e:
            return APITestResult(
                api_name="Open Library",
                response_time=time.time() - start_time,
                success=False,
                metadata=None,
                error=str(e)
            )

    def test_isbnlib_providers(self, isbn: str) -> List[APITestResult]:
        """Testa os métodos básicos disponíveis no isbnlib."""
        results = []
        providers = {
            'isbnlib_default': isbnlib.meta,
            'isbnlib_mask': isbnlib.mask,
            'isbnlib_info': isbnlib.info,
            'isbnlib_desc': isbnlib.desc,
            'isbnlib_classify': isbnlib.classify,
            'isbnlib_editions': isbnlib.editions,
            'isbnlib_goom': isbnlib.goom,
            'isbnlib_doi2tex': isbnlib.doi2tex,
            'isbnlib_isbn10': lambda x: isbnlib.to_isbn10(x) if isbnlib.is_isbn13(x) else x,
            'isbnlib_isbn13': lambda x: isbnlib.to_isbn13(x) if isbnlib.is_isbn10(x) else x
        }

        for provider_name, provider_func in providers.items():
            start_time = time.time()
            try:
                metadata = None
                
                # Trata diferentes tipos de retorno
                try:
                    data = provider_func(isbn)
                    if isinstance(data, dict):
                        metadata = data
                    elif isinstance(data, str):
                        metadata = {'result': data}
                    elif isinstance(data, list):
                        metadata = {'results': data}
                    elif data is not None:
                        metadata = {'data': str(data)}
                except Exception as specific_error:
                    metadata = None
                    error = str(specific_error)
                
                if metadata:
                    results.append(APITestResult(
                        api_name=provider_name,
                        response_time=time.time() - start_time,
                        success=True,
                        metadata=metadata
                    ))
                else:
                    results.append(APITestResult(
                        api_name=provider_name,
                        response_time=time.time() - start_time,
                        success=False,
                        metadata=None,
                        error="No results found"
                    ))
            except Exception as e:
                results.append(APITestResult(
                    api_name=provider_name,
                    response_time=time.time() - start_time,
                    success=False,
                    metadata=None,
                    error=str(e)
                ))

        return results

    def test_worldcat(self, isbn: str) -> APITestResult:
        """Testa a API do WorldCat."""
        start_time = time.time()
        try:
            response = self.http_client.get(
                "http://classify.oclc.org/classify2/Classify",
                params={'isbn': isbn, 'summary': 'true'},
                timeout=10
            )
            
            root = ET.fromstring(response.content)
            work = root.find('.//work')
            
            if work is not None:
                metadata = {
                    'title': work.get('title', ''),
                    'authors': [work.get('author', '')],
                    'publishedDate': work.get('date', ''),
                    'isbn': isbn,
                    'oclc': work.get('oclc', ''),
                    'edition': work.get('edition', '')
                }
                return APITestResult(
                    api_name="WorldCat",
                    response_time=time.time() - start_time,
                    success=True,
                    metadata=metadata,
                    http_status=response.status_code
                )

            return APITestResult(
                api_name="WorldCat",
                response_time=time.time() - start_time,
                success=False,
                metadata=None,
                error="No results found",
                http_status=response.status_code
            )

        except Exception as e:
            return APITestResult(
                api_name="WorldCat",
                response_time=time.time() - start_time,
                success=False,
                metadata=None,
                error=str(e)
            )

    def test_crossref(self, isbn: str) -> APITestResult:
        """Testa a API do CrossRef."""
        start_time = time.time()
        try:
            response = self.http_client.get(
                "https://api.crossref.org/works",
                params={
                    'query.bibliographic': isbn,
                    'filter': 'type:book',
                    'select': 'title,author,published-print,publisher'
                },
                timeout=10
            )
            data = response.json()

            if data['message']['items']:
                item = data['message']['items'][0]
                metadata = {
                    'title': item.get('title', [''])[0],
                    'authors': [
                        f"{a.get('given', '')} {a.get('family', '')}"
                        for a in item.get('author', [])
                    ],
                    'publisher': item.get('publisher'),
                    'publishedDate': str(
                        item.get('published-print', {})
                        .get('date-parts', [['']])[0][0]
                    ),
                    'isbn': isbn,
                    'doi': item.get('DOI'),
                    'type': item.get('type')
                }
                return APITestResult(
                    api_name="CrossRef",
                    response_time=time.time() - start_time,
                    success=True,
                    metadata=metadata,
                    http_status=response.status_code,
                    raw_response=data
                )

            return APITestResult(
                api_name="CrossRef",
                response_time=time.time() - start_time,
                success=False,
                metadata=None,
                error="No results found",
                http_status=response.status_code
            )

        except Exception as e:
            return APITestResult(
                api_name="CrossRef",
                response_time=time.time() - start_time,
                success=False,
                metadata=None,
                error=str(e)
            )

    def test_cbl(self, isbn: str) -> APITestResult:
        """Testa API da Câmara Brasileira do Livro."""
        start_time = time.time()
        try:
            response = self.http_client.get(
                f"https://isbn.cbl.org.br/api/isbn/{isbn}",
                timeout=10
            )
            data = response.json()
            
            if response.status_code == 200:
                metadata = {
                    'title': data.get('title'),
                    'authors': data.get('authors', []),
                    'publisher': data.get('publisher'),
                    'publishedDate': data.get('published_date'),
                    'isbn': isbn,
                    'edition': data.get('edition'),
                    'format': data.get('format'),
                    'language': 'pt-BR'
                }
                return APITestResult(
                    api_name="CBL",
                    response_time=time.time() - start_time,
                    success=True,
                    metadata=metadata,
                    http_status=response.status_code,
                    raw_response=data
                )

            return APITestResult(
                api_name="CBL",
                response_time=time.time() - start_time,
                success=False,
                metadata=None,
                error="No results found",
                http_status=response.status_code
            )
        except Exception as e:
            return APITestResult(
                api_name="CBL",
                response_time=time.time() - start_time,
                success=False,
                metadata=None,
                error=str(e)
            )

    def test_mercado_editorial(self, isbn: str) -> APITestResult:
        """Testa API do Mercado Editorial."""
        start_time = time.time()
        try:
            response = self.http_client.get(
                f"https://api.mercadoeditorial.org/api/v1.2/book",
                params={'isbn': isbn},
                timeout=10
            )
            data = response.json()
            
            if data.get('books'):
                book = data['books'][0]
                metadata = {
                    'title': book.get('title'),
                    'authors': book.get('authors', []),
                    'publisher': book.get('publisher'),
                    'publishedDate': book.get('published_date'),
                    'isbn': isbn,
                    'price': book.get('price'),
                    'language': book.get('language', 'pt-BR'),
                    'binding': book.get('binding')
                }
                return APITestResult(
                    api_name="Mercado Editorial",
                    response_time=time.time() - start_time,
                    success=True,
                    metadata=metadata,
                    http_status=response.status_code,
                    raw_response=data
                )

            return APITestResult(
                api_name="Mercado Editorial",
                response_time=time.time() - start_time,
                success=False,
                metadata=None,
                error="No results found",
                http_status=response.status_code
            )
        except Exception as e:
            return APITestResult(
                api_name="Mercado Editorial",
                response_time=time.time() - start_time,
                success=False,
                metadata=None,
                error=str(e)
            )

    def test_manning(self, isbn: str) -> APITestResult:
        """Testa API da Manning Publications."""
        if 'manning' not in self.api_keys:
            return APITestResult(
                api_name="Manning",
                response_time=0,
                success=False,
                metadata=None,
                error="API key not provided",
                requires_key=True
            )

        start_time = time.time()
        try:
            response = self.http_client.get(
                f"https://www.manning.com/api/books/isbn/{isbn}",
                headers={'Authorization': f"Bearer {self.api_keys['manning']}"},
                timeout=10
            )
            data = response.json()
            
            if 'book' in data:
                book = data['book']
                metadata = {
                    'title': book.get('title'),
                    'authors': book.get('authors', []),
                    'publisher': "Manning Publications",
                    'publishedDate': book.get('publicationDate'),
                    'isbn': isbn,
                    'pages': book.get('pageCount'),
                    'topics': book.get('topics', []),
                    'meap': book.get('isMeap', False)
                }
                return APITestResult(
                    api_name="Manning",
                    response_time=time.time() - start_time,
                    success=True,
                    metadata=metadata,
                    http_status=response.status_code,
                    raw_response=data
                )

            return APITestResult(
                api_name="Manning",
                response_time=time.time() - start_time,
                success=False,
                metadata=None,
                error="No results found",
                http_status=response.status_code
            )
        except Exception as e:
            return APITestResult(
                api_name="Manning",
                response_time=time.time() - start_time,
                success=False,
                metadata=None,
                error=str(e)
            )

    def test_packt(self, isbn: str) -> APITestResult:
        """Testa API da Packt Publishing."""
        if 'packt' not in self.api_keys:
            return APITestResult(
                api_name="Packt",
                response_time=0,
                success=False,
                metadata=None,
                error="API key not provided",
                requires_key=True
            )

        start_time = time.time()
        try:
            response = self.http_client.get(
                f"https://api.packtpub.com/products/isbn/{isbn}",
                headers={'Authorization': f"Bearer {self.api_keys['packt']}"},
                timeout=10
            )
            data = response.json()
            
            if data.get('data'):
                book = data['data']
                metadata = {
                    'title': book.get('title'),
                    'authors': book.get('authors', []),
                    'publisher': "Packt Publishing",
                    'publishedDate': book.get('publicationDate'),
                    'isbn': isbn,
                    'pages': book.get('pageCount'),
                    'topics': book.get('topics', []),
                    'format': book.get('productType')
                }
                return APITestResult(
                    api_name="Packt",
                    response_time=time.time() - start_time,
                    success=True,
                    metadata=metadata,
                    http_status=response.status_code,
                    raw_response=data
                )

            return APITestResult(
                api_name="Packt",
                response_time=time.time() - start_time,
                success=False,
                metadata=None,
                error="No results found",
                http_status=response.status_code
            )
        except Exception as e:
            return APITestResult(
                api_name="Packt",
                response_time=time.time() - start_time,
                success=False,
                metadata=None,
                error=str(e)
            )


    def test_oreilly(self, isbn: str) -> APITestResult:
        """Testa API da O'Reilly."""
        start_time = time.time()
        try:
            response = self.http_client.get(
                f"https://learning.oreilly.com/api/v2/book/isbn/{isbn}/",
                headers={'Authorization': f"Bearer {self.api_keys.get('oreilly', '')}"} if 'oreilly' in self.api_keys else {},
                timeout=10
            )
            data = response.json()
            
            if 'title' in data:
                metadata = {
                    'title': data.get('title'),
                    'authors': data.get('authors', []),
                    'publisher': data.get('publisher', "O'Reilly Media"),
                    'publishedDate': data.get('issued'),
                    'isbn': isbn,
                    'topics': data.get('topics', []),
                    'format': data.get('format'),
                    'url': data.get('canonical_url')
                }
                return APITestResult(
                    api_name="O'Reilly",
                    response_time=time.time() - start_time,
                    success=True,
                    metadata=metadata,
                    http_status=response.status_code,
                    raw_response=data
                )

            return APITestResult(
                api_name="O'Reilly",
                response_time=time.time() - start_time,
                success=False,
                metadata=None,
                error="No results found"
            )
        except Exception as e:
            return APITestResult(
                api_name="O'Reilly",
                response_time=time.time() - start_time,
                success=False,
                metadata=None,
                error=str(e)
            )

    def test_pearson(self, isbn: str) -> APITestResult:
        """Testa API da Pearson."""
        if 'pearson' not in self.api_keys:
            return APITestResult(
                api_name="Pearson",
                response_time=0,
                success=False,
                metadata=None,
                error="API key not provided",
                requires_key=True
            )

        start_time = time.time()
        try:
            response = self.http_client.get(
                f"https://api.pearson.com/v1/books",
                params={'isbn': isbn},
                headers={'Authorization': f"Bearer {self.api_keys['pearson']}"},
                timeout=10
            )
            data = response.json()
            
            if data.get('results'):
                book = data['results'][0]
                metadata = {
                    'title': book.get('title'),
                    'authors': book.get('authors', []),
                    'publisher': 'Pearson',
                    'publishedDate': book.get('publicationDate'),
                    'isbn': isbn,
                    'edition': book.get('edition'),
                    'language': book.get('language'),
                    'subjects': book.get('subjects', [])
                }
                return APITestResult(
                    api_name="Pearson",
                    response_time=time.time() - start_time,
                    success=True,
                    metadata=metadata,
                    http_status=response.status_code,
                    raw_response=data
                )

            return APITestResult(
                api_name="Pearson",
                response_time=time.time() - start_time,
                success=False,
                metadata=None,
                error="No results found"
            )
        except Exception as e:
            return APITestResult(
                api_name="Pearson",
                response_time=time.time() - start_time,
                success=False,
                metadata=None,
                error=str(e)
            )

    def test_springer(self, isbn: str) -> APITestResult:
        """Testa a API da Springer."""
        if 'springer' not in self.api_keys:
            return APITestResult(
                api_name="Springer",
                response_time=0,
                success=False,
                metadata=None,
                error="API key not provided",
                requires_key=True
            )

        start_time = time.time()
        try:
            response = self.http_client.get(
                f"https://api.springernature.com/metadata/book/isbn/{isbn}",
                headers={'X-ApiKey': self.api_keys['springer']},
                timeout=10
            )
            data = response.json()

            if 'records' in data and data['records']:
                record = data['records'][0]
                metadata = {
                    'title': record.get('title'),
                    'authors': record.get('creators', []),
                    'publisher': 'Springer',
                    'publishedDate': record.get('publicationDate'),
                    'isbn': isbn,
                    'doi': record.get('doi'),
                    'url': record.get('url'),
                    'subjects': record.get('subjects', [])
                }
                return APITestResult(
                    api_name="Springer",
                    response_time=time.time() - start_time,
                    success=True,
                    metadata=metadata,
                    http_status=response.status_code,
                    raw_response=data
                )

            return APITestResult(
                api_name="Springer",
                response_time=time.time() - start_time,
                success=False,
                metadata=None,
                error="No results found",
                http_status=response.status_code
            )

        except Exception as e:
            return APITestResult(
                api_name="Springer",
                response_time=time.time() - start_time,
                success=False,
                metadata=None,
                error=str(e)
            )
            

    def test_all_apis(self, isbn: str) -> List[APITestResult]:
        """Testa todas as APIs disponíveis para um ISBN."""
        # Primeiro, verifica o cache
        cached_results = self.cache.get(isbn)
        if cached_results:
            results = []
            for r in cached_results:
                r_copy = r.copy()
                r_copy.pop('cache_hit', None)
                result = APITestResult(**r_copy, cache_hit=True)
                results.append(result)
            return results

        # Lista completa de APIs para testar
        apis = [
            # APIs sem chave
            (self.test_google_books, "Google Books", False),
            (self.test_open_library, "OpenLibrary", False),
            (self.test_worldcat, "WorldCat", False),
            (self.test_crossref, "CrossRef", False),
            
            # APIs do seu código original
            (self.test_cbl, "CBL", False),  # Câmara Brasileira do Livro
            (self.test_mercado_editorial, "Mercado Editorial", False),
            (self.test_google_books_br, "Google Books BR", False),
            (self.test_zbib, "ZBib", False),
            (self.test_mybib, "MyBib", False),
            (self.test_ebook_de, "Ebook.de", False),
            
            # APIs técnicas/acadêmicas
            (self.test_springer, "Springer", True),
            (self.test_oreilly, "O'Reilly", True),
            (self.test_internet_archive, "Internet Archive", False),
            (self.test_loc, "Library of Congress", False),
            
            # APIs adicionais para livros técnicos
            (self.test_manning, "Manning", True),
            (self.test_packt, "Packt", True),
            (self.test_apress, "Apress", True),
            
            # APIs de bibliotecas
            (self.test_british_library, "British Library", True),
            (self.test_deutsche_nb, "Deutsche Nationalbibliothek", True),
            (self.test_hathitrust, "HathiTrust", False)
        ]
        
        # Adiciona resultados do isbnlib
        results = self.test_isbnlib_providers(isbn)

        # Testa outras APIs em paralelo
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_api = {}
            for api_func, api_name, requires_key in apis:
                if requires_key and not self._has_api_key(api_name.lower().replace(" ", "_")):
                    results.append(APITestResult(
                        api_name=api_name,
                        response_time=0,
                        success=False,
                        metadata=None,
                        error="API key not provided",
                        requires_key=True
                    ))
                    continue
                future_to_api[executor.submit(api_func, isbn)] = (api_name, requires_key)

            for future in as_completed(future_to_api):
                api_name, requires_key = future_to_api[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                except Exception as e:
                    results.append(APITestResult(
                        api_name=api_name,
                        response_time=0,
                        success=False,
                        metadata=None,
                        error=str(e),
                        requires_key=requires_key
                    ))

        # Cache os resultados
        self.cache.set(isbn, [asdict(r) for r in results])
        return results

    def _has_api_key(self, api_name: str) -> bool:
        """Verifica se possui chave de API para o serviço especificado."""
        return api_name.lower() in self.api_keys

    def _evaluate_confidence(self, results: List[APITestResult]) -> Dict[str, float]:
        """Avalia a confiança dos resultados comparando entre APIs."""
        if not results:
            return {}

        # Coleta todos os valores únicos para cada campo
        fields = {
            'title': [],
            'authors': [],
            'publisher': [],
            'publishedDate': []
        }

        # Agrupa valores por campo
        for result in results:
            if result.success and result.metadata:
                for field in fields:
                    value = result.metadata.get(field)
                    if value:
                        if isinstance(value, list):
                            fields[field].extend(value)
                        else:
                            fields[field].append(value)

        # Calcula confiança para cada campo
        confidence_scores = {}
        for field, values in fields.items():
            if not values:
                confidence_scores[field] = 0
                continue

            # Para campos que são listas (como autores)
            if isinstance(values[0], list):
                flat_values = [item for sublist in values for item in sublist]
                counter = Counter(flat_values)
            else:
                counter = Counter(values)

            if counter:
                most_common = counter.most_common(1)[0]
                confidence = most_common[1] / len(values)
                confidence_scores[field] = confidence

        return confidence_scores

    def process_results(self, isbn: str, results: List[APITestResult]) -> Dict:
        """Processa e consolida resultados dos testes."""
        successful_results = [r for r in results if r.success]
        
        summary = {
            'isbn': isbn,
            'total_apis_tested': len(results),
            'successful_apis': len(successful_results),
            'total_time': sum(r.response_time for r in results),
            'fastest_api': min(results, key=lambda x: x.response_time if x.response_time > 0 else float('inf')).api_name,
            'confidence_scores': self._evaluate_confidence(results),
            'results': [asdict(r) for r in results]
        }

        # Tenta consolidar metadados
        if successful_results:
            consolidated = {}
            for field in ['title', 'authors', 'publisher', 'publishedDate']:
                values = [r.metadata.get(field) for r in successful_results if r.metadata and r.metadata.get(field)]
                if values:
                    if isinstance(values[0], list):
                        # Para campos que são listas (como autores)
                        all_values = [item for sublist in values for item in sublist]
                        consolidated[field] = Counter(all_values).most_common(1)[0][0]
                    else:
                        consolidated[field] = Counter(values).most_common(1)[0][0]
            summary['consolidated_metadata'] = consolidated

        return summary

    def run_tests(self, isbn: str) -> dict:
        """Executa testes para um ISBN e retorna resultados processados."""
        results = self.test_all_apis(isbn)
        return self.process_results(isbn, results)

    def batch_test(self, isbns: List[str], progress_bar: bool = True) -> List[dict]:
        """Executa testes para múltiplos ISBNs."""
        results = []
        iterator = tqdm(isbns) if progress_bar else isbns
        
        for isbn in iterator:
            if progress_bar:
                iterator.set_description(f"Testando ISBN {isbn}")
            try:
                result = self.run_tests(isbn)
                results.append(result)
            except Exception as e:
                logging.error(f"Erro processando ISBN {isbn}: {str(e)}")
                results.append({
                    'isbn': isbn,
                    'error': str(e),
                    'success': False
                })
                
        return results

    def generate_report(self, results: List[dict], output_dir: str = "reports") -> Tuple[str, str]:
        """Gera relatórios HTML e JSON dos resultados."""
        Path(output_dir).mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Gera relatório JSON
        json_file = Path(output_dir) / f"report_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        # Gera relatório HTML
        html_file = Path(output_dir) / f"report_{timestamp}.html"
        self._generate_html_report(results, html_file)

        return str(html_file), str(json_file)

    def _generate_html_report(self, results: List[dict], output_file: Path):
        """Gera relatório HTML detalhado."""
        # Coleta estatísticas gerais
        total_tests = len(results)
        successful_tests = sum(1 for r in results if r.get('successful_apis', 0) > 0)
        api_stats = {}

        for result in results:
            for api_result in result.get('results', []):
                api_name = api_result['api_name']
                if api_name not in api_stats:
                    api_stats[api_name] = {
                        'success': 0, 
                        'total': 0, 
                        'avg_time': 0,
                        'errors': []
                    }
                
                stats = api_stats[api_name]
                stats['total'] += 1
                if api_result['success']:
                    stats['success'] += 1
                    stats['avg_time'] += api_result['response_time']
                elif api_result.get('error'):
                    stats['errors'].append(api_result['error'])

        for stats in api_stats.values():
            if stats['success'] > 0:
                stats['avg_time'] /= stats['success']

        # Gera HTML
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>ISBN API Test Results</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; max-width: 1200px; margin: 0 auto; }}
                .card {{ background: #fff; border-radius: 8px; padding: 20px; margin: 10px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .success {{ color: green; }}
                .failure {{ color: red; }}
                table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background: #f5f5f5; }}
                .metadata {{ background: #f8f9fa; padding: 10px; border-radius: 4px; }}
                .check-success {{ color: green; font-weight: bold; }}
                .check-failure {{ color: red; font-weight: bold; }}
            </style>
        </head>
        <body>
            <h1>ISBN API Test Results</h1>
            <p>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>

            <div class="card">
                <h2>Summary</h2>
                <table>
                    <tr><th>Total Tests</th><td>{total_tests}</td></tr>
                    <tr><th>Successful Tests</th><td>{successful_tests} ({(successful_tests/total_tests*100):.1f}%)</td></tr>
                </table>
            </div>

            <div class="card">
                <h2>API Performance</h2>
                <table>
                    <tr>
                        <th>API</th>
                        <th>Success Rate</th>
                        <th>Avg Response Time</th>
                        <th>Errors</th>
                    </tr>
        """

        # Adiciona estatísticas por API
        for api_name, stats in api_stats.items():
            success_rate = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
            html_content += f"""
                    <tr>
                        <td>{api_name}</td>
                        <td>{success_rate:.1f}%</td>
                        <td>{stats['avg_time']:.3f}s</td>
                        <td>{len(stats['errors'])}</td>
                    </tr>
            """

        html_content += """
                </table>
            </div>

            <div class="card">
                <h2>Detailed Results</h2>
        """

        # Adiciona resultados detalhados por ISBN
        for result in results:
            html_content += f"""
                <div class="metadata">
                    <h3>ISBN: {result['isbn']}</h3>
                    <table>
                        <tr>
                            <th>API</th>
                            <th>Status</th>
                            <th>Time</th>
                            <th>Metadata</th>
                            <th>Error</th>
                        </tr>
            """

        for api_result in result.get('results', []):
            status = "SUCESSO" if api_result['success'] else "FALHA"
            status_class = "check-success" if api_result['success'] else "check-failure"

            metadata_html = ""
            if api_result['metadata']:
                metadata_html = "<ul>"
                for key, value in api_result['metadata'].items():
                    if isinstance(value, list):
                        value = ", ".join(str(v) for v in value)
                    metadata_html += f"<li><strong>{key}:</strong> {value}</li>"
                metadata_html += "</ul>"

            html_content += f"""
                    <tr>
                        <td>{api_result['api_name']}</td>
                        <td class="{status_class}">{status}</td>
                        <td>{api_result['response_time']:.3f}s</td>
                        <td>{metadata_html}</td>
                        <td>{api_result.get('error', '')}</td>
                    </tr>
                """

            html_content += """
                    </table>
                </div>
            """

        html_content += """
            </div>
        </body>
        </html>
        """

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

def main():
    """Função principal para demonstração e teste."""
    # Lista de ISBNs para testar
    test_isbns = [
        # Brasileiros
        "9786586057485",  # Casa do Código - Entendendo Algoritmos
        "9788575228289",  # Novatec - Python e Django
        "9788550800653",  # Alta Books - Docker
        
        # No Starch Press
        "9781718502666",  # The Rust Programming Language
        "9781593279288",  # Python Crash Course
        
        # O'Reilly
        "9781492056355",  # Fluent Python
        "9781492051367",  # Designing Data-Intensive Applications
        
        # Pearson
        "9780134685991",  # Effective Java
        
        # Wiley
        "9781119775553",  # AWS Certified Solutions Architect
        "9781118951309"   # Software Architecture in Practice
        
    ]

    # Configuração de APIs (adicione suas chaves aqui)
    api_keys = {
        'isbndb': 'sua_chave_isbndb',
        'springer': 'sua_chave_springer',
    }

    try:
        # Inicializa o testador
        tester = ISBNAPITester(api_keys)
        
        # Testa ISBNs com barra de progresso
        print("\nTestando ISBNs...")
        results = tester.batch_test(test_isbns)
        
        # Gera relatórios
        html_report, json_report = tester.generate_report(results)
        
        print(f"\nRelatórios gerados:")
        print(f"HTML: {html_report}")
        print(f"JSON: {json_report}")
        
    except Exception as e:
        print(f"Erro: {str(e)}")
        raise

if __name__ == "__main__":
    main()