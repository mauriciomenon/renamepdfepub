# Configuracoes do Sistema

## Arquivos de Configuracao

### search_algorithms.json
Configuracoes dos algoritmos de busca do sistema.

**Conteudo:**
- Parametros de similaridade para fuzzy search
- Configuracoes de threshold para ISBN search  
- Configuracoes de cache e performance
- Pesos e metricas para semantic search

**Uso:**
Os algoritmos carregam automaticamente estas configuracoes durante a execucao.

**Exemplo de estrutura:**
```json
{
  "algorithms": {
    "fuzzy": {
      "similarity_threshold": 0.6,
      "use_levenshtein": true
    },
    "isbn": {
      "partial_match_threshold": 0.8
    }
  }
}
```

## Como Modificar Configuracoes

1. **Edite o arquivo apropriado** em config/
2. **Reinicie o sistema** para aplicar mudancas
3. **Teste as mudancas** com scripts de teste

## Organizacao

Cada arquivo de configuracao tem proposito especifico:
- **search_algorithms.json** - Algoritmos de busca
- Futuros: database.json, cache.json, etc.

## Validacao

As configuracoes sao validadas automaticamente pelos algoritmos durante a carga.