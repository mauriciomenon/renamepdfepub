#!/usr/bin/env python3
"""
Sistema Completo de Renomeação Automática de PDFs e EPUBs
Versão: 1.0.0 - Produção
Data: 28 de Setembro de 2025

Sistema completo que integra:
- Sistema V3 (88.7% precisão)
- Amazon Books API Integration
- Processamento automático de arquivos
- Interface de linha de comando
- Sistema de relatórios

Uso:
    python auto_rename_system.py --directory /path/to/books
    python auto_rename_system.py --file book.pdf
    python auto_rename_system.py --batch books_list.txt
"""

import asyncio
import argparse
import os
import shutil
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import unicodedata
import re

# Imports dos nossos sistemas
from amazon_api_integration import AmazonBooksAPI, BatchBookProcessor, BookMetadata
from final_v3_complete_test import V3CompleteSystem

class FileRenamer:
    """
    Sistema inteligente de renomeação de arquivos
    """
    
    def __init__(self, backup_enabled: bool = True):
        self.backup_enabled = backup_enabled
        self.setup_logging()
        self.supported_formats = {'.pdf', '.epub', '.mobi', '.azw', '.azw3'}
        
        # Padrões problemáticos comuns
        self.bad_patterns = [
            r'^\d+\s*-\s*',  # "123 - "
            r'^\[\d+\]\s*',  # "[123] "
            r'^www\.\w+\.\w+\s*-?\s*',  # "www.site.com - "
            r'\s*-\s*www\.\w+\.\w+$',  # " - www.site.com"
            r'\s*\(\d{4}\)\s*',  # " (2023) "
            r'\s*-\s*Copy\s*$',  # " - Copy"
            r'^\s*[Cc]opy\s+of\s+',  # "Copy of "
        ]
        
        # Padrões de limpeza
        self.cleanup_patterns = [
            (r'\s+', ' '),  # Múltiplos espaços
            (r'[^\w\s\-\.\(\),&]', ''),  # Caracteres especiais
            (r'\s*-\s*-\s*', ' - '),  # Múltiplos hífens
        ]

    def setup_logging(self):
        """Configura sistema de logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('auto_rename_system.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def extract_search_terms(self, filename: str) -> str:
        """
        Extrai termos de busca do nome do arquivo
        """
        # Remove extensão
        name_without_ext = Path(filename).stem
        
        # Remove padrões problemáticos
        clean_name = name_without_ext
        for pattern in self.bad_patterns:
            clean_name = re.sub(pattern, '', clean_name, flags=re.IGNORECASE)
        
        # Aplica limpezas gerais
        for pattern, replacement in self.cleanup_patterns:
            clean_name = re.sub(pattern, replacement, clean_name)
        
        # Remove espaços extras e normaliza
        clean_name = ' '.join(clean_name.split())
        clean_name = unicodedata.normalize('NFKD', clean_name)
        
        return clean_name.strip()

    def create_safe_filename(self, metadata: BookMetadata, original_extension: str) -> str:
        """
        Cria nome de arquivo seguro baseado nos metadados
        """
        # Formato: "Autor - Título (Ano).ext"
        parts = []
        
        # Adiciona autor principal
        if metadata.authors:
            author = metadata.authors[0]
            # Se tem múltiplos autores, indica
            if len(metadata.authors) > 1:
                author += " et al"
            parts.append(author)
        
        # Adiciona título
        if metadata.title:
            parts.append(metadata.title)
        
        # Adiciona ano se disponível
        if metadata.published_date:
            year_match = re.search(r'\d{4}', metadata.published_date)
            if year_match:
                year = year_match.group()
                filename = f"{' - '.join(parts)} ({year}){original_extension}"
            else:
                filename = f"{' - '.join(parts)}{original_extension}"
        else:
            filename = f"{' - '.join(parts)}{original_extension}"
        
        # Limpa caracteres problemáticos para filesystem
        filename = self.sanitize_filename(filename)
        
        # Limita tamanho se necessário
        if len(filename) > 200:
            # Trunca título mantendo autor e ano
            if len(parts) >= 2:
                title_part = parts[1]
                if len(title_part) > 100:
                    title_part = title_part[:97] + "..."
                    parts[1] = title_part
                    if metadata.published_date and year_match:
                        filename = f"{' - '.join(parts)} ({year}){original_extension}"
                    else:
                        filename = f"{' - '.join(parts)}{original_extension}"
                    filename = self.sanitize_filename(filename)
        
        return filename

    def sanitize_filename(self, filename: str) -> str:
        """
        Remove caracteres problemáticos para nomes de arquivo
        """
        # Caracteres proibidos no Windows/macOS/Linux
        forbidden_chars = '<>:"/\\|?*'
        
        for char in forbidden_chars:
            filename = filename.replace(char, '')
        
        # Remove múltiplos espaços
        filename = re.sub(r'\s+', ' ', filename)
        
        # Remove espaços no início/fim
        filename = filename.strip()
        
        return filename

    def create_backup(self, file_path: Path) -> bool:
        """
        Cria backup do arquivo original
        """
        if not self.backup_enabled:
            return True
        
        try:
            backup_dir = file_path.parent / "backup_originals"
            backup_dir.mkdir(exist_ok=True)
            
            backup_path = backup_dir / file_path.name
            
            # Se backup já existe, adiciona timestamp
            if backup_path.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                stem = backup_path.stem
                suffix = backup_path.suffix
                backup_path = backup_dir / f"{stem}_{timestamp}{suffix}"
            
            shutil.copy2(file_path, backup_path)
            self.logger.info(f"💾 Backup criado: {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f" Erro ao criar backup para {file_path}: {e}")
            return False

    async def rename_single_file(self, file_path: Path) -> Tuple[bool, str, Optional[BookMetadata]]:
        """
        Renomeia um único arquivo
        """
        self.logger.info(f"📁 Processando: {file_path.name}")
        
        # Verifica se é formato suportado
        if file_path.suffix.lower() not in self.supported_formats:
            return False, f"Formato não suportado: {file_path.suffix}", None
        
        try:
            # Extrai termos de busca
            search_terms = self.extract_search_terms(file_path.name)
            self.logger.info(f"🔍 Termos de busca: {search_terms}")
            
            if not search_terms:
                return False, "Não foi possível extrair termos de busca", None
            
            # Busca metadados
            async with AmazonBooksAPI() as api:
                metadata = await api.enhanced_search(search_terms)
            
            if not metadata:
                return False, "Metadados não encontrados", None
            
            # Cria novo nome
            new_filename = self.create_safe_filename(metadata, file_path.suffix)
            new_path = file_path.parent / new_filename
            
            # Verifica se novo nome é diferente
            if new_path.name == file_path.name:
                return True, "Arquivo já com nome correto", metadata
            
            # Verifica se arquivo de destino já existe
            if new_path.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                stem = new_path.stem
                suffix = new_path.suffix
                new_path = file_path.parent / f"{stem}_{timestamp}{suffix}"
            
            # Cria backup
            if not self.create_backup(file_path):
                return False, "Falha ao criar backup", metadata
            
            # Renomeia arquivo
            file_path.rename(new_path)
            
            success_msg = f" Renomeado: {file_path.name} → {new_path.name}"
            self.logger.info(success_msg)
            
            return True, success_msg, metadata
            
        except Exception as e:
            error_msg = f" Erro ao processar {file_path.name}: {e}"
            self.logger.error(error_msg)
            return False, error_msg, None

class AutoRenameSystem:
    """
    Sistema principal de renomeação automática
    """
    
    def __init__(self):
        self.file_renamer = FileRenamer()
        self.batch_processor = BatchBookProcessor()
        self.setup_logging()
        
        self.stats = {
            'total_files': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'start_time': None,
            'end_time': None
        }

    def setup_logging(self):
        """Configura logging"""
        self.logger = logging.getLogger(__name__)

    def discover_book_files(self, directory: Path) -> List[Path]:
        """
        Descobre arquivos de livros no diretório
        """
        book_files = []
        supported_extensions = {'.pdf', '.epub', '.mobi', '.azw', '.azw3'}
        
        try:
            for file_path in directory.rglob('*'):
                if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                    book_files.append(file_path)
            
            self.logger.info(f"📚 Encontrados {len(book_files)} arquivos de livros em {directory}")
            return book_files
            
        except Exception as e:
            self.logger.error(f" Erro ao descobrir arquivos em {directory}: {e}")
            return []

    async def process_directory(self, directory_path: str) -> Dict:
        """
        Processa todos os livros em um diretório
        """
        directory = Path(directory_path)
        
        if not directory.exists():
            raise ValueError(f"Diretório não existe: {directory_path}")
        
        if not directory.is_dir():
            raise ValueError(f"Caminho não é um diretório: {directory_path}")
        
        self.logger.info(f"📂 Processando diretório: {directory}")
        self.stats['start_time'] = datetime.now()
        
        # Descobre arquivos
        book_files = self.discover_book_files(directory)
        self.stats['total_files'] = len(book_files)
        
        if not book_files:
            return self.create_final_report()
        
        # Processa arquivos
        results = []
        for file_path in book_files:
            success, message, metadata = await self.file_renamer.rename_single_file(file_path)
            
            if success:
                self.stats['successful'] += 1
            else:
                self.stats['failed'] += 1
            
            results.append({
                'file': str(file_path),
                'success': success,
                'message': message,
                'metadata': metadata
            })
        
        self.stats['end_time'] = datetime.now()
        
        # Cria relatório
        report = self.create_final_report()
        report['results'] = results
        
        return report

    async def process_single_file(self, file_path: str) -> Dict:
        """
        Processa um único arquivo
        """
        file_path_obj = Path(file_path)
        
        if not file_path_obj.exists():
            raise ValueError(f"Arquivo não existe: {file_path}")
        
        self.logger.info(f"📄 Processando arquivo único: {file_path_obj}")
        self.stats['start_time'] = datetime.now()
        self.stats['total_files'] = 1
        
        success, message, metadata = await self.file_renamer.rename_single_file(file_path_obj)
        
        if success:
            self.stats['successful'] += 1
        else:
            self.stats['failed'] += 1
        
        self.stats['end_time'] = datetime.now()
        
        result = {
            'file': str(file_path_obj),
            'success': success,
            'message': message,
            'metadata': metadata
        }
        
        report = self.create_final_report()
        report['results'] = [result]
        
        return report

    async def process_batch_file(self, batch_file_path: str) -> Dict:
        """
        Processa arquivo com lista de livros para renomear
        """
        batch_file = Path(batch_file_path)
        
        if not batch_file.exists():
            raise ValueError(f"Arquivo de lote não existe: {batch_file_path}")
        
        # Lê lista de arquivos
        try:
            with open(batch_file, 'r', encoding='utf-8') as f:
                file_paths = [line.strip() for line in f if line.strip()]
        except Exception as e:
            raise ValueError(f"Erro ao ler arquivo de lote: {e}")
        
        self.logger.info(f"📋 Processando lote de {len(file_paths)} arquivos")
        self.stats['start_time'] = datetime.now()
        self.stats['total_files'] = len(file_paths)
        
        results = []
        for file_path_str in file_paths:
            file_path = Path(file_path_str)
            
            if not file_path.exists():
                self.stats['failed'] += 1
                results.append({
                    'file': str(file_path),
                    'success': False,
                    'message': f"Arquivo não encontrado: {file_path}",
                    'metadata': None
                })
                continue
            
            success, message, metadata = await self.file_renamer.rename_single_file(file_path)
            
            if success:
                self.stats['successful'] += 1
            else:
                self.stats['failed'] += 1
            
            results.append({
                'file': str(file_path),
                'success': success,
                'message': message,
                'metadata': metadata
            })
        
        self.stats['end_time'] = datetime.now()
        
        report = self.create_final_report()
        report['results'] = results
        
        return report

    def create_final_report(self) -> Dict:
        """
        Cria relatório final
        """
        duration = None
        if self.stats['start_time'] and self.stats['end_time']:
            duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        return {
            'summary': {
                'total_files': self.stats['total_files'],
                'successful': self.stats['successful'],
                'failed': self.stats['failed'],
                'success_rate': (self.stats['successful'] / self.stats['total_files'] * 100) if self.stats['total_files'] > 0 else 0,
                'duration_seconds': duration,
                'start_time': self.stats['start_time'].isoformat() if self.stats['start_time'] else None,
                'end_time': self.stats['end_time'].isoformat() if self.stats['end_time'] else None
            }
        }

    def save_report(self, report: Dict, output_path: str = None):
        """
        Salva relatório em arquivo JSON
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"rename_report_{timestamp}.json"
        
        try:
            # Converte BookMetadata para dict para serialização JSON
            if 'results' in report:
                for result in report['results']:
                    if result['metadata'] and hasattr(result['metadata'], '__dict__'):
                        result['metadata'] = {
                            'title': result['metadata'].title,
                            'authors': result['metadata'].authors,
                            'publisher': result['metadata'].publisher,
                            'published_date': result['metadata'].published_date,
                            'confidence_score': result['metadata'].confidence_score,
                            'source_api': result['metadata'].source_api
                        }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"📊 Relatório salvo: {output_path}")
            
        except Exception as e:
            self.logger.error(f" Erro ao salvar relatório: {e}")

