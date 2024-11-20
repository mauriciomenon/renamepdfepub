import logging
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
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

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('isbn_api_tester.log')
    ]
)

@dataclass
class APITestResult:
    """Classe para armazenar resultados dos testes de API"""
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

class HttpClient:
    """Cliente HTTP com retry e timeouts"""
    def __init__(self):
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        session.headers.update({
            'User-Agent': 'ISBN-API-Tester/1.0',
            'Accept': 'application/json'
        })
        
        return session

    def get(self, url: str, **kwargs) -> requests.Response:
        return self.session.get(url, **kwargs)

class ISBNAPITester:
    def __init__(self, api_keys: Optional[Dict[str, str]] = None):
        self.http_client = HttpClient()
        self.api_keys = api_keys or {}

    def test_google_books(self, isbn: str) -> APITestResult:
        start_time = time.time()
        try:
            response = self.http_client.get(
                f"https://www.googleapis.com/books/v1/volumes",
                params={'q': f'isbn:{isbn}'},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            if 'items' in data and data['items']:
                book = data['items'][0]['volumeInfo']
                metadata = {
                    'title': book.get('title'),
                    'authors': book.get('authors', []),
                    'publisher': book.get('publisher'),
                    'publishedDate': book.get('publishedDate'),
                    'isbn': isbn
                }
                return APITestResult(
                    api_name="Google Books",
                    response_time=time.time() - start_time,
                    success=True,
                    metadata=metadata
                )
            
            # Se não encontrou resultados
            return APITestResult(
                api_name="Google Books",
                response_time=time.time() - start_time,
                success=False,
                metadata=None,
                error="No results found"
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
        start_time = time.time()
        try:
            response = self.http_client.get(
                f"https://openlibrary.org/api/books",
                params={
                    'bibkeys': f"ISBN:{isbn}",
                    'format': 'json',
                    'jscmd': 'data'
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            if f"ISBN:{isbn}" in data:
                book = data[f"ISBN:{isbn}"]
                metadata = {
                    'title': book.get('title'),
                    'authors': [a.get('name') for a in book.get('authors', [])],
                    'publisher': book.get('publishers', [{}])[0].get('name'),
                    'publishedDate': book.get('publish_date'),
                    'isbn': isbn
                }
                return APITestResult(
                    api_name="Open Library",
                    response_time=time.time() - start_time,
                    success=True,
                    metadata=metadata
                )

        except Exception as e:
            return APITestResult(
                api_name="Open Library",
                response_time=time.time() - start_time,
                success=False,
                metadata=None,
                error=str(e)
            )

    def test_isbndb(self, isbn: str) -> APITestResult:
        if 'isbndb' not in self.api_keys:
            return APITestResult(
                api_name="ISBNdb",
                response_time=0,
                success=False,
                metadata=None,
                error="API key not provided",
                requires_key=True
            )

        start_time = time.time()
        try:
            response = self.http_client.get(
                f"https://api2.isbndb.com/book/{isbn}",
                headers={'Authorization': self.api_keys['isbndb']},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            if 'book' in data:
                book = data['book']
                metadata = {
                    'title': book.get('title'),
                    'authors': book.get('authors', []),
                    'publisher': book.get('publisher'),
                    'publishedDate': book.get('date_published'),
                    'isbn': isbn
                }
                return APITestResult(
                    api_name="ISBNdb",
                    response_time=time.time() - start_time,
                    success=True,
                    metadata=metadata
                )

        except Exception as e:
            return APITestResult(
                api_name="ISBNdb",
                response_time=time.time() - start_time,
                success=False,
                metadata=None,
                error=str(e)
            )

    def test_all_apis(self, isbn: str) -> List[APITestResult]:
        apis = [
            self.test_google_books,
            self.test_open_library,
            self.test_isbndb,
            # ... adicione mais APIs aqui
        ]

        results = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_api = {
                executor.submit(api, isbn): api.__name__ 
                for api in apis
            }
            
            for future in as_completed(future_to_api):
                api_name = future_to_api[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append(APITestResult(
                        api_name=api_name,
                        response_time=0,
                        success=False,
                        metadata=None,
                        error=str(e)
                    ))

        return results

    def run_test(self, isbn: str) -> dict:
        results = self.test_all_apis(isbn)
        
        successful_results = [r for r in results if r and r.success]
        total_time = sum(r.response_time for r in results if r)
        
        summary = {
            'isbn': isbn,
            'total_apis_tested': len(results),
            'successful_apis': len(successful_results),
            'total_time': total_time,
            'results': []
        }
        
        for result in results:
            if result:  # Verifica se o resultado não é None
                summary['results'].append({
                    'api_name': result.api_name,
                    'success': result.success,
                    'response_time': result.response_time,
                    'metadata': result.metadata,
                    'error': result.error
                })
        
        return summary

    def generate_report(self, results: List[dict], output_dir: str = "reports") -> str:
        """Gera relatório HTML com os resultados."""
        Path(output_dir).mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = Path(output_dir) / f"report_{timestamp}.html"

        # Coleta estatísticas
        total_tests = len(results)
        successful_tests = sum(1 for r in results if r['successful_apis'] > 0)
        api_stats = {}

        for result in results:
            for api_result in result['results']:
                api_name = api_result['api_name']
                if api_name not in api_stats:
                    api_stats[api_name] = {'success': 0, 'total': 0, 'time': 0}
                api_stats[api_name]['total'] += 1
                if api_result['success']:
                    api_stats[api_name]['success'] += 1
                api_stats[api_name]['time'] += api_result['response_time']

        # Gera HTML
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>ISBN API Test Results</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; max-width: 1200px; }}
                .card {{ background: #fff; border-radius: 8px; padding: 20px; 
                        margin: 10px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .success {{ color: green; }}
                .failure {{ color: red; }}
                table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background: #f5f5f5; }}
                .metadata {{ background: #f8f9fa; padding: 10px; border-radius: 4px; }}
            </style>
        </head>
        <body>
            <h1>ISBN API Test Results</h1>
            <p>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>

            <div class="card">
                <h2>Summary</h2>
                <table>
                    <tr>
                        <th>Total Tests</th>
                        <td>{total_tests}</td>
                    </tr>
                    <tr>
                        <th>Successful Tests</th>
                        <td>{successful_tests} ({successful_tests/total_tests*100:.1f}%)</td>
                    </tr>
                </table>
            </div>

            <div class="card">
                <h2>API Performance</h2>
                <table>
                    <tr>
                        <th>API</th>
                        <th>Success Rate</th>
                        <th>Avg Response Time</th>
                    </tr>
        """

        for api_name, stats in api_stats.items():
            success_rate = stats['success'] / stats['total'] * 100
            avg_time = stats['time'] / stats['total']
            html_content += f"""
                    <tr>
                        <td>{api_name}</td>
                        <td>{success_rate:.1f}%</td>
                        <td>{avg_time:.2f}s</td>
                    </tr>
            """

        html_content += """
                </table>
            </div>

            <div class="card">
                <h2>Detailed Results</h2>
        """

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
                        </tr>
            """

            for api_result in result['results']:
                status_class = "success" if api_result['success'] else "failure"
                status_text = "✓" if api_result['success'] else "✗"
                metadata_html = ""
                if api_result['metadata']:
                    metadata_html = "<ul>"
                    for key, value in api_result['metadata'].items():
                        if isinstance(value, list):
                            value = ", ".join(value)
                        metadata_html += f"<li><strong>{key}:</strong> {value}</li>"
                    metadata_html += "</ul>"

                html_content += f"""
                        <tr>
                            <td>{api_result['api_name']}</td>
                            <td class="{status_class}">{status_text}</td>
                            <td>{api_result['response_time']:.2f}s</td>
                            <td>{metadata_html}</td>
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

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return str(report_file)

def main():
    """Função principal para demonstração do uso."""
    # Lista de ISBNs para testar
    test_isbns = [
        "9781449355739",  # Learning Python
        "9781617294136",  # Spring Boot in Action
        "9780134685991",  # Effective Java
    ]

    # Configuração de APIs (adicione suas chaves aqui)
    api_keys = {
        'isbndb': 'sua_chave_isbndb',
        # Adicione outras chaves conforme necessário
    }

    try:
        # Inicializa o testador
        tester = ISBNAPITester(api_keys)
        
        # Lista para armazenar resultados
        all_results = []
        
        print("Testando ISBNs...")
        for isbn in test_isbns:
            print(f"Testando ISBN: {isbn}")
            result = tester.run_test(isbn)
            all_results.append(result)
        
        # Gera relatório
        report_file = tester.generate_report(all_results)
        print(f"\nRelatório gerado: {report_file}")
        
    except Exception as e:
        print(f"Erro: {str(e)}")

if __name__ == "__main__":
    main()
