#!/usr/bin/env python3
"""
Launcher para Interface Web (ASCII only)
=======================================

Instala dependencias e executa a interface Streamlit
"""

import subprocess
import sys
import os
from pathlib import Path

def install_streamlit():
    """Instala Streamlit se nao estiver disponivel"""
    try:
        import streamlit
        print("[OK] Streamlit ja esta instalado")
        return True
    except ImportError:
        print("[INFO] Instalando Streamlit...")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "streamlit"
            ])
            print("[OK] Streamlit instalado com sucesso!")
            return True
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Erro ao instalar Streamlit: {e}")
            return False

def _hint_real_reports():
    """Exibe uma dica sobre geracao de relatorios reais a partir de books/."""
    reports_dir = Path(__file__).parent.parent.parent / "reports"
    print("[INFO] Para relatorios reais, use os dados gerados pelo pipeline que le a pasta books/.")
    if reports_dir.exists():
        latest = sorted(reports_dir.glob("metadata_report_*.json"))
        if latest:
            print(f"[OK] Relatorio encontrado: {latest[-1].name}")
        else:
            print("[INFO] Nenhum relatorio JSON encontrado em reports/. Execute o pipeline de extracao.")
    else:
        print("[INFO] Pasta reports/ nao encontrada. Sera criada quando o pipeline for executado.")

def launch_streamlit():
    """Executa a interface Streamlit"""
    print("Iniciando interface Streamlit...")
    print("A interface abrira no navegador.")
    print("Pressione Ctrl+C para encerrar.")
    
    # Caminho correto para o arquivo
    streamlit_file = Path(__file__).parent / "streamlit_interface.py"
    
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", 
            str(streamlit_file),
            "--server.port=8501",
            "--server.address=localhost",
            "--browser.gatherUsageStats=false"
        ])
    except KeyboardInterrupt:
        print("\nInterface encerrada")
    except Exception as e:
        print(f"Erro ao executar Streamlit: {e}")

def generate_simple_report():
    """Gera relatorio HTML simples"""
    print("[INFO] Gerando relatorio HTML...")
    try:
        # Usa o gerador de relatorios raiz (real)
        report_generator = Path(__file__).parent.parent.parent / "simple_report_generator.py"
        if report_generator.exists():
            subprocess.run([sys.executable, str(report_generator)], check=False)
        else:
            print("[INFO] Gerador simples nao encontrado no raiz. Consulte a documentacao.")
    except Exception as e:
        print(f"[WARNING] Erro ao gerar relatorio: {e}")

def run_scan_interactive():
    """Executa varredura (scan) de uma pasta gerando JSON/HTML em reports/."""
    try:
        default_dir = str((Path(__file__).parent.parent.parent / 'books').resolve())
        print("\nVarredura (scan) de metadados")
        directory = input(f"Pasta a escanear [default: {default_dir}]: ").strip() or default_dir
        recursive = input("Modo recursivo? (s/N): ").strip().lower() in {"s", "sim", "y", "yes"}
        threads_raw = input("Threads (1-16) [4]: ").strip()
        try:
            threads = max(1, min(16, int(threads_raw))) if threads_raw else 4
        except Exception:
            threads = 4

        # Usa o CLI canônico (core)
        start_cli = Path(__file__).parents[2] / 'start_cli.py'
        if not start_cli.exists():
            print("[ERROR] start_cli.py nao encontrado no raiz do projeto")
            return
        cmd = [sys.executable, str(start_cli), 'scan', directory, '-t', str(threads)]
        if recursive:
            cmd.append('-r')
        print("\nExecutando varredura...\n")
        result = subprocess.run(cmd)
        if result.returncode == 0:
            print("\n[OK] Varredura concluida. Relatorios gerados em reports/.")
        else:
            print("\n[ERROR] Falha na varredura. Verifique os logs.")
    except KeyboardInterrupt:
        print("\nOperacao cancelada")
    except Exception as e:
        print(f"[ERROR] Erro ao executar varredura: {e}")

def main():
    """Funcao principal"""
    print("=" * 60)
    print("RENAMEPDFEPUB - INTERFACE WEB LAUNCHER")
    print("=" * 60)
    
    # Menu de opcoes
    print("\nEscolha uma opcao:")
    print("1. Iniciar Interface Streamlit (recomendado)")
    print("2. Executar scan de uma pasta (gera JSON/HTML)")
    print("3. Gerar Relatorio HTML (usar ultimo JSON ou informar outro)")
    print("4. Executar teste de algoritmos (heuristico)")
    print("5. Dica sobre relatorios reais")
    print("0. Sair")
    
    try:
        choice = input("\nDigite sua escolha (0-5): ").strip()
        
        if choice == "1":
            # Instala Streamlit se necessario
            if not install_streamlit():
                print("[ERROR] Nao foi possivel instalar Streamlit")
                return
            
            # Executa interface
            launch_streamlit()
            
        elif choice == "2":
            run_scan_interactive()
        elif choice == "3":
            _hint_real_reports()
            # Permitir escolher um JSON especifico
            default_dir = str((Path(__file__).parent.parent.parent / 'reports').resolve())
            sel = input(f"Usar JSON especifico? (enter p/ padrao em {default_dir}): ").strip()
            if sel:
                # Chama o gerador com --json
                report_generator = Path(__file__).parent.parent.parent / "simple_report_generator.py"
                subprocess.run([sys.executable, str(report_generator), "--json", sel], check=False)
            else:
                generate_simple_report()
            
        elif choice == "4":
            print("[INFO] Executando teste de algoritmos...")
            print("[NOTE] Este teste usa heuristicas baseadas em nomes de arquivos.")
            print("[NOTE] Para metricas reais por conteudo, use a opcao 2 (scan).")
            try:
                # Caminho correto para o algoritmo
                algorithm_file = Path(__file__).parent.parent / "core" / "advanced_algorithm_comparison.py"
                subprocess.run([sys.executable, str(algorithm_file)])
            except Exception as e:
                print(f"[ERROR] Erro: {e}")
                
        elif choice == "5":
            _hint_real_reports()
            
        elif choice == "0":
            print("Ate logo!")
            
        else:
            print("[ERROR] Opcao invalida")
            
    except KeyboardInterrupt:
        print("\nOperacao cancelada")
    except Exception as e:
        print(f"[ERROR] Erro: {e}")

if __name__ == "__main__":
    main()
