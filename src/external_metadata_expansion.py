#!/usr/bin/env python3
"""
Sistema de Expansão para Fontes Externas de Metadados
===================================================

Este módulo prepara a infraestrutura para integração futura com:
- Catálogos de editoras (O'Reilly, Packt, Manning, etc.)
- Amazon e grandes vendedores
- APIs de bibliotecas e bases de dados bibliográficas
- Sistemas de ISBN internacionais

Estrutura Modular:
- PublisherCatalogManager: Gerencia catálogos de editoras
- AmazonScraper: Interface para scraping da Amazon
- ISBNDatabaseConnector: Conexão com bases ISBN
- MetadataAggregator: Agregador de múltiplas fontes
"""

import os
import sys
import json
import time
import logging
import asyncio
import aiohttp
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from urllib.parse import urljoin, quote
import hashlib
from datetime import datetime, timedelta

# Adicionar src ao path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from src.renamepdfepub.logging_config import setup_logging

logger = setup_logging(__name__)

@dataclass
class ExternalMetadata:
    """Metadados obtidos de fonte externa"""
    source: str
    title: str
    authors: List[str]
    publisher: str
    isbn: Optional[str]
    publication_date: Optional[str]
    description: Optional[str]
    categories: List[str]
    confidence_score: float
    source_url: Optional[str]
    extracted_at: str

@dataclass
class PublisherConfig:
    """Configuração para uma editora específica"""
    name: str
    base_url: str
    catalog_endpoint: str
    search_endpoint: str
    api_key_required: bool
    rate_limit_per_second: int
    supported_formats: List[str]
    metadata_fields: Dict[str, str]

