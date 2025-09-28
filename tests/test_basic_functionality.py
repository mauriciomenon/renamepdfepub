#!/usr/bin/env python3
"""
Teste simples da GUI para verificar funcionamento básico
"""

import sys
import os
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def test_gui_imports():
    """Testa se conseguimos importar a GUI sem erros"""
    try:
        from gui_RenameBook import RenamePDFGUI
        print(" GUI import successful")
        return True
    except Exception as e:
        print(f" GUI import failed: {e}")
        return False

def test_cli_imports():
    """Testa se conseguimos importar o CLI sem erros"""
    try:
        import renomeia_livro
        print(" CLI import successful")
        return True
    except Exception as e:
        print(f" CLI import failed: {e}")
        return False

def test_shared_modules():
    """Testa se conseguimos importar os módulos compartilhados"""
    try:
        from renamepdfepub import metadata_extractor, metadata_cache, renamer
        print(" Shared modules import successful")
        return True
    except Exception as e:
        print(f" Shared modules import failed: {e}")
        return False

def test_sample_books():
    """Lista alguns arquivos de teste disponíveis"""
    books_dir = Path("books")
    if not books_dir.exists():
        print(" Books directory not found")
        return False
    
    pdf_files = list(books_dir.glob("*.pdf"))
    epub_files = list(books_dir.glob("*.epub"))
    
    print(f" Found {len(pdf_files)} PDF files and {len(epub_files)} EPUB files")
    
    # Show first 3 of each type
    if pdf_files:
        print("📄 Sample PDFs:")
        for pdf in pdf_files[:3]:
            print(f"   - {pdf.name}")
    
    if epub_files:
        print("📚 Sample EPUBs:")
        for epub in epub_files[:3]:
            print(f"   - {epub.name}")
    
    return True

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