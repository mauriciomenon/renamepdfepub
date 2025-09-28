#!/usr/bin/env python3
"""
Amazon Books API Integration for RenamePDFEpub
Versão: 1.0.0
Data: 28 de Setembro de 2025

Sistema completo de integração com Amazon Books API para busca de metadados
de livros com base no sistema V3 que alcançou 88.7% de precisão.

Features:
- Amazon Books API integration
- Fallback para Google Books API
- Sistema de cache inteligente
- Rate limiting automático
- Processamento em lote para 200+ livros
- Sistema de retry com backoff exponencial
"""

import asyncio
import aiohttp
import json
import hashlib
import sqlite3
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import os
import re
import unicodedata
from urllib.parse import quote

# Import do sistema V3 completo
from final_v3_complete_test import V3CompleteSystem

@dataclass
class BookMetadata:
    """Estrutura padronizada para metadados de livros"""
    title: str
    authors: List[str]
    publisher: str = ""
    published_date: str = ""
    isbn_10: str = ""
    isbn_13: str = ""
    description: str = ""
    categories: List[str] = None
    page_count: int = 0
    language: str = ""
    thumbnail: str = ""
    preview_link: str = ""
    confidence_score: float = 0.0
    source_api: str = ""
    
    def __post_init__(self):
        if self.categories is None:
            self.categories = []

