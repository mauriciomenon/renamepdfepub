# Changelog

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
