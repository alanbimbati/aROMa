#!/usr/bin/env python3
"""
Improved Python-based migration script from SQLite to PostgreSQL
Uses existing SQLAlchemy models instead of reflecting schema
"""
import os
import sys
sys.path.append(os.getcwd())

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
import getpass

def migrate_to_postgresql():
    """Migrate data from SQLite to PostgreSQL using SQLAlchemy models"""
    
    print("🚀 Migrazione Python da SQLite a PostgreSQL (v2)")
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
        pg_engine.connect()
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
    
    # Create all tables in PostgreSQL using SQLAlchemy models
    print("📋 Creazione tabelle in PostgreSQL...")
    Base.metadata.create_all(pg_engine)
    print(f"✅ Tabelle create")
    
    # Get all table names
    inspector = inspect(sqlite_engine)
    table_names = inspector.get_table_names()
    
    # Migrate data table by table
    print("\n🔄 Migrazione dati...")
    sqlite_session = sessionmaker(bind=sqlite_engine)()
    pg_session = sessionmaker(bind=pg_engine)()
    
    total_rows = 0
    for table_name in table_names:
        try:
            # Get table object from metadata
            if table_name not in Base.metadata.tables:
                print(f"  ⚠️  {table_name}: tabella non trovata nei modelli, skip")
                continue
                
            table = Base.metadata.tables[table_name]
            
            # Read from SQLite
            rows = sqlite_session.execute(table.select()).fetchall()
            
            if rows:
                print(f"  📊 {table_name}: {len(rows)} righe")
                
                # Insert into PostgreSQL in batches
                batch_size = 1000
                for i in range(0, len(rows), batch_size):
                    batch = rows[i:i+batch_size]
                    for row in batch:
                        pg_session.execute(table.insert().values(dict(row._mapping)))
                    pg_session.commit()
                
                total_rows += len(rows)
            else:
                print(f"  📊 {table_name}: 0 righe (vuota)")
        except Exception as e:
            print(f"  ❌ {table_name}: Errore - {e}")
            pg_session.rollback()
            continue
    
    print(f"\n✅ {total_rows} righe totali migrate")
    
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
    print("1. Sostituisci database.py:")
    print("   mv database.py database_sqlite.py.backup")
    print("   mv database_postgresql.py database.py")
    print("\n2. Riavvia il bot:")
    print("   python3 main.py")
    print("\n3. Verifica che tutto funzioni")
    print("\nIn caso di problemi:")
    print("   mv database_sqlite.py.backup database.py")
    print("   rm .env")
    
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
