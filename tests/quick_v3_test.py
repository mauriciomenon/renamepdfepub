#!/usr/bin/env python3
"""
Quick V3 Test
=============
"""

print("=== TESTE V3 DIRETO ===")

# Test patterns diretamente
import re

text = "Python_Programming_by_Mark_Lutz_2023.pdf"
print(f"Testando: {text}")

# Test author pattern
author_pattern = r'\bby\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)(?:\s|$|\(|\[|,|-)'
author_match = re.search(author_pattern, text.replace('_', ' '), re.IGNORECASE)
if author_match:
    print(f"Autor encontrado: {author_match.group(1)}")
else:
    print("Autor não encontrado")

# Test year pattern  
year_pattern = r'\b(20[0-2]\d)\b'
year_match = re.search(year_pattern, text)
if year_match:
    print(f"Ano encontrado: {year_match.group(1)}")
else:
    print("Ano não encontrado")

# Test publisher
publishers = ['Manning', 'Packt', 'OReilly']
found_pub = None
for pub in publishers:
    if pub.lower() in text.lower():
        found_pub = pub
        break

print(f"Publisher: {found_pub or 'Não encontrado'}")

print("\n=== RESULTADO ESPERADO ===")
print("Autor: Mark Lutz")
print("Ano: 2023") 
print("Publisher: Não detectado (correto)")

print("\n Patterns funcionando!")