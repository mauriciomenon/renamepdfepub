#!/usr/bin/env python3

# Teste rapido dos entry points
import sys
from pathlib import Path

print("Testing entry points...")

entry_points = ['start_cli.py', 'start_web.py', 'start_gui.py']

for script in entry_points:
    script_path = Path(script)
    if script_path.exists():
        print(f"✓ {script} exists")
        
        # Tenta importar como módulo
        try:
            with open(script_path, 'r') as f:
                first_lines = f.read(500)
            
            if 'import argparse' in first_lines:
                print(f"  ✓ Has argparse")
            else:
                print(f"  ✗ Missing argparse")
                
            if 'VERSION' in first_lines:
                print(f"  ✓ Has VERSION")
            else:
                print(f"  ✗ Missing VERSION")
                
        except Exception as e:
            print(f"  ✗ Error reading: {e}")
    else:
        print(f"✗ {script} missing")

# Teste referencias de arquivos
print("\nTesting file references...")

web_launcher = Path('src/gui/web_launcher.py')
if web_launcher.exists():
    print("✓ web_launcher.py exists")
    
    with open(web_launcher, 'r') as f:
        content = f.read()
    
    # Verifica referencias corrigidas
    if 'streamlit_interface.py' in content:
        print("  ✓ References streamlit_interface.py")
    
    if 'simple_report_generator.py' in content:
        print("  ✓ References simple_report_generator.py")
        
    if 'advanced_algorithm_comparison.py' in content:
        print("  ✓ References advanced_algorithm_comparison.py")

else:
    print("✗ web_launcher.py missing")

print("\nTest complete!")