# Análise de Arquitetura - renamepdfepub v0.10.1

## Visão Geral da Arquitetura

### Estrutura do Projeto
```
renamepdfepub/
├── gui_RenameBook.py          # Interface Gráfica (PyQt6)
├── renomeia_livro.py          # Interface CLI (8536 linhas)
├── src/renamepdfepub/         # Módulos Compartilhados
│   ├── __init__.py
│   ├── logging_config.py      # Configurações de log
│   ├── metadata_cache.py      # Cache SQLite compartilhado
│   ├── metadata_enricher.py   # Enriquecimento de metadados
│   ├── metadata_extractor.py  # Extração de metadados (314 linhas)
│   └── renamer.py            # Lógica de renomeação
├── books/                     # Arquivos de teste (100+ PDFs/EPUBs)
├── tests/                     # Testes unitários
└── reports/                   # Relatórios de análise
```

## Componentes por Responsabilidade

### 🖥️ GUI (Interface Gráfica) - `gui_RenameBook.py`
**Responsabilidade**: Interface visual para usuários que preferem interação gráfica

**Características**:
- **Framework**: PyQt6 (769 linhas)
- **Arquitetura**: Interface limpa que **importa e reutiliza** módulos compartilhados
- **Threading**: PreviewWorker e RenameWorker para operações não-bloqueantes
- **Estado**: Grade A+ (9.5/10) após otimizações v0.10.0

**Dependências**:
```python
from src.renamepdfepub.metadata_extractor import extract_metadata
# Reutiliza todos os módulos compartilhados
```

**Funcionalidades Exclusivas da GUI**:
- Preview visual em tempo real
- Drag & drop de arquivos
- Progress bars com threading
- Validação visual de nomes
- Interface para configurações

### 🖲️ CLI (Interface de Linha de Comando) - `renomeia_livro.py`
**Responsabilidade**: Interface completa para automação e processamento em lote

**Características**:
- **Tamanho**: 8536 linhas (arquivo monolítico)
- **Arquitetura**: Script autônomo com classes embutidas
- **Performance**: 75% de melhoria após otimizações v0.10.1
- **Paralelismo**: ThreadPoolExecutor para processamento concorrente

**Classes Embutidas no CLI**:
- `DependencyManager` (linha ~110): Gerencia dependências opcionais
- `MetadataCache` (linha 266): Cache SQLite **embutido no CLI**
- `BookMetadataExtractor` (linha 4456): Extração de metadados **embutida**
- `EbookProcessor` (linha 7464): Processamento de eBooks
- `PacktBookProcessor` (linha 8174): Especialização para livros Packt
- `main()` (linha 8383): Função principal

**Funcionalidades Exclusivas do CLI**:
- Processamento em lote massivo
- APIs de múltiplas fontes (Google Books, OpenLibrary, etc.)
- OCR avançado para PDFs escaneados
- Relatórios detalhados de performance
- Configuração via argumentos de linha de comando

### 🔗 Módulos Compartilhados - `src/renamepdfepub/`
**Responsabilidade**: Funcionalidades core reutilizadas por GUI e CLI

#### `metadata_extractor.py` (314 linhas)
- **Função**: Extração básica de metadados (PDF, EPUB, HTML)
- **Otimizações**: Cache de texto PDF, regex pré-compilados
- **Uso**: Importado pela GUI, **duplicado** no CLI como BookMetadataExtractor

#### `metadata_cache.py`
- **Função**: Cache SQLite para metadados
- **Uso**: Utilizado pela GUI, **reimplementado** no CLI como classe embutida

#### `metadata_enricher.py`
- **Função**: Enriquecimento de metadados via APIs
- **Uso**: Compartilhado entre GUI e CLI

#### `renamer.py`
- **Função**: Lógica de geração de nomes de arquivo
- **Uso**: Compartilhado entre GUI e CLI

#### `logging_config.py`
- **Função**: Configuração centralizada de logs
- **Uso**: Compartilhado entre todos os componentes

## Padrões Arquiteturais Identificados

### ✅ Pontos Fortes
1. **GUI Limpa**: Interface enxuta que reutiliza módulos compartilhados
2. **Modularidade**: Separação clara de responsabilidades nos módulos
3. **Performance**: Otimizações recentes (cache, threading, SQLite)
4. **Robustez**: Tratamento extensivo de erros e dependências opcionais

### ⚠️ Pontos de Atenção
1. **CLI Monolítico**: 8536 linhas em um único arquivo
2. **Duplicação de Código**: MetadataCache reimplementado no CLI
3. **Inconsistência**: CLI não usa módulos compartilhados completamente

## Estratégia de Modularização Recomendada

### Fase 1: Refatoração do CLI
```
renomeia_livro.py (atual: 8536 linhas)
│
├── renomeia_livro_main.py (~200 linhas)     # Script principal
├── src/renamepdfepub/
│   ├── cli_processor.py                      # EbookProcessor
│   ├── dependency_manager.py                 # DependencyManager
│   ├── specialized_processors/
│   │   ├── packt_processor.py               # PacktBookProcessor
│   │   └── publisher_handlers.py            # Handlers específicos
│   └── batch_processor.py                   # Processamento em lote
```

### Fase 2: Unificação de Componentes
- Consolidar MetadataCache (eliminar duplicação)
- Unificar BookMetadataExtractor com metadata_extractor.py
- Criar interfaces consistentes entre GUI e CLI

## Impacto nos Algoritmos de Busca (Fase 2)

### 🎯 Implementação Planejada
1. **Módulo de Busca Compartilhado**: `src/renamepdfepub/search_algorithms/`
2. **Interface GUI**: Widgets para configuração de algoritmos
3. **Interface CLI**: Parâmetros para seleção de estratégias
4. **Benchmarking**: Comparação de performance entre algoritmos

### 📊 Estratégias de Teste
- **Conjunto de Teste**: 100+ arquivos em `books/`
- **Métricas**: Precision, Recall, Tempo de execução
- **Cenários**: PDFs limpos, escaneados, EPUBs, casos edge

## Conclusão

A arquitetura atual apresenta uma **GUI bem estruturada** que reutiliza módulos compartilhados, e um **CLI poderoso porém monolítico**. Para a implementação dos algoritmos de busca, será necessário:

1. **Manter** a estrutura limpa da GUI
2. **Refatorar** o CLI para usar módulos compartilhados
3. **Criar** módulos específicos para algoritmos de busca
4. **Implementar** testes extensivos usando o conjunto `books/`

Esta base sólida permitirá implementar algoritmos de busca sofisticados mantendo performance e robustez.