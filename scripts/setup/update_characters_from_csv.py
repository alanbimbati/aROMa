#!/usr/bin/env python3
"""
Script per aggiornare i personaggi nel database dal CSV
"""
import csv
from database import Database
from models.system import Livello

def update_characters_from_csv():
    db = Database()
    session = db.get_session()
    
    # Leggi il CSV
    with open('data/characters.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        characters_data = list(reader)
    
    print(f"📋 Trovati {len(characters_data)} personaggi nel CSV")
    
    # Cancella tutti i personaggi esistenti
    print("🗑️  Cancellazione personaggi esistenti...")
    session.query(Livello).delete()
    session.commit()
    
    # Inserisci i nuovi personaggi
    print("➕ Inserimento nuovi personaggi...")
    for char_data in characters_data:
        character = Livello(
            id=int(char_data['id']),
            nome=char_data['nome'],
            livello=int(char_data['livello']),
            lv_premium=int(char_data['lv_premium']),
            exp_required=int(char_data['exp_required']),
            special_attack_name=char_data['special_attack_name'] if char_data['special_attack_name'] else None,
            special_attack_damage=int(char_data['special_attack_damage']) if char_data['special_attack_damage'] else None,
            special_attack_mana_cost=int(char_data['special_attack_mana_cost']) if char_data['special_attack_mana_cost'] else None,
            price=int(char_data['price']),
            description=char_data['description'] if char_data['description'] else None,
            character_group=char_data['character_group'] if char_data['character_group'] else None
            # Note: max_concurrent_owners and is_pokemon are not in the database model
        )
        session.add(character)
    
    session.commit()
    print(f"✅ Aggiornati {len(characters_data)} personaggi nel database!")
    
    # Mostra alcuni esempi
    print("\n📊 Esempi di personaggi per livello:")
    for level in [1, 10, 20, 30, 50, 75, 100]:
        chars = session.query(Livello).filter_by(livello=level).all()
        if chars:
            print(f"  Lv {level}: {', '.join([c.nome for c in chars[:3]])}...")
    
    session.close()
    print("\n🎮 Database aggiornato! Riavvia il bot per vedere i cambiamenti.")

if __name__ == "__main__":
    update_characters_from_csv()
