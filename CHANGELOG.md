# Changelog

## [0.10.0] - 2024-12-05

### Reestruturação
- Consolidado `metadata_cache`, `metadata_extractor`, `metadata_enricher`, `renamer` e `logging_config` em um pacote `src/renamepdfepub/`.
- Ajustados imports dos testes e do código legado para utilizarem o pacote.
- Atualizado `pytest.ini` para expor `src/` no `PYTHONPATH`.
- Movidos arquivos de log residuais para `logs/` e detalhada a nova topologia no `README.md`.

### Infraestrutura
- Preparado terreno para decompor o monolito `renomeia_livro.py` em módulos menores em etapas futuras.

## [0.9.1] - 2024-12-04

### Organizações
- `renomeia_livro.py` passa a ser o script principal; `renomeia_livro_renew_v5.py` foi arquivado em `legacy/`.
- Arquivos de relatório isolados foram movidos para `reports/`.
- Diretórios `legacy/`, `logs/` e `reports/` documentados no `README.md`.
- Novos arquivos `CHANGELOG.md` e `TODO.md` criados para acompanhar evoluções.

### Infraestrutura
- Estrutura preparada para futuras refatorações sem alterar o fluxo atual de renomeação.

---
Entradas anteriores podem ser consultadas em `RELEASE_NOTES_v0.9.md`.
