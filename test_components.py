#!/usr/bin/env python3
"""
Teste de GUI sem PyQt6 - apenas testa imports e lógica básica
"""

import sys
import os
from pathlib import Path

def test_gui_logic():
    """Testa a lógica da GUI sem inicializar interface"""
    try:
        # Add src to path like the GUI does
        project_root = Path(__file__).resolve().parent
        src_dir = project_root / "src"
        if src_dir.exists() and str(src_dir) not in sys.path:
            sys.path.insert(0, str(src_dir))
        
        # Test shared modules import
        import renamepdfepub.metadata_extractor as extractor
        print("✅ metadata_extractor import successful")
        
        # Test a basic function
        result = extractor.extract_from_epub("nonexistent.epub")
        expected_keys = ['title', 'subtitle', 'authors', 'publisher', 'year', 'isbn10', 'isbn13']
        if all(key in result for key in expected_keys):
            print("✅ metadata_extractor.extract_from_epub returns expected structure")
        else:
            print("❌ Unexpected structure from extract_from_epub")
            
        return True
    except Exception as e:
        print(f"❌ GUI logic test failed: {e}")
        return False

def test_cli_functionality():
    """Testa algumas funcionalidades do CLI"""
    try:
        # Import CLI
        sys.path.insert(0, "/Users/menon/git/renamepdfepub")
        import renomeia_livro
        
        print("✅ CLI import successful")
        
        # Test if main classes exist
        if hasattr(renomeia_livro, 'DependencyManager'):
            print("✅ DependencyManager class found")
        if hasattr(renomeia_livro, 'MetadataCache'):
            print("✅ MetadataCache class found") 
        if hasattr(renomeia_livro, 'BookMetadataExtractor'):
            print("✅ BookMetadataExtractor class found")
            
        return True
    except Exception as e:
        print(f"❌ CLI functionality test failed: {e}")
        return False

def test_shared_modules_detailed():
    """Testa módulos compartilhados em detalhe"""
    try:
        from pathlib import Path
        src_dir = Path("/Users/menon/git/renamepdfepub/src")
        sys.path.insert(0, str(src_dir))
        
        # Test all shared modules
        modules = ['metadata_extractor', 'metadata_cache', 'metadata_enricher', 'renamer', 'logging_config']
        imported = []
        
        for module in modules:
            try:
                __import__(f'renamepdfepub.{module}')
                imported.append(module)
                print(f"✅ {module} imported successfully")
            except Exception as e:
                print(f"❌ {module} import failed: {e}")
        
        return len(imported) == len(modules)
    except Exception as e:
        print(f"❌ Shared modules test failed: {e}")
        return False

if __name__ == "__main__":
    print("=== Teste de Funcionalidade sem PyQt6 ===\n")
    
    results = []
    results.append(test_shared_modules_detailed())
    results.append(test_gui_logic())
    results.append(test_cli_functionality())
    
    print(f"\n=== Resumo: {sum(results)}/3 testes passaram ===")
    
    if all(results):
        print("🎉 Todos os componentes estão funcionando!")
    else:
        print("⚠️  Alguns componentes apresentaram problemas")