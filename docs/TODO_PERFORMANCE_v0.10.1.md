# TODO - Performance Optimization v0.10.1

## High Priority - Performance Quick Wins

### 1. PDF Text Extraction Caching
- [ ] Implementar cache baseado em hash do arquivo para texto extraido
- [ ] Adicionar TTL para cache (evitar dados obsoletos)
- [ ] Cache size limits e LRU eviction policy
- [ ] Metricas de hit rate para monitoramento

### 2. SQLite Performance Optimization 
- [ ] Adicionar PRAGMAs otimizados:
 - `PRAGMA journal_mode=WAL`
 - `PRAGMA synchronous=NORMAL`
 - `PRAGMA cache_size=10000`
 - `PRAGMA temp_store=memory`
- [ ] Connection poolingsingleton pattern para MetadataCache
- [ ] Batch insertupdate operations (reduzir transacoes)
- [ ] Indices compostos para queries complexas

### 3. Regex Compilation Optimization
- [ ] Pre-compilar todos os regex patterns como constantes de modulo
- [ ] ISBN13_RE, ISBN10_RE, title patterns compilados uma vez
- [ ] Benchmark impacto na performance de extracao
- [ ] Documentar patterns para manutencao

### 4. Database Schema Enhancements
- [ ] Adicionar FTS5 virtual table para full-text search:
 ```sql
 CREATE VIRTUAL TABLE metadata_fts USING fts5(
 title, authors, publisher, content=metadata_cache
 );
 ```
- [ ] Indices otimizados para algoritmos de busca
- [ ] Schema migration system para updates seguros

## Medium Priority - Search Algorithm Foundation

### 5. Async HTTP Operations
- [ ] Migrar requests para aiohttp (asyncawait)
- [ ] Implementar request batching quando APIs suportam
- [ ] Rate limiting inteligente com exponential backoff
- [ ] Connection pooling para HTTP calls

### 6. Advanced Search Capabilities
- [ ] Fuzzy string matching (rapidfuzz) para titulos similares
- [ ] Levenshtein distance para correcao de typos
- [ ] N-gram analysis para deteccao de similaridade
- [ ] TF-IDF scoring para relevance ranking

### 7. Memory Management
- [ ] LRU cache para consultas frequentes de metadados
- [ ] Lazy loading para datasets grandes
- [ ] Streaming JSON parsing para responses grandes
- [ ] Memory profiling e optimization

### 8. File IO Optimization
- [ ] Single-pass directory scanning (eliminar multiplas passadas)
- [ ] Cache de file metadata (size, mtime) para grouping
- [ ] Parallel directory traversal para diretorios grandes
- [ ] Bloom filters para deduplicacao rapida

## Low Priority - Advanced Features

### 9. Distributed Processing
- [ ] Multiprocessing support para CPU-bound tasks
- [ ] Worker queue system para processamento paralelo
- [ ] Progress reporting cross-process
- [ ] Resource management e cleanup

### 10. Machine Learning Integration
- [ ] ML-based titleauthor extraction para PDFs complexos
- [ ] Confidence scoring baseado em ML models
- [ ] Training data collection e model updates
- [ ] AB testing para comparar accuracy

### 11. Monitoring e Benchmarking
- [ ] Performance metrics collection
- [ ] Benchmark suite automatizado
- [ ] Performance regression testing
- [ ] Dashboard para monitoring em producao

## Testing e Validation

### 12. Performance Testing
- [ ] Benchmark suite com datasets controlados
- [ ] Memory leak detection
- [ ] Stress testing com arquivos grandes
- [ ] Regression testing para performance

### 13. Compatibility Testing
- [ ] Validar mudancas com diferentes Python versions
- [ ] Cross-platform testing (macOS, Linux, Windows)
- [ ] Dependency version compatibility
- [ ] Database migration testing

## Implementation Guidelines

### Code Quality Standards
- Manter compatibilidade total com API existente
- Adicionar type hints para novas funcoes
- Unit tests para todas as otimizacoes
- Documentation updates para mudancas de comportamento

### Performance Targets
- **PDF extraction**: 1s por arquivo (atual: 2-5s)
- **Cache lookup**: 20ms (atual: 50ms) 
- **Total throughput**: 40 arquivosminuto (atual: 15-20)
- **Memory usage**: Manter 100MB para 1000 arquivos

### Rollout Strategy
1. **Fase 1**: Quick wins (items 1-4) - Esta sprint
2. **Fase 2**: Search foundation (items 5-8) - Proxima sprint 
3. **Fase 3**: Advanced features (items 9-11) - Roadmap futuro

## Success Metrics

- [ ] 50+ reducao no tempo de extracao de metadados
- [ ] 30+ aumento no throughput total
- [ ] 5 aumento no memory footprint
- [ ] 100 backward compatibility mantida
- [ ] Zero regressao em accuracy de metadados

---

**Note**: Este TODO foca em melhorias incrementais que preparam o terreno para algoritmos avancados de buscapesquisa, mantendo a estabilidade e compatibilidade do codigo atual.