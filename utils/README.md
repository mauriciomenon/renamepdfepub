# Utilitários - RenamePDFEPUB

## Ferramentas Auxiliares na Pasta utils/

### executive_test_system.py
**Função**: Sistema executivo de testes completos
**Uso**: Testes extensivos com 200+ livros da coleção
**Quando usar**: Validação completa do sistema, benchmarks
```bash
python3 utils/executive_test_system.py
```

### clean_md_files.py
**Função**: Limpador de arquivos Markdown
**Uso**: Remove emojis e caracteres especiais dos arquivos .md
**Quando usar**: Manutenção da documentação, padronização
```bash
python3 utils/clean_md_files.py
```

### verify_project.py
**Função**: Verificador da estrutura do projeto
**Uso**: Valida se todos os arquivos estão no lugar correto
**Quando usar**: Após reorganizações, troubleshooting
```bash
python3 utils/verify_project.py
```

### reorganize_project.py
**Função**: Script de reorganização da estrutura
**Uso**: Reorganiza arquivos dispersos em estrutura profissional
**Quando usar**: Manutenção da estrutura, limpeza
```bash
python3 utils/reorganize_project.py
```

### validation_report.json
**Função**: Relatório de validação do projeto
**Uso**: Dados estruturais do projeto, métricas de validação
**Quando usar**: Referência para status do projeto

## Uso dos Utilitários

### Para Desenvolvedores
```bash
# Verificar estrutura do projeto
python3 utils/verify_project.py

# Limpar documentação
python3 utils/clean_md_files.py

# Reorganizar arquivos
python3 utils/reorganize_project.py
```

### Para Testes Extensivos
```bash
# Executar sistema de testes completo
python3 utils/executive_test_system.py
```

### Para Manutenção
```bash
# Verificar status geral
python3 utils/verify_project.py

# Ver relatório de validação
cat utils/validation_report.json
```

## Características dos Utilitários

### Independentes
- Cada utilitário funciona de forma independente
- Não requerem configuração especial
- Podem ser executados a qualquer momento

### Auxiliares
- Não são pontos de entrada principais
- Ferramentas de suporte e manutenção
- Úteis eventualmente, não diariamente

### Organizados
- Todos centralizados na pasta utils/
- Nomes descritivos e funções claras
- Documentação inline em cada arquivo

Esta organização mantém os utilitários acessíveis mas separados dos pontos de entrada principais, seguindo o princípio de que "pela própria organização dá para saber para que serve".