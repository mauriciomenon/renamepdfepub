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
from xml.etree.ElementTree import ParseError

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('isbn_api_tester.log')
    ]
)

# Configuração das APIs e seus requisitos
API_REQUIREMENTS = {
    'google_books': {
        'name': 'Google Books',
        'requires_key': False,
        'free_tier': True,
        'rate_limit': '1000/day',
        'notes': 'Totalmente gratuita, sem necessidade de registro'
    },
    'open_library': {
        'name': 'Open Library',
        'requires_key': False,
        'free_tier': True,
        'rate_limit': 'Sem limite explícito',
        'notes': 'Totalmente gratuita, sem necessidade de registro'
    },
    'isbndb': {
        'name': 'ISBNdb',
        'requires_key': True,
        'free_tier': True,
        'rate_limit': '1000/mês',
        'notes': 'Requer registro. Plano gratuito limitado'
    },
    'springer': {
        'name': 'Springer Nature',
        'requires_key': True,
        'free_tier': True,
        'rate_limit': '5000/mês',
        'notes': 'Requer registro para chave de API. Boa para livros técnicos'
    },
    'crossref': {
        'name': 'CrossRef',
        'requires_key': False,
        'free_tier': True,
        'rate_limit': '50/seg',
        'notes': 'Gratuita. Recomendado registrar email para maior quota'
    },
    'worldcat': {
        'name': 'WorldCat',
        'requires_key': False,
        'free_tier': True,
        'rate_limit': '100/min',
        'notes': 'API básica gratuita, versão completa requer registro'
    }
}

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

