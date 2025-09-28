"""
Utilitário para Gerenciar Listas de Arquivos para Cache Iterativo
================================================================

Ferramentas para criar listas de arquivos a partir de diferentes fontes:
- Diretórios locais
- Outputs de `ls` ou `find`
- URLs do Google Drive ou OneDrive
- Arquivos de texto com caminhos
"""

import argparse
import json
import re
from pathlib import Path
from typing import List, Dict, Optional
import urllib.parse

def create_file_list_from_directory(directory: Path, patterns: List[str] = None, 
                                   recursive: bool = True) -> List[str]:
    """Cria lista de arquivos a partir de um diretório"""
    if patterns is None:
        patterns = ['*.pdf', '*.epub', '*.mobi', '*.txt', '*.doc', '*.docx']
    
    files = []
    
    if recursive:
        for pattern in patterns:
            files.extend(directory.rglob(pattern))
    else:
        for pattern in patterns:
            files.extend(directory.glob(pattern))
    
    return [str(f) for f in files]

def parse_ls_output(ls_output: str, base_path: str = "") -> List[str]:
    """Converte output de comando `ls` em lista de caminhos"""
    lines = ls_output.strip().split('\n')
    files = []
    
    for line in lines:
        line = line.strip()
        if line and not line.startswith('total '):
            # Remove informações de permissão se presente (ls -la)
            if line.startswith('-') or line.startswith('d'):
                # Formato ls -la: drwxr-xr-x ... filename
                parts = line.split()
                if len(parts) >= 9:
                    filename = ' '.join(parts[8:])  # Nome pode ter espaços
                    files.append(str(Path(base_path) / filename))
            else:
                # ls simples
                files.append(str(Path(base_path) / line))
    
    return files

def parse_find_output(find_output: str) -> List[str]:
    """Converte output de comando `find` em lista de caminhos"""
    lines = find_output.strip().split('\n')
    return [line.strip() for line in lines if line.strip()]

def extract_gdrive_files_from_text(text: str) -> Dict[str, str]:
    """Extrai informações de arquivos do Google Drive de texto"""
    # Padrões para detectar links/IDs do Google Drive
    gdrive_patterns = [
        r'drive\.google\.com/file/d/([a-zA-Z0-9_-]+)',  # URL completa
        r'id=([a-zA-Z0-9_-]+)',  # ID em parâmetro
        r'([a-zA-Z0-9_-]{25,})',  # ID standalone (25+ chars)
    ]
    
    files = {}
    lines = text.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Tenta extrair ID do Google Drive
        gdrive_id = None
        for pattern in gdrive_patterns:
            match = re.search(pattern, line)
            if match:
                gdrive_id = match.group(1)
                break
        
        if gdrive_id:
            # Tenta extrair nome do arquivo da linha
            # Remove URLs e IDs para ficar só com o nome
            filename = re.sub(r'https?://[^\s]+', '', line)
            filename = re.sub(r'[a-zA-Z0-9_-]{25,}', '', filename)
            filename = filename.strip(' -.,')
            
            if not filename:
                filename = f"gdrive_file_{gdrive_id}.pdf"  # Nome padrão
                
            files[filename] = gdrive_id
    
    return files

def extract_onedrive_files_from_text(text: str) -> Dict[str, str]:
    """Extrai informações de arquivos do OneDrive de texto"""
    onedrive_patterns = [
        r'1drv\.ms/[a-zA-Z]/[a-zA-Z0-9_-]+',  # URL curta
        r'[a-zA-Z0-9-]+\.sharepoint\.com.*',  # URL completa SharePoint
    ]
    
    files = {}
    lines = text.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Tenta extrair URL do OneDrive
        onedrive_url = None
        for pattern in onedrive_patterns:
            match = re.search(pattern, line)
            if match:
                onedrive_url = match.group(0)
                break
        
        if onedrive_url:
            # Tenta extrair nome do arquivo
            filename = line.replace(onedrive_url, '').strip(' -.,')
            
            if not filename:
                # Tenta extrair nome da URL
                try:
                    parsed = urllib.parse.urlparse(onedrive_url)
                    filename = Path(parsed.path).name or f"onedrive_file.pdf"
                except:
                    filename = f"onedrive_file.pdf"
                    
            files[filename] = onedrive_url
    
    return files

