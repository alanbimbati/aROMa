#!/usr/bin/env python3
"""
Seed new declarative achievements into the database.
"""
import sqlite3
import os
import json

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'points.db')

ACHIEVEMENTS = [
    {
        'key': 'butcher',
        'name': '🔪 Macellaio',
        'description': 'Uccidi mostri per dimostrare la tua forza.',
        'stat_key': 'total_kills',
        'condition_type': '>=',
        'category': 'classici',
        'tiers': {
            'bronze': {'threshold': 100, 'rewards': {'exp': 100, 'title': 'Macellaio Principiante'}},
            'silver': {'threshold': 500, 'rewards': {'exp': 300, 'title': 'Macellaio Esperto'}},
            'gold': {'threshold': 1000, 'rewards': {'exp': 500, 'title': 'Sterminatore'}},
            'diamond': {'threshold': 5000, 'rewards': {'exp': 1000, 'title': 'Leggenda del Sangue'}}
        }
    },
    {
        'key': 'colossus_killer',
        'name': '👹 Colosso Killer',
        'description': 'Uccidi mostri molto più forti di te (Livello +10).',
        'stat_key': 'high_level_kills',
        'condition_type': '>=',
        'category': 'classici',
        'tiers': {
            'bronze': {'threshold': 10, 'rewards': {'exp': 100, 'title': 'Coraggioso'}},
            'silver': {'threshold': 50, 'rewards': {'exp': 300, 'title': 'Eroico'}},
            'gold': {'threshold': 100, 'rewards': {'exp': 500, 'title': 'Leggendario'}},
            'diamond': {'threshold': 250, 'rewards': {'exp': 1000, 'title': 'Uccisore di Giganti'}}
        }
    },
    {
        'key': 'one_shot_one_kill',
        'name': '🎯 One Shot, One Kill',
        'description': 'Elimina i nemici con un solo colpo.',
        'stat_key': 'one_shots',
        'condition_type': '>=',
        'category': 'classici',
        'tiers': {
            'bronze': {'threshold': 20, 'rewards': {'exp': 100, 'title': 'Cecchino'}},
            'silver': {'threshold': 100, 'rewards': {'exp': 300, 'title': 'Infallibile'}},
            'gold': {'threshold': 500, 'rewards': {'exp': 500, 'title': 'Morte Istantanea'}},
            'diamond': {'threshold': 1000, 'rewards': {'exp': 1000, 'title': 'Fantasma della Morte'}}
        }
    },
    {
        'key': 'dungeon_master',
        'name': '🏰 Dungeon Master',
        'description': 'Completa i dungeon.',
        'stat_key': 'dungeons_completed',
        'condition_type': '>=',
        'category': 'classici',
        'tiers': {
            'bronze': {'threshold': 5, 'rewards': {'exp': 100, 'title': 'Esploratore'}},
            'silver': {'threshold': 25, 'rewards': {'exp': 300, 'title': 'Veterano dei Dungeon'}},
            'gold': {'threshold': 50, 'rewards': {'exp': 500, 'title': 'Signore dei Dungeon'}},
            'diamond': {'threshold': 100, 'rewards': {'exp': 1000, 'title': 'Architetto del Destino'}}
        }
    },
    {
        'key': 'chatterbox',
        'name': '💬 Chiacchierone',
        'description': 'Guadagna EXP chattando.',
        'stat_key': 'total_chat_exp',
        'condition_type': '>=',
        'category': 'classici',
        'tiers': {
            'bronze': {'threshold': 1000, 'rewards': {'exp': 100, 'title': 'Chiacchierone'}},
            'silver': {'threshold': 10000, 'rewards': {'exp': 300, 'title': 'Oratore'}},
            'gold': {'threshold': 50000, 'rewards': {'exp': 500, 'title': 'Maestro della Parola'}},
            'diamond': {'threshold': 100000, 'rewards': {'exp': 1000, 'title': 'Voce dell''Infinito'}}
        }
    },
    {
        'key': 'wumpa_collector',
        'name': '🍑 Collezionista di Wumpa',
        'description': 'Accumula una fortuna in Wumpa.',
        'stat_key': 'total_wumpa_earned',
        'condition_type': '>=',
        'category': 'classici',
        'tiers': {
            'bronze': {'threshold': 1000, 'rewards': {'exp': 100, 'title': 'Risparmiatore'}},
            'silver': {'threshold': 10000, 'rewards': {'exp': 300, 'title': 'Mercante'}},
            'gold': {'threshold': 50000, 'rewards': {'exp': 500, 'title': 'Magnate'}},
            'diamond': {'threshold': 100000, 'rewards': {'exp': 1000, 'title': 'Re Mida'}}
        }
    },
    {
        'key': 'boss_slayer',
        'name': '👑 Sterminatore di Boss',
        'description': 'Sconfiggi i boss più temibili.',
        'stat_key': 'boss_kills',
        'condition_type': '>=',
        'category': 'classici',
        'tiers': {
            'bronze': {'threshold': 5, 'rewards': {'exp': 100, 'title': 'Cacciatore di Teste'}},
            'silver': {'threshold': 20, 'rewards': {'exp': 300, 'title': 'Flagello dei Re'}},
            'gold': {'threshold': 50, 'rewards': {'exp': 500, 'title': 'Divoratore di Dei'}},
            'diamond': {'threshold': 100, 'rewards': {'exp': 1000, 'title': 'Senza Pari'}}
        }
    },
    {
        'key': 'critical_master',
        'name': '✨ Maestro dei Critici',
        'description': 'Metti a segno colpi critici devastanti.',
        'stat_key': 'critical_hits',
        'condition_type': '>=',
        'category': 'classici',
        'tiers': {
            'bronze': {'threshold': 50, 'rewards': {'exp': 100, 'title': 'Preciso'}},
            'silver': {'threshold': 250, 'rewards': {'exp': 300, 'title': 'Letale'}},
            'gold': {'threshold': 1000, 'rewards': {'exp': 500, 'title': 'Chirurgo'}},
            'diamond': {'threshold': 2500, 'rewards': {'exp': 1000, 'title': 'Punto Debole'}}
        }
    },
    {
        'key': 'potion_addict',
        'name': '🧪 Alchimista',
        'description': 'Usa oggetti e pozioni per sopravvivere.',
        'stat_key': 'item_used',
        'condition_type': '>=',
        'category': 'classici',
        'tiers': {
            'bronze': {'threshold': 10, 'rewards': {'exp': 100, 'title': 'Sperimentatore'}},
            'silver': {'threshold': 50, 'rewards': {'exp': 300, 'title': 'Speziale'}},
            'gold': {'threshold': 200, 'rewards': {'exp': 500, 'title': 'Alchimista'}},
            'diamond': {'threshold': 500, 'rewards': {'exp': 1000, 'title': 'Maestro delle Pozioni'}}
        }
    },
    {
        'key': 'tank',
        'name': '🛡️ Scudo Vivente',
        'description': 'Subisci danni massicci e rimani in piedi.',
        'stat_key': 'damage_received',
        'condition_type': '>=',
        'category': 'classici',
        'tiers': {
            'bronze': {'threshold': 5000, 'rewards': {'exp': 100, 'title': 'Resistente'}},
            'silver': {'threshold': 25000, 'rewards': {'exp': 300, 'title': 'Incrollabile'}},
            'gold': {'threshold': 100000, 'rewards': {'exp': 500, 'title': 'Baluardo'}},
            'diamond': {'threshold': 500000, 'rewards': {'exp': 1000, 'title': 'Invincibile'}}
        }
    },
    {
        'key': 'level_master',
        'name': '🆙 Maestro del Livello',
        'description': 'Raggiungi nuove vette di potere.',
        'stat_key': 'level_up',
        'condition_type': '>=',
        'category': 'classici',
        'tiers': {
            'bronze': {'threshold': 10, 'rewards': {'exp': 100, 'title': 'Promessa'}},
            'silver': {'threshold': 25, 'rewards': {'exp': 300, 'title': 'Veterano'}},
            'gold': {'threshold': 50, 'rewards': {'exp': 500, 'title': 'Eroe'}},
            'diamond': {'threshold': 100, 'rewards': {'exp': 1000, 'title': 'Semidio'}}
        }
    },
    {
        'key': 'mio_fratello',
        'name': '👨‍👦 Mio fratello!',
        'description': 'Sconfiggi Raditz per la prima volta.',
        'stat_key': 'kill_raditz',
        'condition_type': '>=',
        'category': 'dragon_ball',
        'tiers': {
            'bronze': {'threshold': 1, 'rewards': {'exp': 200, 'title': 'Fratricida'}}
        }
    },
    {
        'key': 'pure_saiyan',
        'name': '🥦 Sono un puro Saiyan',
        'description': 'Sblocca il leggendario Broly.',
        'stat_key': 'unlock_broly',
        'condition_type': '>=',
        'category': 'dragon_ball',
        'tiers': {
            'bronze': {'threshold': 1, 'rewards': {'exp': 500, 'title': 'Saiyan Leggendario'}}
        }
    },
    {
        'key': 'android_slayer',
        'name': '🤖 Sterminatore di Androidi',
        'description': 'Sconfiggi gli Androidi della Red Ribbon.',
        'stat_key': 'android_kills',
        'condition_type': '>=',
        'category': 'dragon_ball',
        'tiers': {
            'bronze': {'threshold': 4, 'rewards': {'exp': 400, 'title': 'Distruttore di Circuiti'}}
        }
    },
    {
        'key': 'living_legend',
        'name': '🌌 Leggenda Vivente',
        'description': 'Sblocca la forma definitiva: Goku Ultra Istinto.',
        'stat_key': 'unlock_goku_ultra_instinct',
        'condition_type': '>=',
        'category': 'dragon_ball',
        'tiers': {
            'bronze': {'threshold': 1, 'rewards': {'exp': 1000, 'title': 'Oltre il Limite'}}
        }
    },
    {
        'key': 'dragon_ball_hunter',
        'name': '🔮 Cacciatore di Sfere',
        'description': 'Raccogli le leggendarie Sfere del Drago.',
        'stat_key': 'dragon_balls_collected',
        'condition_type': '>=',
        'category': 'dragon_ball',
        'tiers': {
            'bronze': {'threshold': 7, 'rewards': {'exp': 200, 'title': 'Cercatore di Sfere'}},
            'silver': {'threshold': 21, 'rewards': {'exp': 500, 'title': 'Collezionista di Sfere'}},
            'gold': {'threshold': 49, 'rewards': {'exp': 1000, 'title': 'Maestro delle Sfere'}}
        }
    },
    {
        'key': 'shenron_summoner',
        'name': '🐉 Desiderio di Shenron',
        'description': 'Evoca il drago Shenron per esaudire i tuoi desideri.',
        'stat_key': 'shenron_summons',
        'condition_type': '>=',
        'category': 'dragon_ball',
        'tiers': {
            'bronze': {'threshold': 1, 'rewards': {'exp': 300, 'title': 'Evocatore di Shenron'}},
            'silver': {'threshold': 5, 'rewards': {'exp': 700, 'title': 'Amico dei Draghi'}},
            'gold': {'threshold': 10, 'rewards': {'exp': 1500, 'title': 'Signore dei Desideri'}}
        }
    },
    {
        'key': 'porunga_summoner',
        'name': '🐸 Desiderio di Porunga',
        'description': 'Evoca il drago Porunga su Namecc.',
        'stat_key': 'porunga_summons',
        'condition_type': '>=',
        'category': 'dragon_ball',
        'tiers': {
            'bronze': {'threshold': 1, 'rewards': {'exp': 500, 'title': 'Evocatore di Porunga'}},
            'silver': {'threshold': 3, 'rewards': {'exp': 1000, 'title': 'Viaggiatore di Namecc'}},
            'gold': {'threshold': 7, 'rewards': {'exp': 2000, 'title': 'Eroe di Namecc'}}
        }
    }
]

