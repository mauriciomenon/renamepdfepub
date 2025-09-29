# RenamePDFEPUB v1.0.0

Sistema automatizado para renomeacao de arquivos PDF e EPUB baseado em extracao de metadados.

## TL;DR – Operações Principais

As operações abaixo cobrem varredura (scan) sem renomear, varredura repetida, renomear com base em relatório existente e renomear enquanto busca. Válidas para pastas locais e pastas sincronizadas (OneDrive/Google Drive).

```bash
# 0) Instalar dependências
pip install -r requirements.txt

# 1) Scan (gera relatórios JSON/HTML em reports/, não renomeia)
python3 start_cli.py scan "/caminho/livros"
python3 start_cli.py scan "/caminho/livros" -r                # recursivo
python3 start_cli.py scan "/caminho/livros" -t 8 -o out.json   # threads e saída

# 2) Scan por ciclos/tempo (repetiçōes retroalimentadas)
python3 start_cli.py scan-cycles "/caminho/livros" --cycles 3
python3 start_cli.py scan-cycles "/caminho/livros" --time-seconds 120

# 3) Renomear com dados já existentes (relatório JSON)
python3 start_cli.py rename-existing --report relatorio.json --apply [--copy]

# 4) Renomear fazendo a procura (scan + rename)
python3 start_cli.py rename-search "/caminho/livros" --rename

# 5) Streamlit (dashboard + scan pela barra lateral)
python3 start_web.py --auto-start
# Ajuste "Pasta de livros" na barra lateral e use "Executar varredura". Dashboard lê reports/.

# 6) GUI Desktop
python3 start_gui.py --dir "/caminho/inicial"   # inicia apontando para a pasta
# Na GUI, use "Gerar relatório da pasta" (com opção Recursivo) para produzir JSON/HTML.

# 7) Algoritmos (comparação)
python3 start_cli.py algorithms

# 8) Testes
python3 run_tests.py
```

## Algoritmos Disponiveis

| Algoritmo | Precisao | Especializacao |
|-----------|----------|----------------|
| **Hybrid Orchestrator** | 96% | Combinacao de todas as tecnicas |
| **Brazilian Specialist** | 93% | Livros e editoras brasileiras |
| **Smart Inferencer** | 91% | Inferencia inteligente |
| **Enhanced Parser** | 85% | Parser com validacao |
| **Basic Parser** | 78% | Extracao basica rapida |

## Estrutura do Projeto

## Estrutura do Projeto

