# TODO Phase 2 - Search Algorithms Implementation

## Objetivos da Fase 2

### Implementacao de Algoritmos de Busca e Pesquisa
- **Foco principal**: Melhorias de desempenho para suporte a multiplos algoritmos
- **Escopo**: CLI + GUI com componentes compartilhados
- **Qualidade**: Implementacao longa, refinada, confiavel e robusta
- **Testes**: Extensivos e criativos usando colecao books

## TODO List Detalhado

### Arquitetura e Refatoracao (Prioridade Alta)

#### CLI Refactoring
- [ ] **Dividir renomeia_livro.py (8536 linhas)**
 - [ ] Extrair DependencyManager srcrenamepdfepubdependency_manager.py
 - [ ] Consolidar MetadataCache (eliminar duplicacao CLIshared)
 - [ ] Extrair EbookProcessor srcrenamepdfepubebook_processor.py
 - [ ] Extrair PacktBookProcessor srcrenamepdfepubspecialized_processors
 - [ ] Manter renomeia_livro.py como script principal (200 linhas)

#### Unificacao de Componentes
- [ ] **Consolidar extratores de metadados**
 - [ ] Unificar BookMetadataExtractor (CLI) com metadata_extractor.py (shared)
 - [ ] Implementar interface consistente entre GUI e CLI
 - [ ] Otimizar cache compartilhado de texto PDF

#### Modulo de Busca Compartilhado
- [ ] **Criar srcrenamepdfepubsearch_algorithms**
 - [ ] base_search.py - Interface base para algoritmos
 - [ ] fuzzy_search.py - Busca fuzzy para titulosautores
 - [ ] isbn_search.py - Busca especializada por ISBN
 - [ ] text_similarity.py - Algoritmos de similaridade de texto
 - [ ] search_orchestrator.py - Coordenacao de multiplos algoritmos

### Algoritmos de Busca (Prioridade Alta)

#### Algoritmos Fundamentais
- [ ] **Fuzzy String Matching**
 - [ ] Implementar Levenshtein distance
 - [ ] Implementar Jaro-Winkler similarity
 - [ ] Implementar soundexmetaphone para nomes
 - [ ] Benchmark de performance

- [ ] **Busca por Similaridade Semantica**
 - [ ] TF-IDF para comparacao de titulos
 - [ ] N-gram matching para autores
 - [ ] Normalizacao de editoras (ja existe, expandir)

- [ ] **Busca Hibrida Multi-criterio**
 - [ ] Combinacao ponderada de algoritmos
 - [ ] Sistema de scoring dinamico
 - [ ] Fallback automatico entre estrategias

#### Busca Especializada
- [ ] **ISBN Intelligence**
 - [ ] Validacao e correcao automatica de ISBNs
 - [ ] Busca por ISBN parcialcorrompido
 - [ ] Cache inteligente de resultados ISBN

- [ ] **Publisher-Specific Search**
 - [ ] Extensao dos processadores Packt, O'Reilly, etc.
 - [ ] Padroes especificos por editora
 - [ ] Tratamento de edge cases por publisher

### Interface GUI (Prioridade Media)

#### Widgets de Configuracao de Algoritmos
- [ ] **Painel de Selecao de Algoritmos**
 - [ ] Checkboxes para algoritmos disponiveis
 - [ ] Sliders para pesosthresholds
 - [ ] Preview em tempo real de resultados

- [ ] **Visualizacao de Performance**
 - [ ] Graficos de tempo de execucao
 - [ ] Metricas de precisao por algoritmo
 - [ ] Comparacao lado-a-lado

#### Funcionalidades Avancadas GUI
- [ ] **Modo Batch Inteligente**
 - [ ] Selecao automatica de algoritmo por tipo de arquivo
 - [ ] Progress bar detalhado por algoritmo
 - [ ] Relatorio de resultados por estrategia

### Interface CLI (Prioridade Media)

#### Parametros de Linha de Comando
- [ ] **Opcoes de Algoritmo**
 - [ ] --search-algorithm (fuzzy|semantic|hybrid|auto)
 - [ ] --fuzzy-threshold (0.0-1.0)
 - [ ] --fallback-strategy (chain|parallel|adaptive)

- [ ] **Modo Benchmark**
 - [ ] --benchmark - testa todos algoritmos
 - [ ] --compare-algorithms - comparacao detalhada
 - [ ] --export-metrics - exporta resultados CSVJSON

