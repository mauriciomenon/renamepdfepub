# Utilitarios - RenamePDFEPUB

## Ferramentas Auxiliares na Pasta utils/

### executive_test_system.py
**Funcao**: Sistema executivo de testes completos
**Uso**: Testes extensivos com 200+ livros da colecao
**Quando usar**: Validacao completa do sistema, benchmarks
```bash
python3 utils/executive_test_system.py
```

### clean_md_files.py
**Funcao**: Limpador de arquivos Markdown
**Uso**: Remove emojis e caracteres especiais dos arquivos .md
**Quando usar**: Manutencao da documentacao, padronizacao
```bash
python3 utils/clean_md_files.py
```

### verify_project.py
**Funcao**: Verificador da estrutura do projeto
**Uso**: Valida se todos os arquivos estao no lugar correto
**Quando usar**: Apos reorganizacoes, troubleshooting
```bash
python3 utils/verify_project.py
```

### reorganize_project.py
**Funcao**: Script de reorganizacao da estrutura
**Uso**: Reorganiza arquivos dispersos em estrutura profissional
**Quando usar**: Manutencao da estrutura, limpeza
```bash
python3 utils/reorganize_project.py
```

### validation_report.json
**Funcao**: Relatorio de validacao do projeto
**Uso**: Dados estruturais do projeto, metricas de validacao
**Quando usar**: Referencia para status do projeto

## Uso dos Utilitarios

### Para Desenvolvedores
```bash
# Verificar estrutura do projeto
python3 utils/verify_project.py

# Limpar documentacao
python3 utils/clean_md_files.py

# Reorganizar arquivos
python3 utils/reorganize_project.py
```

### Para Testes Extensivos
```bash
# Executar sistema de testes completo
python3 utils/executive_test_system.py
```

### Para Manutencao
```bash
# Verificar status geral
python3 utils/verify_project.py

# Ver relatorio de validacao
cat utils/validation_report.json
```

## Caracteristicas dos Utilitarios

### Independentes
- Cada utilitario funciona de forma independente
- Nao requerem configuracao especial
- Podem ser executados a qualquer momento

### Auxiliares
- Nao sao pontos de entrada principais
- Ferramentas de suporte e manutencao
- Uteis eventualmente, nao diariamente

### Organizados
- Todos centralizados na pasta utils/
- Nomes descritivos e funcoes claras
- Documentacao inline em cada arquivo

Esta organizacao mantem os utilitarios acessiveis mas separados dos pontos de entrada principais, seguindo o principio de que "pela propria organizacao da para saber para que serve".