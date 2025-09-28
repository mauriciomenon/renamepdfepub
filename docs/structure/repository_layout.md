# Estrutura do Projeto RenamePDFEPUB

## Pontos de Entrada Principais

```bash
# Interface Web Interativa (Streamlit) - PRINCIPAL
python3 start_web.py

# Relatorios HTML Estaticos - "Pagina Antiga"
python3 start_html.py

# Interface CLI - Linha de Comando
python3 start_cli.py

# Interface Grafica Desktop
python3 start_gui.py

# Executar testes
python3 run_tests.py
```

## Estrutura de Diretorios

```
renamepdfepub/
 cli.py              # Ponto de entrada CLI
 web.py              # Ponto de entrada Web
 gui.py              # Ponto de entrada GUI
 run_tests.py        # Executor de testes

 src/                # Codigo fonte
    core/          # Algoritmos e logica principal
    cli/           # Interface linha de comando
    gui/           # Interfaces graficas

 tests/             # Testes automatizados
 docs/              # Documentacao
 logs/              # Arquivos de log
 data/              # Dados e cache
    cache/        # Cache de metadados
    results/      # Resultados de testes

 reports/           # Relatorios gerados
     html/         # Relatorios HTML
     performance/  # Analises de performance
```

## Componentes por Diretorio

### src/core/ - Logica Principal
- `advanced_algorithm_comparison.py` - 5 algoritmos especializados
- `algorithms_v3.py` - Versao 3 dos algoritmos
- `renomeia_livro.py` - Sistema legado de renomeacao
- `auto_rename_system.py` - Sistema automatico
- `quality_validator.py` - Validacao de qualidade

### src/cli/ - Interface CLI
- `launch_system.py` - Launcher do sistema
- `demo_complete.py` - Demonstracao completa
- `manual_analysis.py` - Analise manual
- `quick_validation.py` - Validacao rapida

### src/gui/ - Interfaces Graficas
- `web_launcher.py` - Launcher web
- `streamlit_interface.py` - Interface Streamlit
- `gui_modern.py` - Interface GUI moderna

### reports/ - Relatorios
- `html/` - Relatorios HTML interativos
- `performance/` - Analises de performance

### data/ - Dados
- `cache/` - Cache de metadados (*.db)
- `results/` - Resultados JSON de testes

### logs/ - Logs
- Todos os arquivos *.log centralizados

## Uso Recomendado

1. **Usuario Final**: `python3 web.py` (Interface Streamlit)
2. **Desenvolvedor**: `python3 cli.py algorithms` (Testes)
3. **Analise**: `python3 run_tests.py` (Validacao)
