# Changelog

## [0.11.0] - 2025-09-28 - Sistema Avançado de Algoritmos

### 🚀 Principais Adições
- **Sistema de 5 Algoritmos**: Basic Parser, Enhanced Parser, Smart Inferencer, Hybrid Orchestrator, Brazilian Specialist
- **Brazilian Specialist**: Algoritmo especializado em livros e editoras brasileiras (Casa do Código, Novatec, Érica, etc.)
- **Interface Web Streamlit**: Dashboard moderno e interativo para análise de algoritmos
- **Sistema de Relatórios Avançado**: Relatórios HTML responsivos com visualizações

### 🔄 Mudanças
- **Renomeação**: "Ultimate Extractor" → "Hybrid Orchestrator" (nome mais descritivo)
- **Arquitetura Modular**: Sistema plugável de algoritmos independentes
- **Performance**: Accuracy média de 88.6%, melhor resultado 96%

### 📁 Novos Arquivos
- `advanced_algorithm_comparison.py` - Sistema principal de algoritmos
- `simple_report_generator.py` - Gerador de relatórios HTML
- `streamlit_interface.py` - Interface web moderna
- `web_launcher.py` - Launcher com instalação automática
- `demo_system.py` - Sistema de demonstração
- `comprehensive_test_suite.py` - Testes abrangentes
- `quality_validator.py` - Validação de qualidade

### 🇧🇷 Funcionalidades Brasileiras
- Detecção de editoras nacionais (Casa do Código, Novatec, Érica, Brasport, Alta Books)
- Reconhecimento de padrões de nomes brasileiros
- Identificação de palavras em português
- Suporte a formatos de edição brasileiros

### 🌐 Interface Web
- Dashboard interativo com Streamlit
- Visualizações em tempo real de métricas
- Comparação avançada entre algoritmos
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
