#  Documentacao RenamePDFEPUB

##  TL;DR - Uso Rapido

**O que faz:** Sistema avancado de renomeacao automatica de PDFs e EPUBs usando metadados extraidos com 5 algoritmos especializados.

**Instalacao:**
```bash
git clone https://github.com/mauriciomenon/renamepdfepub.git
cd renamepdfepub
python3 web_launcher.py
```

**Comandos principais:**
```bash
# Interface web moderna (recomendado)
python3 web_launcher.py

# Teste direto dos algoritmos
python3 advanced_algorithm_comparison.py

# Renomeacao simples (legado)
python3 renomeia_livro.py
```

**Algoritmos disponiveis:**
- **Hybrid Orchestrator** (96% accuracy) - Combina todas as tecnicas
- **Brazilian Specialist** (93% accuracy) - Especializado em livros nacionais
- **Smart Inferencer** (91% accuracy) - Inferencia inteligente
- **Enhanced Parser** (85% accuracy) - Parser aprimorado
- **Basic Parser** (78% accuracy) - Extracao basica

---

##  Estrutura da Documentacao

### [Releases](releases/)
- [CHANGELOG.md](releases/CHANGELOG.md) - Historico de mudancas
- [Release Notes v0.11.0](releases/RELEASE_NOTES_v0.11.0_ADVANCED_ALGORITHMS.md) - Release atual
- [Releases anteriores](releases/) - Historico completo

### [Analises](analysis/)
- [Analise de Arquitetura](analysis/ARCHITECTURE_ANALYSIS_v0.10.1.md)
- [Analise de Padroes](analysis/ANALISE_PADROES_REAIS.md)
- [Relatorio de Qualidade](analysis/QUALITY_REPORT_v0.11.0.md)
- [Avaliacoes Completas](analysis/)

### [Performance](performance/)
- [Relatorio de Dados Reais](performance/RELATORIO_DADOS_REAIS.md)
- [Analise Final v3](performance/RELATORIO_FINAL_V3.md)
- [Melhorias de Performance](performance/)

### Status e Progresso
- [Conclusao Final](CONCLUSAO_FINAL_SUCESSO.md)
- [Status do Projeto](STATUS_FINAL_PROJETO.md)
- [TODO](TODO.md)

---

## Sistema de 5 Algoritmos

| Algoritmo | Accuracy | Especializacao |
|-----------|----------|----------------|
| **Hybrid Orchestrator** | 96% | Combinacao de todas as tecnicas |
| **Brazilian Specialist** | 93% | Livros e editoras brasileiras |
| **Smart Inferencer** | 91% | Inferencia inteligente |
| **Enhanced Parser** | 85% | Parser com validacao |
| **Basic Parser** | 78% | Extracao basica rapida |

## Funcionalidades Brasileiras

- **Editoras:** Casa do Codigo, Novatec, Erica, Brasport, Alta Books
- **Padroes:** Nomes brasileiros, portugues, formatos locais
- **Especializacao:** 93% de accuracy em conteudo nacional

## Interface Web

- **Dashboard Streamlit:** Visualizacoes interativas em tempo real
- **Relatorios HTML:** Analises detalhadas sem dependencias
- **Instalacao Automatica:** Sistema plug-and-play

---

##  Performance Atual

- **Accuracy Media:** 88.6%
- **Melhor Resultado:** 96% (Hybrid Orchestrator)
- **Tempo Medio:** <150ms por livro
- **Taxa de Sucesso:** 95%+

##  Requisitos

- Python 3.8+
- Dependencias automaticas via web_launcher.py
- Streamlit (instalacao automatica)

##  Suporte

- **Issues:** [GitHub Issues](https://github.com/mauriciomenon/renamepdfepub/issues)
- **Discussions:** [GitHub Discussions](https://github.com/mauriciomenon/renamepdfepub/discussions)
- **Wiki:** [Documentacao Completa](https://github.com/mauriciomenon/renamepdfepub/wiki)

---

*Ultima atualizacao: 28/09/2025 - v1.0.0_20250928*
