# Plano de Acoes Futuras

- [ ] Refatorar `renomeia_livro.py` em modulos menores (CLI, extracao, enriquecimento, IO) mantendo cobertura de testes.
 - [ ] Identificar blocos principais (parsing CLI, orquestracao, pipelines) e mapea-los para novos modulos sob `renamepdfepub`.
 - [ ] Extrair primeiro o fluxo de entradasaida (carregamento de relatorios, escrita de logs) mantendo a API compativel.
 - [ ] Em seguida mover o pipeline de extracaoenriquecimento para funcoes puras testaveis.
 - [ ] Criar testes unitarios adicionais para cada modulo novo antes de remover o codigo original.
- [ ] Revisar configuracoes de logging para suportar rotacao e niveis configuraveis por ambiente.
- [ ] Automatizar geracao de relatorios diarios na pasta `reports` com metadados consolidados.
- [ ] Revisar requisitos de sistema (OCR, poppler, bibliotecas opcionais) e documentar alternativas multiplataforma.
- [ ] Incrementar cobertura de testes na pasta `tests`, iniciando pelos fluxos criticos de renomeacao.
