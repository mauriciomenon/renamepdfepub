#!/usr/bin/env python3
"""
Script de reorganização da estrutura do projeto RenamePDFEPUB
===============================================================

Reorganiza arquivos dispersos em uma estrutura profissional e rastreável.
"""

import os
import shutil
from pathlib import Path

def reorganize_project():
    """Reorganiza toda a estrutura do projeto"""
    
    print("[INFO] Iniciando reorganização da estrutura do projeto...")
    
    # Mapas de reorganização
    file_mappings = {
        # CORE - Algoritmos principais e lógica de negócio
        'src/core/': [
            'advanced_algorithm_comparison.py',
            'algorithms_v3.py', 
            'renomeia_livro.py',
            'auto_rename_system.py',
            'amazon_api_integration.py',
            'metadata_*.py',  # todos os metadata_*.py
            'quality_validator.py',
            'performance_analyzer.py'
        ],
        
        # CLI - Interface de linha de comando
        'src/cli/': [
            'launch_system.py',
            'demo_complete.py',
            'manual_analysis.py',
            'quick_validation.py',
            'rigorous_validation.py',
            'validate_*.py'  # todos os validate_*.py
        ],
        
        # GUI - Interfaces gráficas
        'src/gui/': [
            'web_launcher.py',
            'streamlit_interface.py', 
            'gui_modern.py',
            'gui_RenameBook.py'
        ],
        
        # REPORTS - Geradores de relatórios
        'reports/': [
            'simple_report_generator.py',
            'advanced_report_generator.py',
            'final_report.py',
            'final_summary.py'
        ],
        
        # TESTS - Testes organizados (já existe)
        # tests/ já está organizado
        
        # DATA/CACHE - Dados e cache
        'data/cache/': [
            '*.db',  # todos os .db
            '*.cache'
        ],
        
        # DATA/RESULTS - Resultados de testes
        'data/results/': [
            '*_results.json',
            '*_test_results*.json',
            'demo_results.json'
        ],
        
        # REPORTS/HTML - Relatórios HTML
        'reports/html/': [
            '*.html'
        ],
        
        # REPORTS/PERFORMANCE - Análises de performance  
        'reports/performance/': [
            '*_results.txt',
            'advanced_algorithm_results.txt',
            'multi_algorithm_results.txt'
        ],
        
        # LOGS - Arquivos de log
        'logs/': [
            '*.log'
        ]
    }
    
    # Executa reorganização
    for target_dir, patterns in file_mappings.items():
        target_path = Path(target_dir)
        target_path.mkdir(parents=True, exist_ok=True)
        
        for pattern in patterns:
            if '*' in pattern:
                # Padrão com wildcard
                import glob
                matches = glob.glob(pattern)
                for match in matches:
                    if Path(match).is_file():
                        move_file(match, target_path)
            else:
                # Arquivo específico
                if Path(pattern).exists():
                    move_file(pattern, target_path)
    
    # Limpa arquivos de teste dispersos
    cleanup_test_files()
    
    # Cria pontos de entrada principais
    create_entry_points()
    
    print("[OK] Reorganização concluída!")

def move_file(source, target_dir):
    """Move arquivo para diretório de destino"""
    source_path = Path(source)
    target_path = target_dir / source_path.name
    
    if source_path.exists() and source_path.is_file():
        try:
            shutil.move(str(source_path), str(target_path))
            print(f"[OK] Movido: {source} -> {target_path}")
        except Exception as e:
            print(f"[WARNING] Erro ao mover {source}: {e}")

def cleanup_test_files():
    """Remove arquivos de teste dispersos no root"""
    test_patterns = [
        'test_*.py',
        '*_test.py', 
        'quick_test*.py',
        'simple_test*.py',
        'comprehensive_test*.py',
        'real_*_test*.py',
        'final_v3_test.py',
        'improved_*test*.py'
    ]
    
    print("[INFO] Limpando arquivos de teste dispersos...")
    
    import glob
    for pattern in test_patterns:
        matches = glob.glob(pattern)
        for match in matches:
            try:
                # Move para tests/ se não estiver lá
                target = Path('tests') / Path(match).name
                if not target.exists():
                    shutil.move(match, str(target))
                    print(f"[OK] Movido teste: {match} -> {target}")
                else:
                    # Remove duplicata
                    os.remove(match)
                    print(f"[OK] Removido duplicata: {match}")
            except Exception as e:
                print(f"[WARNING] Erro ao limpar {match}: {e}")

def create_entry_points():
    """Cria pontos de entrada principais"""
    
    # CLI principal
    cli_main = """#!/usr/bin/env python3
'''
RenamePDFEPUB - CLI Interface
============================

Ponto de entrada principal para interface de linha de comando.
'''

import sys
from pathlib import Path

# Adiciona src ao path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.core.advanced_algorithm_comparison import main as run_algorithms
from src.cli.launch_system import main as launch_system

def main():
    '''Interface CLI principal'''
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == 'algorithms':
            run_algorithms()
        elif command == 'launch':
            launch_system()
        else:
            print_help()
    else:
        print_help()

def print_help():
    '''Mostra ajuda'''
    print("RenamePDFEPUB - Sistema de Renomeação de PDFs/EPUBs")
    print()
    print("Uso:")
    print("  python3 cli.py algorithms  # Executar algoritmos")
    print("  python3 cli.py launch      # Launcher sistema")
    print("  python3 web.py             # Interface web")
    print("  python3 gui.py             # Interface gráfica")

if __name__ == '__main__':
    main()
"""
    
    # Interface web
    web_main = """#!/usr/bin/env python3
'''
RenamePDFEPUB - Web Interface
============================

Ponto de entrada para interface web Streamlit.
'''

import sys
from pathlib import Path

# Adiciona src ao path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.gui.web_launcher import main

if __name__ == '__main__':
    main()
"""
    
    # Interface GUI
    gui_main = """#!/usr/bin/env python3
'''
RenamePDFEPUB - GUI Interface
============================

Ponto de entrada para interface gráfica.
'''

import sys
from pathlib import Path

# Adiciona src ao path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

try:
    from src.gui.gui_modern import main
    main()
except ImportError:
    print("[ERROR] Interface gráfica requer dependências adicionais")
    print("Execute: pip install tkinter")
"""
    
    # Escreve arquivos
    Path('cli.py').write_text(cli_main)
    Path('web.py').write_text(web_main)  
    Path('gui.py').write_text(gui_main)
    
    print("[OK] Pontos de entrada criados: cli.py, web.py, gui.py")

def create_structure_readme():
    """Cria README da nova estrutura"""
    
    readme_content = """# Estrutura do Projeto RenamePDFEPUB

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
"""
    
    Path('STRUCTURE.md').write_text(readme_content)
    print("[OK] Documentação da estrutura criada: STRUCTURE.md")

if __name__ == '__main__':
    reorganize_project()
    create_structure_readme()
    print()
    print("=" * 60)
    print("REORGANIZAÇÃO COMPLETA!")
    print("=" * 60)
    print()
    print("Novos pontos de entrada:")
    print("  python3 web.py    # Interface Web (Streamlit)")
    print("  python3 cli.py    # Interface CLI")
    print("  python3 gui.py    # Interface Gráfica")
    print()
    print("Estrutura organizada em:")
    print("  src/core/        # Algoritmos principais")
    print("  src/cli/         # Interface CLI") 
    print("  src/gui/         # Interfaces gráficas")
    print("  reports/         # Relatórios HTML/Performance")
    print("  data/            # Cache e resultados")
    print("  logs/            # Arquivos de log")
    print()