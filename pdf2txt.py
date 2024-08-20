from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QFileDialog,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QMessageBox,
)
from PyQt6.QtCore import Qt, QDir
from functools import partial
import sys
import os
import PyPDF2

MAX_FILE_SIZE_MB = 150  # Limite de tamanho de arquivo em MB
MAX_PAGES = 1000  # Limite de número de páginas

class PDFToTextOrRTFConverter(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("PDF to Text/RTF Converter")
        layout = QVBoxLayout()

        self.label = QLabel("Selecione um arquivo PDF para converter.")
        self.label.setWordWrap(True)
        layout.addWidget(self.label)

        self.select_btn = QPushButton("Selecionar Arquivo PDF")
        self.select_btn.clicked.connect(self.openFileNameDialog)
        layout.addWidget(self.select_btn)

        self.convert_btn = QPushButton("Converter para TXT")
        self.convert_btn.setEnabled(False)
        self.convert_btn.clicked.connect(partial(self.convertFile, 'txt'))
        layout.addWidget(self.convert_btn)

        self.convert_btn_rtf = QPushButton("Converter para RTF")
        self.convert_btn_rtf.setEnabled(False)
        self.convert_btn_rtf.clicked.connect(partial(self.convertFile, 'rtf'))
        layout.addWidget(self.convert_btn_rtf)

        self.setLayout(layout)
        self.setGeometry(100, 100, 400, 200)
        
    def openFileNameDialog(self):
        file, _ = QFileDialog.getOpenFileName(
            self,
            "Selecione um arquivo PDF",
            "",
            "PDF Files (*.pdf)"
        )
        if file:
            if self.is_file_too_large(file):
                QMessageBox.warning(self, "Erro", f"O arquivo selecionado é muito grande. O tamanho máximo permitido é {MAX_FILE_SIZE_MB} MB.")
                return

            self.selected_file = file
            self.label.setText(f"Arquivo selecionado: {file}")
            self.convert_btn.setEnabled(True)
            self.convert_btn_rtf.setEnabled(True)

    def is_file_too_large(self, file_path):
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        return file_size_mb > MAX_FILE_SIZE_MB

    def convertFile(self, output_format):
        if not hasattr(self, 'selected_file'):
            QMessageBox.warning(self, "Erro", "Nenhum arquivo selecionado.")
            return

        try:
            with open(self.selected_file, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                if len(reader.pages) > MAX_PAGES:
                    QMessageBox.warning(self, "Erro", f"O arquivo selecionado tem muitas páginas. O número máximo permitido é {MAX_PAGES}.")
                    return
                
                text_content = ""
                for page in reader.pages[:MAX_PAGES]:
                    text_content += page.extract_text()
            
            output_file = os.path.splitext(self.selected_file)[0] + f".{output_format}"
            
            if output_format == 'txt':
                with open(output_file, "w", encoding="utf-8") as out_f:
                    out_f.write(text_content)
            elif output_format == 'rtf':
                self.save_rtf(text_content, output_file)

            QMessageBox.information(self, "Sucesso", f"Arquivo convertido para {output_format.upper()} com sucesso.\nSalvo em: {output_file}")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao converter o arquivo: {str(e)}")

    def save_rtf(self, text_content, output_file):
        try:
            rtf_content = (
                r"{\rtf1\ansi\deff0"
                r"{\fonttbl{\f0 Courier;}}"
                r"\viewkind4\uc1\pard\f0\fs20"
                + text_content.replace('\n', r'\par ').encode('latin-1', 'replace').decode('latin-1') +
                r"}"
            )

            with open(output_file, 'w', encoding='latin-1') as out_f:
                out_f.write(rtf_content)
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao salvar o arquivo RTF: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    converter = PDFToTextOrRTFConverter()
    converter.show()
    sys.exit(app.exec())
