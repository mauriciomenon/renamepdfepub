#!/usr/bin/env python3
"""
Teste Ultra Simples
"""

import os
from pathlib import Path

def main():
    """Teste basico"""
    print("INICIANDO TESTE ULTRA SIMPLES")
    print("=" * 40)
    
    # Verifica pasta books
    books_dir = Path("books")
    
    if not books_dir.exists():
        print("ERRO: Pasta books/ nao encontrada!")
        return
    
    # Lista arquivos
    book_files = [f for f in books_dir.iterdir() 
                 if f.suffix.lower() in ['.pdf', '.epub', '.mobi'] 
                 and not f.name.startswith('.')]
    
    print(f"Encontrados {len(book_files)} livros na pasta books/")
    
    if book_files:
        print("\nPrimeiros 10 livros:")
        for i, book in enumerate(book_files[:10], 1):
            print(f"{i}. {book.name}")
    
    print(f"\nTESTE FINALIZADO!")

if __name__ == "__main__":
    main()