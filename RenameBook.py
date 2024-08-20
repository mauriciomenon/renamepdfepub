from PyQt6.QtWidgets import QApplication, QWidget, QFileDialog, QVBoxLayout, QPushButton, QLabel, QCheckBox, QSpinBox, QGridLayout, QMessageBox, QLineEdit
from PyQt6.QtCore import Qt, QDir
from PyQt6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDropEvent
import requests
import sys
import os
import shutil
import PyPDF2
from ebooklib import epub

class FileRenamer(QWidget):
    def __init__(self):
        super().__init__()

        grid = QGridLayout()

        self.field_counter = {}
        self.check_boxes = {}
        self.selected_files = []
        self.info = {}

        self.key_to_display = {
            'Year': 'Ano',
            'ISBN': 'ISBN',
            'Author': 'Autor',
            'Publisher': 'Editora',
            'Title': 'Título'
        }

        self.label = QLabel("Selecione um arquivo (PDF/EPUB) para renomear.")
        self.label.setWordWrap(True)
        grid.addWidget(self.label, 0, 0, 1, 3)

        btn = QPushButton("Selecionar Arquivo(s)")
        btn.clicked.connect(self.openFileNameDialog)
        grid.addWidget(btn, 1, 0)

        self.copy_check = QCheckBox("Copiar - Manter original inalterado")
        grid.addWidget(self.copy_check, 1, 1)

        self.confirm_btn = QPushButton("Confirmar")
        self.confirm_btn.setEnabled(False)
        self.confirm_btn.clicked.connect(self.executeRenaming)
        grid.addWidget(self.confirm_btn, 8, 0, 1, 3)

        grid.setRowMinimumHeight(0, 65)

        self.setLayout(grid)

        self.setGeometry(100, 100, 400, 250)
        self.setAcceptDrops(True)

        self.dropArea = QLabel("Arraste e solte arquivos aqui.")
        self.dropArea.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.dropArea.setStyleSheet("border: 2px solid gray")
        grid.addWidget(self.dropArea, 2, 0, 1, 3)
        
        self.info_boxes = {}  # Dicionário para guardar os QLineEdit
        self.create_check_boxes(grid, ['Year', 'ISBN', 'Author', 'Publisher', 'Title'])

    def create_check_boxes(self, grid, fields):
        for i, field in enumerate(fields):
            check = QCheckBox(self.key_to_display[field])
            check.stateChanged.connect(self.updatePreview)
            self.check_boxes[field] = check
            grid.addWidget(check, i + 3, 0)

            info_box = QLineEdit("Info será mostrada aqui")  # QLineEdit para mostrar as informações
            info_box.setEnabled(False)
            self.info_boxes[field] = info_box
            grid.addWidget(info_box, i + 3, 1)  # Adiciona ao mesmo row do checkbox, mas na coluna 1
            
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dragLeaveEvent(self, event: QDragLeaveEvent):
        self.dropArea.clear()

    def dropEvent(self, event: QDropEvent):
        file_paths = []
        for url in event.mimeData().urls():
            file_paths.append(str(QDir.toNativeSeparators(url.toLocalFile())))
        self.selected_files = file_paths
        self.label.setText("Arquivo(s) selecionado(s) via arrastar e soltar: " + ", ".join(file_paths))
        self.confirm_btn.setEnabled(True)
        self.updatePreview()

    def openFileNameDialog(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Selecione um ou mais arquivos", "", "PDF Files (*.pdf);;EPUB Files (*.epub)")
        if files:
            self.selected_files = files
            self.label.setText("Arquivo(s) selecionado(s): " + ", ".join(files))
            self.confirm_btn.setEnabled(True)
            self.updatePreview()

    def updatePreview(self):
        if self.selected_files:
            first_file = self.selected_files[0]
            ext = os.path.splitext(first_file)[1]
            if ext == '.pdf':
                self.info = self.extract_info_from_pdf(first_file)  # Atualizando self.info
            elif ext == '.epub':
                self.info = self.extract_info_from_epub(first_file)  # Atualizando self.info
            else:
                self.info = {}

            if self.info.get('ISBN', 'Unknown') != 'Unknown':
                google_info = self.get_info_from_google_books(self.info['ISBN'])
                self.info.update(google_info)
            elif self.info.get('Title', 'Unknown') != 'Unknown':
                google_info = self.get_info_from_google_books(self.info['Title'])
                self.info.update(google_info)

            # Preenche os QLineEdit com as informações
            for field, box in self.info_boxes.items():
                box.setText(self.info.get(field, 'Não disponível'))  # Utilizando self.info

    def executeRenaming(self):
        if not self.selected_files:
            return

        for selected_file in self.selected_files:
            ext = os.path.splitext(selected_file)[1]
            if ext == '.pdf':
                info = self.extract_info_from_pdf(selected_file)
            elif ext == '.epub':
                info = self.extract_info_from_epub(selected_file)
            else:
                info = {}

            if info.get('ISBN', 'Unknown') != 'Unknown':
                google_info = self.get_info_from_google_books(info['ISBN'])
                info.update(google_info)
            elif info.get('Title', 'Unknown') != 'Unknown':
                google_info = self.get_info_from_google_books(info['Title'])
                info.update(google_info)

            new_file_name = self.generateNewName(info)
            new_file_path = os.path.join(os.path.dirname(selected_file), new_file_name + ext)
            if self.copy_check.isChecked():
                shutil.copy(selected_file, new_file_path)
            else:
                os.rename(selected_file, new_file_path)
        
        self.confirm_btn.setEnabled(False)
        self.selected_files = []
        self.label.setText("Renomeação concluída.")

    def generateNewName(self, info):
        sorted_keys = sorted(self.check_boxes.keys(), key=lambda x: self.order_spinboxes[x].value())
        elements = [info.get(key, 'Unknown') for key in sorted_keys if self.check_boxes[key].isChecked()]
        return '_'.join(elements)

    def extract_info_from_pdf(self, pdf_path):
        info = {'ISBN': 'Unknown', 'Title': 'Unknown', 'Year': 'Unknown',
            'Publisher': 'Unknown', 'Author': 'Unknown'}
        
        # Simulação de extração de dados do PDF
        try:
            with open(pdf_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                # Extração básica para simulação
                info['Title'] = reader.getDocumentInfo().title if reader.getDocumentInfo().title else 'Unknown'
                info['Author'] = reader.getDocumentInfo().author if reader.getDocumentInfo().author else 'Unknown'
                info['Year'] = reader.getDocumentInfo().subject if reader.getDocumentInfo().subject else 'Unknown'
                info['ISBN'] = '1234567890123'  # Exemplo estático
        except Exception as e:
            print(f"Ocorreu um erro ao ler o PDF: {e}")

        return info

    def extract_info_from_epub(self, epub_path):
        book = epub.read_epub(epub_path)
        return {
            'Year': str(book.get_metadata('DC', 'date')[0])[:4] if book.get_metadata('DC', 'date') else 'Unknown',
            'ISBN': str(book.get_metadata('DC', 'identifier')[0]) if book.get_metadata('DC', 'identifier') else 'Unknown',
            'Author': ', '.join([str(author) for author in book.get_metadata('DC', 'creator')]) if book.get_metadata('DC', 'creator') else 'Unknown',
            'Publisher': str(book.get_metadata('DC', 'publisher')[0]) if book.get_metadata('DC', 'publisher') else 'Unknown',
            'Title': str(book.get_metadata('DC', 'title')[0]) if book.get_metadata('DC', 'title') else 'Unknown'
        }

    def get_info_from_google_books(self, identifier):
        # Consultar a API do Google Books sem chave de API
        if identifier.isdigit():
            url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{identifier}"
        else:
            url = f"https://www.googleapis.com/books/v1/volumes?q=intitle:{identifier}"

        response = requests.get(url)
        book_info = response.json()

        info = {
            'Title': 'Unknown',
            'Author': 'Unknown',
            'Publisher': 'Unknown',
            'Year': 'Unknown'
        }

        if 'items' in book_info:
            volume_info = book_info['items'][0]['volumeInfo']
            info['Title'] = volume_info.get('title', 'Unknown')
            info['Author'] = ', '.join(volume_info.get('authors', ['Unknown']))
            info['Publisher'] = volume_info.get('publisher', 'Unknown')
            info['Year'] = volume_info.get('publishedDate', 'Unknown')[:4]

        return info


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    fr = FileRenamer()
    fr.show()
    sys.exit(app.exec())
