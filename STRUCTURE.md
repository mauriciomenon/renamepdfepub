# Estrutura do Projeto RenamePDFEPUB

## Pontos de Entrada Principais

```bash
# Interface CLI
python3 cli.py

# Interface Web (Streamlit)  
python3 web.py

# Interface Gráfica
python3 gui.py

# Executar testes
python3 run_tests.py
```

## Estrutura de Diretórios

```
renamepdfepub/
├── cli.py              # Ponto de entrada CLI
├── web.py              # Ponto de entrada Web
├── gui.py              # Ponto de entrada GUI
├── run_tests.py        # Executor de testes
│
├── src/                # Código fonte
│   ├── core/          # Algoritmos e lógica principal
│   ├── cli/           # Interface linha de comando
│   └── gui/           # Interfaces gráficas
│
├── tests/             # Testes automatizados
├── docs/              # Documentação
├── logs/              # Arquivos de log
├── data/              # Dados e cache
│   ├── cache/        # Cache de metadados
│   └── results/      # Resultados de testes
│
└── reports/           # Relatórios gerados
    ├── html/         # Relatórios HTML
    └── performance/  # Análises de performance
```

## Componentes por Diretório

### src/core/ - Lógica Principal
- `advanced_algorithm_comparison.py` - 5 algoritmos especializados
- `algorithms_v3.py` - Versão 3 dos algoritmos
- `renomeia_livro.py` - Sistema legado de renomeação
- `auto_rename_system.py` - Sistema automático
- `quality_validator.py` - Validação de qualidade

### src/cli/ - Interface CLI
- `launch_system.py` - Launcher do sistema
- `demo_complete.py` - Demonstração completa
- `manual_analysis.py` - Análise manual
- `quick_validation.py` - Validação rápida

### src/gui/ - Interfaces Gráficas
- `web_launcher.py` - Launcher web
- `streamlit_interface.py` - Interface Streamlit
- `gui_modern.py` - Interface GUI moderna

### reports/ - Relatórios
- `html/` - Relatórios HTML interativos
- `performance/` - Análises de performance

### data/ - Dados
- `cache/` - Cache de metadados (*.db)
- `results/` - Resultados JSON de testes

### logs/ - Logs
- Todos os arquivos *.log centralizados

## Uso Recomendado

1. **Usuário Final**: `python3 web.py` (Interface Streamlit)
2. **Desenvolvedor**: `python3 cli.py algorithms` (Testes)
3. **Análise**: `python3 run_tests.py` (Validação)
