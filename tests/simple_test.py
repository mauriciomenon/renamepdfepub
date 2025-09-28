#!/usr/bin/env python3
"""
Teste Simples de Validacao de Dados
"""

import os
from pathlib import Path

def test_books():
    books_dir = Path("books")
    
    if not books_dir.exists():
        print("Pasta books nao encontrada")
        return
    
    count = 0
    for file_path in books_dir.iterdir():
        if file_path.suffix.lower() in ['.pdf', '.epub', '.mobi']:
            count += 1
            if count <= 10:
                print(f"{count}. {file_path.name}")
    
    print(f"\nTotal: {count} livros encontrados")

if __name__ == "__main__":
    test_books()