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
python3 renomeia_livro.py --help
```

Observações: sem as dependências Python e de sistema instaladas, o script pode falhar na importação (ModuleNotFoundError) ou na execução de OCR/pdf2image.

5. Rodar a suíte de testes:

```bash
pytest -q
```

## Interface gráfica opcional

Para quem prefere uma interface visual simples:

1. Instale as dependências extras:

```bash
pip install PyQt6
```

2. Execute o aplicativo:

```bash
python gui_RenameBook.py
```

A GUI reutiliza o pacote `renamepdfepub` para extrair metadados; bibliotecas opcionais como `pypdf`/`pdfplumber` e `ebooklib` continuam melhorando a precisão da leitura.
As preferências básicas (campos selecionados, modo copiar e limite de caracteres) ficam registradas entre execuções.
O histórico da última execução aparece em um painel dentro da janela, com atalhos para copiar o resultado e abrir rapidamente a pasta processada.
Ao executar `gui_RenameBook.py` diretamente no repositório, o script adiciona automaticamente a pasta `src/` ao `PYTHONPATH`, dispensando a instalação em modo editable (`pip install -e .`).

### Estrutura do projeto

- `renomeia_livro.py`: script principal com a lógica de extração/enriquecimento de metadados e renomeação.
- `gui_RenameBook.py`: interface gráfica em PyQt6 que aproveita o pacote para renomear arquivos interativamente.
- `src/renamepdfepub/`: pacote Python com os módulos reutilizáveis (`metadata_cache`, `metadata_extractor`, `metadata_enricher`, `renamer`, `logging_config`).
- `tests/`: suíte de testes unitários que valida os utilitários do pacote.
- `logs/`: diretório para logs gerados em runtime (mantido vazio no repositório, com `.gitkeep`).
- `legacy/`: scripts antigos e utilitários mantidos apenas para referência histórica.
- `reports/`: relatórios de execução e notas de reorganização.

A maior parte dos utilitários experimentais e relatórios soltos foi movida para `legacy/` e `reports/` para manter o diretório raiz mais limpo. Consulte `reports/reorganization_20241204.md` para um resumo das mudanças. A refatoração atual consolida os módulos reutilizáveis em um pacote `renamepdfepub`, preparando futuras extrações de funcionalidades do script principal.