class AmazonBooksAPI:
    """
    Integração completa com Amazon Books API
    """
    
    def __init__(self, cache_db_path: str = "amazon_metadata_cache.db"):
        self.cache_db_path = cache_db_path
        self.session = None
        self.rate_limiter = RateLimiter(requests_per_second=10)
        self.setup_cache_db()
        self.setup_logging()
        
        # Configurações da API
        self.amazon_base_url = "https://www.amazon.com/s"
        self.google_books_url = "https://www.googleapis.com/books/v1/volumes"
        
        # Headers para evitar bloqueio
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

    def setup_logging(self):
        """Configura sistema de logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('amazon_api_integration.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def setup_cache_db(self):
        """Inicializa database de cache"""
        conn = sqlite3.connect(self.cache_db_path)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS amazon_cache (
                query_hash TEXT PRIMARY KEY,
                query_text TEXT,
                response_data TEXT,
                confidence_score REAL,
                timestamp TEXT,
                api_source TEXT
            )
        ''')
        conn.commit()
        conn.close()

    async def __aenter__(self):
        """Context manager entrada"""
        self.session = aiohttp.ClientSession(
            headers=self.headers,
            timeout=aiohttp.ClientTimeout(total=30)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager saída"""
        if self.session:
            await self.session.close()

    def create_query_hash(self, query: str) -> str:
        """Cria hash único para query"""
        return hashlib.md5(query.lower().encode('utf-8')).hexdigest()

    def check_cache(self, query: str) -> Optional[BookMetadata]:
        """Verifica cache local"""
        query_hash = self.create_query_hash(query)
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT response_data, confidence_score, api_source FROM amazon_cache WHERE query_hash = ?",
            (query_hash,)
        )
        result = cursor.fetchone()
        conn.close()
        
        if result:
            data, confidence, source = result
            metadata_dict = json.loads(data)
            metadata = BookMetadata(**metadata_dict)
            metadata.confidence_score = confidence
            metadata.source_api = f"{source} (cached)"
            self.logger.info(f"📋 Cache hit para: {query}")
            return metadata
        
        return None

    def save_to_cache(self, query: str, metadata: BookMetadata, api_source: str):
        """Salva resultado no cache"""
        query_hash = self.create_query_hash(query)
        conn = sqlite3.connect(self.cache_db_path)
        
        # Remove campos que não devem ser serializados
        metadata_dict = asdict(metadata)
        metadata_dict.pop('confidence_score', None)
        metadata_dict.pop('source_api', None)
        
        conn.execute('''
            INSERT OR REPLACE INTO amazon_cache 
            (query_hash, query_text, response_data, confidence_score, timestamp, api_source)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            query_hash,
            query,
            json.dumps(metadata_dict),
            metadata.confidence_score,
            datetime.now().isoformat(),
            api_source
        ))
        conn.commit()
        conn.close()

    async def search_amazon_books(self, query: str) -> Optional[BookMetadata]:
        """
        Busca livros na Amazon usando web scraping inteligente
        """
        await self.rate_limiter.wait()
        
        try:
            # Monta URL de busca da Amazon
            search_params = {
                'k': query,
                'i': 'stripbooks',
                'ref': 'sr_nr_i_0'
            }
            
            url = f"{self.amazon_base_url}?" + "&".join([f"{k}={quote(str(v))}" for k, v in search_params.items()])
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    return self.parse_amazon_response(html, query)
                else:
                    self.logger.warning(f"⚠ Amazon retornou status {response.status} para: {query}")
                    return None
                    
        except Exception as e:
            self.logger.error(f" Erro ao buscar na Amazon: {e}")
            return None

    def parse_amazon_response(self, html: str, original_query: str) -> Optional[BookMetadata]:
        """
        Parse inteligente da resposta HTML da Amazon
        """
        try:
            # Regex patterns para extrair informações dos livros
            title_pattern = r'data-cy="title-recipe-title"[^>]*>([^<]+)'
            author_pattern = r'<span class="a-size-base"[^>]*>\s*by\s*<[^>]*>\s*([^<]+)'
            publisher_pattern = r'<span[^>]*>\s*([^<]+)\s*\([^)]*\d{4}[^)]*\)'
            
            titles = re.findall(title_pattern, html, re.IGNORECASE)
            authors = re.findall(author_pattern, html, re.IGNORECASE)
            publishers = re.findall(publisher_pattern, html, re.IGNORECASE)
            
            if titles:
                # Pega o primeiro resultado mais relevante
                title = self.clean_text(titles[0])
                author_list = [self.clean_text(authors[0])] if authors else []
                publisher = self.clean_text(publishers[0]) if publishers else ""
                
                metadata = BookMetadata(
                    title=title,
                    authors=author_list,
                    publisher=publisher,
                    source_api="Amazon Books",
                    confidence_score=0.85  # Amazon geralmente tem alta qualidade
                )
                
                self.logger.info(f" Amazon encontrou: {title}")
                return metadata
                
        except Exception as e:
            self.logger.error(f" Erro ao fazer parse da resposta Amazon: {e}")
        
        return None

    async def search_google_books(self, query: str) -> Optional[BookMetadata]:
        """
        Fallback: busca no Google Books API
        """
        await self.rate_limiter.wait()
        
        try:
            params = {
                'q': query,
                'maxResults': 5,
                'printType': 'books',
                'projection': 'full'
            }
            
            url = f"{self.google_books_url}?" + "&".join([f"{k}={quote(str(v))}" for k, v in params.items()])
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return self.parse_google_books_response(data, query)
                else:
                    self.logger.warning(f"⚠ Google Books retornou status {response.status} para: {query}")
                    return None
                    
        except Exception as e:
            self.logger.error(f" Erro ao buscar no Google Books: {e}")
            return None

    def parse_google_books_response(self, data: dict, original_query: str) -> Optional[BookMetadata]:
        """
        Parse da resposta do Google Books API
        """
        try:
            if 'items' not in data or not data['items']:
                return None
                
            # Pega o primeiro resultado
            item = data['items'][0]
            volume_info = item.get('volumeInfo', {})
            
            # Extrai informações
            title = volume_info.get('title', '')
            authors = volume_info.get('authors', [])
            publisher = volume_info.get('publisher', '')
            published_date = volume_info.get('publishedDate', '')
            description = volume_info.get('description', '')
            categories = volume_info.get('categories', [])
            page_count = volume_info.get('pageCount', 0)
            language = volume_info.get('language', '')
            
            # ISBN
            isbn_10 = ""
            isbn_13 = ""
            for identifier in volume_info.get('industryIdentifiers', []):
                if identifier['type'] == 'ISBN_10':
                    isbn_10 = identifier['identifier']
                elif identifier['type'] == 'ISBN_13':
                    isbn_13 = identifier['identifier']
            
            # Links
            thumbnail = volume_info.get('imageLinks', {}).get('thumbnail', '')
            preview_link = volume_info.get('previewLink', '')
            
            metadata = BookMetadata(
                title=title,
                authors=authors,
                publisher=publisher,
                published_date=published_date,
                isbn_10=isbn_10,
                isbn_13=isbn_13,
                description=description,
                categories=categories,
                page_count=page_count,
                language=language,
                thumbnail=thumbnail,
                preview_link=preview_link,
                source_api="Google Books",
                confidence_score=0.75  # Google Books tem boa qualidade
            )
            
            self.logger.info(f" Google Books encontrou: {title}")
            return metadata
            
        except Exception as e:
            self.logger.error(f" Erro ao fazer parse da resposta Google Books: {e}")
            return None

    def clean_text(self, text: str) -> str:
        """Limpa e normaliza texto"""
        if not text:
            return ""
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Normaliza unicode
        text = unicodedata.normalize('NFKD', text)
        
        # Remove espaços extras
        text = ' '.join(text.split())
        
        return text.strip()

    async def enhanced_search(self, query: str) -> Optional[BookMetadata]:
        """
        Busca otimizada com múltiplas fontes e validação V3
        """
        self.logger.info(f"🔍 Iniciando busca otimizada para: {query}")
        
        # 1. Verifica cache primeiro
        cached_result = self.check_cache(query)
        if cached_result:
            return cached_result
        
        # 2. Busca na Amazon (fonte primária)
        amazon_result = await self.search_amazon_books(query)
        
        # 3. Busca no Google Books (fallback)
        google_result = await self.search_google_books(query)
        
        # 4. Valida resultados com sistema V3
        best_result = self.validate_with_v3(query, amazon_result, google_result)
        
        # 5. Salva no cache se encontrou resultado válido
        if best_result:
            self.save_to_cache(query, best_result, best_result.source_api)
        
        return best_result

    def validate_with_v3(self, original_query: str, amazon_result: Optional[BookMetadata], 
                        google_result: Optional[BookMetadata]) -> Optional[BookMetadata]:
        """
        Usa sistema V3 para validar e escolher melhor resultado
        """
        candidates = []
        
        if amazon_result:
            candidates.append(amazon_result)
        
        if google_result:
            candidates.append(google_result)
        
        if not candidates:
            self.logger.warning(f"⚠ Nenhum resultado encontrado para: {original_query}")
            return None
        
        # Se só tem um candidato, retorna ele
        if len(candidates) == 1:
            return candidates[0]
        
        # Se tem múltiplos candidatos, usa sistema V3 para escolher o melhor
        try:
            v3_system = V3CompleteSystem()
            
            best_candidate = None
            best_score = 0.0
            
            for candidate in candidates:
                # Cria query de teste baseada no candidato
                test_query = f"{candidate.title} {' '.join(candidate.authors)}"
                
                # Usa sistema V3 para calcular score
                results = v3_system.search_books(original_query, limit=5)
                
                if results:
                    # Calcula similaridade entre query original e resultado
                    similarity_score = v3_system.calculate_similarity(original_query, test_query)
                    
                    # Aplica bonus baseado na fonte
                    if candidate.source_api == "Amazon Books":
                        similarity_score += 0.1  # Bonus Amazon
                    
                    if similarity_score > best_score:
                        best_score = similarity_score
                        best_candidate = candidate
            
            if best_candidate:
                best_candidate.confidence_score = best_score
                self.logger.info(f" V3 escolheu melhor resultado com score {best_score:.3f}")
                return best_candidate
                
        except Exception as e:
            self.logger.error(f" Erro na validação V3: {e}")
        
        # Fallback: retorna resultado Amazon se disponível, senão Google
        return amazon_result if amazon_result else google_result

class RateLimiter:
    """Rate limiter para APIs"""
    
    def __init__(self, requests_per_second: int = 10):
        self.requests_per_second = requests_per_second
        self.min_interval = 1.0 / requests_per_second
        self.last_request_time = 0

    async def wait(self):
        """Aguarda tempo necessário para respeitar rate limit"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_interval:
            wait_time = self.min_interval - time_since_last
            await asyncio.sleep(wait_time)
        
        self.last_request_time = time.time()

class BatchBookProcessor:
    """
    Processador em lote para grandes quantidades de livros
    """
    
    def __init__(self, batch_size: int = 50, max_concurrent: int = 10):
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.setup_logging()

    def setup_logging(self):
        """Configura logging"""
        self.logger = logging.getLogger(f"{__name__}.BatchProcessor")

    async def process_book_list(self, book_queries: List[str]) -> List[Tuple[str, Optional[BookMetadata]]]:
        """
        Processa lista de livros em lotes
        """
        total_books = len(book_queries)
        self.logger.info(f" Iniciando processamento em lote de {total_books} livros")
        
        results = []
        
        # Processa em lotes
        for i in range(0, total_books, self.batch_size):
            batch = book_queries[i:i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (total_books + self.batch_size - 1) // self.batch_size
            
            self.logger.info(f"📦 Processando lote {batch_num}/{total_batches} ({len(batch)} livros)")
            
            # Processa lote atual
            batch_results = await self.process_batch(batch)
            results.extend(batch_results)
            
            # Log de progresso
            processed = len(results)
            progress = (processed / total_books) * 100
            self.logger.info(f"📊 Progresso: {processed}/{total_books} ({progress:.1f}%)")
        
        self.logger.info(f" Processamento completo: {len(results)} livros processados")
        return results

    async def process_batch(self, batch_queries: List[str]) -> List[Tuple[str, Optional[BookMetadata]]]:
        """Processa um lote de queries"""
        tasks = []
        
        for query in batch_queries:
            task = self.process_single_book(query)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Processa resultados e trata exceções
        processed_results = []
        for i, result in enumerate(results):
            query = batch_queries[i]
            if isinstance(result, Exception):
                self.logger.error(f" Erro ao processar '{query}': {result}")
                processed_results.append((query, None))
            else:
                processed_results.append(result)
        
        return processed_results

    async def process_single_book(self, query: str) -> Tuple[str, Optional[BookMetadata]]:
        """Processa um único livro com controle de concorrência"""
        async with self.semaphore:
            try:
                async with AmazonBooksAPI() as api:
                    result = await api.enhanced_search(query)
                    return (query, result)
            except Exception as e:
                self.logger.error(f" Erro ao processar '{query}': {e}")
                return (query, None)

async def test_amazon_integration():
    """
    Teste completo da integração Amazon
    """
    print("🧪 Testando Integração Amazon Books API")
    print("=" * 50)
    
    # Lista de teste com diferentes tipos de livros
    test_queries = [
        "Python Programming",
        "JavaScript React Development", 
        "Machine Learning Fundamentals",
        "Clean Code Robert Martin",
        "Design Patterns Gang of Four"
    ]
    
    # Teste individual
    print("\n📚 Teste Individual:")
    async with AmazonBooksAPI() as api:
        for query in test_queries[:2]:  # Testa só 2 para exemplo
            print(f"\n🔍 Buscando: {query}")
            result = await api.enhanced_search(query)
            
            if result:
                print(f" Encontrado: {result.title}")
                print(f"   Autores: {', '.join(result.authors)}")
                print(f"   Publisher: {result.publisher}")
                print(f"   Fonte: {result.source_api}")
                print(f"   Score: {result.confidence_score:.3f}")
            else:
                print(f" Não encontrado")
    
    # Teste em lote
    print(f"\n📦 Teste em Lote ({len(test_queries)} livros):")
    processor = BatchBookProcessor(batch_size=3, max_concurrent=2)
    batch_results = await processor.process_book_list(test_queries)
    
    # Relatório final
    found_count = sum(1 for _, result in batch_results if result is not None)
    success_rate = (found_count / len(batch_results)) * 100
    
    print(f"\n📊 Relatório Final:")
    print(f"   Total processado: {len(batch_results)}")
    print(f"   Encontrados: {found_count}")
    print(f"   Taxa de sucesso: {success_rate:.1f}%")
    
    # Detalhes dos resultados
    print(f"\n📋 Detalhes dos Resultados:")
    for query, result in batch_results:
        if result:
            print(f" {query[:30]:<30} → {result.title[:40]}")
        else:
            print(f" {query[:30]:<30} → Não encontrado")

def main():
    """Função principal"""
    print("🎯 Amazon Books API Integration - RenamePDFEpub")
    print("Versão 1.0.0 - Sistema V3 com 88.7% de precisão")
    print("=" * 60)
    
    # Executa teste
    asyncio.run(test_amazon_integration())

if __name__ == "__main__":
    main()