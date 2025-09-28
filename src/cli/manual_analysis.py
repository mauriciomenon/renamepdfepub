#!/usr/bin/env python3
"""
Analise Manual de Livros - Dados Reais
======================================

Analisa manualmente alguns livros para entender os padroes reais
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple

def analyze_book_filename(filename: str) -> Dict[str, str]:
    """Analisa um nome de arquivo e extrai informacoes"""
    
    result = {
        'original': filename,
        'cleaned': '',
        'title': '',
        'author': '',
        'publisher': '',
        'year': '',
        'edition': '',
        'version': '',
        'format': ''
    }
    
    # Limpar nome
    name = Path(filename).stem
    
    # Remover extensoes duplas
    if name.endswith('.pdf') or name.endswith('.epub') or name.endswith('.mobi'):
        name = name.rsplit('.', 1)[0]
    
    result['cleaned'] = name
    
    # Detectar versao MEAP
    meap_match = re.search(r'v(\d+)_MEAP', name)
    if meap_match:
        result['version'] = f"v{meap_match.group(1)} MEAP"
        name = re.sub(r'_v\d+_MEAP', '', name)
    
    # Detectar edicao
    edition_patterns = [
        r'(Second|Third|Fourth|Fifth)\s*Edition',
        r'(\d+)(st|nd|rd|th)\s*Edition'
    ]
    
    for pattern in edition_patterns:
        match = re.search(pattern, name, re.IGNORECASE)
        if match:
            result['edition'] = match.group(0)
            name = re.sub(pattern, '', name, flags=re.IGNORECASE)
            break
    
    # Detectar ano
    year_match = re.search(r'\b(19|20)\d{2}\b', name)
    if year_match:
        result['year'] = year_match.group(0)
        name = re.sub(r'\b(19|20)\d{2}\b', '', name)
    
    # Detectar publishers conhecidos
    publishers = ['Manning', 'Packt', 'OReilly', 'Wiley', 'Addison', 'Wesley']
    for pub in publishers:
        if pub.lower() in name.lower():
            result['publisher'] = pub
            break
    
    # Limpar underscores e espacos extras
    name = name.replace('_', ' ').replace('-', ' ')
    name = re.sub(r'\s+', ' ', name).strip()
    
    result['title'] = name
    
    return result

def main():
    """Funcao principal"""
    print("=== ANALISE MANUAL DE LIVROS ===\n")
    
    # Livros de exemplo para analise
    sample_books = [
        'AI_Agents_and_Applications_v7_MEAP.pdf',
        'Python_Workout_Second_Edition_v3_MEAP.epub',
        'Secrets_of_the_JavaScript_Ninja_Third_E_v8_MEAP.pdf',
        'Learn Computer Forensics - Second Edition.pdf',
        'aprenda-a-programar-com-python-descomplicando-o-desenvolvimento-de-software.epub',
        'machinelearningwithpythoncookbook_secondedition_V2.epub',
        'blackhatgo.pdf',
        'ethicalhacking.mobi'
    ]
    
    for i, book in enumerate(sample_books, 1):
        print(f"{i}. ANALISANDO: {book}")
        
        analysis = analyze_book_filename(book)
        
        print(f"   Titulo extraido: '{analysis['title']}'")
        print(f"   Edicao: '{analysis['edition']}'")
        print(f"   Versao: '{analysis['version']}'")
        print(f"   Ano: '{analysis['year']}'")
        print(f"   Publisher: '{analysis['publisher']}'")
        print()
    
    # Testar busca simples
    print("=== TESTE DE BUSCA SIMPLES ===\n")
    
    query = "python programming"
    print(f"Query: '{query}'\n")
    
    matches = []
    for book in sample_books:
        analysis = analyze_book_filename(book)
        title_lower = analysis['title'].lower()
        
        # Calcular match simples
        if 'python' in title_lower:
            score = 0.8
            matches.append((book, analysis['title'], score))
        elif 'programming' in title_lower or 'code' in title_lower:
            score = 0.6
            matches.append((book, analysis['title'], score))
    
    matches.sort(key=lambda x: x[2], reverse=True)
    
    print("Resultados encontrados:")
    for book, title, score in matches:
        print(f"  - {title} (score: {score:.1f}) [{book}]")
    
    if not matches:
        print("  Nenhum resultado encontrado")

if __name__ == "__main__":
    main()