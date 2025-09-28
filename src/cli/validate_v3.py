#!/usr/bin/env python3
"""
Teste Completo V3 - Validação dos Algoritmos Melhorados
=======================================================
"""

import re
from pathlib import Path

def test_metadata_extraction():
    print("=== VALIDAÇÃO EXTRAÇÃO V3 ===\n")
    
    # Test cases com resultados esperados
    test_cases = [
        {
            'filename': 'Python_Programming_by_Mark_Lutz_2023.pdf',
            'expected_author': 'Mark Lutz',
            'expected_year': '2023',
            'expected_publisher': None
        },
        {
            'filename': 'JavaScript_React_Manning_2022.epub',
            'expected_author': None,
            'expected_year': '2022', 
            'expected_publisher': 'Manning'
        },
        {
            'filename': 'Ethical_Hacking_by_John_Smith_Packt.pdf',
            'expected_author': 'John Smith',
            'expected_year': None,
            'expected_publisher': 'Packt'
        }
    ]
    
    # Patterns melhorados
    author_patterns = [
        r'\bby\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)(?:\s|$|\(|\[|,|-)',
        r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s+presents\b',
        r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+?)\s*-\s*'
    ]
    
    year_patterns = [
        r'\b(20[0-2]\d)\b',  # 2000-2029
        r'\b(19[89]\d)\b',   # 1980-1999
        r'(\d{4})(?=\.pdf|\.epub|\.mobi|$)'  # Ano no final
    ]
    
    publisher_patterns = {
        'Manning': [r'\bmanning\b', r'\bmeap\b'],
        'Packt': [r'\bpackt\b', r'cookbook'],
        'OReilly': [r'o\'?reilly'],
        'NoStarch': [r'no\s*starch']
    }
    
    results = {
        'author_success': 0,
        'year_success': 0,
        'publisher_success': 0,
        'total_tests': len(test_cases)
    }
    
    for i, case in enumerate(test_cases, 1):
        filename = case['filename']
        clean_name = filename.replace('_', ' ').replace('.pdf', '').replace('.epub', '').replace('.mobi', '')
        
        print(f"--- Teste {i}: {filename} ---")
        print(f"Texto limpo: {clean_name}")
        
        # Test Author
        found_author = None
        for pattern in author_patterns:
            match = re.search(pattern, clean_name, re.IGNORECASE)
            if match:
                author = match.group(1).strip()
                # Validar nome
                words = author.split()
                if len(words) >= 2 and all(word[0].isupper() for word in words) and not any(c.isdigit() for c in author):
                    found_author = author
                    break
        
        # Test Year
        found_year = None
        for pattern in year_patterns:
            match = re.search(pattern, clean_name)
            if match:
                year = match.group(1)
                year_int = int(year)
                if 1990 <= year_int <= 2030:
                    found_year = year
                    break
        
        # Test Publisher
        found_publisher = None
        for publisher, patterns in publisher_patterns.items():
            for pattern in patterns:
                if re.search(pattern, clean_name, re.IGNORECASE):
                    found_publisher = publisher
                    break
            if found_publisher:
                break
        
        # Verificar resultados
        print(f"Autor encontrado: '{found_author}' (esperado: '{case['expected_author']}')")
        print(f"Ano encontrado: '{found_year}' (esperado: '{case['expected_year']}')")  
        print(f"Publisher encontrado: '{found_publisher}' (esperado: '{case['expected_publisher']}')")
        
        # Contar sucessos
        if found_author == case['expected_author']:
            results['author_success'] += 1
            print(" Autor correto")
        else:
            print(" Autor incorreto")
            
        if found_year == case['expected_year']:
            results['year_success'] += 1
            print(" Ano correto")
        else:
            print(" Ano incorreto")
            
        if found_publisher == case['expected_publisher']:
            results['publisher_success'] += 1
            print(" Publisher correto")
        else:
            print(" Publisher incorreto")
        
        print()
    
    # Relatório final
    print("=== RELATÓRIO FINAL V3 ===")
    author_pct = results['author_success'] / results['total_tests'] * 100
    year_pct = results['year_success'] / results['total_tests'] * 100
    publisher_pct = results['publisher_success'] / results['total_tests'] * 100
    
    print(f"Autor detection: {results['author_success']}/{results['total_tests']} ({author_pct:.1f}%)")
    print(f"Ano detection: {results['year_success']}/{results['total_tests']} ({year_pct:.1f}%)")
    print(f"Publisher detection: {results['publisher_success']}/{results['total_tests']} ({publisher_pct:.1f}%)")
    
    # Avaliação contra metas
    print(f"\n=== AVALIAÇÃO CONTRA METAS V3 ===")
    print(f"Meta Autor (40%): {'' if author_pct >= 40 else ''} {author_pct:.1f}%")
    print(f"Meta Ano (30%): {'' if year_pct >= 30 else ''} {year_pct:.1f}%")
    print(f"Meta Publisher (25%): {'' if publisher_pct >= 25 else ''} {publisher_pct:.1f}%")
    
    overall_success = author_pct >= 40 and year_pct >= 30 and publisher_pct >= 25
    print(f"\nResultado V3: {'🎯 METAS ATINGIDAS' if overall_success else '🔧 PRECISA AJUSTES'}")

if __name__ == "__main__":
    test_metadata_extraction()