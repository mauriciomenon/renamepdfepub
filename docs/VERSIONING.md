#  Sistema de Versionamento Semantico

##  Padrao de Versoes

O RenamePDFEPUB segue o padrao **Semantic Versioning 2.0.0** com extensao timestamp:

```
MAJOR.MINOR.PATCH_YYYYMMDD
```

### Formato:
- **MAJOR** (1.x.x) - Mudancas incompativeis na API
- **MINOR** (x.1.x) - Novas funcionalidades compativeis  
- **PATCH** (x.x.1) - Correcoes de bugs
- **TIMESTAMP** (_20250928) - Melhorias menores do mesmo dia

##  Historico de Versoes

### v1.0.0_20250928 (Atual)
- ** MAJOR RELEASE** - Sistema de 5 algoritmos avancados
- **Hybrid Orchestrator** (96% accuracy)
- **Brazilian Specialist** (93% accuracy) 
- **Interface web Streamlit moderna**
- **Sistema de relatorios HTML avancado**

### v0.11.0 (Anterior)
- Implementacao inicial dos algoritmos avancados
- Sistema de comparacao de algoritmos

### v0.10.1
- Melhorias de performance
- Correcoes de bugs

### v0.10.0  
- Empacotamento do nucleo
- Reorganizacao da estrutura

### v0.9.1
- Organizacoes e limpeza
- Estrutura para refatoracoes

### v0.9 (GitHub Release)
- PyPDF2 → pypdf migration
- Primeira release oficial no GitHub

##  Tags do GitHub

Para alinhar com o GitHub, criaremos as seguintes tags:

```bash
# Release atual
git tag -a v1.0.0 -m "v1.0.0 - Sistema Avancado de Algoritmos"

# Releases anteriores (se necessario)
git tag -a v0.11.0 -m "v0.11.0 - Algoritmos Avancados" 
git tag -a v0.10.1 -m "v0.10.1 - Melhorias de Performance"
git tag -a v0.10.0 -m "v0.10.0 - Empacotamento do Nucleo"
```

##  Cronograma de Releases

### Proximas Versoes Planejadas:

**v1.1.0** (Q4 2025)
- [ ] API REST para integracao
- [ ] Processamento em lote otimizado
- [ ] Mais editoras brasileiras

**v1.2.0** (Q1 2026) 
- [ ] Algoritmo de Machine Learning
- [ ] Suporte multilingue completo
- [ ] Integracao com cloud storage

**v2.0.0** (Q2 2026)
- [ ] Interface completamente redesenhada
- [ ] Breaking changes na API
- [ ] Sistema de plugins

##  Politica de Suporte

- **MAJOR**: Suporte por 2 anos
- **MINOR**: Suporte por 1 ano  
- **PATCH**: Suporte por 6 meses
- **Timestamp**: Apenas ate proxima versao

##  Compatibilidade

### v1.0.0_20250928
- **Python**: 3.8+
- **Dependencias**: Instalacao automatica
- **OS**: Windows, macOS, Linux
- **Backward Compatibility**: Com v0.11.x

---

*Ultima atualizacao: 28/09/2025*