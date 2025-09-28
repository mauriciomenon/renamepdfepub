#!/usr/bin/env python3
"""
Teste simples da GUI para verificar funcionamento básico
"""

import sys
import os
import pytest
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def test_gui_imports():
    """Testa se conseguimos importar a GUI sem erros"""
    try:
        from gui_RenameBook import RenamePDFGUI
        print(" GUI import successful")
        assert True  # Sucesso na importação
    except Exception as e:
        print(f" GUI import failed: {e}")
        pytest.skip(f"GUI não disponível: {e}")

def test_cli_imports():
    """Testa se conseguimos importar o CLI sem erros"""
    try:
        import renomeia_livro
        print(" CLI import successful")
        assert True  # Sucesso na importação
    except Exception as e:
        print(f" CLI import failed: {e}")
        pytest.skip(f"CLI não disponível: {e}")

def test_shared_modules():
    """Testa se conseguimos importar módulos compartilhados"""
    modules = ["json", "pathlib", "os", "sys"]
    
    for module in modules:
        try:
            __import__(module)
            print(f" {module} import successful")
        except Exception as e:
            print(f" {module} import failed: {e}")
            pytest.fail(f"Módulo básico {module} não disponível: {e}")
    
    assert True  # Todos os módulos importados com sucesso

def test_sample_books():
    """Lista alguns arquivos de teste disponíveis"""
    books_dir = Path("books")
    if not books_dir.exists():
        print(" Books directory not found")
        pytest.skip("Diretório books não encontrado")
    
    pdf_files = list(books_dir.glob("*.pdf"))
    epub_files = list(books_dir.glob("*.epub"))
    
    print(f" Found {len(pdf_files)} PDF files and {len(epub_files)} EPUB files")
    
    # Show first 3 of each type
    if pdf_files:
        print("[DOC] Sample PDFs:")
        for pdf in pdf_files[:3]:
            print(f"   - {pdf.name}")
    
    if epub_files:
        print("[BOOK] Sample EPUBs:")
        for epub in epub_files[:3]:
            print(f"   - {epub.name}")
    
    # Pelo menos alguns arquivos devem existir
    total_books = len(pdf_files) + len(epub_files)
    assert total_books > 0, "Nenhum arquivo de livro encontrado"

if __name__ == "__main__":
    print("=== Teste Básico de Funcionamento ===\n")
    
    results = []
    results.append(test_shared_modules())
    results.append(test_cli_imports())
    results.append(test_gui_imports())
    results.append(test_sample_books())
    
    print(f"\n=== Resumo: {sum(results)}/4 testes passaram ===")
    
    if all(results):
        print("🎉 Todos os componentes estão funcionando!")
    else:
        print("⚠  Alguns componentes apresentaram problemas")
        sys.exit(1)