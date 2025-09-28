# Release v0.9.1 Reorganizacao de diretorios

## Resumo
Organizacao incremental que promove `renomeia_livro.py` como script principal e separa artefatos legados em diretorios dedicados, preparando o terreno para refatoracoes futuras sem alterar o comportamento atual.

## Por que
- Evitar confusao entre multiplas versoes do script principal.
- Reduzir ruido no diretorio raiz e facilitar a descoberta de arquivos relevantes.
- Centralizar logs e relatorios em locais previsiveis.

## O que mudou
- `renomeia_livro_renew_v5.py` arquivado em `legacy`; `renomeia_livro.py` mantem o mesmo conteudo para continuidade operacional.
- Relatorios JSON soltos movidos para `reports`.
- Nova documentacao (`CHANGELOG.md`, `TODO.md`, `reportsreorganization_20241204.md`) descrevendo a reorganizacao e proximos passos.
- `README.md` atualizado com a nova estrutura.

## Validacao
- Estrutura de diretorios revisada manualmente.
- Suite de testes (`pytest -q`) executada apos a reorganizacao.

## Follow-up
- Refatorar gradualmente `renomeia_livro.py` em componentes menores com cobertura de testes.
- Automatizar limpeza dos diretorios `logs` e `reports`.
