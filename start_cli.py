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
        import os as _os
        extractor = Path(__file__).parent / 'src' / 'core' / 'renomeia_livro.py'
        if not extractor.exists():
            print("[ERROR] src/core/renomeia_livro.py não encontrado")
            sys.exit(1)
        if not extras:
            subprocess.run([sys.executable, str(extractor), '--help'])
            return
        # Support --open-report flag (handled here; stripped before forwarding)
        open_report = False
        if '--open-report' in extras:
            open_report = True
            extras = [e for e in extras if e != '--open-report']
        # Acelera em ambiente de testes (somente se não houver --limit explícito)
        if _os.environ.get('PYTEST_CURRENT_TEST') and '--limit' not in extras:
            extras = extras + ['--limit', '8']
        cmd = [sys.executable, str(extractor)] + extras
        res = subprocess.run(cmd)
        if open_report and res.returncode == 0:
            try:
                import webbrowser
                latest = sorted((Path(__file__).parent / 'reports').glob('report_*.html'))
                if latest:
                    webbrowser.open(latest[-1].as_uri())
            except Exception:
                pass

    elif args.command == 'scan-cycles':
        # Executa varreduras repetidas com o pipeline canônico do core
        import time as _time
        import os as _os
        import subprocess
        extractor = Path(__file__).parent / 'src' / 'core' / 'renomeia_livro.py'
        if not extractor.exists():
            print("[ERROR] src/core/renomeia_livro.py não encontrado")
            sys.exit(1)
        argv = extras
        open_report = False
        if '--open-report' in argv:
            open_report = True
            argv = [e for e in argv if e != '--open-report']
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
        # Limita carga em ambiente de teste se não houver --limit
        if _os.environ.get('PYTEST_CURRENT_TEST') and '--limit' not in argv:
            argv = list(argv) + ['--limit', '8']
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
        if open_report:
            try:
                import webbrowser
                latest = sorted((Path(__file__).parent / 'reports').glob('report_*.html'))
                if latest:
                    webbrowser.open(latest[-1].as_uri())
            except Exception:
                pass

    elif args.command == 'rename-existing':
        # Renomeia a partir de um relatório JSON existente (sem buscar)
        import subprocess
        import json as _json
        import time as _time
        renamer = Path(__file__).parent / 'src' / 'renamepdfepub' / 'renamer.py'
        if not renamer.exists():
            print("[ERROR] src/renamepdfepub/renamer.py não encontrado")
            sys.exit(1)
        if not extras:
            print("Uso: python start_cli.py rename-existing --report relatorio.json [--apply] [--copy] [--pattern PATTERN]")
            return
        # Aceita tanto '--report caminho' quanto '--report=caminho'
        report_path = None
        new_extras = []
        i = 0
        while i < len(extras):
            item = extras[i]
            if item.startswith('--report='):
                report_path = item.split('=', 1)[1].strip()
                i += 1
                continue
            if item == '--report' and i + 1 < len(extras):
                report_path = extras[i + 1].strip()
                i += 2
                continue
            new_extras.append(item)
            i += 1
        if not report_path:
            # Mantém compatibilidade: se usuário passou apenas caminho posicional
            if new_extras and not new_extras[0].startswith('-'):
                report_path = new_extras.pop(0)
            else:
                print("[ERROR] Caminho do relatório não informado. Use --report <arquivo.json> ou passe o caminho como primeiro argumento.")
                return
        # Se o relatório for no formato de scan (dict com successful_extractions),
        # converte para o formato esperado pelo renamer (lista de entradas)
        try:
            rp = Path(report_path)
            converted = None
            if rp.exists():
                try:
                    data = _json.loads(rp.read_text(encoding='utf-8'))
                except Exception:
                    data = None
                if isinstance(data, dict) and 'successful_extractions' in data:
                    items = []
                    for e in data.get('successful_extractions', []):
                        fp = e.get('file_path') or ''
                        if not fp:
                            continue
                        items.append({
                            'path': fp,
                            'metadata': {
                                'title': e.get('title') or '',
                                'authors': ', '.join(e.get('authors')) if isinstance(e.get('authors'), list) else (e.get('authors') or ''),
                                'publisher': e.get('publisher') or '',
                                'year': (e.get('published_date') or '').split('-')[0],
                                'isbn13': e.get('isbn_13') or '',
                                'isbn10': e.get('isbn_10') or ''
                            }
                        })
                    reports_dir = Path(__file__).parent / 'reports'
                    reports_dir.mkdir(exist_ok=True)
                    out = reports_dir / f"renamer_from_report_{_time.strftime('%Y%m%d_%H%M%S')}.json"
                    out.write_text(_json.dumps(items, ensure_ascii=False, indent=2), encoding='utf-8')
                    print(f"[INFO] Convertido relatório de scan para formato renamer: {out}")
                    report_path = str(out)
        except Exception:
            # Em caso de qualquer erro, segue com o caminho informado originalmente
            pass

        # Monta comando final: renamer.py <report> [flags]
        cmd = [sys.executable, str(renamer), report_path] + new_extras
        subprocess.run(cmd)

    elif args.command == 'rename-search':
        # Busca metadados (core) e renomeia (modo completo)
        import subprocess
        import os as _os
        extractor = Path(__file__).parent / 'src' / 'core' / 'renomeia_livro.py'
        if not extractor.exists():
            print("[ERROR] src/core/renomeia_livro.py não encontrado")
            sys.exit(1)
        argv = extras
        open_report = False
        if '--open-report' in argv:
            open_report = True
            argv = [e for e in argv if e != '--open-report']
        if '--rename' not in argv:
            argv = argv + ['--rename']
        # Limita carga em ambiente de teste se não houver --limit
        if _os.environ.get('PYTEST_CURRENT_TEST') and '--limit' not in argv:
            argv = list(argv) + ['--limit', '8']
        # Gera também um JSON padrão no diretório atual se nenhum -o/--output foi fornecido
        if not any(a in ('-o', '--output') for a in argv):
            argv = list(argv) + ['-o', 'book_metadata_report.json']
        cmd = [sys.executable, str(extractor)] + argv
        res = subprocess.run(cmd)
        if open_report and res.returncode == 0:
            try:
                import webbrowser
                latest = sorted((Path(__file__).parent / 'reports').glob('report_*.html'))
                if latest:
                    webbrowser.open(latest[-1].as_uri())
            except Exception:
                pass
    
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
    print("  python start_cli.py rename-existing --report relatorio.json --apply     # Renomear por relatório (aceita JSON do scan)")
    print("  python start_cli.py rename-search '/caminho/livros' --rename           # Buscar e renomear (gera book_metadata_report.json)")
    print("\nOutros pontos de entrada:")
    print("  python start_web.py       # Interface web Streamlit")
    print("  python start_gui.py       # Interface grafica")
    print("  python start_html.py      # Visualizador de relatorios HTML")

if __name__ == '__main__':
    main()
