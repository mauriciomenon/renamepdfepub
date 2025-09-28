#!/usr/bin/env python3
"""
RenamePDFEPUB - HTML Reports Viewer
===================================

Ponto de entrada para visualizar relatórios HTML estáticos.
Esta é a "página antiga" - relatórios HTML sem dependências.
"""

import sys
import webbrowser
from pathlib import Path

def main():
    """Interface para relatórios HTML"""
    print("RenamePDFEPUB v1.0.0 - Visualizador de Relatórios HTML")
    print("="*60)
    print()
    print("Relatórios HTML disponíveis:")
    
    html_dir = Path('reports/html')
    if not html_dir.exists():
        print("[ERROR] Diretório reports/html não encontrado")
        return
    
    html_files = list(html_dir.glob('*.html'))
    if not html_files:
        print("[ERROR] Nenhum relatório HTML encontrado")
        return
    
    for i, html_file in enumerate(html_files, 1):
        print(f"{i}. {html_file.name}")
    
    print("0. Gerar novos relatórios")
    print()
    
    try:
        choice = input("Digite sua escolha: ").strip()
        
        if choice == "0":
            generate_reports()
        elif choice.isdigit() and 1 <= int(choice) <= len(html_files):
            selected_file = html_files[int(choice) - 1]
            open_html_report(selected_file)
        else:
            print("[ERROR] Opção inválida")
            
    except KeyboardInterrupt:
        print("\nOperação cancelada")

def open_html_report(html_file):
    """Abre relatório HTML no navegador"""
    try:
        webbrowser.open(f'file://{html_file.absolute()}')
        print(f"[OK] Abrindo {html_file.name} no navegador...")
    except Exception as e:
        print(f"[ERROR] Erro ao abrir relatório: {e}")

def generate_reports():
    """Gera novos relatórios"""
    print("[INFO] Gerando novos relatórios HTML...")
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from reports.simple_report_generator import main as generate_simple
        from reports.advanced_report_generator import main as generate_advanced
        
        generate_simple()
        generate_advanced()
        print("[OK] Relatórios gerados com sucesso!")
        
    except ImportError as e:
        print(f"[ERROR] Erro ao importar geradores: {e}")
    except Exception as e:
        print(f"[ERROR] Erro ao gerar relatórios: {e}")

if __name__ == '__main__':
    main()