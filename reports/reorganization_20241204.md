# Reorganização do repositório (2024-12-04)

Este documento registra a migração estrutural que prepara o projeto para as próximas refatorações sem alterar o comportamento em produção.

## Objetivos

- Promover `renomeia_livro.py` como script principal, substituindo o antigo fluxo `renomeia_livro_renew_v5.py`.
- Manter somente os arquivos necessários no diretório raiz, preservando utilitários antigos em `legacy/`.
- Centralizar arquivos de log em `logs/` e relatórios em `reports/`.
- Documentar a nova organização e criar insumos para o próximo ciclo de refatoração.

## Mudanças aplicadas

- `renomeia_livro_renew_v5.py` foi movido para `legacy/`; o conteúdo idêntico continua disponível como `renomeia_livro.py`.
- Relatórios avulsos (`book_metadata_report.json`, `metadata_report_dev.json`) foram realocados para `reports/`.
- O `README.md` agora aponta para o script principal e descreve a nova topologia de diretórios.
- Criados `CHANGELOG.md` e `TODO.md` (ver diretório raiz) para acompanhar melhorias incrementais.
- Preparado o release incremental `v0.9.1` com foco em organização de arquivos.

## Próximos passos sugeridos

1. Rodar a suíte de testes sempre que novos módulos forem extraídos do monolito `renomeia_livro.py`.
2. Automatizar rotação e limpeza dos arquivos em `logs/`.
3. Mapear dependências externas (OCR, poppler, etc.) para geração de documentação de setup multiplataforma.

---
Atualizado por GitHub Copilot em 2024-12-04.
