#!/usr/bin/env python3
"""
Seed chat EXP achievements into the database
"""
import sqlite3
import os
import json

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'points.db')

CHAT_ACHIEVEMENTS = [
    {
        'achievement_key': 'chatterbox_bronze',
        'name': '💬 Chiacchierone',
        'description': 'Guadagna 100 EXP chattando',
        'category': 'social',
        'tier': 'bronze',
        'trigger_event': 'chat_exp',
        'trigger_condition': json.dumps({'min_chat_exp': 100}),
        'reward_points': 50,
        'reward_title': 'Chiacchierone',
        'flavor_text': 'Le parole sono la tua arma!'
    },
    {
        'achievement_key': 'chatterbox_silver',
        'name': '💬 Oratore',
        'description': 'Guadagna 1,000 EXP chattando',
        'category': 'social',
        'tier': 'silver',
        'trigger_event': 'chat_exp',
        'trigger_condition': json.dumps({'min_chat_exp': 1000}),
        'reward_points': 100,
        'reward_title': 'Oratore',
        'flavor_text': 'La tua eloquenza non conosce limiti!'
    },
    {
        'achievement_key': 'chatterbox_gold',
        'name': '💬 Maestro della Conversazione',
        'description': 'Guadagna 10,000 EXP chattando',
        'category': 'social',
        'tier': 'gold',
        'trigger_event': 'chat_exp',
        'trigger_condition': json.dumps({'min_chat_exp': 10000}),
        'reward_points': 250,
        'reward_title': 'Maestro della Conversazione',
        'flavor_text': 'Potresti parlare per ore senza fermarti!'
    },
    {
        'achievement_key': 'chatterbox_platinum',
        'name': '💬 Leggenda della Chat',
        'description': 'Guadagna 50,000 EXP chattando',
        'category': 'social',
        'tier': 'platinum',
        'trigger_event': 'chat_exp',
        'trigger_condition': json.dumps({'min_chat_exp': 50000}),
        'reward_points': 500,
        'reward_title': 'Leggenda della Chat',
        'flavor_text': 'La chat è il tuo regno!'
    },
    {
        'achievement_key': 'social_butterfly',
        'name': '🦋 Farfalla Sociale',
        'description': 'Livella fino al livello 10 solo chattando',
        'category': 'social',
        'tier': 'gold',
        'trigger_event': 'chat_level_milestone',
        'trigger_condition': json.dumps({'min_level_from_chat': 10}),
        'reward_points': 300,
        'reward_title': 'Farfalla Sociale',
        'flavor_text': 'Chi ha bisogno di combattere quando puoi parlare?'
    }
]

def seed_achievements():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        added_count = 0
        updated_count = 0
        for ach in CHAT_ACHIEVEMENTS:
            # Extract max_progress from trigger_condition
            condition = json.loads(ach['trigger_condition'])
            max_prog = condition.get('min_chat_exp', 1)
            
            # Check if achievement already exists
            cursor.execute(
                "SELECT id FROM achievement WHERE achievement_key = ?",
                (ach['achievement_key'],)
            )
            existing = cursor.fetchone()
            
            if not existing:
                cursor.execute("""
                    INSERT INTO achievement (
                        achievement_key, name, description, category, tier,
                        trigger_event, trigger_condition, reward_points,
                        reward_title, flavor_text, is_progressive, max_progress
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    ach['achievement_key'],
                    ach['name'],
                    ach['description'],
                    ach['category'],
                    ach['tier'],
                    ach['trigger_event'],
                    ach['trigger_condition'],
                    ach['reward_points'],
                    ach.get('reward_title'),
                    ach.get('flavor_text'),
                    True, # is_progressive
                    max_prog # max_progress
                ))
                added_count += 1
                print(f"✅ Added achievement: {ach['name']}")
            else:
                # Update existing achievement to ensure correct flags
                cursor.execute("""
                    UPDATE achievement SET
                        is_progressive = ?,
                        max_progress = ?,
                        trigger_event = ?
                    WHERE achievement_key = ?
                """, (True, max_prog, ach['trigger_event'], ach['achievement_key']))
                updated_count += 1
                print(f"🔄 Updated achievement: {ach['name']}")
        
        conn.commit()
        print(f"\n✅ Seeding completed: Added {added_count}, Updated {updated_count} chat achievements")
        
    except sqlite3.Error as e:
        print(f"❌ Seeding failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    seed_achievements()
