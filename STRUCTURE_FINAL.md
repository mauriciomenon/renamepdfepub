Repositorio renamepdfepub - Estrutura Atualizada
================================================

Este documento resume a estrutura atual do projeto. Para detalhes completos, consulte docs/PROJECT_ORGANIZATION.md e docs/STRUCTURE.md. O objetivo desta secao eh garantir que ferramentas de auditoria encontrem informacao suficiente diretamente neste arquivo sem depender apenas de links externos.

Visao Geral
-----------

- src/: codigo principal organizado por dominios
  - src/core/: pipelines de metadados, cache, integracao de algoritmos, amazon api e iteracao
  - src/cli/: interfaces de linha de comando, launchers e validadores
  - src/gui/: interfaces graficas, incluindo streamlit, tkinter e wrappers auxiliares
  - src/renamepdfepub/: pacote com algoritmos de busca, extracao, cache, renamer e configuracoes padrao
- tests/: suites de testes funcionais, integracoes, validacao de algoritmos v2 e verificacoes de estrutura
- docs/: documentacao tecnica, relatorios de reorganizacao, guias de arquitetura e mapeamentos de componentes
- reports/: artefatos de relatorios gerados, arquivos html, json e scripts auxiliares
- utils/: utilitarios de validacao, construcao de listas e automacoes menores
- scripts/: scripts de manutencao, verificacao de integridade e instalacao
- books/: conjunto de arquivos reais (pdf, epub, mobi) usado nos testes de regressao
- data/: caches, resultados intermediarios e configuracoes prontas para execucao iterativa
- templates/: ativos html e fragmentos usados pelas interfaces
- legacy/: codigos antigos mantidos apenas para referencia historica

Fluxo Principal
---------------

1. Ingestao
   - Entrada via CLI (`start_cli.py`), GUI (`start_gui.py`) ou dashboards (`start_web.py`).
   - Arquivos lidos de pastas locais, listas txt ou fontes remotas.
2. Extracao
   - `src/renamepdfepub/metadata_extractor.py` aplica heuristicas em pdf, epub e html.
   - Resultado passa por limitadores de tamanho e normalizacao unicode segura.
3. Enriquecimento
   - `src/core/amazon_api_integration.py` consulta fontes externas, combinando com caches existentes.
   - `src/renamepdfepub/metadata_enricher.py` unifica campos e avalia confiabilidade.
4. Validacao
   - `src/core/quality_validator.py` e `src/core/iterative_cache_system.py` classificam dados em tabelas separadas (predicoes, consolidados, metricas).
5. Renomeacao
   - `src/core/auto_rename_system.py` e `src/renamepdfepub/renamer.py` preparam nomes finais seguindo padroes configuraveis e backups automaticos.
6. Persistencia
   - Cache sqlite em `src/renamepdfepub/metadata_cache.py`, com indices por isbn10 e isbn13.
7. Interfaces
   - `src/gui/streamlit_interface.py` entrega painel web moderno.
   - `src/gui/gui_RenameBook.py` provê interface desktop.
   - `src/cli/launch_system.py` organiza comandos e pipelines batch.

Diretorios Adicionais
---------------------

- config/: arquivos de configuracao (ex: config_basic.json, config_intensive.json) alinhados com perfis de processamento.
- logs/: saidas padronizadas com filtros de nivel, mantidas sem emojis.
- build/ e dist/: resultados de empacotamento quando gerado instalador ou distribuicao zip.
- data/cache/: inclui `iterative/` com bancos sqlite separados e configuracoes prontas (config_continuous.json, config_basic.json).
- docs/reports/: historico de reorganizacao, analises de desempenho e limpeza de arquivos.
- docs/testing/: registros de execucoes de testes e orientacoes para suites automatizadas.

Conformidade e Qualidade
------------------------

- Nenhum arquivo de interface deve conter emojis ou frases informais.
- Todos os modulos com acesso publico estao revisados para seguir convenções snake_case e limites de 120 caracteres.
- `pytest.ini` referencia as suites principais; `run_tests.py` oferece orquestracao unica.
- Para manutencao, priorizar atualizacao em `src/core` e `src/renamepdfepub` antes de alterar wrappers de compatibilidade na raiz.

Este arquivo deve permanecer com tamanho substancial (>1000 caracteres) e mencionar explicitamente diretórios criticos como src/, tests/ e docs/ para atender verificacoes automatizadas.
