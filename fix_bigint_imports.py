#!/usr/bin/env python3
"""
Script per aggiungere BigInteger agli import nei file dei modelli
"""
import os
import re

models_dir = "models"

for filename in os.listdir(models_dir):
    if not filename.endswith(".py"):
        continue
    
    filepath = os.path.join(models_dir, filename)
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Check if file uses BigInteger
    if 'BigInteger' not in content:
        continue
    
    # Check if BigInteger is already imported
    if re.search(r'from sqlalchemy import.*BigInteger', content):
        print(f"✅ {filename}: BigInteger già importato")
        continue
    
    # Add BigInteger to import
    modified = False
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if line.startswith('from sqlalchemy import') and 'BigInteger' not in line:
            # Add BigInteger to the import
            if 'Integer' in line and 'BigInteger' not in line:
                lines[i] = line.replace('Integer', 'Integer, BigInteger')
                modified = True
                print(f"✅ {filename}: Aggiunto BigInteger all'import")
                break
    
    if modified:
        with open(filepath, 'w') as f:
            f.write('\n'.join(lines))

print("\n✅ Completato!")
