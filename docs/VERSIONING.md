# 📋 Sistema de Versionamento Semântico

## 🔢 Padrão de Versões

O RenamePDFEPUB segue o padrão **Semantic Versioning 2.0.0** com extensão timestamp:

```
MAJOR.MINOR.PATCH_YYYYMMDD
```

### Formato:
- **MAJOR** (1.x.x) - Mudanças incompatíveis na API
- **MINOR** (x.1.x) - Novas funcionalidades compatíveis  
- **PATCH** (x.x.1) - Correções de bugs
- **TIMESTAMP** (_20250928) - Melhorias menores do mesmo dia

## 📈 Histórico de Versões

### v1.0.0_20250928 (Atual)
- **🚀 MAJOR RELEASE** - Sistema de 5 algoritmos avançados
- **Hybrid Orchestrator** (96% accuracy)
- **Brazilian Specialist** (93% accuracy) 
- **Interface web Streamlit moderna**
- **Sistema de relatórios HTML avançado**

### v0.11.0 (Anterior)
- Implementação inicial dos algoritmos avançados
- Sistema de comparação de algoritmos

### v0.10.1
- Melhorias de performance
- Correções de bugs

### v0.10.0  
- Empacotamento do núcleo
- Reorganização da estrutura

### v0.9.1
- Organizações e limpeza
- Estrutura para refatorações

### v0.9 (GitHub Release)
- PyPDF2 → pypdf migration
- Primeira release oficial no GitHub

## 🏷️ Tags do GitHub

Para alinhar com o GitHub, criaremos as seguintes tags:

```bash
# Release atual
git tag -a v1.0.0 -m "v1.0.0 - Sistema Avançado de Algoritmos"

# Releases anteriores (se necessário)
git tag -a v0.11.0 -m "v0.11.0 - Algoritmos Avançados" 
git tag -a v0.10.1 -m "v0.10.1 - Melhorias de Performance"
git tag -a v0.10.0 -m "v0.10.0 - Empacotamento do Núcleo"
```

## 📅 Cronograma de Releases

### Próximas Versões Planejadas:

**v1.1.0** (Q4 2025)
- [ ] API REST para integração
- [ ] Processamento em lote otimizado
- [ ] Mais editoras brasileiras

**v1.2.0** (Q1 2026) 
- [ ] Algoritmo de Machine Learning
- [ ] Suporte multilíngue completo
- [ ] Integração com cloud storage

**v2.0.0** (Q2 2026)
- [ ] Interface completamente redesenhada
- [ ] Breaking changes na API
- [ ] Sistema de plugins

## 🔄 Política de Suporte

- **MAJOR**: Suporte por 2 anos
- **MINOR**: Suporte por 1 ano  
- **PATCH**: Suporte por 6 meses
- **Timestamp**: Apenas até próxima versão

## 📊 Compatibilidade

### v1.0.0_20250928
- **Python**: 3.8+
- **Dependências**: Instalação automática
- **OS**: Windows, macOS, Linux
- **Backward Compatibility**: Com v0.11.x

---

*Última atualização: 28/09/2025*