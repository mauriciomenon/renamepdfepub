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

    def test_internet_archive(self, isbn: str) -> APITestResult:
        """Testa API do Internet Archive."""
        start_time = time.time()
        try:
            url = "https://archive.org/advancedsearch.php"
            params = {
                'q': f'identifier:{isbn} OR isbn:{isbn}',
                'output': 'json',
                'rows': 1,
                'fl[]': ['title', 'creator', 'publisher', 'date', 'language']
            }
            response = self.http_client.get(url, params=params, timeout=10)
            data = response.json()

            if data.get('response', {}).get('docs'):
                doc = data['response']['docs'][0]
                metadata = {
                    'title': doc.get('title'),
                    'authors': [doc.get('creator')] if doc.get('creator') else [],
                    'publisher': doc.get('publisher'),
                    'publishedDate': doc.get('date'),
                    'isbn': isbn,
                    'language': doc.get('language')
                }
                return APITestResult(
                    api_name="Internet Archive",
                    response_time=time.time() - start_time,
                    success=True,
                    metadata=metadata,
                    http_status=response.status_code,
                    raw_response=data
                )

            return APITestResult(
                api_name="Internet Archive",
                response_time=time.time() - start_time,
                success=False,
                metadata=None,
                error="No results found"
            )
        except Exception as e:
            return APITestResult(
                api_name="Internet Archive",
                response_time=time.time() - start_time,
                success=False,
                metadata=None,
                error=str(e)
            )

    def test_hathitrust(self, isbn: str) -> APITestResult:
        """Testa API do HathiTrust."""
        start_time = time.time()
        try:
            url = f"https://catalog.hathitrust.org/api/volumes/brief/isbn/{isbn}.json"
            response = self.http_client.get(url, timeout=10)
            data = response.json()

            if data.get('items'):
                item = data['items'][0]
                metadata = {
                    'title': item.get('title'),
                    'authors': item.get('authors', []),
                    'publisher': item.get('pub', {}).get('name'),
                    'publishedDate': item.get('pub', {}).get('date'),
                    'isbn': isbn,
                    'language': item.get('language', {}).get('name')
                }
                return APITestResult(
                    api_name="HathiTrust",
                    response_time=time.time() - start_time,
                    success=True,
                    metadata=metadata,
                    http_status=response.status_code,
                    raw_response=data
                )

            return APITestResult(
                api_name="HathiTrust",
                response_time=time.time() - start_time,
                success=False,
                metadata=None,
                error="No results found"
            )
        except Exception as e:
            return APITestResult(
                api_name="HathiTrust",
                response_time=time.time() - start_time,
                success=False,
                metadata=None,
                error=str(e)
            )

    def test_google_books_br(self, isbn: str) -> APITestResult:
        """Testa API do Google Books com filtro para Brasil."""
        start_time = time.time()
        try:
            url = "https://www.googleapis.com/books/v1/volumes"
            params = {
                'q': f'isbn:{isbn}',
                'country': 'BR',
                'langRestrict': 'pt'
            }
            response = self.http_client.get(url, params=params, timeout=10)
            data = response.json()

            if 'items' in data:
                book = data['items'][0]['volumeInfo']
                metadata = {
                    'title': book.get('title'),
                    'authors': book.get('authors', []),
                    'publisher': book.get('publisher'),
                    'publishedDate': book.get('publishedDate'),
                    'isbn': isbn,
                    'language': 'pt-BR',
                    'categories': book.get('categories', [])
                }
                return APITestResult(
                    api_name="Google Books BR",
                    response_time=time.time() - start_time,
                    success=True,
                    metadata=metadata,
                    http_status=response.status_code,
                    raw_response=data
                )

            return APITestResult(
                api_name="Google Books BR",
                response_time=time.time() - start_time,
                success=False,
                metadata=None,
                error="No results found"
            )
        except Exception as e:
            return APITestResult(
                api_name="Google Books BR",
                response_time=time.time() - start_time,
                success=False,
                metadata=None,
                error=str(e)
            )

    def test_zbib(self, isbn: str) -> APITestResult:
        """Testa API do ZBib."""
        start_time = time.time()
        try:
            url = f"https://api.zbib.org/v1/search"
            params = {'q': f'isbn:{isbn}'}
            response = self.http_client.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get('items'):
                item = data['items'][0]
                metadata = {
                    'title': item.get('title'),
                    'authors': item.get('authors', []),
                    'publisher': item.get('publisher'),
                    'publishedDate': str(item.get('year')),
                    'isbn': isbn,
                    'type': item.get('type')
                }
                return APITestResult(
                    api_name="ZBib",
                    response_time=time.time() - start_time,
                    success=True,
                    metadata=metadata,
                    http_status=response.status_code,
                    raw_response=data
                )
            return APITestResult(
                api_name="ZBib",
                response_time=time.time() - start_time,
                success=False,
                metadata=None,
                error="No results found"
            )
        except Exception as e:
            return APITestResult(
                api_name="ZBib",
                response_time=time.time() - start_time,
                success=False,
                metadata=None,
                error=str(e)
            )

    def test_mybib(self, isbn: str) -> APITestResult:
        """Testa API do MyBib."""
        start_time = time.time()
        try:
            url = "https://www.mybib.com/api/v1/references"
            params = {'q': isbn}
            response = self.http_client.get(url, params=params, timeout=10)
            data = response.json()

            if data.get('references'):
                ref = data['references'][0]
                metadata = {
                    'title': ref.get('title'),
                    'authors': ref.get('authors', []),
                    'publisher': ref.get('publisher'),
                    'publishedDate': ref.get('year'),
                    'isbn': isbn,
                    'type': ref.get('type')
                }
                return APITestResult(
                    api_name="MyBib",
                    response_time=time.time() - start_time,
                    success=True,
                    metadata=metadata,
                    http_status=response.status_code,
                    raw_response=data
                )
            return APITestResult(
                api_name="MyBib",
                response_time=time.time() - start_time,
                success=False,
                metadata=None,
                error="No results found"
            )
        except Exception as e:
            return APITestResult(
                api_name="MyBib",
                response_time=time.time() - start_time,
                success=False,
                metadata=None,
                error=str(e)
            )

    def test_loc(self, isbn: str) -> APITestResult:
        """Testa API da Library of Congress."""
        start_time = time.time()
        try:
            url = f"https://www.loc.gov/books/?q={isbn}&fo=json"
            response = self.http_client.get(url, timeout=10)
            data = response.json()

            if data.get('results'):
                item = data['results'][0]
                metadata = {
                    'title': item.get('title'),
                    'authors': [item.get('contributor')] if item.get('contributor') else [],
                    'publisher': item.get('publisher'),
                    'publishedDate': item.get('date'),
                    'isbn': isbn,
                    'subjects': item.get('subject', []),
                    'language': item.get('language', [])
                }
                return APITestResult(
                    api_name="Library of Congress",
                    response_time=time.time() - start_time,
                    success=True,
                    metadata=metadata,
                    http_status=response.status_code,
                    raw_response=data
                )
            return APITestResult(
                api_name="Library of Congress",
                response_time=time.time() - start_time,
                success=False,
                metadata=None,
                error="No results found"
            )
        except Exception as e:
            return APITestResult(
                api_name="Library of Congress",
                response_time=time.time() - start_time,
                success=False,
                metadata=None,
                error=str(e)
            )

    def test_deutsche_nb(self, isbn):
        # Lógica do método
        return {"success": False, "error": "Método não implementado"}

    def test_ebook_de(self, isbn: str) -> APITestResult:
        """Testa API do Ebook.de."""
        start_time = time.time()
        try:
            url = f"https://www.ebook.de/de/tools/isbn2bibtex/{isbn}"
            response = self.http_client.get(url, timeout=10)
            text = response.text

            metadata = {}
            patterns = {
                'title': r'title\s*=\s*{([^}]+)}',
                'author': r'author\s*=\s*{([^}]+)}',
                'publisher': r'publisher\s*=\s*{([^}]+)}',
                'year': r'year\s*=\s*{(\d{4})}',
                'isbn': r'isbn\s*=\s*{([^}]+)}'
            }

            for key, pattern in patterns.items():
                match = re.search(pattern, text)
                if match:
                    metadata[key] = match.group(1)

            if metadata:
                formatted_metadata = {
                    'title': metadata.get('title'),
                    'authors': [a.strip() for a in metadata.get('author', '').split(' and ')],
                    'publisher': metadata.get('publisher'),
                    'publishedDate': metadata.get('year'),
                    'isbn': isbn
                }
                return APITestResult(
                    api_name="Ebook.de",
                    response_time=time.time() - start_time,
                    success=True,
                    metadata=formatted_metadata,
                    http_status=response.status_code,
                    raw_response=metadata
                )
            return APITestResult(
                api_name="Ebook.de",
                response_time=time.time() - start_time,
                success=False,
                metadata=None,
                error="No results found"
            )
        except Exception as e:
            return APITestResult(
                api_name="Ebook.de",
                response_time=time.time() - start_time,
                success=False,
                metadata=None,
                error=str(e)
            )

    def test_apress(self, isbn: str) -> APITestResult:
        """Testa API da Apress."""
        if 'apress' not in self.api_keys:
            return APITestResult(
                api_name="Apress",
                response_time=0,
                success=False,
                metadata=None,
                error="API key not provided",
                requires_key=True
            )

        start_time = time.time()
        try:
            url = f"https://api.springernature.com/metadata/book/isbn/{isbn}"
            headers = {
                'X-ApiKey': self.api_keys['apress'],
                'Accept': 'application/json'
            }
            response = self.http_client.get(url, headers=headers, timeout=10)
            data = response.json()

            if data.get('records'):
                record = data['records'][0]
                metadata = {
                    'title': record.get('title'),
                    'authors': record.get('creators', []),
                    'publisher': 'Apress',
                    'publishedDate': record.get('publicationDate'),
                    'isbn': isbn,
                    'doi': record.get('doi'),
                    'subjects': record.get('subjects', [])
                }
                return APITestResult(
                    api_name="Apress",
                    response_time=time.time() - start_time,
                    success=True,
                    metadata=metadata,
                    http_status=response.status_code,
                    raw_response=data
                )
            return APITestResult(
                api_name="Apress",
                response_time=time.time() - start_time,
                success=False,
                metadata=None,
                error="No results found"
            )
        except Exception as e:
            return APITestResult(
                api_name="Apress",
                response_time=time.time() - start_time,
                success=False,
                metadata=None,
                error=str(e)
            )

    def test_british_library(self, isbn: str) -> APITestResult:
        """Testa API da British Library."""
        start_time = time.time()
        try:
            url = f"http://bnb.data.bl.uk/doc/resource/isbn/{isbn}"
            headers = {'Accept': 'application/json'}
            response = self.http_client.get(url, headers=headers, timeout=10)
            data = response.json()

            if data.get('result'):
                item = data['result']
                metadata = {
                    'title': item.get('title'),
                    'authors': [a.get('name') for a in item.get('authors', [])],
                    'publisher': item.get('publisher', {}).get('name'),
                    'publishedDate': item.get('publicationDate'),
                    'isbn': isbn,
                    'language': item.get('language'),
                    'subjects': item.get('subjects', [])
                }
                return APITestResult(
                    api_name="British Library",
                    response_time=time.time() - start_time,
                    success=True,
                    metadata=metadata,
                    http_status=response.status_code,
                    raw_response=data
                )
            return APITestResult(
                api_name="British Library",
                response_time=time.time() - start_time,
                success=False,
                metadata=None,
                error="No results found"
            )
        except Exception as e:
            return APITestResult(
                api_name="British Library",
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
        # Coleta estatísticas
        total_tests = len(results)
        total_apis = len(API_REQUIREMENTS)
        successful_tests = sum(1 for r in results if r.get('successful_apis', 0) > 0)
        failed_tests = total_tests - successful_tests
        
        # Estatísticas por API
        api_stats = {}
        publisher_stats = self._collect_publisher_stats(results)
        country_stats = self._collect_country_stats(results)
        
        for result in results:
            for api_result in result.get('results', []):
                api_name = api_result['api_name']
                if api_name not in api_stats:
                    api_stats[api_name] = {
                        'success': 0,
                        'failure': 0,
                        'total': 0,
                        'avg_time': 0,
                        'errors': [],
                        'cache_hits': 0,
                        'fastest_response': float('inf'),
                        'slowest_response': 0,
                        'error_types': Counter()
                    }
                
                stats = api_stats[api_name]
                stats['total'] += 1
                
                if api_result['success']:
                    stats['success'] += 1
                    response_time = api_result['response_time']
                    stats['avg_time'] += response_time
                    stats['fastest_response'] = min(stats['fastest_response'], response_time)
                    stats['slowest_response'] = max(stats['slowest_response'], response_time)
                else:
                    stats['failure'] += 1
                    if api_result.get('error'):
                        error_type = self._categorize_error(api_result['error'])
                        stats['error_types'][error_type] += 1
                        stats['errors'].append(api_result['error'])
                
                if api_result.get('cache_hit'):
                    stats['cache_hits'] += 1

        # Calcula médias e porcentagens
        for stats in api_stats.values():
            if stats['success'] > 0:
                stats['avg_time'] /= stats['success']
            stats['success_rate'] = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
            stats['failure_rate'] = (stats['failure'] / stats['total'] * 100) if stats['total'] > 0 else 0
            stats['cache_hit_rate'] = (stats['cache_hits'] / stats['total'] * 100) if stats['total'] > 0 else 0

        # Gera HTML
        html_content = self._generate_html_header()
        html_content += self._generate_summary_section(total_tests, successful_tests, failed_tests, total_apis)
        html_content += self._generate_api_performance_section(api_stats)
        html_content += self._generate_publisher_section(publisher_stats)
        html_content += self._generate_country_section(country_stats)
        html_content += self._generate_detailed_results_section(results)
        html_content += self._generate_error_analysis_section(api_stats)
        html_content += "</body></html>"

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

    def _collect_publisher_stats(self, results: List[dict]) -> Dict:
        """Coleta estatísticas por editora."""
        publisher_stats = {}
        for result in results:
            isbn = result['isbn']
            publisher = self._identify_publisher(isbn)
            publisher_stats.setdefault(publisher, {'success': 0, 'total': 0})
            publisher_stats[publisher]['total'] += 1
            if result.get('successful_apis', 0) > 0:
                publisher_stats[publisher]['success'] += 1
        return publisher_stats

    def _collect_country_stats(self, results: List[dict]) -> Dict:
        """Coleta estatísticas por país."""
        country_stats = {}
        for result in results:
            isbn = result['isbn']
            country = self._identify_country(isbn)
            country_stats.setdefault(country, {'success': 0, 'total': 0})
            country_stats[country]['total'] += 1
            if result.get('successful_apis', 0) > 0:
                country_stats[country]['success'] += 1
        return country_stats

    def _categorize_error(self, error: str) -> str:
        """Categoriza tipos de erro."""
        error = error.lower()
        if 'timeout' in error:
            return 'Timeout'
        elif 'not found' in error:
            return 'Not Found'
        elif 'key' in error and ('invalid' in error or 'missing' in error):
            return 'API Key Error'
        elif 'rate limit' in error or '429' in error:
            return 'Rate Limit'
        elif any(code in error for code in ['500', '502', '503', '504']):
            return 'Server Error'
        elif 'connection' in error:
            return 'Connection Error'
        return 'Other'

    def _identify_publisher(self, isbn: str) -> str:
        """Identifica editora pelo ISBN."""
        publisher_prefixes = {
            '65': 'Brazilian Publishers',
            '85': 'Brazilian Publishers',
            '14': "O'Reilly/Apress",
            '17': 'Packt',
            '16': 'Manning',
            '11': 'Wiley',
            '13': 'Pearson'
        }
        
        if len(isbn) == 13 and isbn.startswith('978'):
            prefix = isbn[3:5]
            return publisher_prefixes.get(prefix, 'Other')
        return 'Unknown'

    def _identify_country(self, isbn: str) -> str:
        """Identifica país pelo ISBN."""
        country_groups = {
            '0': 'English (US/UK)',
            '1': 'English (US/UK)',
            '2': 'French',
            '3': 'German',
            '65': 'Brazil',
            '85': 'Brazil',
            '7': 'China',
            '4': 'Japan',
            '5': 'Russia',
            '84': 'Spain',
            '88': 'Italy',
            '89': 'Korea',
            '91': 'Sweden',
            '972': 'Portugal'
        }
        
        if len(isbn) == 13 and isbn.startswith('978'):
            group = isbn[3:5]
            # Verifica prefixos especiais de 3 dígitos
            if isbn[3:6] in country_groups:
                return country_groups[isbn[3:6]]
            return country_groups.get(group, 'Other')
        return 'Unknown'

    def _generate_html_header(self) -> str:
        """Gera cabeçalho HTML com estilos melhorados."""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>ISBN API Test Results</title>
            <style>
                :root {
                    --success-color: #28a745;
                    --warning-color: #ffc107;
                    --danger-color: #dc3545;
                    --info-color: #17a2b8;
                }
                body { 
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                    margin: 20px auto;
                    max-width: 1200px;
                    background-color: #f8f9fa;
                    color: #212529;
                    line-height: 1.5;
                }
                .card { 
                    background: #fff;
                    border-radius: 8px;
                    padding: 20px;
                    margin: 15px 0;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                .success { color: var(--success-color); }
                .warning { color: var(--warning-color); }
                .failure { color: var(--danger-color); }
                table { 
                    width: 100%;
                    border-collapse: collapse;
                    margin: 10px 0;
                    background: white;
                }
                th, td { 
                    border: 1px solid #dee2e6;
                    padding: 12px 8px;
                    text-align: left;
                }
                th { 
                    background: #f8f9fa;
                    font-weight: 600;
                    color: #495057;
                }
                .metadata { 
                    background: #f8f9fa;
                    padding: 15px;
                    border-radius: 4px;
                    margin: 10px 0;
                }
                .error-box {
                    background: #fff3f3;
                    padding: 15px;
                    border-radius: 4px;
                    margin: 10px 0;
                    border-left: 4px solid var(--danger-color);
                }
                .stats-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                    gap: 20px;
                    margin: 20px 0;
                }
                .stat-box {
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                .progress-bar {
                    height: 20px;
                    background: #e9ecef;
                    border-radius: 10px;
                    overflow: hidden;
                    margin: 10px 0;
                }
                .progress-bar-fill {
                    height: 100%;
                    transition: width .6s ease;
                }
                .progress-bar-success { background-color: var(--success-color); }
                .progress-bar-failure { background-color: var(--danger-color); }
                .tab-container {
                    margin: 20px 0;
                }
                .tab-header {
                    display: flex;
                    gap: 10px;
                    margin-bottom: 10px;
                }
                .tab {
                    padding: 10px 20px;
                    background: #e9ecef;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    font-weight: 500;
                }
                .tab.active {
                    background: var(--info-color);
                    color: white;
                }
                .tab-content {
                    display: none;
                }
                .tab-content.active {
                    display: block;
                }
                .chart {
                    height: 400px;
                    margin: 20px 0;
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                @media (max-width: 768px) {
                    .stats-grid {
                        grid-template-columns: 1fr;
                    }
                    .card {
                        margin: 10px;
                    }
                    table {
                        display: block;
                        overflow-x: auto;
                    }
                }
            </style>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        </head>
        <body>
            <h1>ISBN API Test Results</h1>
            <p>Generated: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
        """

    def _generate_summary_section(self, total_tests: int, successful_tests: int, 
                                failed_tests: int, total_apis: int) -> str:
        """Gera seção de resumo com estatísticas gerais."""
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        failure_rate = (failed_tests / total_tests * 100) if total_tests > 0 else 0
        
        return f"""
            <div class="card">
                <h2>Summary</h2>
                <div class="stats-grid">
                    <div class="stat-box">
                        <h3>Tests Overview</h3>
                        <p>Total Tests: {total_tests}</p>
                        <p class="success">Successful: {successful_tests} ({success_rate:.1f}%)</p>
                        <p class="failure">Failed: {failed_tests} ({failure_rate:.1f}%)</p>
                        <div class="progress-bar">
                            <div class="progress-bar-fill progress-bar-success" 
                                style="width: {success_rate}%"></div>
                        </div>
                    </div>
                    <div class="stat-box">
                        <h3>APIs Overview</h3>
                        <p>Total APIs: {total_apis}</p>
                        <p>Free APIs: {len([k for k, v in API_REQUIREMENTS.items() if not v['requires_key']])}</p>
                        <p>APIs requiring key: {len([k for k, v in API_REQUIREMENTS.items() if v['requires_key']])}</p>
                    </div>
                    <div class="stat-box">
                        <h3>Success Rate</h3>
                        <div class="progress-bar">
                            <div class="progress-bar-fill progress-bar-success" 
                                style="width: {success_rate}%"></div>
                        </div>
                        <p>Success Rate: {success_rate:.1f}%</p>
                        <p>Failure Rate: {failure_rate:.1f}%</p>
                    </div>
                </div>
            </div>
        """

    def _generate_api_performance_section(self, api_stats: Dict) -> str:
        """Gera seção de performance das APIs."""
        content = """
            <div class="card">
                <h2>API Performance</h2>
                <table>
                    <tr>
                        <th>API</th>
                        <th>Success/Total</th>
                        <th>Success Rate</th>
                        <th>Failure Rate</th>
                        <th>Avg Time</th>
                        <th>Fastest</th>
                        <th>Slowest</th>
                        <th>Cache Hits</th>
                        <th>Errors</th>
                    </tr>
        """
        
        for api_name, stats in sorted(api_stats.items(), 
                                    key=lambda x: x[1]['success_rate'], 
                                    reverse=True):
            total = stats['total']
            success = stats['success']
            failures = stats['failure']
            content += f"""
                <tr>
                    <td>{api_name}</td>
                    <td>{success}/{total}</td>
                    <td class="success">{stats['success_rate']:.1f}%</td>
                    <td class="failure">{stats['failure_rate']:.1f}%</td>
                    <td>{stats['avg_time']:.3f}s</td>
                    <td>{stats['fastest_response']:.3f}s</td>
                    <td>{stats['slowest_response']:.3f}s</td>
                    <td>{stats['cache_hits']} ({stats['cache_hit_rate']:.1f}%)</td>
                    <td>{failures} ({len(stats['errors'])} unique)</td>
                </tr>
            """
        
        content += """
                </table>
            </div>
        """
        return content

    def _generate_publisher_section(self, publisher_stats: Dict) -> str:
        """Gera seção de estatísticas por editora."""
        content = """
            <div class="card">
                <h2>Publisher Statistics</h2>
                <table>
                    <tr>
                        <th>Publisher</th>
                        <th>Success</th>
                        <th>Total</th>
                        <th>Success Rate</th>
                        <th>Failure Rate</th>
                    </tr>
        """
        
        for publisher, stats in sorted(publisher_stats.items(),
                                    key=lambda x: (x[1]['success']/x[1]['total'] 
                                                if x[1]['total'] > 0 else 0),
                                    reverse=True):
            total = stats['total']
            success = stats['success']
            failures = total - success
            success_rate = (success / total * 100) if total > 0 else 0
            failure_rate = (failures / total * 100) if total > 0 else 0
            
            content += f"""
                <tr>
                    <td>{publisher}</td>
                    <td>{success}</td>
                    <td>{total}</td>
                    <td class="success">{success_rate:.1f}%</td>
                    <td class="failure">{failure_rate:.1f}%</td>
                </tr>
            """
        
        content += """
                </table>
            </div>
        """
        return content

    def _generate_country_section(self, country_stats: Dict) -> str:
        """Gera seção de estatísticas por país."""
        content = """
            <div class="card">
                <h2>Country Statistics</h2>
                <table>
                    <tr>
                        <th>Country/Region</th>
                        <th>Success</th>
                        <th>Total</th>
                        <th>Success Rate</th>
                        <th>Failure Rate</th>
                    </tr>
        """
        
        for country, stats in sorted(country_stats.items(),
                                key=lambda x: (x[1]['success']/x[1]['total'] 
                                                if x[1]['total'] > 0 else 0),
                                reverse=True):
            total = stats['total']
            success = stats['success']
            failures = total - success
            success_rate = (success / total * 100) if total > 0 else 0
            failure_rate = (failures / total * 100) if total > 0 else 0
            
            content += f"""
                <tr>
                    <td>{country}</td>
                    <td>{success}</td>
                    <td>{total}</td>
                    <td class="success">{success_rate:.1f}%</td>
                    <td class="failure">{failure_rate:.1f}%</td>
                </tr>
            """
        
        content += """
                </table>
            </div>
        """
        return content

    def _generate_error_analysis_section(self, api_stats: Dict) -> str:
        """Gera seção de análise de erros."""
        content = """
            <div class="card">
                <h2>Error Analysis</h2>
        """
        
        for api_name, stats in api_stats.items():
            if stats['errors']:
                content += f"""
                    <div class="error-box">
                        <h3>{api_name}</h3>
                        <p>Total Errors: {len(stats['errors'])} in {stats['failure']} failures</p>
                        <h4>Error Types:</h4>
                        <ul>
                """
                
                for error_type, count in stats['error_types'].most_common():
                    percentage = (count / stats['failure'] * 100) if stats['failure'] > 0 else 0
                    content += f"""
                        <li><strong>{error_type}:</strong> {count} ({percentage:.1f}%)</li>
                    """
                
                content += """
                        </ul>
                    </div>
                """
        
        content += """
            </div>
        """
        return content

    def _generate_detailed_results_section(self, results: List[dict]) -> str:
        """Gera seção de resultados detalhados por ISBN."""
        content = """
            <div class="card">
                <h2>Detailed Results</h2>
                <div class="tab-container">
                    <div class="tab-header">
                        <button class="tab active" onclick="showTab('overview')">Overview</button>
                        <button class="tab" onclick="showTab('details')">Details</button>
                    </div>
        """
        
        # Overview tab
        content += """
            <div id="overview" class="tab-content active">
                <table>
                    <tr>
                        <th>ISBN</th>
                        <th>Success Rate</th>
                        <th>APIs Success</th>
                        <th>Best Response</th>
                        <th>Best Source</th>
                    </tr>
        """
        
        for result in results:
            isbn = result['isbn']
            api_results = result.get('results', [])
            successful_apis = [r for r in api_results if r['success']]
            success_rate = len(successful_apis)/len(api_results)*100 if api_results else 0
            fastest_api = min((r for r in successful_apis), 
                            key=lambda x: x['response_time']) if successful_apis else None
            
            fastest_time = f"{fastest_api['response_time']:.3f}s" if fastest_api else "N/A"
            fastest_api_name = fastest_api['api_name'] if fastest_api else "N/A"

            content += f"""
                <tr>
                    <td>{isbn}</td>
                    <td>{success_rate:.1f}%</td>
                    <td>{len(successful_apis)}/{len(api_results)}</td>
                    <td>{fastest_time}</td>
                    <td>{fastest_api_name}</td>
                </tr>
            """
        
        content += """
                </table>
            </div>
        """
        
        # Detailed tab
        content += """
            <div id="details" class="tab-content">
        """
        
        for result in results:
            isbn = result['isbn']
            api_results = result.get('results', [])
            successful_apis = [r for r in api_results if r['success']]
            
            content += f"""
                <div class="metadata">
                    <h3>ISBN: {isbn}</h3>
                    <p>Success Rate: {len(successful_apis)}/{len(api_results)} 
                    ({len(successful_apis)/len(api_results)*100:.1f}%)</p>
                    <table>
                        <tr>
                            <th>API</th>
                            <th>Status</th>
                            <th>Time</th>
                            <th>Metadata</th>
                            <th>Error/Info</th>
                        </tr>
            """
            
            for api_result in api_results:
                status = "SUCCESS" if api_result['success'] else "FAILURE"
                status_class = "success" if api_result['success'] else "failure"
                
                metadata_html = ""
                if api_result['metadata']:
                    metadata_html = "<ul style='margin: 0; padding-left: 20px;'>"
                    for key, value in api_result['metadata'].items():
                        if isinstance(value, list):
                            value = ", ".join(str(v) for v in value)
                        metadata_html += f"<li><strong>{key}:</strong> {value}</li>"
                    metadata_html += "</ul>"
                
                content += f"""
                    <tr>
                        <td>{api_result['api_name']}</td>
                        <td class="{status_class}">{status}</td>
                        <td>{api_result['response_time']:.3f}s</td>
                        <td>{metadata_html}</td>
                        <td>{api_result.get('error', 'OK')}</td>
                    </tr>
                """
            
            content += """
                    </table>
                </div>
            """
        
        content += """
                </div>
            </div>
            <script>
                function showTab(tabId) {
                    // Hide all tabs
                    document.querySelectorAll('.tab-content').forEach(tab => {
                        tab.classList.remove('active');
                    });
                    document.querySelectorAll('.tab').forEach(tab => {
                        tab.classList.remove('active');
                    });
                    
                    // Show selected tab
                    document.getElementById(tabId).classList.add('active');
                    document.querySelector(`button[onclick="showTab('${tabId}')"]`).classList.add('active');
                }
            </script>
        """
        
        return content

    def _generate_charts_section(self, api_stats: Dict) -> str:
        """Gera seção com gráficos interativos."""
        # Prepara dados para os gráficos
        api_names = list(api_stats.keys())
        success_rates = [stats['success_rate'] for stats in api_stats.values()]
        response_times = [stats['avg_time'] for stats in api_stats.values()]
        error_rates = [stats['failure_rate'] for stats in api_stats.values()]
        cache_hits = [stats['cache_hits'] for stats in api_stats.values()]

        return f"""
            <div class="card">
                <h2>Performance Charts</h2>
                
                <div class="chart">
                    <div id="success-rate-chart"></div>
                </div>
                
                <div class="chart">
                    <div id="response-time-chart"></div>
                </div>
                
                <div class="chart">
                    <div id="error-rate-chart"></div>
                </div>
                
                <script>
                    // Success Rate Chart
                    const successData = {{
                        x: {api_names},
                        y: {success_rates},
                        type: 'bar',
                        name: 'Success Rate',
                        marker: {{ color: '#28a745' }}
                    }};
                    
                    Plotly.newPlot('success-rate-chart', [successData], {{
                        title: 'API Success Rates',
                        xaxis: {{ title: 'API' }},
                        yaxis: {{ title: 'Success Rate (%)', range: [0, 100] }},
                        margin: {{ t: 50, b: 100 }}
                    }});
                    
                    // Response Time Chart
                    const timeData = {{
                        x: {api_names},
                        y: {response_times},
                        type: 'bar',
                        name: 'Response Time',
                        marker: {{ color: '#17a2b8' }}
                    }};
                    
                    Plotly.newPlot('response-time-chart', [timeData], {{
                        title: 'Average Response Times',
                        xaxis: {{ title: 'API' }},
                        yaxis: {{ title: 'Time (seconds)' }},
                        margin: {{ t: 50, b: 100 }}
                    }});
                    
                    // Error Rate Chart
                    const errorData = {{
                        x: {api_names},
                        y: {error_rates},
                        type: 'bar',
                        name: 'Error Rate',
                        marker: {{ color: '#dc3545' }}
                    }};
                    
                    Plotly.newPlot('error-rate-chart', [errorData], {{
                        title: 'API Error Rates',
                        xaxis: {{ title: 'API' }},
                        yaxis: {{ title: 'Error Rate (%)', range: [0, 100] }},
                        margin: {{ t: 50, b: 100 }}
                    }});
                </script>
            </div>
        """

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