#### Relatorios CLI Avancados
- [ ] **Performance Analytics**
 - [ ] Tempo por algoritmo
 - [ ] Taxa de sucesso por estrategia 
 - [ ] Recomendacoes automaticas

### Testing Strategy (Prioridade Alta)

#### Test Dataset (books directory - 100+ files)
- [ ] **Categorizacao de Arquivos de Teste**
 - [ ] PDFs limpos vs. escaneados
 - [ ] EPUBs comsem metadados completos
 - [ ] Casos edge: nomes especiais, caracteres Unicode
 - [ ] Arquivos corrompidosincompletos

#### Test Scenarios
- [ ] **Accuracy Tests**
 - [ ] Ground truth dataset com metadados validados
 - [ ] PrecisionRecall por algoritmo
 - [ ] F1-score para comparacao

- [ ] **Performance Tests**
 - [ ] Benchmark de tempo por algoritmo
 - [ ] Memory usage profiling
 - [ ] Concurrency stress tests

- [ ] **Edge Case Tests**
 - [ ] Titulos com caracteres especiais
 - [ ] Autores com multiplas grafias
 - [ ] ISBNs corrompidosparciais
 - [ ] Metadados conflitantes

#### Creative Testing Approaches
- [ ] **Algoritmos Geneticos para Otimizacao**
 - [ ] Evolucao automatica de pesos
 - [ ] Descoberta de combinacoes otimas
 - [ ] Adaptacao por tipo de conteudo

- [ ] **AB Testing Framework**
 - [ ] Comparacao estatistica de algoritmos
 - [ ] Significance testing
 - [ ] Automated regression detection

### Metrics Analytics (Prioridade Media)

#### Performance Monitoring
- [ ] **Real-time Metrics**
 - [ ] Dashboard de performance em tempo real
 - [ ] Alertas para degradacao de performance
 - [ ] Historical trending

- [ ] **Algorithm Effectiveness**
 - [ ] Success rate por tipo de arquivo
 - [ ] Confidence score distribution
 - [ ] False positivenegative analysis

### Infrastructure DevOps (Prioridade Baixa)

#### Development Tools
- [ ] **Profiling Integration**
 - [ ] cProfile integration para benchmarks
 - [ ] Memory profiling com memory_profiler
 - [ ] Visual profiling reports

- [ ] **CICD Enhancement**
 - [ ] Performance regression tests
 - [ ] Automated benchmarking pipeline
 - [ ] Algorithm comparison reports

## Milestone Planning

### Milestone 1: Architecture Cleanup (1-2 weeks)
- CLI refactoring completo
- Modulos compartilhados consolidados
- Base para algoritmos de busca

### Milestone 2: Core Search Algorithms (2-3 weeks)
- Fuzzy matching implementado
- Busca semantica basica
- Sistema de scoring unificado

### Milestone 3: Advanced Features (2-3 weeks)
- GUI widgets para configuracao
- CLI parametros avancados
- Busca hibrida multi-criterio

### Milestone 4: Testing Optimization (1-2 weeks)
- Test suite completo usando books
- Performance benchmarking
- Documentacao e refinamentos

## Success Criteria

### Performance Goals
- **Throughput**: Mantermelhorar 75 improvement atual
- **Accuracy**: 90 precision em dataset de teste
- **Scalability**: Suporte a 1000+ arquivos simultaneos

### Quality Goals
- **Code Coverage**: 85 para novos modulos
- **Documentation**: Completa para todos algoritmos
- **Maintainability**: Modular, testavel, extensivel

### User Experience Goals
- **GUI**: Configuracao intuitiva de algoritmos
- **CLI**: Parametros flexiveis e informativos
- **Robustez**: Graceful handling de edge cases

---

## Notas de Implementacao

### Distincao CLI vs GUI vs Compartilhado

#### GUI-Specific (gui_RenameBook.py)
- Widgets de configuracao visual
- Progress bars para algoritmos
- Preview em tempo real
- Visualizacoesgraficos

#### CLI-Specific (renomeia_livro_main.py refatorado)
- Parsing de argumentos avancados
- Relatorios detalhados em texto
- Processamento batch otimizado
- Export de metricas

#### Shared (srcrenamepdfepub)
- **Todos os algoritmos de busca**
- **Logica de scoring**
- **Cache e performance optimizations**
- **Core metadata processing**

Esta separacao clara permitira implementacao eficiente mantendo codigo DRY e performance otimizada.