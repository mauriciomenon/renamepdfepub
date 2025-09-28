# Release v0.10.0 Empacotamento do nucleo

## Resumo
Reorganizacao inicial que transforma os principais utilitarios em um pacote Python (`renamepdfepub`), abrindo caminho para modularizar o script monolitico `renomeia_livro.py` sem alterar seu comportamento.

## O que mudou
- Modulos `metadata_cache`, `metadata_enricher`, `metadata_extractor`, `renamer` e `logging_config` foram movidos para `srcrenamepdfepub`.
- Import paths atualizados nos testes e scripts legados; `pytest` passou a resolver modulos via `pythonpath = src`.
- Documentacao refinada (`README.md`, `CHANGELOG.md`) descrevendo a nova estrutura.
- Arquivos de log soltos recolhidos em `logs` para manter o diretorio raiz enxuto.

## Como testar
```bash
python3 -m venv .venv
source .venvbinactivate
pip install -r requirements.txt
pytest -q
```

## Proximos passos sugeridos
- Extrair classes e funcoes especificas de `renomeia_livro.py` para modulos dentro do pacote recem-criado.
- Avaliar criacao de entry points (`console_scripts`) para distribuir o CLI futuramente.
- Automatizar limpezarotacao de arquivos em `logs`.
