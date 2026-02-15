#!/usr/bin/env python3
"""Test character loader with new unified CSV"""
import sys
sys.path.insert(0, '/home/alan/Documenti/Coding/aroma')

from services.character_loader import get_character_loader

# Temporarily point to new CSV
import services.character_loader as cl_module
cl_module.BASE_DIR = '/home/alan/Documenti/Coding/aroma'

# Test unified CSV loading
import os
os.rename('/home/alan/Documenti/Coding/aroma/data/characters.csv',  
          '/home/alan/Documenti/Coding/aroma/data/characters_old_backup.csv')
os.rename('/home/alan/Documenti/Coding/aroma/data/characters_new.csv',
          '/home/alan/Documenti/Coding/aroma/data/characters.csv')

try:
    loader = get_character_loader()
    loader.clear_cache()
    
    print("🔄 Testing Unified CSV Loading...")
    print()
    
    # Test 1: Load all
    all_chars = loader.get_all_characters()
    print(f"✅ Total entities loaded: {len(all_chars)}")
    
    # Test 2: Get playable
    playable = loader.get_playable_characters()
    print(f"✅ Playable characters: {len(playable)}")
    
    # Test 3: Get spawnable
    spawnable = loader.get_spawnable_entities()
    print(f"✅ Spawnable entities (Evil): {len(spawnable)}")
    
    # Test 4: Get bosses
    bosses = loader.get_boss_entities()
    print(f"✅ Boss entities: {len(bosses)}")
    
    # Test 5: Get mobs
    mobs = loader.get_mob_entities()
    print(f"✅ Mob entities: {len(mobs)}")
    
    print()
    print("📊 Sample Spawnable Entity:")
    if spawnable:
        sample = spawnable[0]
        print(f"  ID: {sample['id']}")
        print(f"  Nome: {sample['nome']}")
        print(f"  Alignment: {sample.get('alignment')}")
        print(f"  Entity Type: {sample.get('entity_type')}")
        print(f"  Spawn Eligible: {sample.get('spawn_eligible')}")
        print(f"  Base Stat Multiplier: {sample.get('base_stat_multiplier')}")
    
    print()
    print("📊 Sample Boss Entity:")
    if bosses:
        sample = bosses[0]
        print(f"  ID: {sample['id']}")
        print(f"  Nome: {sample['nome']}")
        print(f"  Livello: {sample['livello']}")
        print(f"  Alignment: {sample.get('alignment')}")
        print(f"  Entity Type: {sample.get('entity_type')}")
        print(f"  Base Stat Multiplier: {sample.get('base_stat_multiplier')}")
    
    print()
    print("✅ All tests passed!")
    
finally:
    # Restore original CSV
    os.rename('/home/alan/Documenti/Coding/aroma/data/characters.csv',
              '/home/alan/Documenti/Coding/aroma/data/characters_new.csv')
    os.rename('/home/alan/Documenti/Coding/aroma/data/characters_old_backup.csv',
              '/home/alan/Documenti/Coding/aroma/data/characters.csv')
    print()
    print("🔄 CSV files restored to original state")