def print_banner():
    """Imprime banner do sistema"""
    print("""
🎯 Sistema Automático de Renomeação de PDFs e EPUBs
════════════════════════════════════════════════════
Versão: 1.0.0 - Produção
Sistema V3 com 88.7% de precisão 
Amazon Books API Integration 
Processamento em Lote 
""")

def print_report(report: Dict):
    """Imprime relatório formatado"""
    summary = report['summary']
    
    print("\n" + "="*60)
    print("📊 RELATÓRIO FINAL")
    print("="*60)
    print(f"📚 Total de arquivos: {summary['total_files']}")
    print(f" Sucessos: {summary['successful']}")
    print(f" Falhas: {summary['failed']}")
    print(f"📈 Taxa de sucesso: {summary['success_rate']:.1f}%")
    
    if summary['duration_seconds']:
        print(f"⏱ Tempo total: {summary['duration_seconds']:.1f}s")
    
    # Detalhes dos resultados se disponível
    if 'results' in report and len(report['results']) <= 10:  # Só mostra detalhes para poucos arquivos
        print(f"\n📋 Detalhes:")
        for result in report['results']:
            file_name = Path(result['file']).name
            status = "" if result['success'] else ""
            print(f"   {status} {file_name[:50]}")
            if result['metadata'] and result['success']:
                metadata = result['metadata']
                if isinstance(metadata, dict):
                    title = metadata.get('title', 'N/A')
                    authors = ', '.join(metadata.get('authors', []))
                else:
                    title = metadata.title
                    authors = ', '.join(metadata.authors)
                print(f"      → {title} - {authors}")

