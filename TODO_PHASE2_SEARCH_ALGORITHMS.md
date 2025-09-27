# TODO Phase 2 - Search Algorithms Implementation

## 🎯 Objetivos da Fase 2

### Implementação de Algoritmos de Busca e Pesquisa
- **Foco principal**: Melhorias de desempenho para suporte a múltiplos algoritmos
- **Escopo**: CLI + GUI com componentes compartilhados
- **Qualidade**: Implementação longa, refinada, confiável e robusta
- **Testes**: Extensivos e criativos usando coleção books/

## 📋 TODO List Detalhado

### 🏗️ Arquitetura e Refatoração (Prioridade Alta)

#### CLI Refactoring
- [ ] **Dividir renomeia_livro.py (8536 linhas)**
  - [ ] Extrair DependencyManager → src/renamepdfepub/dependency_manager.py
  - [ ] Consolidar MetadataCache (eliminar duplicação CLI/shared)
  - [ ] Extrair EbookProcessor → src/renamepdfepub/ebook_processor.py
  - [ ] Extrair PacktBookProcessor → src/renamepdfepub/specialized_processors/
  - [ ] Manter renomeia_livro.py como script principal (~200 linhas)

#### Unificação de Componentes
- [ ] **Consolidar extratores de metadados**
  - [ ] Unificar BookMetadataExtractor (CLI) com metadata_extractor.py (shared)
  - [ ] Implementar interface consistente entre GUI e CLI
  - [ ] Otimizar cache compartilhado de texto PDF