class ReportGenerator:
    """Classe para gerar relatórios HTML e JSON dos resultados"""
    def __init__(self, output_dir: str = "reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def generate_html_report(self, isbn: str, results: List[APITestResult], comparison: Dict) -> str:
        """Gera relatório HTML dos resultados"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.output_dir / f"isbn_report_{isbn}_{timestamp}.html"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Relatório de Teste de APIs ISBN - {isbn}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .success {{ color: green; }}
                .failure {{ color: red; }}
                .warning {{ color: orange; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .metadata-section {{ background-color: #f9f9f9; padding: 15px; margin: 10px 0; }}
                .api-requirements {{ background-color: #fff3e0; padding: 15px; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <h1>Relatório de Teste de APIs ISBN</h1>
            <h2>ISBN: {isbn}</h2>
            <p>Data do teste: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        """
        
        # Adiciona seção de metadados consolidados
        if comparison['status'] == 'success':
            html_content += """
            <div class="metadata-section">
                <h3>Metadados Consolidados</h3>
                <table>
                    <tr><th>Campo</th><th>Valor</th><th>Confiança</th></tr>
            """
            
            for field, value in comparison['most_common_metadata'].items():
                if value:
                    confidence = comparison['confidence_scores'][field] * 100
                    confidence_class = 'success' if confidence > 70 else 'warning'
                    value_str = ", ".join(value) if isinstance(value, list) else value
                    html_content += f"""
                    <tr>
                        <td>{field}</td>
                        <td>{value_str}</td>
                        <td class="{confidence_class}">{confidence:.1f}%</td>
                    </tr>
                    """
            
            html_content += "</table></div>"
        
        # Adiciona resultados por API
        html_content += """
            <h3>Resultados por API</h3>
            <table>
                <tr>
                    <th>API</th>
                    <th>Status</th>
                    <th>Tempo de Resposta</th>
                    <th>Requer Chave</th>
                    <th>Detalhes</th>
                </tr>
        """
        
        for result in results:
            status_class = "success" if result.success else "failure"
            status_text = "✓ Sucesso" if result.success else "✗ Falha"
            response_time = f"{result.response_time:.2f}s" if result.response_time > 0 else "N/A"
            
            html_content += f"""
                <tr>
                    <td>{result.api_name}</td>
                    <td class="{status_class}">{status_text}</td>
                    <td>{response_time}</td>
                    <td>{"Sim" if result.requires_key else "Não"}</td>
                    <td>{result.error if result.error else "OK"}</td>
                </tr>
            """
        
        html_content += "</table></body></html>"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return str(report_file)

    def generate_json_report(self, isbn: str, results: List[APITestResult], comparison: Dict) -> str:
        """Gera relatório JSON dos resultados"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.output_dir / f"isbn_report_{isbn}_{timestamp}.json"
        
        report_data = {
            'isbn': isbn,
            'timestamp': datetime.now().isoformat(),
            'summary': comparison,
            'results': [
                {
                    'api_name': r.api_name,
                    'success': r.success,
                    'response_time': round(r.response_time, 3) if r.response_time > 0 else None,
                    'metadata': r.metadata,
                    'error': r.error,
                    'requires_key': r.requires_key,
                    'http_status': r.http_status
                }
                for r in results
            ],
            'api_requirements': API_REQUIREMENTS
        }
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        return str(report_file)

class ISBNAPITester:
    """Classe principal para testar APIs de ISBN"""
    def __init__(self, api_keys: Optional[Dict[str, str]] = None):
        self.session = self._create_session()
        self.api_keys = api_keys or {}
        self.report_generator = ReportGenerator()

    def _create_session(self) -> requests.Session:
        """Cria e configura uma sessão HTTP com retry"""
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Headers padrão
        session.headers.update({
            'User-Agent': 'ISBN-API-Tester/1.0',
            'Accept': 'application/json',
        })
        
        return session

    def test_all_apis(self, isbn: str) -> List[APITestResult]:
        """Testa todas as APIs disponíveis para um ISBN"""
        apis_to_test = [
            (self.test_google_books, "Google Books", False),
            (self.test_open_library, "OpenLibrary", False),
            (self.test_crossref, "CrossRef", False),
            (self.test_worldcat, "WorldCat", False),
            (self.test_isbndb, "ISBNdb", True),
            (self.test_springer, "Springer", True),
        ]

        results = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_api = {}
            for api_func, api_name, requires_key in apis_to_test:
                if requires_key and not self._has_api_key(api_name.lower()):
                    results.append(APITestResult(
                        api_name=api_name,
                        response_time=-1,
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
                    result.requires_key = requires_key
                    results.append(result)
                except Exception as e:
                    results.append(APITestResult(
                        api_name=api_name,
                        response_time=-1,
                        success=False,
                        metadata=None,
                        error=str(e),
                        requires_key=requires_key
                    ))

        return sorted(results, key=lambda x: x.response_time if x.response_time > 0 else float('inf'))

    def test_google_books(self, isbn: str) -> APITestResult:
        """Testa a API do Google Books"""
        start_time = time.time()
        try:
            url = f"https://www.googleapis.com/books/v1/volumes"
            params = {'q': f'isbn:{isbn}'}
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'items' in data:
                book_info = data['items'][0]['volumeInfo']
                metadata = {
                    'title': book_info.get('title'),
                    'authors': book_info.get('authors', []),
                    'publisher': book_info.get('publisher'),
                    'publishedDate': book_info.get('publishedDate'),
                    'isbn': isbn
                }
                return APITestResult(
                    api_name="Google Books",
                    response_time=time.time() - start_time,
                    success=True,
                    metadata=metadata,
                    http_status=response.status_code
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
        """Testa a API do Open Library"""
        start_time = time.time()
        try:
            url = f"https://openlibrary.org/api/books"
            params = {
                'bibkeys': f"ISBN:{isbn}",
                'format': 'json',
                'jscmd': 'data'
            }
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if f"ISBN:{isbn}" in data:
                book_info = data[f"ISBN:{isbn}"]
                metadata = {
                    'title': book_info.get('title'),
                    'authors': [author['name'] for author in book_info.get('authors', [])],
                    'publisher': book_info.get('publishers', [{}])[0].get('name'),
                    'publishedDate': book_info.get('publish_date'),
                    'isbn': isbn
                }
                return APITestResult(
                    api_name="OpenLibrary",
                    response_time=time.time() - start_time,
                    success=True,
                    metadata=metadata,
                    http_status=response.status_code
                )
            return APITestResult(
                api_name="OpenLibrary",
                response_time=time.time() - start_time,
                success=False,
                metadata=None,
                error="No results found",
                http_status=response.status_code
            )
        except Exception as e:
            return APITestResult(
                api_name="OpenLibrary",
                response_time=time.time() - start_time,
                success=False,
                metadata=None,
                error=str(e)
            )


                
                
                
    def test_crossref(self, isbn: str) -> APITestResult:
            """Testa a API do CrossRef"""
            start_time = time.time()
            try:
                url = "https://api.crossref.org/works"
                params = {
                    'query.bibliographic': isbn,
                    'filter': 'type:book',
                    'select': 'title,author,published-print,publisher'
                }
                response = self.session.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                if data['message']['items']:
                    item = data['message']['items'][0]
                    metadata = {
                        'title': item.get('title', [''])[0],
                        'authors': [f"{a.get('given', '')} {a.get('family', '')}" 
                                for a in item.get('author', [])],
                        'publisher': item.get('publisher'),
                        'publishedDate': str(item.get('published-print', {})
                                        .get('date-parts', [[0]])[0][0]),
                        'isbn': isbn
                    }
                    return APITestResult(
                        api_name="CrossRef",
                        response_time=time.time() - start_time,
                        success=True,
                        metadata=metadata,
                        http_status=response.status_code
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

    def test_worldcat(self, isbn: str) -> APITestResult:
        """Testa a API do WorldCat"""
        start_time = time.time()
        try:
            url = "http://classify.oclc.org/classify2/Classify"
            params = {'isbn': isbn, 'summary': 'true'}
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            try:
                root = ET.fromstring(response.content)
                work = root.find('.//work')
                
                if work is not None:
                    metadata = {
                        'title': work.get('title', ''),
                        'authors': [work.get('author', '')],
                        'publisher': '',  # WorldCat API básica não fornece editora
                        'publishedDate': work.get('date', ''),
                        'isbn': isbn
                    }
                    return APITestResult(
                        api_name="WorldCat",
                        response_time=time.time() - start_time,
                        success=True,
                        metadata=metadata,
                        http_status=response.status_code
                    )
            except ParseError as e:
                return APITestResult(
                    api_name="WorldCat",
                    response_time=time.time() - start_time,
                    success=False,
                    metadata=None,
                    error=f"XML Parse Error: {str(e)}",
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

    def test_isbndb(self, isbn: str) -> APITestResult:
        """Testa a API do ISBNdb"""
        if not self._has_api_key('isbndb'):
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
            url = f"https://api2.isbndb.com/book/{isbn}"
            headers = {'Authorization': self.api_keys['isbndb']}
            response = self.session.get(url, headers=headers, timeout=10)
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
                    metadata=metadata,
                    http_status=response.status_code
                )
            return APITestResult(
                api_name="ISBNdb",
                response_time=time.time() - start_time,
                success=False,
                metadata=None,
                error="No results found",
                http_status=response.status_code
            )
        except Exception as e:
            return APITestResult(
                api_name="ISBNdb",
                response_time=time.time() - start_time,
                success=False,
                metadata=None,
                error=str(e)
            )

    def test_springer(self, isbn: str) -> APITestResult:
        """Testa a API da Springer"""
        if not self._has_api_key('springer'):
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
            url = f"https://api.springernature.com/metadata/book/isbn/{isbn}"
            headers = {'X-ApiKey': self.api_keys['springer']}
            response = self.session.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            if 'records' in data and data['records']:
                record = data['records'][0]
                metadata = {
                    'title': record.get('title'),
                    'authors': record.get('creators', []),
                    'publisher': 'Springer',
                    'publishedDate': record.get('publicationDate'),
                    'isbn': isbn
                }
                return APITestResult(
                    api_name="Springer",
                    response_time=time.time() - start_time,
                    success=True,
                    metadata=metadata,
                    http_status=response.status_code
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

    def _has_api_key(self, api_name: str) -> bool:
        """Verifica se possui chave de API para o serviço especificado"""
        return api_name.lower() in self.api_keys

    def compare_results(self, results: List[APITestResult]) -> Dict:
        """Compara resultados de diferentes APIs e fornece um resumo"""
        successful_results = [r for r in results if r.success]
        if not successful_results:
            return {
                'status': 'No successful results',
                'apis_tested': len(results),
                'successful_apis': 0,
                'failures': {r.api_name: r.error for r in results if not r.success}
            }

        titles = []
        authors_sets = []
        publishers = []
        dates = []

        for result in successful_results:
            if result.metadata.get('title'):
                titles.append(result.metadata['title'])
            if result.metadata.get('authors'):
                authors_sets.append(set(result.metadata['authors']))
            if result.metadata.get('publisher'):
                publishers.append(result.metadata['publisher'])
            if result.metadata.get('publishedDate'):
                dates.append(result.metadata['publishedDate'])

        most_common = {
            'title': max(set(titles), key=titles.count) if titles else None,
            'authors': list(max(authors_sets, key=len)) if authors_sets else None,
            'publisher': max(set(publishers), key=publishers.count) if publishers else None,
            'publishedDate': max(set(dates), key=dates.count) if dates else None,
        }

        confidence_scores = {
            'title': len([t for t in titles if t == most_common['title']]) / len(titles) if titles else 0,
            'authors': len([a for a in authors_sets if a == set(most_common['authors'])]) / len(authors_sets) if authors_sets else 0,
            'publisher': len([p for p in publishers if p == most_common['publisher']]) / len(publishers) if publishers else 0,
            'publishedDate': len([d for d in dates if d == most_common['publishedDate']]) / len(dates) if dates else 0,
        }

        return {
            'status': 'success',
            'apis_tested': len(results),
            'successful_apis': len(successful_results),
            'fastest_api': min(results, key=lambda x: x.response_time if x.response_time > 0 else float('inf')).api_name,
            'most_common_metadata': most_common,
            'confidence_scores': confidence_scores,
            'response_times': {r.api_name: round(r.response_time, 2) for r in results if r.response_time > 0},
            'failures': {r.api_name: r.error for r in results if not r.success}
        }

    def run_tests(self, isbn: str) -> Tuple[str, str]:
        """Executa todos os testes e gera relatórios"""
        logging.info(f"Iniciando testes para ISBN: {isbn}")
        
        results = self.test_all_apis(isbn)
        logging.info(f"Total de APIs testadas: {len(results)}")
        
        comparison = self.compare_results(results)
        logging.info(f"APIs bem-sucedidas: {comparison['successful_apis']}")
        
        try:
            html_report = self.report_generator.generate_html_report(isbn, results, comparison)
            json_report = self.report_generator.generate_json_report(isbn, results, comparison)
            
            logging.info("Relatórios gerados com sucesso:")
            logging.info(f"HTML: {html_report}")
            logging.info(f"JSON: {json_report}")
            
            return html_report, json_report
        except Exception as e:
            logging.error(f"Erro ao gerar relatórios: {str(e)}")
            raise

    def cleanup(self):
        """Limpa recursos e fecha conexões"""
        if hasattr(self, 'session'):
            self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

def main():
    """Função principal do programa"""
    # Lista de ISBNs para testar
    test_isbns = [
        "9781449355739",  # Learning Python, 5th Edition
        "9781617294136",  # Spring Boot in Action
        "9780134685991",  # Effective Java 3rd Edition
    ]

    # Configuração de chaves de API (substitua com suas chaves)
    api_keys = {
        'isbndb': 'sua_chave_isbndb',
        'springer': 'sua_chave_springer'
    }

    try:
        with ISBNAPITester(api_keys) as tester:
            for isbn in test_isbns:
                print(f"\nTestando ISBN: {isbn}")
                try:
                    html_report, json_report = tester.run_tests(isbn)
                    print(f"Relatórios gerados:")
                    print(f"HTML: {html_report}")
                    print(f"JSON: {json_report}")
                except Exception as e:
                    print(f"Erro ao processar ISBN {isbn}: {str(e)}")
                print("-" * 80)

    except Exception as e:
        print(f"Erro durante a execução: {str(e)}")
        raise

if __name__ == "__main__":
    main()