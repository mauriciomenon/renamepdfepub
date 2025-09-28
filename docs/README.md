# 📚 Documentação RenamePDFEPUB

## 📖 TL;DR - Uso Rápido

**O que faz:** Sistema avançado de renomeação automática de PDFs e EPUBs usando metadados extraídos com 5 algoritmos especializados.

**Instalação:**
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

# Renomeação simples (legado)
python3 renomeia_livro.py
```

**Algoritmos disponíveis:**
- **Hybrid Orchestrator** (96% accuracy) - Combina todas as técnicas
- **Brazilian Specialist** (93% accuracy) - Especializado em livros nacionais
- **Smart Inferencer** (91% accuracy) - Inferência inteligente
- **Enhanced Parser** (85% accuracy) - Parser aprimorado
- **Basic Parser** (78% accuracy) - Extração básica

---

## 📂 Estrutura da Documentação

### [Releases](releases/)
- [CHANGELOG.md](releases/CHANGELOG.md) - Histórico de mudanças
- [Release Notes v0.11.0](releases/RELEASE_NOTES_v0.11.0_ADVANCED_ALGORITHMS.md) - Release atual
- [Releases anteriores](releases/) - Histórico completo

### [Análises](analysis/)
- [Análise de Arquitetura](analysis/ARCHITECTURE_ANALYSIS_v0.10.1.md)
- [Análise de Padrões](analysis/ANALISE_PADROES_REAIS.md)
- [Relatório de Qualidade](analysis/QUALITY_REPORT_v0.11.0.md)
- [Avaliações Completas](analysis/)

### [Performance](performance/)
- [Relatório de Dados Reais](performance/RELATORIO_DADOS_REAIS.md)
- [Análise Final v3](performance/RELATORIO_FINAL_V3.md)
- [Melhorias de Performance](performance/)

### Status e Progresso
- [Conclusão Final](CONCLUSAO_FINAL_SUCESSO.md)
- [Status do Projeto](STATUS_FINAL_PROJETO.md)
- [TODO](TODO.md)

---

## Sistema de 5 Algoritmos

| Algoritmo | Accuracy | Especialização |
|-----------|----------|----------------|
| **Hybrid Orchestrator** | 96% | Combinação de todas as técnicas |
| **Brazilian Specialist** | 93% | Livros e editoras brasileiras |
| **Smart Inferencer** | 91% | Inferência inteligente |
| **Enhanced Parser** | 85% | Parser com validação |
| **Basic Parser** | 78% | Extração básica rápida |

## Funcionalidades Brasileiras

- **Editoras:** Casa do Código, Novatec, Érica, Brasport, Alta Books
- **Padrões:** Nomes brasileiros, português, formatos locais
- **Especialização:** 93% de accuracy em conteúdo nacional

## Interface Web

- **Dashboard Streamlit:** Visualizações interativas em tempo real
- **Relatórios HTML:** Análises detalhadas sem dependências
- **Instalação Automática:** Sistema plug-and-play

---

## 📈 Performance Atual

- **Accuracy Média:** 88.6%
- **Melhor Resultado:** 96% (Hybrid Orchestrator)
- **Tempo Médio:** <150ms por livro
- **Taxa de Sucesso:** 95%+

## 🔧 Requisitos

- Python 3.8+
- Dependências automáticas via web_launcher.py
- Streamlit (instalação automática)

## 📞 Suporte

- **Issues:** [GitHub Issues](https://github.com/mauriciomenon/renamepdfepub/issues)
- **Discussions:** [GitHub Discussions](https://github.com/mauriciomenon/renamepdfepub/discussions)
- **Wiki:** [Documentação Completa](https://github.com/mauriciomenon/renamepdfepub/wiki)

---

*Última atualização: 28/09/2025 - v1.0.0_20250928*
