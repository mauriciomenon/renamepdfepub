#!/usr/bin/env python3
"""
EXECUTOR PRINCIPAL DE TESTES - RenamePDFEPUB
===========================================

Este e o executor PRINCIPAL de testes que usa pytest para executar
a suite completa de testes automatizados do projeto.

DIFERENCA ENTRE OS TIPOS DE TESTE:

1. run_tests.py (ESTE ARQUIVO) - PRINCIPAL
   - Executor pytest padrao e oficial
   - Suite completa de testes automatizados 
   - 60 testes organizados em 6 categorias
   - Usado para validacao continua do sistema

2. scripts/basic_system_testing.py (ex: run_simple_tests.py)
   - Testes basicos SEM pytest
   - Validacao rapida de entry points
   - Verificacao de sintaxe e imports
   - Usado para diagnostico rapido

3. scripts/algorithm_comprehensive_testing.py (ex: run_comprehensive_tests.py)  
   - Testes ESPECIFICOS dos algoritmos de busca
   - Analise de performance e acuracia
   - Testes progressivos 50% -> 90%
   - Usado para desenvolvimento de algoritmos

USO RECOMENDADO:
- Desenvolvimento diario: python3 run_tests.py
- Diagnostico rapido: python3 scripts/basic_system_testing.py  
- Algoritmos: python3 scripts/algorithm_comprehensive_testing.py
"""
import subprocess
import sys
import os
from pathlib import Path

def install_pytest():
    """Instala pytest se não estiver disponível"""
    try:
        import pytest
        print("[OK] pytest já está instalado")
        return True
    except ImportError:
        print("[INFO] Instalando pytest...")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "pytest"
            ])
            print("[OK] pytest instalado com sucesso!")
            return True
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Erro ao instalar pytest: {e}")
            return False

def run_tests():
    """Executa os testes"""
    print("[INFO] Executando testes...")
    
    # Muda para o diretório do projeto
    project_dir = Path(__file__).parent
    os.chdir(project_dir)
    
    try:
        # Executa pytest
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/", 
            "-v", 
            "--tb=short"
        ], capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
            
        return result.returncode == 0
        
    except Exception as e:
        print(f"[ERROR] Erro ao executar testes: {e}")
        return False

def main():
    """Função principal"""
    print("=" * 60)
    print("RENAMEPDFEPUB - EXECUTOR DE TESTES")
    print("=" * 60)
    
    # Instala pytest se necessário
    if not install_pytest():
        print("[ERROR] Não foi possível instalar pytest")
        return 1
    
    # Executa testes
    if run_tests():
        print("[OK] Todos os testes passaram!")
        return 0
    else:
        print("[ERROR] Alguns testes falharam")
        return 1

if __name__ == "__main__":
    sys.exit(main())