class PublisherCatalogManager:
    """Gerenciador de catálogos de editoras"""
    
    def __init__(self, cache_dir: str = None):
        self.cache_dir = Path(cache_dir) if cache_dir else project_root / "cache" / "publishers"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Configurações das editoras principais
        self.publishers = {
            'oreilly': PublisherConfig(
                name="O'Reilly Media",
                base_url="https://learning.oreilly.com",
                catalog_endpoint="/api/v2/search/",
                search_endpoint="/api/v2/search/?q={query}",
                api_key_required=True,
                rate_limit_per_second=2,
                supported_formats=['pdf', 'epub'],
                metadata_fields={
                    'title': 'title',
                    'authors': 'authors',
                    'publisher': 'publishers',
                    'isbn': 'isbn',
                    'description': 'description'
                }
            ),
            'packt': PublisherConfig(
                name="Packt Publishing",
                base_url="https://www.packtpub.com",
                catalog_endpoint="/catalogsearch/result/",
                search_endpoint="/catalogsearch/result/?q={query}",
                api_key_required=False,
                rate_limit_per_second=1,
                supported_formats=['pdf', 'epub'],
                metadata_fields={
                    'title': '.product-title',
                    'authors': '.author-name',
                    'publisher': 'Packt Publishing',
                    'description': '.product-description'
                }
            ),
            'manning': PublisherConfig(
                name="Manning Publications",
                base_url="https://www.manning.com",
                catalog_endpoint="/catalog/",
                search_endpoint="/catalog/?query={query}",
                api_key_required=False,
                rate_limit_per_second=1,
                supported_formats=['pdf', 'epub'],
                metadata_fields={
                    'title': '.book-title',
                    'authors': '.book-author',
                    'publisher': 'Manning Publications',
                    'description': '.book-description'
                }
            )
        }
        
        logger.info(f"Inicializado manager com {len(self.publishers)} editoras")
    
    async def search_publisher_catalog(self, publisher: str, query: str) -> List[ExternalMetadata]:
        """Buscar no catálogo de uma editora específica"""
        if publisher not in self.publishers:
            raise ValueError(f"Editora não suportada: {publisher}")
        
        config = self.publishers[publisher]
        logger.info(f"Buscando '{query}' no catálogo da {config.name}")
        
        # Verificar cache primeiro
        cache_key = self._get_cache_key(publisher, query)
        cached_result = self._load_from_cache(cache_key)
        if cached_result:
            logger.info(f"Resultado encontrado no cache para {publisher}")
            return cached_result
        
        try:
            # Executar busca específica por editora
            if publisher == 'oreilly':
                results = await self._search_oreilly(query, config)
            elif publisher == 'packt':
                results = await self._search_packt(query, config)
            elif publisher == 'manning':
                results = await self._search_manning(query, config)
            else:
                results = await self._search_generic_publisher(query, config)
            
            # Salvar no cache
            self._save_to_cache(cache_key, results)
            
            logger.info(f"Encontrados {len(results)} resultados para {publisher}")
            return results
            
        except Exception as e:
            logger.error(f"Erro buscando em {publisher}: {e}")
            return []
    
    async def search_all_publishers(self, query: str) -> Dict[str, List[ExternalMetadata]]:
        """Buscar em todas as editoras configuradas"""
        logger.info(f"Buscando '{query}' em todas as editoras")
        
        results = {}
        
        # Executar buscas em paralelo
        tasks = []
        for publisher in self.publishers.keys():
            task = self.search_publisher_catalog(publisher, query)
            tasks.append((publisher, task))
        
        # Aguardar resultados
        for publisher, task in tasks:
            try:
                publisher_results = await task
                results[publisher] = publisher_results
            except Exception as e:
                logger.error(f"Erro buscando em {publisher}: {e}")
                results[publisher] = []
        
        total_results = sum(len(r) for r in results.values())
        logger.info(f"Total de {total_results} resultados de {len(results)} editoras")
        
        return results
    
    async def _search_oreilly(self, query: str, config: PublisherConfig) -> List[ExternalMetadata]:
        """Buscar especificamente no O'Reilly"""
        # Implementação específica para O'Reilly API
        # Esta é uma implementação mockada - seria necessário API key real
        
        await asyncio.sleep(1)  # Simular delay da API
        
        # Mock data para demonstração
        mock_results = [
            ExternalMetadata(
                source="oreilly",
                title=f"Learning {query.title()}",
                authors=["John Doe", "Jane Smith"],
                publisher="O'Reilly Media",
                isbn="9781234567890",
                publication_date="2024-01-15",
                description=f"Comprehensive guide to {query}",
                categories=["Programming", "Technology"],
                confidence_score=0.85,
                source_url=f"{config.base_url}/library/view/learning-{query.lower()}",
                extracted_at=datetime.now().isoformat()
            )
        ]
        
        return mock_results
    
    async def _search_packt(self, query: str, config: PublisherConfig) -> List[ExternalMetadata]:
        """Buscar especificamente na Packt"""
        # Implementação específica para scraping da Packt
        
        await asyncio.sleep(1)  # Simular delay
        
        # Mock data
        mock_results = [
            ExternalMetadata(
                source="packt",
                title=f"Mastering {query.title()}",
                authors=["Technical Author"],
                publisher="Packt Publishing",
                isbn="9780987654321",
                publication_date="2024-02-01",
                description=f"Professional {query} development guide",
                categories=["Development", "Programming"],
                confidence_score=0.78,
                source_url=f"{config.base_url}/product/mastering-{query.lower()}",
                extracted_at=datetime.now().isoformat()
            )
        ]
        
        return mock_results
    
    async def _search_manning(self, query: str, config: PublisherConfig) -> List[ExternalMetadata]:
        """Buscar especificamente na Manning"""
        # Implementação específica para Manning
        
        await asyncio.sleep(1)  # Simular delay
        
        # Mock data
        mock_results = [
            ExternalMetadata(
                source="manning",
                title=f"{query.title()} in Action",
                authors=["Expert Developer"],
                publisher="Manning Publications",
                isbn="9781122334455",
                publication_date="2024-03-01",
                description=f"Practical {query} for developers",
                categories=["Software Development"],
                confidence_score=0.82,
                source_url=f"{config.base_url}/books/{query.lower()}-in-action",
                extracted_at=datetime.now().isoformat()
            )
        ]
        
        return mock_results
    
    async def _search_generic_publisher(self, query: str, config: PublisherConfig) -> List[ExternalMetadata]:
        """Busca genérica para editoras não implementadas especificamente"""
        logger.info(f"Executando busca genérica para {config.name}")
        
        # Implementação genérica usando requests/beautifulsoup
        await asyncio.sleep(1)
        
        return []  # Implementar conforme necessário
    
    def _get_cache_key(self, publisher: str, query: str) -> str:
        """Gerar chave de cache"""
        combined = f"{publisher}:{query}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    def _load_from_cache(self, cache_key: str) -> Optional[List[ExternalMetadata]]:
        """Carregar resultado do cache"""
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Verificar se não expirou (24 horas)
                extracted_at = datetime.fromisoformat(data.get('cached_at', ''))
                if datetime.now() - extracted_at < timedelta(hours=24):
                    results = []
                    for item in data['results']:
                        results.append(ExternalMetadata(**item))
                    return results
                    
            except Exception as e:
                logger.error(f"Erro carregando cache {cache_key}: {e}")
        
        return None
    
    def _save_to_cache(self, cache_key: str, results: List[ExternalMetadata]):
        """Salvar resultado no cache"""
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        try:
            cache_data = {
                'cached_at': datetime.now().isoformat(),
                'results': [asdict(result) for result in results]
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Erro salvando cache {cache_key}: {e}")

class AmazonScraper:
    """Scraper para Amazon e grandes vendedores"""
    
    def __init__(self, cache_dir: str = None):
        self.cache_dir = Path(cache_dir) if cache_dir else project_root / "cache" / "amazon"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Configurações de scraping
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9,pt;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        self.amazon_domains = {
            'us': 'amazon.com',
            'uk': 'amazon.co.uk',
            'de': 'amazon.de',
            'br': 'amazon.com.br'
        }
        
        logger.info("Amazon scraper inicializado")
    
    async def search_amazon(self, query: str, domain: str = 'us') -> List[ExternalMetadata]:
        """Buscar livros na Amazon"""
        if domain not in self.amazon_domains:
            domain = 'us'
            
        base_url = f"https://www.{self.amazon_domains[domain]}"
        search_url = f"{base_url}/s?k={quote(query)}&i=stripbooks"
        
        logger.info(f"Buscando '{query}' na Amazon {domain}")
        
        # Verificar cache
        cache_key = self._get_cache_key(f"amazon_{domain}", query)
        cached_result = self._load_from_cache(cache_key)
        if cached_result:
            return cached_result
        
        try:
            # Implementação mockada - em produção usaria requests/selenium
            await asyncio.sleep(2)  # Delay para evitar bloqueios
            
            # Mock results
            mock_results = [
                ExternalMetadata(
                    source=f"amazon_{domain}",
                    title=f"Professional {query.title()} Development",
                    authors=["Amazon Author"],
                    publisher="Tech Publisher",
                    isbn="9781234567890",
                    publication_date="2024-01-01",
                    description=f"Comprehensive {query} guide from Amazon",
                    categories=["Books", "Technology"],
                    confidence_score=0.75,
                    source_url=search_url,
                    extracted_at=datetime.now().isoformat()
                )
            ]
            
            # Salvar no cache
            self._save_to_cache(cache_key, mock_results)
            
            return mock_results
            
        except Exception as e:
            logger.error(f"Erro buscando na Amazon: {e}")
            return []
    
    async def search_all_amazon_domains(self, query: str) -> Dict[str, List[ExternalMetadata]]:
        """Buscar em todos os domínios da Amazon"""
        logger.info(f"Buscando '{query}' em todos os domínios Amazon")
        
        results = {}
        
        # Buscar em paralelo com delay entre requisições
        for domain in self.amazon_domains.keys():
            try:
                domain_results = await self.search_amazon(query, domain)
                results[domain] = domain_results
                
                # Delay entre domínios
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Erro buscando Amazon {domain}: {e}")
                results[domain] = []
        
        return results
    
    def _get_cache_key(self, source: str, query: str) -> str:
        """Gerar chave de cache"""
        combined = f"{source}:{query}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    def _load_from_cache(self, cache_key: str) -> Optional[List[ExternalMetadata]]:
        """Carregar do cache"""
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Cache válido por 12 horas (Amazon muda frequentemente)
                extracted_at = datetime.fromisoformat(data.get('cached_at', ''))
                if datetime.now() - extracted_at < timedelta(hours=12):
                    results = []
                    for item in data['results']:
                        results.append(ExternalMetadata(**item))
                    return results
                    
            except Exception as e:
                logger.error(f"Erro carregando cache Amazon {cache_key}: {e}")
        
        return None
    
    def _save_to_cache(self, cache_key: str, results: List[ExternalMetadata]):
        """Salvar no cache"""
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        try:
            cache_data = {
                'cached_at': datetime.now().isoformat(),
                'results': [asdict(result) for result in results]
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Erro salvando cache Amazon {cache_key}: {e}")

class ISBNDatabaseConnector:
    """Conector para bases de dados ISBN internacionais"""
    
    def __init__(self, cache_dir: str = None):
        self.cache_dir = Path(cache_dir) if cache_dir else project_root / "cache" / "isbn"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # APIs de ISBN disponíveis
        self.isbn_apis = {
            'openlibrary': {
                'base_url': 'https://openlibrary.org',
                'isbn_endpoint': '/isbn/{isbn}.json',
                'search_endpoint': '/search.json?q={query}'
            },
            'google_books': {
                'base_url': 'https://www.googleapis.com/books/v1',
                'isbn_endpoint': '/volumes?q=isbn:{isbn}',
                'search_endpoint': '/volumes?q={query}'
            },
            'worldcat': {
                'base_url': 'https://www.worldcat.org',
                'isbn_endpoint': '/isbn/{isbn}',
                'search_endpoint': '/search?q={query}'
            }
        }
        
        logger.info("ISBN database connector inicializado")
    
    async def lookup_isbn(self, isbn: str) -> List[ExternalMetadata]:
        """Buscar informações por ISBN"""
        logger.info(f"Buscando ISBN: {isbn}")
        
        # Limpar ISBN
        clean_isbn = isbn.replace('-', '').replace(' ', '')
        
        # Verificar cache
        cache_key = self._get_cache_key("isbn", clean_isbn)
        cached_result = self._load_from_cache(cache_key)
        if cached_result:
            return cached_result
        
        results = []
        
        # Buscar em múltiplas APIs
        for api_name, config in self.isbn_apis.items():
            try:
                api_results = await self._lookup_isbn_api(clean_isbn, api_name, config)
                results.extend(api_results)
                
                # Delay entre APIs
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Erro buscando ISBN em {api_name}: {e}")
        
        # Salvar no cache
        if results:
            self._save_to_cache(cache_key, results)
        
        logger.info(f"Encontrados {len(results)} resultados para ISBN {isbn}")
        return results
    
    async def search_by_title(self, title: str) -> List[ExternalMetadata]:
        """Buscar por título nas bases de dados"""
        logger.info(f"Buscando título: '{title}'")
        
        # Verificar cache
        cache_key = self._get_cache_key("title", title)
        cached_result = self._load_from_cache(cache_key)
        if cached_result:
            return cached_result
        
        results = []
        
        # Buscar em múltiplas APIs
        for api_name, config in self.isbn_apis.items():
            try:
                api_results = await self._search_title_api(title, api_name, config)
                results.extend(api_results)
                
                # Delay entre APIs
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Erro buscando título em {api_name}: {e}")
        
        # Salvar no cache
        if results:
            self._save_to_cache(cache_key, results)
        
        logger.info(f"Encontrados {len(results)} resultados para título '{title}'")
        return results
    
    async def _lookup_isbn_api(self, isbn: str, api_name: str, config: Dict) -> List[ExternalMetadata]:
        """Buscar ISBN em API específica"""
        # Implementação mockada - seria implementação real das APIs
        await asyncio.sleep(0.5)
        
        if api_name == 'openlibrary':
            return [
                ExternalMetadata(
                    source="openlibrary",
                    title=f"Book with ISBN {isbn}",
                    authors=["Open Library Author"],
                    publisher="Publisher Name",
                    isbn=isbn,
                    publication_date="2024-01-01",
                    description="Book from Open Library",
                    categories=["Literature"],
                    confidence_score=0.90,
                    source_url=f"{config['base_url']}/isbn/{isbn}",
                    extracted_at=datetime.now().isoformat()
                )
            ]
        
        return []
    
    async def _search_title_api(self, title: str, api_name: str, config: Dict) -> List[ExternalMetadata]:
        """Buscar título em API específica"""
        # Implementação mockada
        await asyncio.sleep(0.5)
        
        if api_name == 'google_books':
            return [
                ExternalMetadata(
                    source="google_books",
                    title=title,
                    authors=["Google Books Author"],
                    publisher="Google Publisher",
                    isbn="9781234567890",
                    publication_date="2024-01-01",
                    description=f"Book about {title} from Google Books",
                    categories=["Technology"],
                    confidence_score=0.85,
                    source_url=f"{config['base_url']}/search?q={quote(title)}",
                    extracted_at=datetime.now().isoformat()
                )
            ]
        
        return []
    
    def _get_cache_key(self, search_type: str, query: str) -> str:
        """Gerar chave de cache"""
        combined = f"{search_type}:{query}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    def _load_from_cache(self, cache_key: str) -> Optional[List[ExternalMetadata]]:
        """Carregar do cache"""
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Cache ISBN válido por 7 dias
                extracted_at = datetime.fromisoformat(data.get('cached_at', ''))
                if datetime.now() - extracted_at < timedelta(days=7):
                    results = []
                    for item in data['results']:
                        results.append(ExternalMetadata(**item))
                    return results
                    
            except Exception as e:
                logger.error(f"Erro carregando cache ISBN {cache_key}: {e}")
        
        return None
    
    def _save_to_cache(self, cache_key: str, results: List[ExternalMetadata]):
        """Salvar no cache"""
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        try:
            cache_data = {
                'cached_at': datetime.now().isoformat(),
                'results': [asdict(result) for result in results]
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"Erro salvando cache ISBN {cache_key}: {e}")

class MetadataAggregator:
    """Agregador de metadados de múltiplas fontes"""
    
    def __init__(self, cache_dir: str = None):
        self.cache_dir = Path(cache_dir) if cache_dir else project_root / "cache" / "aggregated"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Inicializar componentes
        self.publisher_manager = PublisherCatalogManager()
        self.amazon_scraper = AmazonScraper()
        self.isbn_connector = ISBNDatabaseConnector()
        
        # Pesos para scoring de confiança
        self.source_weights = {
            'isbn_database': 0.9,
            'publisher_official': 0.85,
            'amazon': 0.7,
            'generic_scraper': 0.6
        }
        
        logger.info("Metadata aggregator inicializado")
    
    async def comprehensive_search(self, query: str, isbn: Optional[str] = None) -> List[ExternalMetadata]:
        """Busca abrangente em todas as fontes"""
        logger.info(f"Iniciando busca abrangente para: '{query}'" + (f" (ISBN: {isbn})" if isbn else ""))
        
        all_results = []
        
        # 1. Busca por ISBN se disponível
        if isbn:
            logger.info("Buscando por ISBN...")
            try:
                isbn_results = await self.isbn_connector.lookup_isbn(isbn)
                all_results.extend(isbn_results)
            except Exception as e:
                logger.error(f"Erro na busca por ISBN: {e}")
        
        # 2. Busca em catálogos de editoras
        logger.info("Buscando em catálogos de editoras...")
        try:
            publisher_results = await self.publisher_manager.search_all_publishers(query)
            for publisher, results in publisher_results.items():
                all_results.extend(results)
        except Exception as e:
            logger.error(f"Erro na busca de editoras: {e}")
        
        # 3. Busca na Amazon
        logger.info("Buscando na Amazon...")
        try:
            amazon_results = await self.amazon_scraper.search_all_amazon_domains(query)
            for domain, results in amazon_results.items():
                all_results.extend(results)
        except Exception as e:
            logger.error(f"Erro na busca Amazon: {e}")
        
        # 4. Busca por título em bases ISBN
        logger.info("Buscando título em bases ISBN...")
        try:
            title_results = await self.isbn_connector.search_by_title(query)
            all_results.extend(title_results)
        except Exception as e:
            logger.error(f"Erro na busca por título: {e}")
        
        # 5. Deduplicar e rankear resultados
        deduplicated_results = self._deduplicate_results(all_results)
        ranked_results = self._rank_results(deduplicated_results, query)
        
        logger.info(f"Busca concluída: {len(all_results)} resultados brutos, {len(ranked_results)} após deduplicação")
        
        return ranked_results
    
    def _deduplicate_results(self, results: List[ExternalMetadata]) -> List[ExternalMetadata]:
        """Remover resultados duplicados"""
        seen_titles = set()
        deduplicated = []
        
        for result in results:
            # Criar chave única baseada em título e editora
            key = f"{result.title.lower()}:{result.publisher.lower()}"
            
            if key not in seen_titles:
                seen_titles.add(key)
                deduplicated.append(result)
        
        logger.info(f"Deduplicação: {len(results)} -> {len(deduplicated)} resultados")
        return deduplicated
    
    def _rank_results(self, results: List[ExternalMetadata], query: str) -> List[ExternalMetadata]:
        """Rankear resultados por relevância e confiança"""
        def calculate_relevance_score(result: ExternalMetadata) -> float:
            # Score baseado em confiança da fonte
            source_score = self._get_source_weight(result.source) * result.confidence_score
            
            # Score baseado em similaridade do título
            title_similarity = self._calculate_title_similarity(query, result.title)
            
            # Score combinado
            combined_score = (source_score * 0.6) + (title_similarity * 0.4)
            
            return combined_score
        
        # Calcular scores e ordenar
        scored_results = []
        for result in results:
            score = calculate_relevance_score(result)
            scored_results.append((score, result))
        
        # Ordenar por score decrescente
        scored_results.sort(key=lambda x: x[0], reverse=True)
        
        # Retornar apenas os resultados ordenados
        ranked_results = [result for score, result in scored_results]
        
        logger.info(f"Resultados rankeados. Melhor score: {scored_results[0][0]:.3f}" if scored_results else "Nenhum resultado para rankear")
        
        return ranked_results
    
    def _get_source_weight(self, source: str) -> float:
        """Obter peso da fonte"""
        if 'isbn' in source.lower() or 'openlibrary' in source.lower() or 'google_books' in source.lower():
            return self.source_weights['isbn_database']
        elif source in ['oreilly', 'packt', 'manning']:
            return self.source_weights['publisher_official']
        elif 'amazon' in source.lower():
            return self.source_weights['amazon']
        else:
            return self.source_weights['generic_scraper']
    
    def _calculate_title_similarity(self, query: str, title: str) -> float:
        """Calcular similaridade entre query e título"""
        from difflib import SequenceMatcher
        
        query_lower = query.lower()
        title_lower = title.lower()
        
        # Similaridade direta
        direct_similarity = SequenceMatcher(None, query_lower, title_lower).ratio()
        
        # Bonus se query está contido no título
        containment_bonus = 0.2 if query_lower in title_lower else 0
        
        return min(1.0, direct_similarity + containment_bonus)

# Função principal para demonstração
async def main():
    """Função principal para demonstração"""
    logger.info("=== DEMONSTRAÇÃO DO SISTEMA DE EXPANSÃO ===")
    
    # Inicializar agregador
    aggregator = MetadataAggregator()
    
    # Teste com um livro da coleção
    test_queries = [
        ("Python Workout", None),
        ("JavaScript Ninja", None),
        ("Machine Learning", "9781234567890"),
        ("Docker", None)
    ]
    
    for query, isbn in test_queries:
        logger.info(f"\n{'='*50}")
        logger.info(f"TESTANDO: {query}")
        logger.info(f"{'='*50}")
        
        try:
            results = await aggregator.comprehensive_search(query, isbn)
            
            logger.info(f"Encontrados {len(results)} resultados:")
            
            for i, result in enumerate(results[:3], 1):  # Mostrar top 3
                logger.info(f"\n{i}. {result.title}")
                logger.info(f"   Autor(es): {', '.join(result.authors)}")
                logger.info(f"   Editora: {result.publisher}")
                logger.info(f"   Fonte: {result.source}")
                logger.info(f"   Confiança: {result.confidence_score:.2f}")
                
        except Exception as e:
            logger.error(f"Erro testando '{query}': {e}")
    
    logger.info("\n=== DEMONSTRAÇÃO CONCLUÍDA ===")

if __name__ == "__main__":
    asyncio.run(main())