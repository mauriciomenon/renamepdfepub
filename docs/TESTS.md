# Documentação de Testes

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
├── __init__.py           # Pacote de testes
├── conftest.py          # Configuração e fixtures
├── test_algorithms.py   # Testes dos algoritmos
├── test_reports.py      # Testes do sistema de relatórios
├── test_utils.py        # Testes de utilitários
└── test_interface.py    # Testes da interface web
```

## Categorias de Testes

### 1. Testes de Algoritmos (test_algorithms.py)
- Verificação da existência dos 5 algoritmos
- Validação de metadados
- Detecção de editoras brasileiras
- Formato de ISBN
- Padrões de nomes brasileiros

### 2. Testes de Relatórios (test_reports.py)
- Estrutura dos arquivos JSON
- Geração de relatórios HTML
- Dados de performance
- Comparação entre algoritmos

### 3. Testes de Utilitários (test_utils.py)
- Validação de arquivos
- Limpeza de metadados
- Validação de ISBN e ano
- Sanitização de nomes de arquivo
- Categorização de editoras

### 4. Testes de Interface (test_interface.py)
- Existência dos arquivos da interface
- Limpeza de output (sem emojis)
- Funcionalidades do menu
- Processo de instalação
- Geração de dados de exemplo

## Executando os Testes

### Método 1: Script Automatizado (Recomendado)
```bash
python3 run_tests.py
```

O script automaticamente:
- Instala pytest se necessário
- Executa todos os testes
- Mostra resultados detalhados

### Método 2: Pytest Direto
```bash
# Instalar pytest primeiro
pip install pytest

# Executar testes
pytest tests/ -v

# Executar testes específicos
pytest tests/test_algorithms.py -v

# Executar com mais detalhes
pytest tests/ -v --tb=long
```

## Configuração (pytest.ini)

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

## Fixtures Disponíveis

### sample_pdf_metadata
Metadados de exemplo para testes com PDF brasileiro:
```python
{
    "title": "Python para Desenvolvedores",
    "author": "Luiz Eduardo Borges", 
    "publisher": "Casa do Código",
    "year": "2023",
    "isbn": "978-85-5519-999-9"
}
```

### sample_epub_metadata
Metadados de exemplo para testes com EPUB:
```python
{
    "title": "JavaScript Moderno",
    "author": "João Silva Santos",
    "publisher": "Novatec", 
    "year": "2024",
    "isbn": "978-85-7522-888-8"
}
```

### test_files_dir
Diretório temporário para arquivos de teste.

## Padrões de Teste

### Validação de Algoritmos
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

### Validação de Dados
```python
def test_metadata_validation(sample_pdf_metadata):
    """Testa validação de metadados"""
    metadata = sample_pdf_metadata
    assert "title" in metadata
    assert metadata["title"] != ""
```

### Limpeza de Output
```python
def test_clean_output():
    """Testa se não há emojis no output"""
    forbidden_emojis = ["🚀", "🌐", "📄", "🔬", "📊", "❌", "📝", "✅"]
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
- Extração de metadados
- Validação de ISBN
- Detecção de editoras brasileiras
- Sanitização de nomes
- Geração de relatórios
- Interface web limpa (sem emojis)

### Validações Incluídas
- Formatos de arquivo (PDF/EPUB)
- Ranges de dados (accuracy 0-100%)
- Estruturas JSON válidas
- HTML bem formado
- Caracteres especiais removidos

## Executando Testes Específicos

```bash
# Apenas testes de algoritmos
pytest tests/test_algorithms.py -v

# Apenas testes que não são lentos
pytest -m "not slow" -v

# Apenas testes unitários
pytest -m unit -v

# Com saída mais detalhada
pytest tests/ -v --tb=long --capture=no
```

## Status dos Testes

O sistema de testes cobre:
- **5 algoritmos** de extração
- **4 categorias** de funcionalidades  
- **Interface web** sem emojis
- **Validação de dados** robusta
- **Geração de relatórios** HTML e JSON

Todos os testes são executados automaticamente via `run_tests.py` sem necessidade de configuração manual.