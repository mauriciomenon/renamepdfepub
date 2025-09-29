# Scripts Utilitários

## Organizacao dos Scripts

## Operações Principais (Cheat Sheet)

```bash
# Scan (gera JSON/HTML, sem renomear)
python3 start_cli.py scan "/caminho/livros"      
python3 start_cli.py scan "/caminho/livros" -r   # recursivo

# Scan por ciclos/tempo
python3 start_cli.py scan-cycles "/caminho/livros" --cycles 3
python3 start_cli.py scan-cycles "/caminho/livros" --time-seconds 120

# Renomear com relatório existente
python3 start_cli.py rename-existing --report relatorio.json --apply [--copy]

# Renomear fazendo a procura (scan + rename)
python3 start_cli.py rename-search "/caminho/livros" --rename
```

## Organização dos Scripts

### Verificação e Diagnóstico
- **file_integrity_check.py** - Verifica integridade de arquivos essenciais
- **basic_system_testing.py** - Testes basicos sem pytest

### Testes Especializados
- **algorithm_comprehensive_testing.py** - Testes abrangentes dos algoritmos

## Diferença entre Tipos de Teste

### 1. Testes Principais (raiz)
```bash
python3 run_tests.py
```
- **Proposito:** Suite principal de testes com pytest
- **Cobertura:** 60 testes automatizados completos
- **Uso:** Validacao diaria e CI/CD

### 2. Testes Básicos (scripts/)
```bash  
python3 scripts/basic_system_testing.py
```
- **Proposito:** Diagnostico rapido sem dependencias
- **Cobertura:** Entry points e funcionalidade basica
- **Uso:** Troubleshooting e verificacao rapida

### 3. Testes de Algoritmos (scripts/)
```bash
python3 scripts/algorithm_comprehensive_testing.py
```
- **Proposito:** Analise detalhada de algoritmos
- **Cobertura:** Performance e acuracia dos algoritmos
- **Uso:** Desenvolvimento e otimizacao

## Como Usar

### Verificação Rápida do Sistema
```bash
# Verifica se arquivos essenciais existem
python3 scripts/file_integrity_check.py

# Testa funcionalidade basica
python3 scripts/basic_system_testing.py
```

### Desenvolvimento de Algoritmos
```bash
# Testa algoritmos especificos
python3 scripts/algorithm_comprehensive_testing.py --algorithm fuzzy
python3 scripts/algorithm_comprehensive_testing.py --target-accuracy 0.8
```

### Validação Completa
```bash
# Suite completa de testes
python3 run_tests.py
```

## Organização

Os scripts estão organizados por propósito:
- **Verificacao** - Diagnostico e integridade
- **Testes** - Diferentes niveis de teste  
- **Utilitarios** - Ferramentas auxiliares

Cada script tem nome autodescritivo que explica sua funcao.