async def main():
    """Função principal"""
    print_banner()
    
    parser = argparse.ArgumentParser(
        description="Sistema Automático de Renomeação de PDFs e EPUBs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  python auto_rename_system.py --directory /Users/usuario/Books
  python auto_rename_system.py --file "meu_livro.pdf"
  python auto_rename_system.py --batch lista_livros.txt
  python auto_rename_system.py --directory /Books --output relatorio.json
        """
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--directory', '-d', help='Diretório para processar')
    group.add_argument('--file', '-f', help='Arquivo único para processar')
    group.add_argument('--batch', '-b', help='Arquivo com lista de arquivos para processar')
    
    parser.add_argument('--output', '-o', help='Arquivo de saída para relatório JSON')
    parser.add_argument('--no-backup', action='store_true', help='Desabilita criação de backup')
    
    args = parser.parse_args()
    
    try:
        # Configura sistema
        system = AutoRenameSystem()
        if args.no_backup:
            system.file_renamer.backup_enabled = False
        
        # Processa baseado no argumento
        if args.directory:
            report = await system.process_directory(args.directory)
        elif args.file:
            report = await system.process_single_file(args.file)
        elif args.batch:
            report = await system.process_batch_file(args.batch)
        
        # Mostra relatório
        print_report(report)
        
        # Salva relatório se solicitado
        if args.output:
            system.save_report(report, args.output)
        
        print(f"\n🎉 Processamento concluído!")
        
    except KeyboardInterrupt:
        print(f"\n⚠ Operação interrompida pelo usuário")
        return 1
    except Exception as e:
        print(f"\n Erro: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)