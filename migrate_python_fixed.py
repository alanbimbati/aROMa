#!/usr/bin/env python3
"""
Improved Python-based migration script from SQLite to PostgreSQL
Handles foreign key dependencies and data sanitization
"""
import os
import sys
sys.path.append(os.getcwd())

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
import getpass
from collections import defaultdict

def get_table_dependencies():
    """Define table migration order based on foreign key dependencies"""
    # Tables with no dependencies first, then tables that depend on them
    return [
        # Base tables (no dependencies)
        'utente',
        'admin',
        'achievement',
        'character_ownership',
        'livello',
        'season',
        'season_reward',
        'item',
        'item_set',
        
        # Tables depending on utente
        'user_achievement',
        'user_character',
        'user_stat',
        'user_item',
        'user_transformation',
        'giocoutente',
        'nomigiochi',
        'collezionabili',
        'game_event',
        'games',
        'steam',
        'domenica',
        
        # Tables depending on season
        'season_progress',
        'season_claimed_reward',
        
        # Guild tables (depend on utente)
        'guilds',
        'guild_members',
        'guild_upgrades',
        'guild_items',
        
        # Dungeon tables
        'dungeon',
        'dungeon_participant',
        
        # Combat tables (depend on utente and dungeon)
        'mob',
        'mob_ability',
        'raid',
        'raid_participation',
        'combat_participation',
    ]

def sanitize_data(table_name, row_dict):
    """Sanitize data before insertion to prevent errors"""
    
    # Truncate long strings for utente table
    if table_name == 'utente':
        if row_dict.get('nome') and len(row_dict['nome']) > 256:
            row_dict['nome'] = row_dict['nome'][:256]
        if row_dict.get('cognome') and len(row_dict['cognome']) > 256:
            row_dict['cognome'] = row_dict['cognome'][:256]
        if row_dict.get('username') and len(row_dict['username']) > 64:
            row_dict['username'] = row_dict['username'][:64]
    
    # Truncate long steam titles
    if table_name == 'steam':
        if row_dict.get('titolo') and len(row_dict['titolo']) > 256:
            row_dict['titolo'] = row_dict['titolo'][:256]
    
    # Fix games table - convert "N/A" to None for integer fields
    if table_name == 'games':
        if row_dict.get('year') == 'N/A' or row_dict.get('year') == '':
            row_dict['year'] = None
        if row_dict.get('premium') == 'N/A' or row_dict.get('premium') == '':
            row_dict['premium'] = None
    
    return row_dict