def create_remote_mapping(source_file: Path, source_type: str) -> Dict[str, str]:
    """Cria mapeamento de arquivos remotos a partir de arquivo de origem"""
    with open(source_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if source_type == 'gdrive':
        return extract_gdrive_files_from_text(content)
    elif source_type == 'onedrive':
        return extract_onedrive_files_from_text(content)
    else:
        raise ValueError(f"Tipo de fonte não suportado: {source_type}")

def main():
    parser = argparse.ArgumentParser(
        description='Utilitário para criar listas de arquivos para Cache Iterativo',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:

1. Criar lista de arquivos de um diretório:
   python utils/file_list_creator.py --directory /path/to/books --output file_list.txt

2. Converter output de `ls` para lista:
   ls -la /path/to/books > ls_output.txt
   python utils/file_list_creator.py --ls-file ls_output.txt --base-path /path/to/books

3. Converter output de `find` para lista:
   find /path -name "*.pdf" > find_output.txt
   python utils/file_list_creator.py --find-file find_output.txt

4. Criar mapeamento de arquivos do Google Drive:
   python utils/file_list_creator.py --remote-file gdrive_links.txt --remote-type gdrive --output gdrive_mapping.json

5. Criar mapeamento de arquivos do OneDrive:
   python utils/file_list_creator.py --remote-file onedrive_urls.txt --remote-type onedrive --output onedrive_mapping.json
        """
    )
    
    # Opções de entrada
    parser.add_argument('--directory', type=str,
                       help='Diretório para escanear arquivos')
    
    parser.add_argument('--ls-file', type=str,
                       help='Arquivo com output de comando `ls`')
    
    parser.add_argument('--find-file', type=str,
                       help='Arquivo com output de comando `find`')
    
    parser.add_argument('--remote-file', type=str,
                       help='Arquivo com URLs/IDs de arquivos remotos')
    
    parser.add_argument('--remote-type', choices=['gdrive', 'onedrive'],
                       help='Tipo de serviço remoto')
    
    # Opções de configuração
    parser.add_argument('--base-path', type=str, default="",
                       help='Caminho base para arquivos (usado com --ls-file)')
    
    parser.add_argument('--patterns', nargs='+', 
                       default=['*.pdf', '*.epub', '*.mobi'],
                       help='Padrões de arquivo para buscar (usado com --directory)')
    
    parser.add_argument('--recursive', action='store_true', default=True,
                       help='Busca recursiva em subdiretórios')
    
    parser.add_argument('--no-recursive', action='store_false', dest='recursive',
                       help='Desabilita busca recursiva')
    
    # Saída
    parser.add_argument('--output', type=str, required=True,
                       help='Arquivo de saída')
    
    parser.add_argument('--format', choices=['txt', 'json'], default='txt',
                       help='Formato do arquivo de saída (default: txt)')
    
    args = parser.parse_args()
    
    # Validação de argumentos
    input_methods = [args.directory, args.ls_file, args.find_file, args.remote_file]
    if sum(1 for method in input_methods if method) != 1:
        parser.error("Especifique exatamente uma fonte: --directory, --ls-file, --find-file, ou --remote-file")
    
    if args.remote_file and not args.remote_type:
        parser.error("--remote-type é obrigatório quando usar --remote-file")
    
    try:
        # Processa entrada
        if args.directory:
            files = create_file_list_from_directory(
                Path(args.directory), args.patterns, args.recursive
            )
            data = files
            
        elif args.ls_file:
            with open(args.ls_file, 'r', encoding='utf-8') as f:
                ls_output = f.read()
            files = parse_ls_output(ls_output, args.base_path)
            data = files
            
        elif args.find_file:
            with open(args.find_file, 'r', encoding='utf-8') as f:
                find_output = f.read()
            files = parse_find_output(find_output)
            data = files
            
        elif args.remote_file:
            remote_mapping = create_remote_mapping(Path(args.remote_file), args.remote_type)
            data = remote_mapping
            args.format = 'json'  # Força JSON para mapeamentos remotos
        
        # Salva saída
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if args.format == 'json':
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        else:
            with open(output_path, 'w', encoding='utf-8') as f:
                if isinstance(data, list):
                    for item in data:
                        f.write(f"{item}\n")
                else:
                    for key, value in data.items():
                        f.write(f"{key}\t{value}\n")
        
        # Relatório
        if isinstance(data, list):
            print(f" Criada lista com {len(data)} arquivos: {output_path}")
        else:
            print(f" Criado mapeamento com {len(data)} arquivos remotos: {output_path}")
            
        # Mostra amostra
        print("\n📋 Amostra dos dados:")
        if isinstance(data, list):
            for item in data[:5]:
                print(f"   • {item}")
            if len(data) > 5:
                print(f"   ... e mais {len(data) - 5} arquivos")
        else:
            for i, (key, value) in enumerate(data.items()):
                if i >= 5:
                    print(f"   ... e mais {len(data) - 5} mapeamentos")
                    break
                print(f"   • {key} -> {value}")
        
    except Exception as e:
        print(f" Erro: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())