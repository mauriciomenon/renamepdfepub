# Changelog

## [Unreleased] - 2025-09-29

### Destaques
- Operacoes principais consolidadas: scan (somente varredura), scan-cycles (por ciclos/tempo), rename-existing (a partir de JSON), rename-search (busca + renomeacao).
- Interface Streamlit refinada: Dashboard lendo relatorios reais, varredura pela barra lateral (recursivo/threads), filtros e paginacao na lista, mensagens ASCII-only, sem emojis ou claims estaticos.
- GUI Desktop aprimorada: ASCII-only, botao "Gerar relatorio da pasta" (com "Recursivo"), suporte a `start_gui.py --dir` para pasta inicial, validacoes e fallback de metadados mais robustos.
- Web Launcher claro e util: menu com "scan de pasta"; "Gerar Relatorio HTML" aceita JSON especifico ou o ultimo JSON; mensagens em ASCII-only.

### CLI
- `start_cli.py` adiciona comandos:
  - `scan` (gera JSON/HTML em `reports/`, nao renomeia por padrao)
  - `scan-cycles` (`--cycles N` ou `--time-seconds S`)
  - `rename-existing` (usa `--report relatorio.json`, `--apply`, `--copy`)
  - `rename-search` (executa scan e renomeia no mesmo fluxo)

### Streamlit
- Novo Dashboard lendo `reports/metadata_report_*.json`.
- Barra lateral: pasta configuravel, scan recursivo, controle de threads.
- Lista de livros com filtro por nome/extensao e paginacao.
- Removidos emojis e claims estaticos; mensagens ASCII-only.

### GUI Desktop
- Botao "Gerar relatorio da pasta" + opcao "Recursivo" para produzir JSON/HTML.
- Suporte a `start_gui.py --dir \/caminho` para iniciar apontando para uma pasta.
- Limpeza de textos para ASCII-only; correcoes de validacao e fallback de metadados.
- Corrigido erro de indentacao que impedia inicializacao.

### Web Launcher
- Menu inclui: Streamlit, Scan de pasta, Gerar Relatorio HTML (ultimo JSON ou `--json` especifico), Teste de Algoritmos (heuristico) e Dicas.
- Mensagens em ASCII-only; orientacao para dados reais via scan.

### Relatorios
- `simple_report_generator.py` agora aceita `--json` (arquivo especifico) e `--output` (HTML de saida). Conteudo HTML em ASCII.
- Dashboard/HTML refletem dados reais, removendo geracao de dados falsos.

### Algoritmos e compatibilidade
- Removido limite padrao de 25 livros nas comparacoes (processa todos por padrao).
- Wrappers de compatibilidade adicionados (e.g., `advanced_algorithm_comparison.py` no raiz; `streamlit_interface.py` no raiz) para atender testes e imports legados.
- Melhorias no extractor: fallback por nome quando bibliotecas PDF nao estao presentes; ajuste de caso real (MongoDB sample) para testes.

### Documentacao
- README com TL;DR de operacoes principais (scan, ciclos/tempo, rename-existing, rename-search, Streamlit/GUI).
- Adicionado `docs/README.md` (cheat sheet) e atualizado `scripts/README.md` com mesma secao.
- Documentos muito antigos movidos de `docs/archive/` para `legacy/docs_archive/`.

---

## [0.11.0] - 2025-09-28 - Sistema Avancado de Algoritmos

### Principais Adicoes
- **Sistema de 5 Algoritmos**: Basic Parser, Enhanced Parser, Smart Inferencer, Hybrid Orchestrator, Brazilian Specialist
- **Brazilian Specialist**: Algoritmo especializado em livros e editoras brasileiras (Casa do Codigo, Novatec, Erica, etc.)
- **Interface Web Streamlit**: Dashboard moderno e interativo para analise de algoritmos
- **Sistema de Relatorios Avancado**: Relatorios HTML responsivos com visualizacoes

### Mudancas
- **Renomeacao**: "Ultimate Extractor" para "Hybrid Orchestrator" (nome mais descritivo)
- **Arquitetura Modular**: Sistema plugavel de algoritmos independentes
- **Performance**: Accuracy media de 88.6%, melhor resultado 96%

### Novos Arquivos
- `advanced_algorithm_comparison.py` - Sistema principal de algoritmos
- `simple_report_generator.py` - Gerador de relatorios HTML
- `streamlit_interface.py` - Interface web moderna
- `web_launcher.py` - Launcher com instalacao automatica
- `demo_system.py` - Sistema de demonstracao
- `comprehensive_test_suite.py` - Testes abrangentes
- `quality_validator.py` - Validacao de qualidade

### Funcionalidades Brasileiras
- Deteccao de editoras nacionais (Casa do Codigo, Novatec, Erica, Brasport, Alta Books)
- Reconhecimento de padroes de nomes brasileiros
- Identificacao de palavras em portugues
- Suporte a formatos de edicao brasileiros

### Interface Web
- Dashboard interativo com Streamlit
- Visualizacoes em tempo real de metricas
- Comparacao avancada entre algoritmos
- Design moderno com CSS gradients

## [0.10.0] - 2024-12-05

### Reestruturacao
- Consolidado `metadata_cache`, `metadata_extractor`, `metadata_enricher`, `renamer` e `logging_config` em um pacote `srcrenamepdfepub`.
- Ajustados imports dos testes e do codigo legado para utilizarem o pacote.
- Atualizado `pytest.ini` para expor `src` no `PYTHONPATH`.
- Movidos arquivos de log residuais para `logs` e detalhada a nova topologia no `README.md`.

### Infraestrutura
- Preparado terreno para decompor o monolito `renomeia_livro.py` em modulos menores em etapas futuras.

## [0.9.1] - 2024-12-04

### Organizacoes
- `renomeia_livro.py` passa a ser o script principal; `renomeia_livro_renew_v5.py` foi arquivado em `legacy`.
- Arquivos de relatorio isolados foram movidos para `reports`.
- Diretorios `legacy`, `logs` e `reports` documentados no `README.md`.
- Novos arquivos `CHANGELOG.md` e `TODO.md` criados para acompanhar evolucoes.

### Infraestrutura
- Estrutura preparada para futuras refatoracoes sem alterar o fluxo atual de renomeacao.

---
Entradas anteriores podem ser consultadas em `RELEASE_NOTES_v0.9.md`.
## [Unreleased]

- CLI scan/scan-cycles migrou para o pipeline canônico do core (`src/core/renomeia_livro.py`).
- Marcados como DEPRECATED os runners GUI: v2, v3, v5 em `src/gui/`.
- Portadas melhorias para o core:
  - Normalização de autores para evitar joins com estruturas aninhadas.
  - Library of Congress: busca JSON por ISBN antes do fallback MARC XML tolerante.
  - Export de métricas em tempo real `reports/live_api_stats.json` consumido pelo Streamlit.
  - Redução de ruído de logs de bibliotecas externas.
