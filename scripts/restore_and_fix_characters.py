#!/usr/bin/env python3
"""
Script per ripristinare livelli corretti e configurare required_character_id
SENZA modificare i livelli originali (che erano giusti).
"""

import csv
import sys

def fix_characters_keep_levels(input_file, backup_file, output_file):
    """
    - Ripristina livelli originali dal backup
    - Mantiene required_character_id configurati
    - Rivede livelli mob per coerenza
    """
    
    # Mapping: ID trasformato -> ID base richiesto (SOLO per reference, non blocca)
    transformations_requirements = {
        # Goku transformations
        78: 60,   # Goku SSJ -> Goku
        90: 78,   # Goku SSJ2 -> Goku SSJ
        108: 90,  # Goku SSJ3 -> Goku SSJ2
        120: 108, # Goku SSJ4 -> Goku SSJ3
        144: 120, # Goku Blue -> Goku SSJ4
        150: 144, # Goku UI -> Goku Blue
        
        # Vegeta transformations
        79: 61,   # Vegeta SSJ -> Vegeta
        91: 79,   # Vegeta SSJ2 -> Vegeta SSJ
        109: 91,  # Vegeta SSJ3 -> Vegeta SSJ2
        121: 109, # Vegeta SSJ4 -> Vegeta SSJ3
        145: 121, # Vegeta Blue -> Vegeta SSJ4
        286: 145, # Vegeta Ultra Ego -> Vegeta Blue
        
        # Gohan transformations
        80: 281,  # Gohan SSJ -> Gohan Base
        92: 80,   # Gohan SSJ2 -> Gohan SSJ
        282: 92,  # Gohan Beast -> Gohan SSJ2
        
        # Trunks transformations
        285: 284, # Trunks SSJ -> Trunks Base
        
        # Piccolo transformations
        283: 62,  # Orange Piccolo -> Piccolo
    }
    
    # Load original levels from backup
    print("📂 Loading original levels from backup...")
    backup_levels = {}
    with open(backup_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        id_idx = header.index('id')
        level_idx = header.index('livello')
        
        for row in reader:
            if not row or not row[0].strip():
                continue
            try:
                char_id = int(row[id_idx])
                level = row[level_idx]
                backup_levels[char_id] = level
            except (ValueError, IndexError):
                continue
    
    print(f"✓ Loaded {len(backup_levels)} original levels")
    
    # Process current file
    rows = []
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        rows.append(header)
        
        id_idx = header.index('id')
        level_idx = header.index('livello')
        required_char_idx = header.index('required_character_id')
        entity_type_idx = header.index('entity_type')
        
        for row in reader:
            if not row or not row[0].strip():
                continue
                
            try:
                char_id = int(row[id_idx])
            except (ValueError, IndexError):
                rows.append(row)
                continue
            
            # Set required_character_id for transformations (for reference)
            if char_id in transformations_requirements:
                row[required_char_idx] = str(transformations_requirements[char_id])
                print(f"✓ ID {char_id}: set required_character_id = {transformations_requirements[char_id]}")
            
            # Restore original level from backup if available
            if char_id in backup_levels:
                old_level = row[level_idx]
                new_level = backup_levels[char_id]
                if old_level != new_level:
                    row[level_idx] = new_level
                    print(f"✓ ID {char_id}: restored level {old_level} -> {new_level}")
            
            rows.append(row)
    
    # Write output
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    
    print(f"\n✅ Fixed CSV written to {output_file}")
    print(f"   - {len(transformations_requirements)} transformations configured")
    print(f"   - Levels restored from backup")
    print(f"   - Transformation system: flexible (no level block, mana penalty)")

if __name__ == '__main__':
    input_csv = 'data/characters.csv'
    backup_csv = 'backups/csv_backup_20260215_135842/characters.csv'
    output_csv = 'data/characters.csv'
    
    print("🔧 Restoring original levels and configuring transformations...")
    fix_characters_keep_levels(input_csv, backup_csv, output_csv)
