#!/usr/bin/env python3
"""
Script de validação rápida do sistema
Executa verificações básicas sem usar pytest
"""

import sys
import os
from pathlib import Path

def main():
    print("=== VALIDAÇÃO RÁPIDA DO SISTEMA ===\n")
    
    # 1. Verificar Python
    print(f"1. Python Version: {sys.version}")
    
    # 2. Verificar estrutura de diretórios
    print("2. Estrutura de Diretórios:")
    required_dirs = ["src", "tests", "books", "data"]
    for dirname in required_dirs:
        dir_path = Path(dirname)
        status = "[OK]" if dir_path.exists() else "[MISSING]"
        print(f"   {dirname}: {status}")
    
    # 3. Verificar startpoints
    print("3. Startpoints:")
    startpoints = ["start_cli.py", "start_gui.py", "start_web.py", "start_html.py"]
    for sp in startpoints:
        sp_path = Path(sp)
        if sp_path.exists():
            try:
                with open(sp_path, 'r') as f:
                    first_line = f.readline()
                status = "[OK]" if first_line.startswith('#!') else "[NO-SHEBANG]"
            except:
                status = "[READ-ERROR]"
        else:
            status = "[MISSING]"
        print(f"   {sp}: {status}")
    
    # 4. Verificar imports básicos
    print("4. Imports Básicos:")
    basic_modules = ["json", "os", "sys", "pathlib", "subprocess"]
    for module in basic_modules:
        try:
            __import__(module)
            status = "[OK]"
        except ImportError:
            status = "[FAIL]"
        print(f"   {module}: {status}")
    
    # 5. Verificar arquivos de teste
    print("5. Arquivos de Teste:")
    test_files = [
        "tests/test_startpoints_integrity.py",
        "tests/test_cache_and_database.py", 
        "tests/test_interfaces.py",
        "tests/test_metadata_and_algorithms.py",
        "tests/test_basic_functionality.py"
    ]
    
    for test_file in test_files:
        test_path = Path(test_file)
        if test_path.exists():
            try:
                with open(test_path, 'r') as f:
                    content = f.read()
                if 'def test_' in content:
                    status = "[OK]"
                else:
                    status = "[NO-TESTS]"
            except:
                status = "[READ-ERROR]"
        else:
            status = "[MISSING]"
        print(f"   {test_path.name}: {status}")
    
    # 6. Verificar livros de amostra
    print("6. Livros de Amostra:")
    books_dir = Path("books")
    if books_dir.exists():
        pdf_count = len(list(books_dir.glob("*.pdf")))
        epub_count = len(list(books_dir.glob("*.epub")))
        print(f"   PDFs: {pdf_count} [{'OK' if pdf_count > 0 else 'NONE'}]")
        print(f"   EPUBs: {epub_count} [{'OK' if epub_count > 0 else 'NONE'}]")
    else:
        print("   books/ directory: [MISSING]")
    
    # 7. Verificar cache e dados
    print("7. Cache e Dados:")
    data_dir = Path("data")
    if data_dir.exists():
        cache_dir = data_dir / "cache"
        cache_status = "[OK]" if cache_dir.exists() else "[MISSING]"
        print(f"   data/cache: {cache_status}")
        
        # Verificar arquivos de configuração
        config_files = ["search_config.json", "pytest.ini"]
        for config_file in config_files:
            config_path = Path(config_file)
            config_status = "[OK]" if config_path.exists() else "[MISSING]"
            print(f"   {config_file}: {config_status}")
    else:
        print("   data/ directory: [MISSING]")
    
    print("\n=== RESUMO ===")
    print("Sistema validado. Verifique os items marcados como [MISSING] ou [FAIL]")
    print("Para corrigir problemas, execute os testes específicos ou recrie os arquivos necessários")

if __name__ == "__main__":
    main()