```
renamepdfepub/
├── start_web.py        # Interface Web Streamlit - PRINCIPAL
├── start_html.py       # Relatorios HTML - "Pagina Antiga"
├── start_cli.py        # Interface CLI - Linha de Comando
├── start_gui.py        # Interface Grafica Desktop
├── run_tests.py        # Testes automatizados
│
├── src/                # Codigo fonte organizado
│   ├── core/          # Algoritmos e logica principal
│   ├── cli/           # Interface linha de comando  
│   └── gui/           # Interfaces graficas (Streamlit, GUI)
│
├── docs/               # Documentacao tecnica organizada
│   ├── structure/     # Documentacao da arquitetura
│   ├── testing/       # Relatorios e analises de testes
│   ├── reports/       # Relatorios de implementacao
│   └── releases/      # Notas de versao
│
├── data/               # Dados e resultados organizados
│   ├── results/       # Resultados de analises
│   ├── algorithm_results/ # Resultados dos algoritmos
│   ├── enhanced_results/  # Analises avancadas
│   └── cache/         # Cache de metadados
│
├── utils/             # Utilitarios e ferramentas auxiliares
├── tests/             # Testes automatizados com pytest
├── reports/           # Relatorios HTML e performance
└── logs/              # Arquivos de log centralizados

## Pontos de Entrada

### 1. Interface Web Interativa (RECOMENDADO)
```bash
python3 start_web.py
```
- **Streamlit Dashboard** - Interface web moderna e interativa
- Visualizacoes em tempo real
- Instalacao automatica de dependencias
- Interface responsiva com widgets

### 2. Relatorios HTML Estaticos
```bash
python3 start_html.py
```
- **"Pagina Antiga"** - Relatorios HTML sem dependencias
- Funciona offline, abre no navegador
- Relatorios pre-gerados com graficos CSS
- Ideal para apresentacoes ou compartilhamento

### 3. Interface CLI
```bash
python3 start_cli.py algorithms    # Executar algoritmos
python3 start_cli.py launch        # Launcher sistema
```
- Interface de linha de comando
- Ideal para automacao e scripts
- Output limpo e profissional

### 4. Interface Grafica Desktop
```bash
python3 start_gui.py
```
- Interface grafica desktop (tkinter)
- Para usuarios menos tecnicos
- Nao requer navegador

## Diferenca: Streamlit vs HTML

### Interface Streamlit (`start_web.py`) - MODERNA
- **Interativa**: Widgets, sliders, botoes em tempo real
- **Dinamica**: Executa algoritmos ao vivo
- **Requer**: Python rodando, dependencias instaladas
- **Uso**: Desenvolvimento, testes, demonstracoes interativas

### Relatorios HTML (`start_html.py`) - ESTATICA
- **Estatica**: Relatorios pre-gerados, sem interacao
- **Offline**: Funciona sem Python rodando
- **Requer**: Apenas navegador web
- **Uso**: Apresentacoes, compartilhamento, arquivamento

## Sistema de 5 Algoritmos

### Hybrid Orchestrator (96% precisao)
O algoritmo mais avancado que combina todas as tecnicas:
- Extracao de multiplas fontes
- Validacao cruzada
- Correcao automatica de erros
- Inferencia inteligente quando dados incompletos

### Brazilian Specialist (93% precisao) 
Especializado no mercado brasileiro:
- **Editoras**: Casa do Codigo, Novatec, Erica, Brasport, Alta Books
- **Padroes**: Deteccao de nomes brasileiros
- **Idioma**: Reconhecimento de portugues
- **Formatos**: Padroes de metadados nacionais

### Smart Inferencer (91% precisao)
Inferencia inteligente para dados ausentes:
- Analise de padroes de nome de arquivo
- Inferencia de autor por padroes
- Correcao automatica de encoding
- Validacao de consistencia

### Enhanced Parser (85% precisao)
Parser robusto com validacao:
- Multiplas tentativas de extracao
- Validacao de formato
- Correcao de erros comuns
- Fallback para metodos alternativos

### Basic Parser (78% precisao)
Extracao basica e rapida:
- Metadados diretos do arquivo
- Processamento rapido
- Ideal para lotes grandes
- Baixo uso de recursos

## Funcionalidades Brasileiras

### Editoras Suportadas
- **Casa do Codigo**: Deteccao especializada
- **Novatec**: Padroes especificos
- **Erica**: Formatos academicos
- **Brasport**: Livros tecnicos
- **Alta Books**: Traducoes

### Padroes Detectados
- **Nomes**: Joao, Maria, Silva, Santos, etc.
- **Idioma**: Palavras em portugues
- **Formatos**: Edicoes brasileiras
- **ISBN**: Prefixos nacionais (978-85)

## Relatorios e Analises

### Relatorios HTML
```bash
# Gerados automaticamente em reports/html/
- advanced_algorithms_report.html  # Comparacao completa
- demo_report.html                 # Demonstracao
- performance_analysis.html        # Analise de performance
```

### Analises de Performance
```bash
# Disponiveis em reports/performance/
- Comparacao entre algoritmos
- Metricas por editora
- Analise de tempo de execucao
- Taxa de sucesso por tipo de arquivo
```

## Testes Automatizados

```bash
# Executar todos os testes
python3 run_tests.py

