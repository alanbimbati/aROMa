"""
Migration script for Character System V3
Adds support for:
- Character groups
- Transformation system
- Stat point allocation tracking
"""
import sqlite3
import sys

def migrate_database():
    """Apply database migrations"""
    conn = sqlite3.connect('points.db')
    cursor = conn.cursor()
    
    print("🔄 Starting migration for Character System V3...")
    
    try:
        # 1. Add character_group column to livello table
        print("\n1️⃣  Adding character_group column to livello table...")
        try:
            cursor.execute("ALTER TABLE livello ADD COLUMN character_group TEXT DEFAULT 'General'")
            print("   ✅ Added character_group column")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print("   ⏭️  character_group column already exists")
            else:
                raise
        
        # 2. Create character_transformation table
        print("\n2️⃣  Creating character_transformation table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS character_transformation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                base_character_id INTEGER NOT NULL,
                transformed_character_id INTEGER NOT NULL,
                transformation_name TEXT NOT NULL,
                wumpa_cost INTEGER NOT NULL,
                duration_days REAL NOT NULL DEFAULT 2.0,
                health_bonus INTEGER DEFAULT 0,
                mana_bonus INTEGER DEFAULT 0,
                damage_bonus INTEGER DEFAULT 0,
                is_progressive BOOLEAN DEFAULT 0,
                previous_transformation_id INTEGER
            )
        """)
        print("   ✅ character_transformation table ready")
        
        # 3. Create user_transformation table
        print("\n3️⃣  Creating user_transformation table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_transformation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                transformation_id INTEGER NOT NULL,
                activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                is_active BOOLEAN DEFAULT 1
            )
        """)
        print("   ✅ user_transformation table ready")
        
        # 4. Add last_stat_reset column to utente table
        print("\n4️⃣  Adding last_stat_reset column to utente table...")
        try:
            cursor.execute("ALTER TABLE utente ADD COLUMN last_stat_reset TIMESTAMP")
            print("   ✅ Added last_stat_reset column")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print("   ⏭️  last_stat_reset column already exists")
            else:
                raise
        
        # 5. Populate default character groups for existing characters
        print("\n5️⃣  Setting default character groups...")
        character_groups = {
            'Crash Bandicoot': 'Crash Bandicoot',
            'Spyro': 'Spyro the Dragon',
            'Sonic': 'Sonic the Hedgehog',
            'Mario': 'Super Mario',
            'Luigi': 'Super Mario',
            'Link': 'The Legend of Zelda',
            'Zelda': 'The Legend of Zelda',
            'Goku': 'Dragon Ball',
            'Naruto': 'Naruto',
            'Cloud Strife': 'Final Fantasy',
            'Samus Aran': 'Metroid',
            'Mega Man': 'Mega Man',
            'Pikachu': 'Pokémon',
            'Ryu': 'Street Fighter',
            'Kratos': 'God of War',
            'Ratchet': 'Ratchet & Clank',
            'Sackboy': 'LittleBigPlanet',
            'Master Chief': 'Halo',
            'Lara Croft': 'Tomb Raider',
            'Dante': 'Devil May Cry',
            'Sora': 'Kingdom Hearts',
            'Kirby': 'Kirby',
            'Donkey Kong': 'Donkey Kong',
            'Pac-Man': 'Pac-Man',
            'Snake': 'Metal Gear',
            'Joker': 'Persona',
            '2B': 'NieR: Automata',
            'Geralt': 'The Witcher',
            'Doom Slayer': 'DOOM',
            'Sephiroth': 'Final Fantasy'
        }
        
        for char_name, group in character_groups.items():
            cursor.execute(
                "UPDATE livello SET character_group = ? WHERE nome = ?",
                (group, char_name)
            )
        
        updated_count = cursor.rowcount
        print(f"   ✅ Updated {updated_count} character groups")
        
        # Commit all changes
        conn.commit()
        print("\n✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()