#### Módulo de Busca Compartilhado
- [ ] **Criar src/renamepdfepub/search_algorithms/**
  - [ ] base_search.py - Interface base para algoritmos
  - [ ] fuzzy_search.py - Busca fuzzy para títulos/autores
  - [ ] isbn_search.py - Busca especializada por ISBN
  - [ ] text_similarity.py - Algoritmos de similaridade de texto
  - [ ] search_orchestrator.py - Coordenação de múltiplos algoritmos

### 🔍 Algoritmos de Busca (Prioridade Alta)

#### Algoritmos Fundamentais
- [ ] **Fuzzy String Matching**
  - [ ] Implementar Levenshtein distance
  - [ ] Implementar Jaro-Winkler similarity
  - [ ] Implementar soundex/metaphone para nomes
  - [ ] Benchmark de performance

- [ ] **Busca por Similaridade Semântica**
  - [ ] TF-IDF para comparação de títulos
  - [ ] N-gram matching para autores
  - [ ] Normalização de editoras (já existe, expandir)

- [ ] **Busca Híbrida Multi-critério**
  - [ ] Combinação ponderada de algoritmos
  - [ ] Sistema de scoring dinâmico
  - [ ] Fallback automático entre estratégias

#### Busca Especializada
- [ ] **ISBN Intelligence**
  - [ ] Validação e correção automática de ISBNs
  - [ ] Busca por ISBN parcial/corrompido
  - [ ] Cache inteligente de resultados ISBN

- [ ] **Publisher-Specific Search**
  - [ ] Extensão dos processadores Packt, O'Reilly, etc.
  - [ ] Padrões específicos por editora
  - [ ] Tratamento de edge cases por publisher

### 🖥️ Interface GUI (Prioridade Média)

#### Widgets de Configuração de Algoritmos
- [ ] **Painel de Seleção de Algoritmos**
  - [ ] Checkboxes para algoritmos disponíveis
  - [ ] Sliders para pesos/thresholds
  - [ ] Preview em tempo real de resultados

- [ ] **Visualização de Performance**
  - [ ] Gráficos de tempo de execução
  - [ ] Métricas de precisão por algoritmo
  - [ ] Comparação lado-a-lado

#### Funcionalidades Avançadas GUI
- [ ] **Modo Batch Inteligente**
  - [ ] Seleção automática de algoritmo por tipo de arquivo
  - [ ] Progress bar detalhado por algoritmo
  - [ ] Relatório de resultados por estratégia

### 🖲️ Interface CLI (Prioridade Média)

#### Parâmetros de Linha de Comando
- [ ] **Opções de Algoritmo**
  - [ ] --search-algorithm (fuzzy|semantic|hybrid|auto)
  - [ ] --fuzzy-threshold (0.0-1.0)
  - [ ] --fallback-strategy (chain|parallel|adaptive)

- [ ] **Modo Benchmark**
  - [ ] --benchmark - testa todos algoritmos
  - [ ] --compare-algorithms - comparação detalhada
  - [ ] --export-metrics - exporta resultados CSV/JSON

#### Relatórios CLI Avançados
- [ ] **Performance Analytics**
  - [ ] Tempo por algoritmo
  - [ ] Taxa de sucesso por estratégia  
  - [ ] Recomendações automáticas

### 🧪 Testing Strategy (Prioridade Alta)

#### Test Dataset (books/ directory - 100+ files)
- [ ] **Categorização de Arquivos de Teste**
  - [ ] PDFs limpos vs. escaneados
  - [ ] EPUBs com/sem metadados completos
  - [ ] Casos edge: nomes especiais, caracteres Unicode
  - [ ] Arquivos corrompidos/incompletos

#### Test Scenarios
- [ ] **Accuracy Tests**
  - [ ] Ground truth dataset com metadados validados
  - [ ] Precision/Recall por algoritmo
  - [ ] F1-score para comparação

- [ ] **Performance Tests**
  - [ ] Benchmark de tempo por algoritmo
  - [ ] Memory usage profiling
  - [ ] Concurrency stress tests

- [ ] **Edge Case Tests**
  - [ ] Títulos com caracteres especiais
  - [ ] Autores com múltiplas grafias
  - [ ] ISBNs corrompidos/parciais
  - [ ] Metadados conflitantes

#### Creative Testing Approaches
- [ ] **Algoritmos Genéticos para Otimização**
  - [ ] Evolução automática de pesos
  - [ ] Descoberta de combinações ótimas
  - [ ] Adaptação por tipo de conteúdo

- [ ] **A/B Testing Framework**
  - [ ] Comparação estatística de algoritmos
  - [ ] Significance testing
  - [ ] Automated regression detection

### 📊 Metrics & Analytics (Prioridade Média)

#### Performance Monitoring
- [ ] **Real-time Metrics**
  - [ ] Dashboard de performance em tempo real
  - [ ] Alertas para degradação de performance
  - [ ] Historical trending

- [ ] **Algorithm Effectiveness**
  - [ ] Success rate por tipo de arquivo
  - [ ] Confidence score distribution
  - [ ] False positive/negative analysis

### 🔧 Infrastructure & DevOps (Prioridade Baixa)

#### Development Tools
- [ ] **Profiling Integration**
  - [ ] cProfile integration para benchmarks
  - [ ] Memory profiling com memory_profiler
  - [ ] Visual profiling reports

- [ ] **CI/CD Enhancement**
  - [ ] Performance regression tests
  - [ ] Automated benchmarking pipeline
  - [ ] Algorithm comparison reports

## 🎯 Milestone Planning

### Milestone 1: Architecture Cleanup (1-2 weeks)
- CLI refactoring completo
- Módulos compartilhados consolidados
- Base para algoritmos de busca

### Milestone 2: Core Search Algorithms (2-3 weeks)
- Fuzzy matching implementado
- Busca semântica básica
- Sistema de scoring unificado

### Milestone 3: Advanced Features (2-3 weeks)
- GUI widgets para configuração
- CLI parâmetros avançados
- Busca híbrida multi-critério

### Milestone 4: Testing & Optimization (1-2 weeks)
- Test suite completo usando books/
- Performance benchmarking
- Documentação e refinamentos

## 🏆 Success Criteria

### Performance Goals
- **Throughput**: Manter/melhorar 75% improvement atual
- **Accuracy**: >90% precision em dataset de teste
- **Scalability**: Suporte a 1000+ arquivos simultâneos

### Quality Goals
- **Code Coverage**: >85% para novos módulos
- **Documentation**: Completa para todos algoritmos
- **Maintainability**: Modular, testável, extensível

### User Experience Goals
- **GUI**: Configuração intuitiva de algoritmos
- **CLI**: Parâmetros flexíveis e informativos
- **Robustez**: Graceful handling de edge cases

---

## 📝 Notas de Implementação

### Distinção CLI vs GUI vs Compartilhado

#### 🖥️ GUI-Specific (gui_RenameBook.py)
- Widgets de configuração visual
- Progress bars para algoritmos
- Preview em tempo real
- Visualizações/gráficos

#### 🖲️ CLI-Specific (renomeia_livro_main.py refatorado)
- Parsing de argumentos avançados
- Relatórios detalhados em texto
- Processamento batch otimizado
- Export de métricas

#### 🔗 Shared (src/renamepdfepub/)
- **Todos os algoritmos de busca**
- **Lógica de scoring**
- **Cache e performance optimizations**
- **Core metadata processing**

Esta separação clara permitirá implementação eficiente mantendo código DRY e performance otimizada.