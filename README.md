# renamepdfepub
This repository contains tools to extract metadata from ebooks (PDF/EPUB), enrich it and rename files.

Note: legacy/ad-hoc scripts have been moved into the `legacy/` folder. Linters exclude that folder by default.
# renamepdfepub
codigo para renomear meus livros comprados, a maioria da o'reilly e packt. Trabalhando em adaptar para outras editoras, além de tornar o codigo mais genérico.

## Setup rápido

1. Recomendo criar um virtualenv e ativá-lo:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Instalar dependências Python:

```bash
pip install -r requirements.txt
```

3. Instalar dependências de sistema (exemplos para Debian/Ubuntu):

```bash
sudo apt update
sudo apt install -y poppler-utils tesseract-ocr libtesseract-dev
```

4. Executar o analisador principal (exemplo):

```bash
python3 renomeia_livro_renew_v5.py --help
```

Observações: sem as dependências Python e de sistema instaladas, o script pode falhar na importação (ModuleNotFoundError) ou na execução de OCR/pdf2image.
