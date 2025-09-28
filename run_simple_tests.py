#!/usr/bin/env python3
"""
Executor de Testes Simples
==========================

Executa testes básicos do repositório sem pytest complexo.
"""

import sys
import os
import subprocess
from pathlib import Path

def test_entry_points():
    """Testa entry points básicos"""
    print("=== TESTANDO ENTRY POINTS ===")
    
    root_dir = Path(__file__).parent
    python_exec = sys.executable
    
    entry_points = ["start_cli.py", "start_web.py", "start_gui.py"]
    results = {}
    
    for script in entry_points:
        script_path = root_dir / script
        print(f"\nTestando {script}...")
        
        if not script_path.exists():
            results[script] = "[X] Arquivo não existe"
            continue
        
        # Teste de sintaxe
        try:
            result = subprocess.run([
                python_exec, "-m", "py_compile", str(script_path)
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                results[script] = "[OK] Sintaxe válida"
            else:
                results[script] = f"[X] Erro sintaxe: {result.stderr[:50]}"
                
        except subprocess.TimeoutExpired:
            results[script] = "[X] Timeout na compilação"
        except Exception as e:
            results[script] = f"[X] Erro: {e}"
    
    # Resultados
    print("\nRESULTADOS DOS ENTRY POINTS:")
    for script, status in results.items():
        print(f"  {script:<20} {status}")
    
    return results

def test_structure():
    """Testa estrutura básica"""
    print("\n=== TESTANDO ESTRUTURA ===")
    
    root_dir = Path(__file__).parent
    
    required_dirs = ["src", "src/core", "src/gui", "reports", "utils", "tests"]
    results = {}
    
    for dir_name in required_dirs:
        dir_path = root_dir / dir_name
        if dir_path.exists() and dir_path.is_dir():
            py_files = len(list(dir_path.glob("*.py")))
            results[dir_name] = f"[OK] {py_files} arquivos Python"
        else:
            results[dir_name] = "[X] Diretório ausente"
    
    print("\nRESULTADOS DA ESTRUTURA:")
    for dir_name, status in results.items():
        print(f"  {dir_name:<15} {status}")
    
    return results

def test_key_files():
    """Testa arquivos-chave"""
    print("\n=== TESTANDO ARQUIVOS-CHAVE ===")
    
    root_dir = Path(__file__).parent
    
    key_files = [
        "src/core/advanced_algorithm_comparison.py",
        "src/gui/web_launcher.py",
        "src/gui/streamlit_interface.py", 
        "reports/simple_report_generator.py",
        "README.md",
        "requirements.txt",
        ".copilot-instructions.md"
    ]
    
    results = {}
    
    for file_name in key_files:
        file_path = root_dir / file_name
        if file_path.exists():
            size = file_path.stat().st_size
            results[file_name] = f"[OK] {size} bytes"
        else:
            results[file_name] = "[X] Arquivo ausente"
    
    print("\nRESULTADOS DOS ARQUIVOS-CHAVE:")
    for file_name, status in results.items():
        print(f"  {file_name:<40} {status}")
    
    return results

def test_no_emojis():
    """Testa se não há emojis em arquivos importantes"""
    print("\n=== TESTANDO AUSÊNCIA DE EMOJIS ===")
    
    root_dir = Path(__file__).parent
    
    files_to_check = [
        "utils/cross_reference_validator.py",
        "utils/quick_validation.py",
        "VALIDACAO_FINAL_REFERENCIAS.md",
        "ESTRUTURA_ATUAL_COMPLETA.md"
    ]
    
    emoji_patterns = ["✅", "❌", "🎯", "🚀", "⚠️"]
    results = {}
    
    for file_name in files_to_check:
        file_path = root_dir / file_name
        if not file_path.exists():
            results[file_name] = "[SKIP] Arquivo não existe"
            continue
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            found_emojis = []
            for emoji in emoji_patterns:
                if emoji in content:
                    found_emojis.append(emoji)
            
            if found_emojis:
                results[file_name] = f"[X] Emojis: {found_emojis}"
            else:
                results[file_name] = "[OK] Sem emojis"
                
        except Exception as e:
            results[file_name] = f"[X] Erro: {e}"
    
    print("\nRESULTADOS VERIFICAÇÃO EMOJIS:")
    for file_name, status in results.items():
        print(f"  {file_name:<40} {status}")
    
    return results

def generate_summary(all_results):
    """Gera resumo dos testes"""
    print("\n" + "="*60)
    print("RESUMO GERAL DOS TESTES")
    print("="*60)
    
    total_tests = 0
    passed_tests = 0
    
    for category, results in all_results.items():
        print(f"\n{category.upper()}:")
        category_passed = 0
        category_total = len(results)
        
        for item, status in results.items():
            total_tests += 1
            if "[OK]" in status:
                passed_tests += 1
                category_passed += 1
                print(f"  PASS: {item}")
            else:
                print(f"  FAIL: {item} - {status}")
        
        print(f"  Categoria: {category_passed}/{category_total} passou")
    
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    
    print(f"\nRESULTADO FINAL:")
    print(f"  Total: {passed_tests}/{total_tests} testes passaram")
    print(f"  Taxa de sucesso: {success_rate:.1f}%")
    
    if success_rate >= 80:
        print("  STATUS: [OK] Repositório em boa forma")
        return 0
    else:
        print("  STATUS: [X] Repositório precisa de correções") 
        return 1

def main():
    """Função principal"""
    print("EXECUTOR DE TESTES SIMPLES")
    print("Testando repositório RenamePDFEPUB")
    print("-" * 60)
    
    all_results = {}
    
    # Executa todos os testes
    all_results["Entry Points"] = test_entry_points()
    all_results["Estrutura"] = test_structure()
    all_results["Arquivos-Chave"] = test_key_files()
    all_results["Verificacao Emojis"] = test_no_emojis()
    
    # Gera resumo
    return generate_summary(all_results)

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)