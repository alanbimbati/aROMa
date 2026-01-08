#!/usr/bin/env python3
"""
Script per verificare quali personaggi hanno già un'immagine fisica
e opzionalmente caricare immagini su Telegram per ottenere il file_id.
"""

import sqlite3
import os
from pathlib import Path

def check_character_images():
    """Verifica quali personaggi hanno immagini fisiche"""
    db_path = 'points.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Prendi i primi 30 personaggi principali
    cursor.execute("""
        SELECT id, nome, image_path, telegram_file_id, character_group 
        FROM livello 
        WHERE id <= 30
        ORDER BY id
    """)
    
    characters = cursor.fetchall()
    
    print("=" * 80)
    print("🎮 STATO PERSONAGGI PRINCIPALI (ID 1-30)")
    print("=" * 80)
    
    with_images = []
    without_images = []
    
    for char_id, name, img_path, file_id, group in characters:
        has_file = img_path and os.path.exists(img_path)
        has_telegram_id = file_id is not None
        
        status = ""
        if has_file and has_telegram_id:
            status = "✅ COMPLETO"
            with_images.append(name)
        elif has_file:
            status = "📁 File presente - manca Telegram ID"
            with_images.append(name)
        else:
            status = "❌ MANCANTE"
            without_images.append(name)
        
        print(f"{char_id:2d}. {name:20s} ({group:25s}) {status}")
    
    print("\n" + "=" * 80)
    print(f"📊 STATISTICHE:")
    print("=" * 80)
    print(f"  ✅ Con immagini: {len(with_images)}/{len(characters)}")
    print(f"  ❌ Senza immagini: {len(without_images)}/{len(characters)}")
    
    if without_images:
        print(f"\n⚠️  Personaggi senza immagini:")
        for i, name in enumerate(without_images, 1):
            print(f"  {i}. {name}")
        print(f"\n💡 Consulta IMAGE_GENERATION_PROMPTS.md per i prompt di generazione!")
    
    conn.close()

def list_available_images():
    """Lista tutte le immagini presenti nella cartella images/characters"""
    img_dir = Path('images/characters')
    
    if not img_dir.exists():
        print(f"❌ Directory {img_dir} non trovata!")
        return
    
    images = sorted(img_dir.glob('*.png'))
    
    print("\n" + "=" * 80)
    print(f"🖼️  IMMAGINI DISPONIBILI IN {img_dir}")
    print("=" * 80)
    
    if not images:
        print("  📭 Nessuna immagine trovata.")
    else:
        for img in images:
            size = img.stat().st_size / 1024  # KB
            print(f"  📷 {img.name} ({size:.1f} KB)")
    
    print(f"\n  📊 Totale: {len(images)} immagini")

def update_telegram_file_id(character_id, file_id):
    """Aggiorna il telegram_file_id per un personaggio"""
    db_path = 'points.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE livello 
        SET telegram_file_id = ? 
        WHERE id = ?
    """, (file_id, character_id))
    
    conn.commit()
    
    cursor.execute("SELECT nome FROM livello WHERE id = ?", (character_id,))
    name = cursor.fetchone()[0]
    
    print(f"✅ Aggiornato Telegram file_id per {name} (ID: {character_id})")
    
    conn.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "update" and len(sys.argv) == 4:
            # Esempio: python verify_images.py update 1 "AgACAgQAAxkBAAI..."
            char_id = int(sys.argv[2])
            file_id = sys.argv[3]
            update_telegram_file_id(char_id, file_id)
        else:
            print("Uso: python verify_images.py [update <character_id> <telegram_file_id>]")
    else:
        check_character_images()
        list_available_images()
