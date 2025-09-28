#!/usr/bin/env python3
"""
Teste Simples V3
================
Teste básico dos algoritmos V3 com sample data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from algorithms_v3 import AdvancedMetadataExtractor

def test_v3():
    print("=== TESTE V3 - EXTRAÇÃO MELHORADA ===")
    
    extractor = AdvancedMetadataExtractor()
    
    # Casos de teste específicos
    test_cases = [
        "Python_Programming_by_Mark_Lutz_2023.pdf",
        "JavaScript_React_Development_Manning_2022.epub",
        "Ethical_Hacking_John_Smith_Packt_2021.pdf",
        "Database_SQL_Complete_Guide_OReilly_2020.mobi",
        "Machine_Learning_Algorithms_by_Sarah_Johnson.pdf"
    ]
    
    print(f"Testando {len(test_cases)} casos...")
    
    author_found = 0
    publisher_found = 0
    year_found = 0
    
    for i, filename in enumerate(test_cases, 1):
        print(f"\n--- Teste {i}: {filename} ---")
        
        try:
            metadata = extractor.extract_v3_metadata(filename)
            
            print(f"Título: '{metadata['title']}'")
            print(f"Autor: '{metadata['author']}'")
            print(f"Publisher: '{metadata['publisher']}'")
            print(f"Ano: '{metadata['year']}'")
            print(f"Categoria: '{metadata['category']}'")
            print(f"Confiança: {metadata['confidence']:.3f}")
            
            # Contar sucessos
            if metadata['author']:
                author_found += 1
            if metadata['publisher']:
                publisher_found += 1
            if metadata['year']:
                year_found += 1
                
        except Exception as e:
            print(f"ERRO: {e}")
    
    print(f"\n=== RESULTADOS V3 ===")
    print(f"Authors detectados: {author_found}/{len(test_cases)} ({author_found/len(test_cases)*100:.1f}%)")
    print(f"Publishers detectados: {publisher_found}/{len(test_cases)} ({publisher_found/len(test_cases)*100:.1f}%)")
    print(f"Anos detectados: {year_found}/{len(test_cases)} ({year_found/len(test_cases)*100:.1f}%)")
    
    # Meta: Author 40%+, Publisher 25%+, Year 30%+
    success = author_found >= 2 and publisher_found >= 1 and year_found >= 1
    status = " SUCESSO" if success else " PRECISA MELHORIA"
    print(f"\nStatus V3: {status}")

if __name__ == "__main__":
    test_v3()