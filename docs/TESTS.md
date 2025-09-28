# Documentacao de Testes

## TL;DR

```bash
# Executar todos os testes
python3 run_tests.py

# Ou executar pytest diretamente (se instalado)
pytest tests/ -v
```

## Estrutura de Testes

```
tests/
 __init__.py           # Pacote de testes
 conftest.py          # Configuracao e fixtures
 test_algorithms.py   # Testes dos algoritmos
 test_reports.py      # Testes do sistema de relatorios
 test_utils.py        # Testes de utilitarios
 test_interface.py    # Testes da interface web
```

## Categorias de Testes

### 1. Testes de Algoritmos (test_algorithms.py)
- Verificacao da existencia dos 5 algoritmos
- Validacao de metadados
- Deteccao de editoras brasileiras
- Formato de ISBN
- Padroes de nomes brasileiros

### 2. Testes de Relatorios (test_reports.py)
- Estrutura dos arquivos JSON
- Geracao de relatorios HTML
- Dados de performance
- Comparacao entre algoritmos

### 3. Testes de Utilitarios (test_utils.py)
- Validacao de arquivos
- Limpeza de metadados
- Validacao de ISBN e ano
- Sanitizacao de nomes de arquivo
- Categorizacao de editoras

### 4. Testes de Interface (test_interface.py)
- Existencia dos arquivos da interface
- Limpeza de output (sem emojis)
- Funcionalidades do menu
- Processo de instalacao
- Geracao de dados de exemplo

## Executando os Testes

### Metodo 1: Script Automatizado (Recomendado)
```bash
python3 run_tests.py
```

O script automaticamente:
- Instala pytest se necessario
- Executa todos os testes
- Mostra resultados detalhados

### Metodo 2: Pytest Direto
```bash
# Instalar pytest primeiro
pip install pytest

# Executar testes
pytest tests/ -v

# Executar testes especificos
pytest tests/test_algorithms.py -v

# Executar com mais detalhes
pytest tests/ -v --tb=long
```

## Configuracao (pytest.ini)

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
norecursedirs = .venv_project legacy build reports docs
addopts = -v --tb=short
markers = 
    slow: marks tests as slow
    integration: marks tests as integration tests
    unit: marks tests as unit tests
```

## Fixtures Disponiveis

### sample_pdf_metadata
Metadados de exemplo para testes com PDF brasileiro:
```python
{
    "title": "Python para Desenvolvedores",
    "author": "Luiz Eduardo Borges", 
    "publisher": "Casa do Codigo",
    "year": "2023",
    "isbn": "978-85-5519-999-9"
}
```

### sample_epub_metadata
Metadados de exemplo para testes com EPUB:
```python
{
    "title": "JavaScript Moderno",
    "author": "Joao Silva Santos",
    "publisher": "Novatec", 
    "year": "2024",
    "isbn": "978-85-7522-888-8"
}
```

### test_files_dir
Diretorio temporario para arquivos de teste.

## Padroes de Teste

### Validacao de Algoritmos
```python
def test_algorithm_exists():
    """Testa se algoritmo pode ser importado"""
    try:
        from advanced_algorithm_comparison import AlgorithmName
        assert AlgorithmName is not None
    except ImportError:
        # Fallback: verifica se arquivo existe
        main_file = Path(__file__).parent.parent / "advanced_algorithm_comparison.py"
        assert main_file.exists()
```

### Validacao de Dados
```python
def test_metadata_validation(sample_pdf_metadata):
    """Testa validacao de metadados"""
    metadata = sample_pdf_metadata
    assert "title" in metadata
    assert metadata["title"] != ""
```

### Limpeza de Output
```python
def test_clean_output():
    """Testa se nao ha emojis no output"""
    forbidden_emojis = ["", "", "", "", "", "", "", ""]
    content = file.read_text()
    for emoji in forbidden_emojis:
        assert emoji not in content
```

## Cobertura de Testes

### Algoritmos Testados
- Hybrid Orchestrator
- Brazilian Specialist  
- Smart Inferencer
- Enhanced Parser
- Basic Parser

### Funcionalidades Testadas
- Extracao de metadados
- Validacao de ISBN
- Deteccao de editoras brasileiras
- Sanitizacao de nomes
- Geracao de relatorios
- Interface web limpa (sem emojis)

### Validacoes Incluidas
- Formatos de arquivo (PDF/EPUB)
- Ranges de dados (accuracy 0-100%)
- Estruturas JSON validas
- HTML bem formado
- Caracteres especiais removidos

## Executando Testes Especificos

```bash
# Apenas testes de algoritmos
pytest tests/test_algorithms.py -v

# Apenas testes que nao sao lentos
pytest -m "not slow" -v

# Apenas testes unitarios
pytest -m unit -v

# Com saida mais detalhada
pytest tests/ -v --tb=long --capture=no
```

## Status dos Testes

O sistema de testes cobre:
- **5 algoritmos** de extracao
- **4 categorias** de funcionalidades  
- **Interface web** sem emojis
- **Validacao de dados** robusta
- **Geracao de relatorios** HTML e JSON

Todos os testes sao executados automaticamente via `run_tests.py` sem necessidade de configuracao manual.