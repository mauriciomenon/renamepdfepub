import os
from pathlib import Path

print("=== TESTE RAPIDO ===")

# Testa entry points
entry_points = ["start_cli.py", "start_web.py", "start_gui.py"] 
print("Entry Points:")
for ep in entry_points:
    exists = os.path.exists(ep)
    print(f"  {ep}: {'[OK]' if exists else '[X]'}")

# Testa estrutura
dirs = ["src/core", "src/gui", "reports", "utils"]
print("\nEstutura:")
for d in dirs:
    exists = os.path.exists(d) and os.path.isdir(d)
    if exists:
        py_count = len([f for f in os.listdir(d) if f.endswith('.py')])
        print(f"  {d}: [OK] {py_count} arquivos py")
    else:
        print(f"  {d}: [X]")

# Testa arquivos chave  
files = ["src/core/advanced_algorithm_comparison.py", "src/gui/web_launcher.py", "README.md"]
print("\nArquivos chave:")
for f in files:
    exists = os.path.exists(f)
    print(f"  {f}: {'[OK]' if exists else '[X]'}")

print("\n=== FIM TESTE ===")