def migrate_to_postgresql():
    """Migrate data from SQLite to PostgreSQL using SQLAlchemy models"""
    
    print("🚀 Migrazione Python da SQLite a PostgreSQL (v3 - Fixed)")
    print("=" * 50)
    
    # Get PostgreSQL credentials
    db_name = input("Nome database PostgreSQL [aroma_bot]: ").strip() or "aroma_bot"
    db_user = input("Utente PostgreSQL [alan]: ").strip() or "alan"
    db_password = getpass.getpass("Password PostgreSQL: ")
    db_host = input("Host PostgreSQL [localhost]: ").strip() or "localhost"
    db_port = input("Porta PostgreSQL [5432]: ").strip() or "5432"
    
    # Create PostgreSQL connection string
    pg_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    print("\n📦 Connessione a PostgreSQL...")
    try:
        pg_engine = create_engine(pg_url)
        with pg_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Connesso a PostgreSQL")
    except Exception as e:
        print(f"❌ Errore connessione PostgreSQL: {e}")
        return False
    
    # Connect to SQLite
    print("\n📦 Connessione a SQLite...")
    sqlite_url = "sqlite:///points_dietpi.db"
    sqlite_engine = create_engine(sqlite_url)
    
    # Backup SQLite
    print("\n💾 Backup SQLite...")
    import shutil
    shutil.copy2("points_dietpi.db", "points_dietpi.db.backup")
    print("✅ Backup salvato in points_dietpi.db.backup")
    
    # Import all models to register them with Base
    print("\n📋 Caricamento modelli SQLAlchemy...")
    from database import Base
    
    # Import all model files to register tables
    import models.user
    import models.pve
    import models.inventory
    import models.character_ownership
    import models.dungeon
    import models.dungeon_progress
    import models.stats
    import models.game
    import models.guild
    import models.seasons
    import models.combat
    import models.system
    import models.item
    import models.items
    import models.achievements
    
    # Drop and recreate all tables in PostgreSQL
    print("\n🗑️  Eliminazione tabelle esistenti in PostgreSQL...")
    Base.metadata.drop_all(pg_engine)
    
    # Create all tables in PostgreSQL using SQLAlchemy models
    print("📋 Creazione tabelle in PostgreSQL...")
    Base.metadata.create_all(pg_engine)
    print(f"✅ Tabelle create")
    
    # Get all table names from SQLite
    inspector = inspect(sqlite_engine)
    sqlite_tables = set(inspector.get_table_names())
    
    # Get ordered table list
    ordered_tables = get_table_dependencies()
    
    # Migrate data table by table in dependency order
    print("\n🔄 Migrazione dati (in ordine di dipendenze)...")
    sqlite_session = sessionmaker(bind=sqlite_engine)()
    pg_session = sessionmaker(bind=pg_engine)()
    
    total_rows = 0
    migration_stats = {}
    
    for table_name in ordered_tables:
        # Skip if table doesn't exist in SQLite
        if table_name not in sqlite_tables:
            continue
            
        # Skip if table not in models
        if table_name not in Base.metadata.tables:
            print(f"  ⚠️  {table_name}: tabella non trovata nei modelli, skip")
            continue
        
        try:
            table = Base.metadata.tables[table_name]
            
            # Read from SQLite
            rows = sqlite_session.execute(table.select()).fetchall()
            
            if rows:
                print(f"  📊 {table_name}: {len(rows)} righe")
                
                successful = 0
                failed = 0
                
                # Insert into PostgreSQL one by one to handle errors gracefully
                for row in rows:
                    try:
                        row_dict = dict(row._mapping)
                        row_dict = sanitize_data(table_name, row_dict)
                        pg_session.execute(table.insert().values(row_dict))
                        pg_session.commit()
                        successful += 1
                    except Exception as e:
                        pg_session.rollback()
                        failed += 1
                        if failed == 1:  # Only print first error per table
                            print(f"     ⚠️  Primo errore: {str(e)[:100]}")
                
                migration_stats[table_name] = {
                    'total': len(rows),
                    'successful': successful,
                    'failed': failed
                }
                
                if failed > 0:
                    print(f"     ✅ {successful} righe migrate, ⚠️  {failed} righe saltate")
                
                total_rows += successful
            else:
                print(f"  📊 {table_name}: 0 righe (vuota)")
                migration_stats[table_name] = {'total': 0, 'successful': 0, 'failed': 0}
                
        except Exception as e:
            print(f"  ❌ {table_name}: Errore - {e}")
            pg_session.rollback()
            migration_stats[table_name] = {'total': 0, 'successful': 0, 'failed': 0, 'error': str(e)}
            continue
    
    print(f"\n✅ {total_rows} righe totali migrate")
    
    # Print summary of critical tables
    print("\n📊 RIEPILOGO TABELLE CRITICHE:")
    critical_tables = ['utente', 'guilds', 'guild_members', 'mob', 'steam', 'season_claimed_reward']
    for table in critical_tables:
        if table in migration_stats:
            stats = migration_stats[table]
            if stats['successful'] > 0:
                print(f"  ✅ {table}: {stats['successful']}/{stats['total']} righe migrate")
            elif stats['total'] == 0:
                print(f"  📭 {table}: tabella vuota")
            else:
                print(f"  ⚠️  {table}: {stats['failed']} righe saltate")
    
    # Create .env file
    print("\n📝 Creazione file .env...")
    with open(".env", "w") as f:
        f.write(f"DB_TYPE=postgresql\n")
        f.write(f"DB_HOST={db_host}\n")
        f.write(f"DB_PORT={db_port}\n")
        f.write(f"DB_NAME={db_name}\n")
        f.write(f"DB_USER={db_user}\n")
        f.write(f"DB_PASSWORD={db_password}\n")
        f.write(f"TEST_DB=0\n")
    print("✅ File .env creato")
    
    print("\n" + "=" * 50)
    print("✅ MIGRAZIONE COMPLETATA!")
    print("=" * 50)
    print("\nProssimi passi:")
    print("1. Verifica i dati migrati:")
    print("   python3 verify_migration.py")
    print("\n2. Se tutto ok, riavvia il bot:")
    print("   python3 main.py")
    print("\nIn caso di problemi:")
    print("   - Controlla il riepilogo sopra")
    print("   - Verifica i log di errore")
    print("   - Riesegui lo script per riprovare")
    
    sqlite_session.close()
    pg_session.close()
    
    return True

if __name__ == "__main__":
    try:
        migrate_to_postgresql()
    except KeyboardInterrupt:
        print("\n\n❌ Migrazione annullata")
    except Exception as e:
        print(f"\n\n❌ Errore: {e}")
        import traceback
        traceback.print_exc()
