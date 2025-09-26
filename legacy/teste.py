import sys
import os
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog, QTextEdit
from PyQt6.QtCore import Qt
try:
    from pypdf import PdfReader  # type: ignore
except Exception:
    from PyPDF2 import PdfReader  # type: ignore
import re
import unicodedata
import requests

KNOWN_PUBLISHERS = [
    "O'Reilly Media", "Wiley", "Packt Publishing", "No Starch Press", 
    "Apress", "Manning Publications", "Casa do Código", "Addison-Wesley", 
    "Pearson", "McGraw-Hill", "Springer", "MIT Press"
]

class PDFMetadataExtractor(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        self.selectButton = QPushButton('Selecionar PDFs')
        self.selectButton.clicked.connect(self.selectPDFs)
        layout.addWidget(self.selectButton)
        self.resultText = QTextEdit()
        layout.addWidget(self.resultText)
        self.setLayout(layout)
        self.setWindowTitle('Extrator de Metadados de PDF Otimizado')
        self.setGeometry(300, 300, 600, 400)

    def selectPDFs(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Selecionar PDFs", "", "PDF Files (*.pdf)")
        if files:
            for file in files:
                metadata = self.extractMetadata(file)
                validated_metadata = self.validate_with_alternative_services(metadata)
                self.resultText.append(f"Arquivo: {file}")
                for key, value in validated_metadata.items():
                    self.resultText.append(f"{key}: {value}")
                self.resultText.append("\n")

    def extractMetadata(self, pdf_path):
        metadata = {
            'Título': 'N/A',
            'Autor': 'N/A',
            'Ano': 'N/A',
            'ISBN': 'N/A',
            'Editora': 'N/A'
        }
        try:
            with open(pdf_path, 'rb') as file:
                reader = PdfReader(file)
                text = ''
                for i in range(min(20, len(reader.pages))):
                    text += reader.pages[i].extract_text()
                
                text = self.normalize_text(text)

                metadata['Título'] = self.extract_title(text)
                metadata['Autor'] = self.extract_author(text)
                metadata['Ano'] = self.extract_year(text)
                metadata['ISBN'] = self.extract_isbn(text)
                metadata['Editora'] = self.extract_publisher(text)

                self.log(f"Metadados extraídos do PDF: {metadata}")

        except Exception as e:
            self.log(f"Erro ao processar {pdf_path}: {str(e)}")

        return metadata

    def normalize_text(self, text):
        text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII')
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def extract_title(self, text):
        title_patterns = [
            r'^([^\n.]+)',
            r'(?i)title:\s*(.+?)(?:\n|$)',
            r'([A-Z][A-Za-z\s]{10,})',
            r'([A-Z][A-Za-z\s&]+(?:Cookbook|Handbook|Guide|Manual|Performance|Bootcamp))'
        ]
        for pattern in title_patterns:
            match = re.search(pattern, text)
            if match:
                title = match.group(1).strip()
                words = title.split()
                return ' '.join(words[:10]) if len(words) > 10 else title
        return "N/A"

    def extract_author(self, text):
        author_patterns = [
            r'(?i)by\s+((?:[A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+(?:,?\s+(?:and|&)\s+)?){1,3})',
            r'(?i)author[s]?:\s*((?:[A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+(?:,?\s+(?:and|&)\s+)?){1,3})',
            r'([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+)'
        ]
        for pattern in author_patterns:
            match = re.search(pattern, text)
            if match:
                author = match.group(1).strip()
                return re.sub(r'Copyright.*$', '', author).strip()
        return "N/A"

    def extract_year(self, text):
        year_patterns = [
            r'(?i)copyright\s*©?\s*(\d{4})',
            r'(?i)published\s*:?\s*(\d{4})',
            r'\b(20\d{2})\b'
        ]
        for pattern in year_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return "N/A"

    def extract_isbn(self, text):
        isbn_patterns = [
            r'ISBN(?:-13)?:?\s*((?:97[89])?\d{9}[\dx])',
            r'ISBN(?:-13)?:?\s*(\d{3}-\d-\d{3}-\d{5}-\d)',
            r'\b(?:97[89])?\d{9}[\dx]\b',
            r'\b\d{3}-\d-\d{3}-\d{5}-\d\b'
        ]
        for pattern in isbn_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return "N/A"

    def extract_publisher(self, text):
        for publisher in KNOWN_PUBLISHERS:
            if publisher.lower() in text.lower():
                return publisher
        publisher_patterns = [
            r'(?i)Published by\s+([^.]+)',
            r'(?i)Publisher:\s+([^.]+)'
        ]
        for pattern in publisher_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        return "N/A"

    def validate_with_alternative_services(self, metadata):
        services = [
            self.validate_with_open_library,
            self.validate_with_isbndb,
            self.validate_with_google_books
        ]
        
        for service in services:
            updated_metadata = service(metadata)
            if self.is_metadata_improved(metadata, updated_metadata):
                self.log(f"Metadados atualizados com informações de {service.__name__}")
                return updated_metadata
        
        self.log("Nenhum serviço conseguiu melhorar os metadados")
        return metadata

    def validate_with_open_library(self, metadata):
        base_url = "https://openlibrary.org/api/books"
        
        if metadata['ISBN'] != "N/A":
            params = {"bibkeys": f"ISBN:{metadata['ISBN']}", "format": "json", "jscmd": "data"}
        else:
            params = {"title": metadata['Título'], "author": metadata['Autor'], "format": "json", "jscmd": "data"}
        
        try:
            response = requests.get(base_url, params=params)
            if response.status_code == 200:
                data = response.json()
                if data:
                    book_info = next(iter(data.values()))
                    return self.update_metadata_from_open_library(metadata, book_info)
        except Exception as e:
            self.log(f"Erro ao validar com Open Library: {str(e)}")
        
        return metadata

    def validate_with_isbndb(self, metadata):
        # Nota: Este serviço requer uma chave de API
        api_key = "YOUR_ISBNDB_API_KEY"
        base_url = "https://api2.isbndb.com/book/"
        
        if metadata['ISBN'] != "N/A":
            url = f"{base_url}{metadata['ISBN']}"
        else:
            url = f"{base_url}{metadata['Título'].replace(' ', '%20')}"
        
        headers = {"Authorization": api_key}
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                if data.get('book'):
                    return self.update_metadata_from_isbndb(metadata, data['book'])
        except Exception as e:
            self.log(f"Erro ao validar com ISBNdb: {str(e)}")
        
        return metadata

    def validate_with_google_books(self, metadata):
        base_url = "https://www.googleapis.com/books/v1/volumes"
        query = f"intitle:{metadata['Título']}"
        
        if metadata['ISBN'] != "N/A":
            query += f" isbn:{metadata['ISBN']}"
        elif metadata['Autor'] != "N/A":
            query += f" inauthor:{metadata['Autor']}"
        
        params = {
            "q": query,
            "maxResults": 3
        }
        
        try:
            response = requests.get(base_url, params=params)
            if response.status_code == 200:
                data = response.json()
                if data.get('totalItems', 0) > 0:
                    for item in data['items']:
                        book_info = item['volumeInfo']
                        if self.is_valid_match(metadata, book_info):
                            return self.update_metadata_from_google_books(metadata, book_info)
                    self.log("Nenhuma correspondência confiável encontrada no Google Books")
                else:
                    self.log("Nenhum resultado encontrado no Google Books")
            else:
                self.log(f"Erro na chamada à API do Google Books: {response.status_code}")
        except Exception as e:
            self.log(f"Erro ao validar com Google Books: {str(e)}")
        
        return metadata

    def update_metadata_from_open_library(self, metadata, book_info):
        metadata['Título'] = book_info.get('title', metadata['Título'])
        metadata['Autor'] = ', '.join(author['name'] for author in book_info.get('authors', []))
        metadata['Ano'] = book_info.get('publish_date', metadata['Ano'])[:4]
        metadata['Editora'] = book_info.get('publishers', [metadata['Editora']])[0]
        metadata['ISBN'] = book_info.get('isbn_13', [metadata['ISBN']])[0]
        return metadata

    def update_metadata_from_isbndb(self, metadata, book_info):
        metadata['Título'] = book_info.get('title', metadata['Título'])
        metadata['Autor'] = ', '.join(book_info.get('authors', [metadata['Autor']]))
        metadata['Ano'] = book_info.get('date_published', metadata['Ano'])[:4]
        metadata['Editora'] = book_info.get('publisher', metadata['Editora'])
        metadata['ISBN'] = book_info.get('isbn13', metadata['ISBN'])
        return metadata

    def update_metadata_from_google_books(self, metadata, book_info):
        metadata['Título'] = book_info.get('title', metadata['Título'])
        metadata['Autor'] = ', '.join(book_info.get('authors', [metadata['Autor']]))
        metadata['Ano'] = book_info.get('publishedDate', metadata['Ano'])[:4]
        metadata['Editora'] = book_info.get('publisher', metadata['Editora'])
        for identifier in book_info.get('industryIdentifiers', []):
            if identifier['type'] in ['ISBN_13', 'ISBN_10']:
                metadata['ISBN'] = identifier['identifier']
                break
        return metadata

    def is_valid_match(self, metadata, book_info):
        score = 0
        if metadata['Título'].lower() in book_info.get('title', '').lower():
            score += 2
        if metadata['Autor'] != "N/A" and metadata['Autor'] in ', '.join(book_info.get('authors', [])):
            score += 2
        if metadata['ISBN'] != "N/A":
            for identifier in book_info.get('industryIdentifiers', []):
                if metadata['ISBN'] in identifier['identifier']:
                    score += 3
                    break
        return score >= 3

    def is_metadata_improved(self, old_metadata, new_metadata):
        improvements = 0
        for key in old_metadata:
            if old_metadata[key] == "N/A" and new_metadata[key] != "N/A":
                improvements += 1
            elif old_metadata[key] != new_metadata[key] and len(new_metadata[key]) > len(old_metadata[key]):
                improvements += 1
        return improvements > 0

    def log(self, message):
        self.resultText.append(f"LOG: {message}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = PDFMetadataExtractor()
    ex.show()
    sys.exit(app.exec())