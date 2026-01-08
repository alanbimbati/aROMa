#!/usr/bin/env python3
"""
Script completo per popolare il database con tutti i personaggi,
assegnando automaticamente i character_group e configurando le immagini.
"""

import sqlite3
import csv
import os

# Mapping dei personaggi ai loro gruppi
CHARACTER_GROUPS = {
    # Crash Bandicoot Universe
    'Crash Bandicoot': 'Crash Bandicoot',
    
    # Spyro Universe
    'Spyro': 'Spyro',
    
    # Sonic Universe
    'Sonic': 'Sonic',
    
    # Mario Universe
    'Mario': 'Super Mario',
    'Luigi': 'Super Mario',
    
    # Zelda Universe
    'Link': 'The Legend of Zelda',
    'Zelda': 'The Legend of Zelda',
    
    # Dragon Ball Universe
    'Goku': 'Dragon Ball',
    
    # Naruto Universe
    'Naruto': 'Naruto',
    
    # Final Fantasy Universe
    'Cloud Strife': 'Final Fantasy',
    'Sephiroth': 'Final Fantasy',
    
    # Metroid Universe
    'Samus Aran': 'Metroid',
    
    # Mega Man Universe
    'Mega Man': 'Mega Man',
    
    # Pokemon Universe
    'Pikachu': 'Pokémon',
    
    # Street Fighter Universe
    'Ryu': 'Street Fighter',
    
    # God of War Universe
    'Kratos': 'God of War',
    
    # Ratchet & Clank Universe
    'Ratchet': 'Ratchet & Clank',
    
    # LittleBigPlanet Universe
    'Sackboy': 'LittleBigPlanet',
    
    # Halo Universe
    'Master Chief': 'Halo',
    
    # Tomb Raider Universe
    'Lara Croft': 'Tomb Raider',
    
    # Devil May Cry Universe
    'Dante': 'Devil May Cry',
    
    # Kingdom Hearts Universe
    'Sora': 'Kingdom Hearts',
    
    # Kirby Universe
    'Kirby': 'Kirby',
    
    # Donkey Kong Universe
    'Donkey Kong': 'Donkey Kong',
    
    # Pac-Man Universe
    'Pac-Man': 'Pac-Man',
    
    # Metal Gear Universe
    'Snake': 'Metal Gear',
    
    # Persona Universe
    'Joker': 'Persona',
    
    # NieR Universe
    '2B': 'NieR',
    
    # The Witcher Universe
    'Geralt': 'The Witcher',
    
    # DOOM Universe
    'Doom Slayer': 'DOOM',
}

def get_image_path(character_id, character_name):
    """Generate image path for character"""
    # Converti nome in formato file (snake_case)
    safe_name = character_name.lower().replace(' ', '_').replace('-', '_')
    return f"images/characters/{character_id}_{safe_name}.png"

def populate_all_characters():
    """Populate livello table with all character data including groups"""
    db_path = 'points.db'
    csv_path = 'data/characters.csv'
    
    if not os.path.exists(csv_path):
        print(f"❌ File {csv_path} non trovato!")
        return
    
    if not os.path.exists(db_path):
        print(f"❌ Database {db_path} non trovato!")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("🔄 Popolamento database personaggi...\n")
    
    # Verifica se la colonna character_group esiste
    cursor.execute("PRAGMA table_info(livello)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'character_group' not in columns:
        print("⚠️  Colonna 'character_group' non trovata. Aggiungendola...")
        cursor.execute("ALTER TABLE livello ADD COLUMN character_group TEXT DEFAULT 'General'")
        conn.commit()
        print("✅ Colonna aggiunta!\n")
    
    if 'image_path' not in columns:
        print("⚠️  Colonna 'image_path' non trovata. Aggiungendola...")
        cursor.execute("ALTER TABLE livello ADD COLUMN image_path TEXT")
        conn.commit()
        print("✅ Colonna aggiunta!\n")
    
    # Leggi CSV e popola
    updated_count = 0
    added_count = 0
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            char_name = row['nome']
            char_id = int(row['id'])
            
            # Ottieni il gruppo del personaggio
            char_group = CHARACTER_GROUPS.get(char_name, 'General')
            
            # Genera path immagine
            img_path = get_image_path(char_id, char_name)
            
            # Verifica se esiste già
            cursor.execute("SELECT id FROM livello WHERE id = ?", (char_id,))
            exists = cursor.fetchone()
            
            if exists:
                # Aggiorna esistente
                cursor.execute("""
                    UPDATE livello SET
                        nome = ?,
                        livello = ?,
                        lv_premium = ?,
                        exp_required = ?,
                        special_attack_name = ?,
                        special_attack_damage = ?,
                        special_attack_mana_cost = ?,
                        price = ?,
                        description = ?,
                        character_group = ?,
                        image_path = ?
                    WHERE id = ?
                """, (
                    char_name,
                    int(row['livello']),
                    int(row['lv_premium']),
                    int(row['exp_required']),
                    row['special_attack_name'],
                    int(row['special_attack_damage']),
                    int(row['special_attack_mana_cost']),
                    int(row['price']),
                    row['description'],
                    char_group,
                    img_path,
                    char_id
                ))
                print(f"  ♻️  Aggiornato: {char_name} ({char_group})")
                updated_count += 1
            else:
                # Inserisci nuovo
                cursor.execute("""
                    INSERT INTO livello (
                        id, nome, livello, lv_premium, exp_required,
                        special_attack_name, special_attack_damage,
                        special_attack_mana_cost, price, description,
                        character_group, image_path
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    char_id,
                    char_name,
                    int(row['livello']),
                    int(row['lv_premium']),
                    int(row['exp_required']),
                    row['special_attack_name'],
                    int(row['special_attack_damage']),
                    int(row['special_attack_mana_cost']),
                    int(row['price']),
                    row['description'],
                    char_group,
                    img_path
                ))
                print(f"  ✅ Aggiunto: {char_name} ({char_group})")
                added_count += 1
    
    conn.commit()
    
    # Statistiche finali
    print(f"\n{'='*60}")
    print(f"✅ COMPLETATO!")
    print(f"{'='*60}")
    print(f"  📊 Personaggi aggiunti: {added_count}")
    print(f"  🔄 Personaggi aggiornati: {updated_count}")
    print(f"  📈 Totale: {added_count + updated_count}")
    
    # Mostra riepilogo per gruppo
    print(f"\n{'='*60}")
    print("📚 PERSONAGGI PER GRUPPO:")
    print(f"{'='*60}")
    
    cursor.execute("""
        SELECT character_group, COUNT(*) as count 
        FROM livello 
        GROUP BY character_group 
        ORDER BY count DESC, character_group
    """)
    
    for group, count in cursor.fetchall():
        print(f"  🎮 {group}: {count} personaggi")
    
    # Lista personaggi senza immagine fisica
    print(f"\n{'='*60}")
    print("🖼️  STATO IMMAGINI:")
    print(f"{'='*60}")
    
    cursor.execute("SELECT nome, image_path FROM livello ORDER BY id")
    missing_images = []
    
    for name, img_path in cursor.fetchall():
        if img_path and os.path.exists(img_path):
            print(f"  ✅ {name}: {img_path}")
        else:
            print(f"  ⚠️  {name}: {img_path} (file mancante)")
            missing_images.append(name)
    
    if missing_images:
        print(f"\n⚠️  {len(missing_images)} personaggi senza immagine fisica.")
        print("   Consulta IMAGE_GENERATION_PROMPTS.md per generare le immagini mancanti.")
    
    conn.close()

if __name__ == "__main__":
    populate_all_characters()
