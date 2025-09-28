import os
print("=== VERIFICACAO DE ARQUIVOS ===")
files = ["start_cli.py", "start_web.py", "start_gui.py", "src/core/advanced_algorithm_comparison.py", "src/gui/web_launcher.py"]
for f in files:
    if os.path.exists(f):
        print(f"OK: {f}")
    else:
        print(f"MISSING: {f}")
print("=== FIM ===")