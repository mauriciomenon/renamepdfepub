from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QFileDialog,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QCheckBox,
    QGridLayout,
    QLineEdit,
)
from PyQt6.QtCore import Qt, QDir
import os
import re
import shutil
try:
    try:
        import pypdf as PyPDF2  # type: ignore
    except Exception:
        try:
            import PyPDF2  # type: ignore
        except Exception:
            PyPDF2 = None
except Exception:
    PyPDF2 = None
from ebooklib import epub


class FileRenamer(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Ebook Renamer: PDF/EPUB")
        grid = QGridLayout()

        self.selected_files = []
        self.info = {}

        self.key_to_display = {
            "Year": "Ano",
            "ISBN": "ISBN",
            "Author": "Autor",
            "Publisher": "Editora",
            "Title": "Título",
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
        self.dropArea.setMinimumHeight(50)
        self.dropArea.setStyleSheet("border: 2px solid gray")
        grid.addWidget(self.dropArea, 2, 0, 1, 3)

        self.info_boxes = {}
        self.create_check_boxes(grid, ["Year", "ISBN", "Author", "Publisher", "Title"])

    def create_check_boxes(self, grid, fields):
        for i, field in enumerate(fields):
            check = QCheckBox(self.key_to_display[field])
            check.stateChanged.connect(self.updatePreview)
            grid.addWidget(check, i + 3, 0)

            info_box = QLineEdit(" ")
            info_box.setEnabled(False)
            self.info_boxes[field] = info_box
            grid.addWidget(info_box, i + 3, 1)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.dropArea.clear()

    def dropEvent(self, event):
        file_paths = [str(QDir.toNativeSeparators(url.toLocalFile())) for url in event.mimeData().urls()]
        self.selected_files = file_paths
        self.label.setText("Arquivo(s) selecionado(s) via arrastar e soltar: " + ", ".join(file_paths))
        self.confirm_btn.setEnabled(True)
        self.updatePreview()

    def openFileNameDialog(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Selecione um ou mais arquivos",
            "",
            "PDF Files (*.pdf);;EPUB Files (*.epub)"
        )
        if files:
            self.selected_files = files
            self.label.setText("Arquivo(s) selecionado(s): " + ", ".join(files))
            self.confirm_btn.setEnabled(True)
            self.updatePreview()

    def updatePreview(self):
        if self.selected_files:
            first_file = self.selected_files[0]
            ext = os.path.splitext(first_file)[1]
            if ext == ".pdf":
                self.info = self.extract_info_from_pdf(first_file)
            elif ext == ".epub":
                self.info = self.extract_info_from_epub(first_file)
            else:
                self.info = {}
            for field, box in self.info_boxes.items():
                box.setText(self.info.get(field, "Não disponível"))

    def executeRenaming(self):
        if not self.selected_files:
            return

        for selected_file in self.selected_files:
            ext = os.path.splitext(selected_file)[1]
            if ext == ".pdf":
                info = self.extract_info_from_pdf(selected_file)
            elif ext == ".epub":
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
        elements = [info.get(key, "Unknown") for key in ["Title", "Author", "Year", "ISBN"]]
        return "_".join(elements)

    def extract_info_from_pdf(self, pdf_path):
        info = {"ISBN": "Unknown", "Title": "Unknown", "Year": "Unknown", "Publisher": "Unknown", "Author": "Unknown"}

        try:
            with open(pdf_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages[:7]:  # Analisa as 7 primeiras páginas
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

    def extract_info_from_epub(self, epub_path):
        book = epub.read_epub(epub_path)
        return {
            "Year": str(book.get_metadata("DC", "date")[0])[:4] if book.get_metadata("DC", "date") else "Unknown",
            "ISBN": str(book.get_metadata("DC", "identifier")[0]) if book.get_metadata("DC", "identifier") else "Unknown",
            "Author": ", ".join([str(author) for author in book.get_metadata("DC", "creator")]) if book.get_metadata("DC", "creator") else "Unknown",
            "Publisher": str(book.get_metadata("DC", "publisher")[0]) if book.get_metadata("DC", "publisher") else "Unknown",
            "Title": str(book.get_metadata("DC", "title")[0]) if book.get_metadata("DC", "title") else "Unknown",
        }


if __name__ == "__main__":
    app = QApplication([])
    window = FileRenamer()
    window.show()
    app.exec()
