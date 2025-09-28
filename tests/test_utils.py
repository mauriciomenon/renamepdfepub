"""
Testes para utilitários e validação
"""
import pytest
import re
from pathlib import Path

def test_file_validation():
    """Testa validações básicas de arquivo"""
    valid_extensions = [".pdf", ".epub"]
    test_files = [
        "livro.pdf",
        "ebook.epub", 
        "documento.txt",  # inválido
        "imagem.jpg"      # inválido
    ]
    
    for filename in test_files:
        extension = Path(filename).suffix.lower()
        is_valid = extension in valid_extensions
        
        if filename.endswith((".pdf", ".epub")):
            assert is_valid, f"Arquivo {filename} deveria ser válido"
        else:
            assert not is_valid, f"Arquivo {filename} deveria ser inválido"

def test_metadata_cleaning():
    """Testa limpeza de metadados"""
    dirty_metadata = {
        "title": "  Python para Desenvolvedores  ",
        "author": "\n\nJoão Silva\n\n",
        "publisher": "\t\tCasa do Código\t\t"
    }
    
    # Simula limpeza
    clean_metadata = {}
    for key, value in dirty_metadata.items():
        if isinstance(value, str):
            clean_metadata[key] = value.strip()
        else:
            clean_metadata[key] = value
    
    assert clean_metadata["title"] == "Python para Desenvolvedores"
    assert clean_metadata["author"] == "João Silva"
    assert clean_metadata["publisher"] == "Casa do Código"

def test_isbn_validation():
    """Testa validação de ISBN"""
    valid_isbns = [
        "978-85-5519-999-9",
        "9788555199999",
        "978-0-123456-78-9"
    ]
    
    invalid_isbns = [
        "123",
        "abc-def-ghi",
        "",
        None
    ]
    
    def is_valid_isbn(isbn):
        if not isbn:
            return False
        clean_isbn = str(isbn).replace("-", "").replace(" ", "")
        return len(clean_isbn) in [10, 13] and clean_isbn.isdigit()
    
    for isbn in valid_isbns:
        assert is_valid_isbn(isbn), f"ISBN {isbn} deveria ser válido"
    
    for isbn in invalid_isbns:
        assert not is_valid_isbn(isbn), f"ISBN {isbn} deveria ser inválido"

def test_year_validation():
    """Testa validação de ano"""
    valid_years = [2020, 2021, 2022, 2023, 2024, 2025]
    invalid_years = [1800, 3000, -1, 0, "abc", None]
    
    def is_valid_year(year):
        try:
            year_int = int(year)
            return 1900 <= year_int <= 2030
        except (ValueError, TypeError):
            return False
    
    for year in valid_years:
        assert is_valid_year(year), f"Ano {year} deveria ser válido"
    
    for year in invalid_years:
        assert not is_valid_year(year), f"Ano {year} deveria ser inválido"

def test_filename_sanitization():
    """Testa sanitização de nomes de arquivo"""
    dangerous_chars = ["<", ">", ":", '"', "/", "\\", "|", "?", "*"]
    test_filename = "Livro: Python - Guia <Completo> (2024).pdf"
    
    # Simula sanitização
    safe_filename = test_filename
    for char in dangerous_chars:
        safe_filename = safe_filename.replace(char, "_")
    
    assert "<" not in safe_filename
    assert ">" not in safe_filename
    assert ":" not in safe_filename
    assert safe_filename.endswith(".pdf")

def test_publisher_categorization():
    """Testa categorização de editoras"""
    brazilian_publishers = [
        "Casa do Código",
        "Novatec", 
        "Érica",
        "Brasport",
        "Alta Books"
    ]
    
    international_publishers = [
        "O'Reilly",
        "Packt",
        "Manning",
        "Addison-Wesley",
        "Pearson"
    ]
    
    def is_brazilian_publisher(publisher):
        return publisher in brazilian_publishers
    
    for publisher in brazilian_publishers:
        assert is_brazilian_publisher(publisher), f"{publisher} deveria ser brasileira"
    
    for publisher in international_publishers:
        assert not is_brazilian_publisher(publisher), f"{publisher} deveria ser internacional"