from PyQt6.QtWidgets import QApplication, QWidget, QFileDialog, QVBoxLayout, QPushButton, QLabel, QCheckBox, QSpinBox, QGridLayout, QMessageBox, QLineEdit
from PyQt6.QtCore import Qt, QDir
from PyQt6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDropEvent
from functools import partial
import sys
import os
import re
import itertools
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
            preview_text = ', '.join([f"{self.key_to_display[k]}: {v}" for k, v in self.info.items()])
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

    def handleAutoNumbering(self, state, field, spinbox):
        if state == Qt.CheckState.Checked:
            spinbox.setEnabled(True)
            self.field_counter[field] = self.counter
            spinbox.setValue(self.counter)
            self.counter += 1
        else:
            spinbox.setEnabled(False)
            self.counter = min(self.field_counter.values())
            for key, value in self.field_counter.items():
                if self.field_counter[key] > self.field_counter[field]:
                    self.order_spinboxes[key].setValue(value - 1)
                    self.field_counter[key] -= 1
            del self.field_counter[field]
        
    def extract_info_from_pdf(self, pdf_path):
        info = {'ISBN': 'Unknown', 'Title': 'Unknown', 'Year': 'Unknown', 'Publisher': 'Unknown', 'Author': 'Unknown'}
        try:
            with open(pdf_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                total_pages = len(reader.pages)
                text_page_2 = reader.pages[1].extract_text()
                text_page_3 = reader.pages[2].extract_text()
                text_page_4 = reader.pages[3].extract_text()
                
                # Primeira Parte: Abordagem mais específica
                # 1A  Extração por regex Packt
                name = re.search(r'(.+?)\n', text_page_2)
                isbn = re.search(r'ISBN (\d{3}-\d{1,5}-\d{1,7}-\d{1,7}-\d{1})', text_page_3)
                year = re.search(r'Copyright \u00A9 (\d{4})', text_page_3)
                publisher = re.search(r'Published by (.+?)\n', text_page_3)
                author = re.search(r'([^\n]+)\nBIRMINGHAM - MUMBAI', text_page_2)
                info['Title'] = name.group(1) if name else 'Unknown'
                info['ISBN'] = isbn.group(1) if isbn else 'Unknown'
                info['Year'] = year.group(1) if year else 'Unknown'
                info['Publisher'] = publisher.group(1) if publisher else 'Unknown'
                info['Author'] = author.group(1) if author else 'Unknown'
                
                if info['Publisher'] == 'Packt Publishing Ltd.':
                    return info
                
                # Lógica para a editora O'Reilly (método 1b)
                name = re.search(r'^([^\n]+)', text_page_4)
                print(f"nome: {name}")
                isbn = re.search(r'ISBN[:\s-]*?(\d{3}-\d{1,5}-\d{1,7}-\d{1,7}-\d{1})', text_page_4)
                print(f"isbn: {isbn}")
                year = re.search(r'Copyright \u00A9 (\d{4})', text_page_4)
                print(f"ano: {year}")
                publisher = re.search(r'published by ([\w\s’]+) Media,', text_page_4, re.IGNORECASE)
                print(f"editora: {publisher}")
                author = re.search(r'\b\d{4}\b\s+([\w\s]+)[.,]', text_page_4)
                print(f"author: {author}")
                info['Title'] = name.group(1) if name else 'Unknown'
                info['ISBN'] = isbn.group(1) if isbn else 'Unknown'
                info['Year'] = year.group(1) if year else 'Unknown'
                info['Publisher'] = publisher.group(1) if publisher else 'Unknown'
                info['Author'] = author.group(1) if author else 'Unknown'
                
                
                
                
                
                
                    
        except Exception as e:
            self.label.setText(f"Erro ao processar o PDF: {e}")

        return info
    
                # Segunda Parte: Abordagem mais genérica
                # for i in itertools.chain(range(min(3, total_pages)), range(-2, 0, 1)):  # 5 primeiras e 3 últimas páginas
                #    page = reader.pages[i]
                #    text = page.extract_text()
                #    # Busca por autor
                #    if info['Author'] == 'Unknown':
                #        author_match = re.search(r'(?:[Aa]uthor|Written\sby|By)[:\s]*([^\n\r]+)', text)
                #        if author_match:
                #            info['Author'] = author_match.group(1).strip()

                # Terceira Parte: busca por dados no próprio arquivo (similar ao que foi feito anteriormente)
                # metadata = reader.getDocumentInfo()
                # if metadata:
                #    info['Title'] = metadata.get('/Title', info['Title'])
                #    info['Author'] = metadata.get('/Author', info['Author'])
                #    info['Year'] = metadata.get('/CreationDate', info['Year'])[:4]
                #    info['Publisher'] = metadata.get('/Producer', info['Publisher'])

    def extract_info_from_epub(self, epub_path):
        book = epub.read_epub(epub_path)
        return {
            'Year': str(book.get_metadata('DC', 'date')[0])[:4] if book.get_metadata('DC', 'date') else 'Unknown',
            'ISBN': str(book.get_metadata('DC', 'identifier')[0]) if book.get_metadata('DC', 'identifier') else 'Unknown',
            'Author': ', '.join([str(author) for author in book.get_metadata('DC', 'creator')]) if book.get_metadata('DC', 'creator') else 'Unknown',
            'Publisher': str(book.get_metadata('DC', 'publisher')[0]) if book.get_metadata('DC', 'publisher') else 'Unknown',
            'Title': str(book.get_metadata('DC', 'title')[0]) if book.get_metadata('DC', 'title') else 'Unknown'
        }

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    fr = FileRenamer()
    fr.show()
    sys.exit(app.exec())
