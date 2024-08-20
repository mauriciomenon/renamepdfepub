import pdfplumber
import re
from PyQt6.QtWidgets import QApplication, QWidget, QFileDialog, QVBoxLayout, QPushButton, QLabel, QCheckBox, QGridLayout, QLineEdit
from PyQt6.QtCore import Qt, QDir
import os
import shutil

class FileRenamer(QWidget):
    def __init__(self):
        super().__init__()

        grid = QGridLayout()

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

        self.info_boxes = {}  
        self.create_check_boxes(grid, ['Year', 'ISBN', 'Author', 'Publisher', 'Title'])

    def create_check_boxes(self, grid, fields):
        for i, field in enumerate(fields):
            check = QCheckBox(self.key_to_display[field])
            check.stateChanged.connect(self.updatePreview)
            grid.addWidget(check, i + 3, 0)

            info_box = QLineEdit("Info será mostrada aqui")
            info_box.setEnabled(False)
            self.info_boxes[field] = info_box
            grid.addWidget(info_box, i + 3, 1)

    def openFileNameDialog(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Selecione um ou mais arquivos", "", "PDF Files (*.pdf)")
        if files:
            self.selected_files = files
            self.label.setText("Arquivo(s) selecionado(s): " + ", ".join(files))
            self.confirm_btn.setEnabled(True)
            self.updatePreview()

    def updatePreview(self):
        if self.selected_files:
            first_file = self.selected_files[0]
            self.info = self.extract_info_from_pdf(first_file)

            for field, box in self.info_boxes.items():
                box.setText(self.info.get(field, 'Não disponível'))

    def executeRenaming(self):
        if not self.selected_files:
            return

        for selected_file in self.selected_files:
            info = self.extract_info_from_pdf(selected_file)
            new_file_name = self.generateNewName(info)
            new_file_path = os.path.join(os.path.dirname(selected_file), new_file_name + '.pdf')
            if self.copy_check.isChecked():
                shutil.copy(selected_file, new_file_path)
            else:
                os.rename(selected_file, new_file_path)

        self.confirm_btn.setEnabled(False)
        self.selected_files = []
        self.label.setText("Renomeação concluída.")

    def generateNewName(self, info):
        elements = [info.get(key, 'Unknown') for key in ['Title', 'Author', 'Year', 'ISBN']]
        return '_'.join(elements)

    def extract_info_from_pdf(self, pdf_path):
        info = {'ISBN': 'Unknown', 'Title': 'Unknown', 'Year': 'Unknown',
                'Publisher': 'Unknown', 'Author': 'Unknown'}

        try:
            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages[:7]):  # Analisa as 7 primeiras páginas
                    text = page.extract_text()
                    if text:
                        # Captura do ISBN
                        isbn_match = re.search(r'ISBN(?:-13)?:?\s?(\d{3}-\d{1,5}-\d{1,7}-\d{1,7}-\d{1})', text)
                        if isbn_match:
                            info['ISBN'] = isbn_match.group(1)

                        # Captura do título
                        title_match = re.search(r'^(.*?)(?:\n|$)', text)
                        if title_match and len(title_match.group(1)) > 5:
                            info['Title'] = title_match.group(1).strip()

                        # Captura do autor
                        author_match = re.search(r'by\s([A-Za-z\s]+)', text)
                        if author_match:
                            info['Author'] = author_match.group(1).strip()

                        # Captura da editora
                        publisher_match = re.search(r'Published by\s(.+?)(?:\n|$)', text)
                        if publisher_match:
                            info['Publisher'] = publisher_match.group(1).strip()

                        # Captura do ano
                        year_match = re.search(r'(\b\d{4}\b)', text)
                        if year_match:
                            info['Year'] = year_match.group(1)

        except Exception as e:
            print(f"Erro ao processar o PDF: {e}")

        return info


if __name__ == '__main__':
    app = QApplication([])
    window = FileRenamer()
    window.show()
    app.exec()
