#!/usr/bin/env python3
import os
import sys
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

# Add current dir to path
sys.path.append(os.getcwd())

def migrate():
    print("🔄 Migrazione SQLite -> PostgreSQL (Docker Edition)")
    
    # SQLite source
    sqlite_db = "points.db"
    if not os.path.exists(sqlite_db):
        print(f"❌ Errore: {sqlite_db} non trovato!")
        return
    
    sqlite_url = f"sqlite:///{sqlite_db}"
    sqlite_engine = create_engine(sqlite_url)
    
    # PostgreSQL destination (from environment)
    db_user = os.getenv('DB_USER', 'alan')
    db_pass = os.getenv('DB_PASSWORD', 'asd1XD2LoL3')
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'aroma_bot')
    
    pg_url = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    print(f"🔗 Connessione a PostgreSQL: {db_host}:{db_port}/{db_name}")
    
    try:
        pg_engine = create_engine(pg_url)
        with pg_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Connesso a PostgreSQL")
    except Exception as e:
        print(f"❌ Errore connessione PostgreSQL: {e}")
        return

    # Import models
    from database import Base
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

    # Create tables
    print("📋 Creazione tabelle in PostgreSQL...")
    Base.metadata.create_all(pg_engine)
    
    # Table order (dependency-aware)
    tables = [
        'utente', 'admin', 'achievement', 'character_ownership', 'livello', 
        'season', 'season_reward', 'item', 'item_set',
        'user_achievement', 'user_character', 'user_stat', 'user_item', 
        'user_transformation', 'giocoutente', 'nomigiochi', 'collezionabili', 
        'game_event', 'games', 'steam', 'domenica',
        'season_progress', 'season_claimed_reward',
        'guilds', 'guild_members', 'guild_upgrades', 'guild_items',
        'dungeon', 'dungeon_participant', 'mob', 'mob_ability', 
        'raid', 'raid_participation', 'combat_participation'
    ]
    
    sqlite_session = sessionmaker(bind=sqlite_engine)()
    pg_session = sessionmaker(bind=pg_engine)()
    
    inspector = inspect(sqlite_engine)
    sqlite_tables = set(inspector.get_table_names())

    for table_name in tables:
        if table_name not in sqlite_tables: continue
        if table_name not in Base.metadata.tables: continue
        
        print(f"  📦 Migrazione {table_name}...", end=" ", flush=True)
        table = Base.metadata.tables[table_name]
        rows = sqlite_session.execute(table.select()).fetchall()
        
        if rows:
            for row in rows:
                try:
                    row_dict = dict(row._mapping)
                    pg_session.execute(table.insert().values(row_dict))
                except Exception:
                    pass # Skip duplicates or errors
            pg_session.commit()
            print(f"✅ {len(rows)} righe")
        else:
            print("📭 Vuota")

    print("\n🔄 Aggiornamento sequenze PostgreSQL...")
    with pg_engine.connect() as conn:
        for table_name in tables:
            if table_name not in Base.metadata.tables: continue
            
            # Check if table has an 'id' column (primary key usually)
            table = Base.metadata.tables[table_name]
            if 'id' in table.columns:
                try:
                    # Reset sequence to max(id) + 1
                    seq_name = f"{table_name}_id_seq"
                    sql = text(f"SELECT setval('{seq_name}', (SELECT MAX(id) FROM {table_name}));")
                    conn.execute(sql)
                    print(f"  🔢 Sequenza aggiornata per {table_name}")
                except Exception as e:
                    print(f"  ⚠️ Impossibile aggiornare sequenza per {table_name}: {e}")
        conn.commit()

    print("\n🎉 Migrazione completata con successo!")
    sqlite_session.close()
    pg_session.close()

if __name__ == "__main__":
    migrate()