# Ou executar pytest diretamente
pytest tests/ -v
```

### Cobertura de Testes
- **5 algoritmos** validados
- **Deteccao de editoras brasileiras**
- **Validacao de metadados**
- **Limpeza de output** (sem emojis)
- **Geracao de relatorios**

## Instalacao

### Requisitos
- Python 3.8+
- Dependencias em requirements.txt

### Instalacao Rapida
```bash
# Clonar repositorio
git clone https://github.com/mauriciomenon/renamepdfepub.git
cd renamepdfepub

# Instalar dependencias
pip install -r requirements.txt

# Executar interface web
python3 web.py
```

## Performance

### Metricas Gerais
- **Precisao Media**: 88.6%
- **Melhor Resultado**: 96% (Hybrid Orchestrator)
- **Tempo Medio**: <150ms por arquivo
- **Taxa de Sucesso**: 95%+

### Benchmarks
- **Arquivos Testados**: 12 livros (2 por editora)
- **Editoras**: 6 (3 brasileiras + 3 internacionais)
- **Formatos**: PDF e EPUB
- **Tamanhos**: 1MB a 50MB

## Desenvolvimento

### Estrutura de Codigo
```
src/core/           # Logica principal
 advanced_algorithm_comparison.py  # 5 algoritmos
 renomeia_livro.py                # Sistema legado
 auto_rename_system.py            # Sistema automatico
 quality_validator.py             # Validacao

src/cli/            # Interface CLI
 launch_system.py     # Launcher
 demo_complete.py     # Demo
 manual_analysis.py   # Analise manual

src/gui/            # Interfaces graficas
 web_launcher.py         # Launcher web
 streamlit_interface.py  # Streamlit
 gui_modern.py          # GUI desktop
```

### Contribuicao
1. Fork do repositorio
2. Criar branch para feature
3. Executar testes: `python3 run_tests.py`
4. Commit com mensagens limpas (sem emojis)
5. Pull request

## Status do Projeto

**PRONTO PARA PRODUCAO**

- **Meta Original**: 70% de precisao
- **Resultado Alcancado**: **88.7% de precisao media**
- **Superacao**: +18.7 pontos percentuais acima da meta

### Versao Atual: v1.0.0
- 5 algoritmos especializados implementados
- Interface web moderna (Streamlit)
- Sistema de relatorios avancado
- Especializacao brasileira
- Testes automatizados
- Documentacao completa
- Estrutura profissional organizada

## Licenca

MIT License - veja LICENSE para detalhes.

## Documentacao Organizada

### Estrutura e Arquitetura
- **Estrutura do Projeto**: [docs/structure/project_structure.md](docs/structure/project_structure.md)
- **Layout do Repositorio**: [docs/structure/repository_layout.md](docs/structure/repository_layout.md)
- **Analise Completa**: [docs/structure/complete_analysis.md](docs/structure/complete_analysis.md)

### Testes e Validacao
- **Suite de Testes**: [docs/testing/test_suite_report.md](docs/testing/test_suite_report.md)
- **Relatorio Final**: [docs/testing/final_test_report.md](docs/testing/final_test_report.md)
- **Analise Abrangente**: [docs/testing/comprehensive_test_report.md](docs/testing/comprehensive_test_report.md)

### Relatorios de Implementacao
- **Validacao de Referencias**: [docs/reports/reference_validation.md](docs/reports/reference_validation.md)
- **Resumo da Reorganizacao**: [docs/reports/reorganization_summary.md](docs/reports/reorganization_summary.md)
- **Correcoes Implementadas**: [docs/reports/implementation_fixes.md](docs/reports/implementation_fixes.md)

## Suporte

- **Documentacao Completa**: [docs/](docs/)
- **Organizacao do Projeto**: [docs/PROJECT_ORGANIZATION.md](docs/PROJECT_ORGANIZATION.md)
- **Testes**: `python3 run_tests.py`
- **Issues**: GitHub Issues
