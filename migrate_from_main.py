"""
Database Migration Script: points_official.db → points.db
This script migrates data from the main branch database to the new RPG-enhanced schema.
Usage: python3 migrate_from_main.py
"""
import sqlite3
import shutil
import os
from datetime import datetime

SOURCE_DB = "points_official.db"
TARGET_DB = "points.db"
BACKUP_DB = f"points_official_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"

def create_backup():
    """Create a backup of the source database"""
    if os.path.exists(SOURCE_DB):
        shutil.copy2(SOURCE_DB, BACKUP_DB)
        print(f"✅ Created backup: {BACKUP_DB}")
        return True
    else:
        print(f"❌ Source database not found: {SOURCE_DB}")
        return False

def ensure_schema_updates(cursor):
    """Ensure target database has all required columns"""
    print("\n🔄 Checking schema updates...")
    
    # Check utente table
    cursor.execute("PRAGMA table_info(utente)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'invincible_until' not in columns:
        print("  ➕ Adding column: invincible_until")
        cursor.execute("ALTER TABLE utente ADD COLUMN invincible_until TIMESTAMP")
        
    if 'luck_boost' not in columns:
        print("  ➕ Adding column: luck_boost")
        cursor.execute("ALTER TABLE utente ADD COLUMN luck_boost INTEGER DEFAULT 0")

    # RPG Stats
    rpg_columns = {
        'health': 'INTEGER DEFAULT 100',
        'max_health': 'INTEGER DEFAULT 100',
        'current_hp': 'INTEGER',
        'mana': 'INTEGER DEFAULT 50',
        'max_mana': 'INTEGER DEFAULT 50',
        'base_damage': 'INTEGER DEFAULT 10',
        'stat_points': 'INTEGER DEFAULT 0',
        'last_health_restore': 'TIMESTAMP',
        'allocated_health': 'INTEGER DEFAULT 0',
        'allocated_mana': 'INTEGER DEFAULT 0',
        'allocated_damage': 'INTEGER DEFAULT 0',
        'allocated_speed': 'INTEGER DEFAULT 0',
        'allocated_resistance': 'INTEGER DEFAULT 0',
        'allocated_crit_rate': 'INTEGER DEFAULT 0',
        'last_stat_reset': 'TIMESTAMP',
        'last_attack_time': 'TIMESTAMP',
        'last_character_change': 'TIMESTAMP',
        'platform': 'VARCHAR(50)',
        'game_name': 'VARCHAR(100)'
    }

    for col_name, col_type in rpg_columns.items():
        if col_name not in columns:
            print(f"  ➕ Adding column: {col_name}")
            cursor.execute(f"ALTER TABLE utente ADD COLUMN {col_name} {col_type}")
        
    print("✅ Schema check completed")

def migrate_data():
    """Migrate data from source to target database"""
    
    # Create backup first
    if not create_backup():
        return False
    
    # Backup current points.db if it exists
    if os.path.exists(TARGET_DB):
        current_backup = f"points_current_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copy2(TARGET_DB, current_backup)
        print(f"✅ Backed up current database: {current_backup}")
    
    # Connect to both databases
    source_conn = sqlite3.connect(SOURCE_DB)
    target_conn = sqlite3.connect(TARGET_DB)
    
    source_cursor = source_conn.cursor()
    target_cursor = target_conn.cursor()
    
    # Ensure schema is up to date before migrating
    ensure_schema_updates(target_cursor)
    
    try:
        print("\n🔄 Starting migration...\n")
        
        # Migrate simple tables (no schema changes)
        simple_tables = ['points', 'gruppo', 'domenica', 'steam', 'nomigiochi', 
                        'admin', 'giocoaroma', 'giocoutente', 'collezionabili', 'games']
        
        for table in simple_tables:
            # Check if table exists in source
            source_cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if not source_cursor.fetchone():
                print(f"⏭️  Skipping {table} (not in source)")
                continue
            
            # Clear existing data in target
            target_cursor.execute(f"DELETE FROM {table}")
            
            # Copy data
            source_cursor.execute(f"SELECT * FROM {table}")
            rows = source_cursor.fetchall()
            
            if rows:
                # Get column count
                placeholders = ','.join(['?' for _ in range(len(rows[0]))])
                target_cursor.executemany(f"INSERT INTO {table} VALUES ({placeholders})", rows)
                print(f"✅ Migrated {table}: {len(rows)} rows")
            else:
                print(f"⏭️  {table}: no data to migrate")
        
        # Migrate utente table with new columns
        print("\n🔄 Migrating utente table with RPG enhancements...")
        
        # Get all columns from source utente table
        source_cursor.execute("PRAGMA table_info(utente)")
        source_columns = [col[1] for col in source_cursor.fetchall()]
        
        # Clear existing data
        target_cursor.execute("DELETE FROM utente")
        
        # Fetch all users from source
        source_cursor.execute(f"SELECT * FROM utente")
        source_rows = source_cursor.fetchall()
        
        if source_rows:
            # Get target column info
            target_cursor.execute("PRAGMA table_info(utente)")
            target_columns = [col[1] for col in target_cursor.fetchall()]
            
            for row in source_rows:
                # Create a dict from source row
                source_dict = dict(zip(source_columns, row))
                
                # Build insert query with default values for new columns
                columns = []
                values = []
                
                for col in target_columns:
                    if col in source_dict:
                        columns.append(col)
                        # Override livello_selezionato to set Chocobo as default
                        if col == 'livello_selezionato':
                            values.append(1)  # Chocobo ID
                        else:
                            values.append(source_dict[col])
                    else:
                        # Default values for new RPG columns
                        columns.append(col)
                        if col == 'health' or col == 'max_health':
                            values.append(100)
                        elif col == 'mana' or col == 'max_mana':
                            values.append(50)
                        elif col == 'base_damage':
                            values.append(10)
                        elif col in ['luck_boost', 'stat_points', 'allocated_health', 
                                    'allocated_mana', 'allocated_damage', 'allocated_speed',
                                    'allocated_resistance', 'allocated_crit_rate']:
                            values.append(0)
                        else:
                            values.append(None)
                
                placeholders = ','.join(['?' for _ in values])
                column_names = ','.join([f'"{c}"' if c == 'id_Telegram' else c for c in columns])
                target_cursor.execute(f"INSERT INTO utente ({column_names}) VALUES ({placeholders})", values)
            
            print(f"✅ Migrated utente: {len(source_rows)} users with RPG stats initialized")
            
            # Create user_character ownership for Chocobo for all users
            print("\n🔄 Assigning Chocobo to all users...")
            for row in source_rows:
                source_dict = dict(zip(source_columns, row))
                user_id = source_dict.get('id_Telegram')
                if user_id:
                    target_cursor.execute(
                        "INSERT INTO user_character (user_id, character_id, obtained_at) VALUES (?, ?, DATE('now'))",
                        (user_id, 1)  # Character ID 1 = Chocobo
                    )
            print(f"✅ Chocobo assigned to all {len(source_rows)} users")
        
        # Migrate livello table (characters)
        print("\n🔄 Migrating character data...")
        
        # Note: Current branch uses CSV for characters, but we migrate DB data if it exists
        source_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='livello'")
        if source_cursor.fetchone():
            source_cursor.execute("PRAGMA table_info(livello)")
            source_lvl_columns = [col[1] for col in source_cursor.fetchall()]
            
            source_cursor.execute("SELECT * FROM livello")
            lvl_rows = source_cursor.fetchall()
            
            if lvl_rows:
                target_cursor.execute("DELETE FROM livello")
                
                target_cursor.execute("PRAGMA table_info(livello)")
                target_lvl_columns = [col[1] for col in target_cursor.fetchall()]
                
                for row in lvl_rows:
                    source_dict = dict(zip(source_lvl_columns, row))
                    
                    columns = []
                    values = []
                    
                    for col in target_lvl_columns:
                        if col in source_dict:
                            columns.append(col)
                            values.append(source_dict[col])
                        else:
                            # Defaults for new character columns
                            columns.append(col)
                            if col == 'exp_required':
                                values.append(100)
                            elif col == 'character_group':
                                values.append('General')
                            elif col == 'max_concurrent_owners':
                                values.append(1)
                            elif col == 'elemental_type':
                                values.append('Normal')
                            elif col == 'crit_chance':
                                values.append(5)
                            elif col == 'crit_multiplier':
                                values.append(1.5)
                            elif col in ['special_attack_damage', 'special_attack_mana_cost', 
                                        'price', 'is_pokemon']:
                                values.append(0)
                            else:
                                values.append(None)
                    
                    placeholders = ','.join(['?' for _ in values])
                    column_names = ','.join(columns)
                    target_cursor.execute(f"INSERT INTO livello ({column_names}) VALUES ({placeholders})", values)
                
                print(f"✅ Migrated livello: {len(lvl_rows)} characters")
        
        # Commit all changes
        target_conn.commit()
        
        print("\n✅ Migration completed successfully!")
        
        # Print summary
        print("\n📊 Migration Summary:")
        for table in ['utente', 'points', 'gruppo', 'admin', 'collezionabili', 'games']:
            target_cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = target_cursor.fetchone()[0]
            print(f"  - {table}: {count} records")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        target_conn.rollback()
        return False
        
    finally:
        source_conn.close()
        target_conn.close()

if __name__ == "__main__":
    print("=" * 60)
    print("Database Migration: points_official.db → points.db")
    print("=" * 60)
    
    if not os.path.exists(SOURCE_DB):
        print(f"\n❌ Source database not found: {SOURCE_DB}")
        print("Please ensure points_official.db is in the current directory.")
        exit(1)
    
    if not os.path.exists(TARGET_DB):
        print(f"\n⚠️  Target database not found: {TARGET_DB}")
        print("The script will create a new database with the current schema.")
        print("Make sure to run this from the correct directory!")
        response = input("\nContinue? (y/n): ")
        if response.lower() != 'y':
            print("Migration cancelled.")
            exit(0)
    
    success = migrate_data()
    
    if success:
        print("\n" + "=" * 60)
        print("✅ Migration completed successfully!")
        print("=" * 60)
        print(f"\nBackups created:")
        print(f"  - {BACKUP_DB}")
        print("\nYou can now run: python3 main.py")
    else:
        print("\n" + "=" * 60)
        print("❌ Migration failed")
        print("=" * 60)
        exit(1)
