# Release v0.10.0 — Empacotamento do núcleo

## Resumo
Reorganização inicial que transforma os principais utilitários em um pacote Python (`renamepdfepub`), abrindo caminho para modularizar o script monolítico `renomeia_livro.py` sem alterar seu comportamento.

## O que mudou
- Módulos `metadata_cache`, `metadata_enricher`, `metadata_extractor`, `renamer` e `logging_config` foram movidos para `src/renamepdfepub/`.
- Import paths atualizados nos testes e scripts legados; `pytest` passou a resolver módulos via `pythonpath = src`.
- Documentação refinada (`README.md`, `CHANGELOG.md`) descrevendo a nova estrutura.
- Arquivos de log soltos recolhidos em `logs/` para manter o diretório raiz enxuto.

## Como testar
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

## Próximos passos sugeridos
- Extrair classes e funções específicas de `renomeia_livro.py` para módulos dentro do pacote recém-criado.
- Avaliar criação de entry points (`console_scripts`) para distribuir o CLI futuramente.
- Automatizar limpeza/rotação de arquivos em `logs/`.
