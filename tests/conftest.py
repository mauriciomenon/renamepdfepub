"""
Configuração e fixtures para testes
"""
import pytest
import os
import sys
from pathlib import Path

# Adiciona o diretório raiz ao PYTHONPATH para importações
ROOT_DIR = Path(__file__).resolve().parents[1]
root_str = str(ROOT_DIR)
if root_str not in sys.path:
    sys.path.insert(0, root_str)

@pytest.fixture
def sample_pdf_metadata():
    """Fixture com metadados de exemplo para teste"""
    return {
        "title": "Python para Desenvolvedores",
        "author": "Luiz Eduardo Borges",
        "publisher": "Casa do Código",
        "year": "2023",
        "isbn": "978-85-5519-999-9"
    }

@pytest.fixture
def sample_epub_metadata():
    """Fixture com metadados EPUB de exemplo"""
    return {
        "title": "JavaScript Moderno",
        "author": "João Silva Santos",
        "publisher": "Novatec",
        "year": "2024",
        "isbn": "978-85-7522-888-8"
    }

@pytest.fixture
def test_files_dir():
    """Diretório para arquivos de teste"""
    test_dir = Path(__file__).parent / "test_files"
    test_dir.mkdir(exist_ok=True)
    return test_dir

@pytest.fixture
def cleanup_test_files():
    """Fixture para limpeza após testes"""
    yield
    # Cleanup code would go here if needed
    pass
