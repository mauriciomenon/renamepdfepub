#!/usr/bin/env python3
"""
Teste com Saida em Arquivo
"""

import sys
import os
import json
import time
import re
from pathlib import Path
from typing import Dict, List, Any
import unicodedata

class FileOutputTester:
    """Testador que salva tudo em arquivo"""
    
    def __init__(self):
        # Redireciona print para arquivo
        self.output_file = open('test_output_real.txt', 'w', encoding='utf-8')
        self.original_stdout = sys.stdout
        sys.stdout = self.output_file

    def __del__(self):
        """Cleanup"""
        if hasattr(self, 'output_file'):
            sys.stdout = self.original_stdout
            self.output_file.close()

    def print_and_save(self, text: str):
        """Imprime e salva"""
        print(text)
        self.output_file.flush()

    def extract_metadata_from_filename(self, filename: str) -> Dict[str, str]:
        """Extrai metadados do nome do arquivo"""
        name = Path(filename).stem
        
        # Patterns comuns
        publisher_patterns = {
            'Manning': ['manning', 'meap'],
            'Packt': ['packt', 'cookbook', 'mastering'],
            'OReilly': ['oreilly', 'learning'],
            'NoStarch': ['nostarch', 'no starch'],
            'Wiley': ['wiley'],
            'Addison': ['addison', 'wesley']
        }
        
        result = {'title': '', 'author': '', 'publisher': '', 'year': ''}
        
        # Extrai ano
        year_match = re.search(r'\((\d{4})\)', name)
        if year_match:
            result['year'] = year_match.group(1)
            name = re.sub(r'\(\d{4}\)', '', name)
        
        # Extrai publisher
        name_lower = name.lower()
        for pub, patterns in publisher_patterns.items():
            if any(pattern in name_lower for pattern in patterns):
                result['publisher'] = pub
                break
        
        # Tenta extrair autor (antes do primeiro " - ")
        if ' - ' in name:
            parts = name.split(' - ', 1)
            potential_author = parts[0].strip()
            if len(potential_author) > 2 and not potential_author[0].isdigit():
                result['author'] = potential_author
                name = parts[1].strip()
        
        # O resto e titulo
        result['title'] = name.strip()
        
        return result

    def simple_algorithm_test(self, filename: str) -> Dict[str, Any]:
        """Algoritmo de teste simples"""
        start_time = time.time()
        
        metadata = self.extract_metadata_from_filename(filename)
        
        # Calcula confianca baseada nos dados extraidos
        confidence = 0.2  # Base
        if metadata['title']:
            confidence += 0.3
        if metadata['author']:
            confidence += 0.3
        if metadata['publisher']:
            confidence += 0.15
        if metadata['year']:
            confidence += 0.05
        
        return {
            'title': metadata['title'],
            'author': metadata['author'],
            'publisher': metadata['publisher'], 
            'year': metadata['year'],
            'confidence': min(confidence, 1.0),
            'execution_time': time.time() - start_time
        }

    def run_test(self):
        """Executa teste principal"""
        self.print_and_save("TESTE COM DADOS REAIS - VERSAO FILE OUTPUT")
        self.print_and_save("=" * 60)
        self.print_and_save(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.print_and_save("")
        
        # Verifica pasta books
        books_dir = Path("books")
        if not books_dir.exists():
            self.print_and_save("ERRO: Pasta books/ nao encontrada!")
            return
        
        # Lista arquivos
        book_files = [f for f in books_dir.iterdir() 
                     if f.suffix.lower() in ['.pdf', '.epub', '.mobi'] 
                     and not f.name.startswith('.')]
        
        self.print_and_save(f"Encontrados {len(book_files)} livros")
        self.print_and_save("")
        
        if not book_files:
            self.print_and_save("Nenhum livro encontrado!")
            return
        
        # Testa sample de livros
        test_books = book_files[:20]  # Primeiros 20
        results = []
        
        self.print_and_save("TESTANDO ALGORITMO SIMPLES")
        self.print_and_save("-" * 40)
        self.print_and_save(f"{'Arquivo':<30} {'Titulo':<25} {'Autor':<20} {'Conf':<6}")
        self.print_and_save("-" * 40)
        
        total_confidence = 0.0
        total_time = 0.0
        
        for i, book_file in enumerate(test_books, 1):
            result = self.simple_algorithm_test(book_file.name)
            results.append({
                'filename': book_file.name,
                'result': result
            })
            
            # Imprime linha da tabela
            filename_short = book_file.name[:29]
            title_short = result['title'][:24] if result['title'] else 'N/A'
            author_short = result['author'][:19] if result['author'] else 'N/A'
            confidence = result['confidence']
            
            self.print_and_save(f"{filename_short:<30} {title_short:<25} {author_short:<20} {confidence:<6.3f}")
            
            total_confidence += confidence
            total_time += result['execution_time']
        
        # Sumario
        avg_confidence = total_confidence / len(test_books)
        avg_time = total_time / len(test_books)
        
        self.print_and_save("")
        self.print_and_save("SUMARIO")
        self.print_and_save("-" * 30)
        self.print_and_save(f"Livros testados: {len(test_books)}")
        self.print_and_save(f"Confianca media: {avg_confidence:.3f} ({avg_confidence*100:.1f}%)")
        self.print_and_save(f"Tempo medio: {avg_time:.3f}s")
        self.print_and_save(f"Taxa sucesso: {sum(1 for r in results if r['result']['confidence'] > 0.5) / len(results):.3f}")
        
        # Salva resultados detalhados
        detailed_results = {
            'test_info': {
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'total_books_tested': len(test_books),
                'algorithm': 'Simple Filename Parser'
            },
            'summary': {
                'average_confidence': avg_confidence,
                'average_time': avg_time,
                'success_rate': sum(1 for r in results if r['result']['confidence'] > 0.5) / len(results)
            },
            'detailed_results': results
        }
        
        with open('file_output_test_results.json', 'w', encoding='utf-8') as f:
            json.dump(detailed_results, f, indent=2, ensure_ascii=False)
        
        self.print_and_save("")
        self.print_and_save("Resultados detalhados salvos em: file_output_test_results.json")
        self.print_and_save("Saida completa salva em: test_output_real.txt")
        self.print_and_save("")
        self.print_and_save("TESTE FINALIZADO COM SUCESSO!")

def main():
    """Main function"""
    tester = FileOutputTester()
    try:
        tester.run_test()
    finally:
        # Garante cleanup
        if hasattr(tester, 'output_file'):
            sys.stdout = tester.original_stdout
            tester.output_file.close()
        
        # Imprime resumo no terminal
        print("Teste executado! Verifique os arquivos:")
        print("- test_output_real.txt (saida completa)")
        print("- file_output_test_results.json (resultados detalhados)")

if __name__ == "__main__":
    main()