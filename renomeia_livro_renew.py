import PyPDF2
import re
import requests
import time
from pathlib import Path
import json

class BookMetadataExtractor:
    def __init__(self):
        self.isbn_patterns = [
            r'ISBN(?:-13)?:?\s*(978[\d-]+)',  # ISBN-13
            r'ISBN(?:-10)?:?\s*([\dX-]{10,})',  # ISBN-10
            r'978[\d-]{10,}',  # Raw ISBN-13
            r'[\dX-]{10,13}'   # Raw ISBN-10/13
        ]
        
    def extract_isbn_from_pdf(self, pdf_path):
        """Tenta extrair ISBN das primeiras páginas do PDF."""
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                pages_to_check = min(5, len(reader.pages))
                
                for page_num in range(pages_to_check):
                    text = reader.pages[page_num].extract_text()
                    
                    # Tenta cada padrão de ISBN
                    for pattern in self.isbn_patterns:
                        matches = re.finditer(pattern, text, re.IGNORECASE)
                        for match in matches:
                            isbn = match.group(1) if '(' in pattern else match.group()
                            isbn = re.sub(r'[^0-9X]', '', isbn)
                            if self.is_valid_isbn(isbn):
                                return isbn
                                
        except Exception as e:
            print(f"Erro ao processar PDF {pdf_path}: {str(e)}")
        return None

    def is_valid_isbn(self, isbn):
        """Validação básica de ISBN."""
        isbn = re.sub(r'[^0-9X]', '', isbn)
        return len(isbn) in [10, 13]

    def get_metadata_from_google_books(self, isbn):
        """Consulta a API do Google Books usando ISBN."""
        try:
            url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
            response = requests.get(url)
            data = response.json()
            
            if 'items' in data and len(data['items']) > 0:
                book_info = data['items'][0]['volumeInfo']
                return {
                    'title': book_info.get('title', 'Unknown'),
                    'authors': book_info.get('authors', ['Unknown']),
                    'publisher': book_info.get('publisher', 'Unknown'),
                    'publishedDate': book_info.get('publishedDate', 'Unknown'),
                    'isbn': isbn
                }
        except Exception as e:
            print(f"Erro na consulta à API do Google Books: {str(e)}")
        return None

    def get_metadata_from_openlibrary(self, isbn):
        """Consulta a Open Library como fallback."""
        try:
            url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
            response = requests.get(url)
            data = response.json()
            
            if f"ISBN:{isbn}" in data:
                book_info = data[f"ISBN:{isbn}"]
                return {
                    'title': book_info.get('title', 'Unknown'),
                    'authors': [author['name'] for author in book_info.get('authors', [])],
                    'publisher': book_info.get('publishers', [{'name': 'Unknown'}])[0]['name'],
                    'publishedDate': book_info.get('publish_date', 'Unknown'),
                    'isbn': isbn
                }
        except Exception as e:
            print(f"Erro na consulta à Open Library: {str(e)}")
        return None

    def process_directory(self, directory_path, include_subdirs):
        """Processa todos os PDFs em um diretório."""
        results = []
        directory = Path(directory_path)
        
        pdf_pattern = '**/*.pdf' if include_subdirs else '*.pdf'
        
        for pdf_path in directory.glob(pdf_pattern):
            print(f"\nProcessando: {pdf_path}")
            
            isbn = self.extract_isbn_from_pdf(pdf_path)
            if not isbn:
                print(f"ISBN não encontrado em: {pdf_path}")
                continue
                
            print(f"ISBN encontrado: {isbn}")
            
            # Tenta Google Books primeiro
            metadata = self.get_metadata_from_google_books(isbn)
            
            # Se falhar, tenta Open Library
            if not metadata:
                metadata = self.get_metadata_from_openlibrary(isbn)
            
            if metadata:
                metadata['file_path'] = str(pdf_path)
                results.append(metadata)
                
                # Exibe informações completas na tela
                print(f"Metadados encontrados:\n"
                      f"  Título: {metadata['title']}\n"
                      f"  Autor(es): {', '.join(metadata['authors'])}\n"
                      f"  Editora: {metadata['publisher']}\n"
                      f"  Ano de Publicação: {metadata['publishedDate']}\n")
            else:
                print(f"Não foi possível encontrar metadados para ISBN: {isbn}")
            
            time.sleep(1)  # Evita sobrecarregar as APIs
        
        return results

    def save_results(self, results, output_file):
        """Salva os resultados em um arquivo JSON."""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

def main():
    extractor = BookMetadataExtractor()
    
    directory_path = input("Digite o caminho do diretório com os PDFs: ")
    include_subdirs = input("Incluir subdiretórios? (s/n): ").strip().lower() == 's'
    
    results = extractor.process_directory(directory_path, include_subdirs)
    
    output_file = "book_metadata_results.json"
    extractor.save_results(results, output_file)
    
    print(f"\nProcessamento concluído. Resultados salvos em: {output_file}")

if __name__ == "__main__":
    main()