def seed():
    print(f"Seeding achievements to {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        count = 0
        for ach in ACHIEVEMENTS:
            # Check if exists
            cursor.execute("SELECT id FROM achievement WHERE achievement_key = ?", (ach['key'],))
            existing = cursor.fetchone()
            
            if not existing:
                cursor.execute("""
                    INSERT INTO achievement (
                        achievement_key, name, description, stat_key, 
                        condition_type, tiers, category
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    ach['key'], ach['name'], ach['description'], ach['stat_key'],
                    ach['condition_type'], json.dumps(ach['tiers']), ach['category']
                ))
                count += 1
                print(f"✅ Added: {ach['name']}")
            else:
                # Update logic
                cursor.execute("""
                    UPDATE achievement SET
                        name = ?, description = ?, stat_key = ?,
                        condition_type = ?, tiers = ?, category = ?
                    WHERE achievement_key = ?
                """, (
                    ach['name'], ach['description'], ach['stat_key'],
                    ach['condition_type'], json.dumps(ach['tiers']), ach['category'],
                    ach['key']
                ))
                print(f"🔄 Updated: {ach['name']}")
                
        conn.commit()
        print(f"Seeding complete. Added {count} new achievements.")
        
    except Exception as e:
        print(f"Seeding failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    seed()
