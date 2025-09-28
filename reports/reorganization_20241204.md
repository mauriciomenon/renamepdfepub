# Reorganizacao do repositorio (2024-12-04)

Este documento registra a migracao estrutural que prepara o projeto para as proximas refatoracoes sem alterar o comportamento em producao.

## Objetivos

- Promover `renomeia_livro.py` como script principal, substituindo o antigo fluxo `renomeia_livro_renew_v5.py`.
- Manter somente os arquivos necessarios no diretorio raiz, preservando utilitarios antigos em `legacy/`.
- Centralizar arquivos de log em `logs/` e relatorios em `reports/`.
- Documentar a nova organizacao e criar insumos para o proximo ciclo de refatoracao.

## Mudancas aplicadas

- `renomeia_livro_renew_v5.py` foi movido para `legacy/`; o conteudo identico continua disponivel como `renomeia_livro.py`.
- Relatorios avulsos (`book_metadata_report.json`, `metadata_report_dev.json`) foram realocados para `reports/`.
- O `README.md` agora aponta para o script principal e descreve a nova topologia de diretorios.
- Criados `CHANGELOG.md` e `TODO.md` (ver diretorio raiz) para acompanhar melhorias incrementais.
- Preparado o release incremental `v0.9.1` com foco em organizacao de arquivos.

## Proximos passos sugeridos

1. Rodar a suite de testes sempre que novos modulos forem extraidos do monolito `renomeia_livro.py`.
2. Automatizar rotacao e limpeza dos arquivos em `logs/`.
3. Mapear dependencias externas (OCR, poppler, etc.) para geracao de documentacao de setup multiplataforma.

---
Atualizado por GitHub Copilot em 2024-12-04.
