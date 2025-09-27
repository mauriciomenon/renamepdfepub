#!/usr/bin/env python3

import subprocess
import sys

# Execute test with proper working directory
result = subprocess.run([
    sys.executable, 
    "/Users/menon/git/renamepdfepub/test_phase2_modules.py"
], capture_output=True, text=True, cwd="/Users/menon/git/renamepdfepub")

print("=== TEST OUTPUT ===")
print(result.stdout)

if result.stderr:
    print("\n=== ERRORS ===")
    print(result.stderr)

print(f"\n=== RETURN CODE: {result.returncode} ===")