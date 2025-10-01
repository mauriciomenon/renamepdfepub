#!/usr/bin/env python3
"""
RenamePDFEPUB - CLI Interface
============================

Ponto de entrada principal para interface de linha de comando.
"""

import sys
import argparse
from pathlib import Path

# Adiciona src ao path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

VERSION = "1.4.0"

def main():
    """Interface CLI principal"""
    parser = argparse.ArgumentParser(
        description='RenamePDFEPUB - Sistema de Renomeacao de PDFs/EPUBs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python start_cli.py algorithms    # Executar algoritmos
  python start_cli.py launch        # Launcher sistema
  python start_cli.py --version     # Mostrar versao
  python start_cli.py --help        # Mostrar esta ajuda
        """
    )
    
    parser.add_argument('command', nargs='?', default='help',
                       choices=['algorithms', 'scan', 'scan-cycles', 'rename-existing', 'rename-search', 'launch', 'help'],
                       help='Comando a executar (default: help)')
    parser.add_argument('extra', nargs=argparse.REMAINDER,
                       help='Argumentos adicionais (diretorio, flags, etc.)')
    
    parser.add_argument('--version', '-v', action='version', 
                       version=f'RenamePDFEPUB v{VERSION}')
    
    args = parser.parse_args()
    
    extras = list(args.extra or [])

    if args.command == 'algorithms':
        try:
            from src.core.advanced_algorithm_comparison import main as run_algorithms
            run_algorithms()
        except ImportError as e:
            print(f"Erro ao importar algoritmos: {e}")
            print("Verifique se os arquivos estao na estrutura correta")
    
    elif args.command == 'scan':
        # Usa o pipeline canônico do core
        import subprocess
        extractor = Path(__file__).parent / 'src' / 'core' / 'renomeia_livro.py'
        if not extractor.exists():
            print("[ERROR] src/core/renomeia_livro.py não encontrado")
            sys.exit(1)
        if not extras:
            subprocess.run([sys.executable, str(extractor), '--help'])
            return
        cmd = [sys.executable, str(extractor)] + extras
        subprocess.run(cmd)

    elif args.command == 'scan-cycles':
        # Executa varreduras repetidas com o pipeline canônico do core
        import time as _time
        import subprocess
        extractor = Path(__file__).parent / 'src' / 'core' / 'renomeia_livro.py'
        if not extractor.exists():
            print("[ERROR] src/core/renomeia_livro.py não encontrado")
            sys.exit(1)
        argv = extras
        # Parâmetros opcionais: --cycles N, --time-seconds S
        def _get_flag(flag):
            if flag in argv:
                try:
                    return int(argv[argv.index(flag) + 1])
                except Exception:
                    return None
            return None
        cycles = _get_flag('--cycles') or 1
        time_limit = _get_flag('--time-seconds')
        # Remove flags do controlador antes de repassar ao extrator
        def _strip_flag_with_value(seq, flag):
            if flag in seq:
                i = seq.index(flag)
                # remove flag e possivel valor seguinte
                del seq[i:i+2]
        argv = list(argv)
        _strip_flag_with_value(argv, '--cycles')
        _strip_flag_with_value(argv, '--time-seconds')
        start = _time.time()
        i = 0
        while True:
            i += 1
            print(f"Iniciando varredura ciclo {i}...")
            subprocess.run([sys.executable, str(extractor)] + argv, check=False)
            if time_limit and (_time.time() - start) >= time_limit:
                print(f"Encerrando ciclos por limite de tempo ({time_limit}s).")
                break
            if i >= cycles:
                break
        print("Varreduras concluídas.")

    elif args.command == 'rename-existing':
        # Renomeia a partir de um relatório JSON existente (sem buscar)
        import subprocess
        renamer = Path(__file__).parent / 'src' / 'renamepdfepub' / 'renamer.py'
        if not renamer.exists():
            print("[ERROR] src/renamepdfepub/renamer.py não encontrado")
            sys.exit(1)
        if not extras:
            print("Uso: python start_cli.py rename-existing --report relatorio.json [--apply] [--copy]")
            return
        cmd = [sys.executable, str(renamer)] + extras
        subprocess.run(cmd)

    elif args.command == 'rename-search':
        # Busca metadados (core) e renomeia (modo completo)
        import subprocess
        extractor = Path(__file__).parent / 'src' / 'core' / 'renomeia_livro.py'
        if not extractor.exists():
            print("[ERROR] src/core/renomeia_livro.py não encontrado")
            sys.exit(1)
        argv = extras
        if '--rename' not in argv:
            argv = argv + ['--rename']
        cmd = [sys.executable, str(extractor)] + argv
        subprocess.run(cmd)
    
    elif args.command == 'launch':
        try:
            from src.cli.launch_system import main as launch_system
            launch_system()
        except ImportError as e:
            print(f"Erro ao importar launcher: {e}")
            print("Verifique se os arquivos estao na estrutura correta")
    
    elif args.command == 'help':
        parser.print_help()
        print_usage_examples()

def print_usage_examples():
    """Mostra exemplos de uso adicionais"""
    print("\nExemplos:")
    print("  python start_cli.py scan '/caminho/livros'             # Varredura (JSON/HTML)")
    print("  python start_cli.py scan '/caminho/livros' -r          # Varredura recursiva")
    print("  python start_cli.py scan-cycles '/caminho/livros' --cycles 3   # N ciclos")
    print("  python start_cli.py scan-cycles '/caminho/livros' --time-seconds 120   # Por tempo")
    print("  python start_cli.py rename-existing --report relatorio.json --apply     # Renomear por relatório")
    print("  python start_cli.py rename-search '/caminho/livros' --rename           # Buscar e renomear")
    print("\nOutros pontos de entrada:")
    print("  python start_web.py       # Interface web Streamlit")
    print("  python start_gui.py       # Interface grafica")
    print("  python start_html.py      # Visualizador de relatorios HTML")

if __name__ == '__main__':
    main()
