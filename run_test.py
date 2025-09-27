#!/usr/bin/env python3

import subprocess
import sys

# Test basic functionality
result = subprocess.run([sys.executable, "test_basic_functionality.py"], 
                       capture_output=True, text=True, cwd="/Users/menon/git/renamepdfepub")

print("STDOUT:")
print(result.stdout)
print("\nSTDERR:")
print(result.stderr)
print(f"\nReturn code: {result.returncode}")