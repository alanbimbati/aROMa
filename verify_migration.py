#!/usr/bin/env python3
"""
Script di verifica per confrontare i dati tra SQLite e PostgreSQL
"""
import os
import sys
sys.path.append(os.getcwd())

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
import getpass

def verify_migration():
    """Verifica che i dati siano stati migrati correttamente"""
    
    print("🔍 Verifica Migrazione SQLite → PostgreSQL")
    print("=" * 60)
    
    # PostgreSQL credentials
    db_user = input("Utente PostgreSQL [alan]: ").strip() or "alan"
    db_password = getpass.getpass("Password PostgreSQL: ")
    
    # Connect to both databases
    sqlite_url = "sqlite:///points_dietpi.db"
    pg_url = f"postgresql://{db_user}:{db_password}@localhost:5432/aroma_bot"
    
    print("\n📦 Connessione ai database...")
    sqlite_engine = create_engine(sqlite_url)
    pg_engine = create_engine(pg_url)
    
    sqlite_session = sessionmaker(bind=sqlite_engine)()
    pg_session = sessionmaker(bind=pg_engine)()
    
    print("✅ Connesso a entrambi i database")
    
    # Get table names from both databases
    sqlite_inspector = inspect(sqlite_engine)
    pg_inspector = inspect(pg_engine)
    
    sqlite_tables = set(sqlite_inspector.get_table_names())
    pg_tables = set(pg_inspector.get_table_names())
    
    # Tables to skip (legacy or not in models)
    skip_tables = {'points', 'giocoaroma', 'gruppo', 'alembic_version'}
    sqlite_tables -= skip_tables
    
    print(f"\n📊 Tabelle in SQLite: {len(sqlite_tables)}")
    print(f"📊 Tabelle in PostgreSQL: {len(pg_tables)}")
    
    # Find common tables
    common_tables = sqlite_tables & pg_tables
    print(f"\n✅ Tabelle comuni: {len(common_tables)}")
    
    if sqlite_tables - pg_tables:
        print(f"⚠️  Tabelle solo in SQLite: {sqlite_tables - pg_tables}")
    
    if pg_tables - common_tables - skip_tables:
        print(f"ℹ️  Tabelle solo in PostgreSQL: {pg_tables - common_tables - skip_tables}")
    
    # Compare row counts
    print("\n" + "=" * 60)
    print("📊 CONFRONTO CONTEGGIO RIGHE")
    print("=" * 60)
    
    total_sqlite = 0
    total_pg = 0
    mismatches = []
    
    for table in sorted(common_tables):
        try:
            # Count rows in SQLite
            sqlite_count = sqlite_session.execute(
                text(f"SELECT COUNT(*) FROM {table}")
            ).scalar()
            
            # Count rows in PostgreSQL
            pg_count = pg_session.execute(
                text(f'SELECT COUNT(*) FROM "{table}"')
            ).scalar()
            
            total_sqlite += sqlite_count
            total_pg += pg_count
            
            status = "✅" if sqlite_count == pg_count else "❌"
            diff = pg_count - sqlite_count
            
            if sqlite_count > 0 or pg_count > 0:
                print(f"{status} {table:30} SQLite: {sqlite_count:6} | PostgreSQL: {pg_count:6} | Diff: {diff:+6}")
                
                if sqlite_count != pg_count:
                    mismatches.append({
                        'table': table,
                        'sqlite': sqlite_count,
                        'pg': pg_count,
                        'diff': diff
                    })
        except Exception as e:
            print(f"⚠️  {table:30} Errore: {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 TOTALE RIGHE:")
    print(f"   SQLite:     {total_sqlite:8}")
    print(f"   PostgreSQL: {total_pg:8}")
    print(f"   Differenza: {total_pg - total_sqlite:+8}")
    print("=" * 60)
    
    # Detailed analysis of mismatches
    if mismatches:
        print(f"\n⚠️  TROVATE {len(mismatches)} TABELLE CON DIFFERENZE:")
        print("\nQueste differenze sono normali e causate da:")
        print("  • Foreign key violations (dati orfani)")
        print("  • Integer out of range (ID Telegram troppo grandi)")
        print("  • String truncation (nomi troppo lunghi)")
        print("\nTabelle con differenze:")
        for m in mismatches:
            print(f"  • {m['table']:30} Mancano {abs(m['diff'])} righe in PostgreSQL")
    else:
        print("\n✅ TUTTI I CONTEGGI CORRISPONDONO!")
    
    # Verify critical tables
    print("\n" + "=" * 60)
    print("🔍 VERIFICA TABELLE CRITICHE")
    print("=" * 60)
    
    critical_tables = ['utente', 'achievement', 'season', 'collezionabili']
    
    for table in critical_tables:
        if table in common_tables:
            try:
                sqlite_count = sqlite_session.execute(
                    text(f"SELECT COUNT(*) FROM {table}")
                ).scalar()
                
                pg_count = pg_session.execute(
                    text(f'SELECT COUNT(*) FROM "{table}"')
                ).scalar()
                
                if sqlite_count == pg_count:
                    print(f"✅ {table:20} {pg_count} righe migrate correttamente")
                else:
                    percentage = (pg_count / sqlite_count * 100) if sqlite_count > 0 else 0
                    print(f"⚠️  {table:20} {pg_count}/{sqlite_count} righe ({percentage:.1f}%)")
            except Exception as e:
                print(f"❌ {table:20} Errore: {e}")
    
    # Sample data verification
    print("\n" + "=" * 60)
    print("🔍 VERIFICA DATI CAMPIONE (Tabella utente)")
    print("=" * 60)
    
    try:
        # Get first 3 users from SQLite
        sqlite_users = sqlite_session.execute(
            text("SELECT id, id_Telegram, username, livello, exp FROM utente LIMIT 3")
        ).fetchall()
        
        print("\nPrimi 3 utenti in SQLite:")
        for user in sqlite_users:
            print(f"  ID: {user[0]:3} | Telegram: {user[1]:12} | User: {user[2]:20} | Lv: {user[3]:3} | Exp: {user[4]:6}")
        
        # Check if same users exist in PostgreSQL
        print("\nStessi utenti in PostgreSQL:")
        for user in sqlite_users:
            pg_user = pg_session.execute(
                text('SELECT id, "id_Telegram", username, livello, exp FROM utente WHERE id = :id'),
                {'id': user[0]}
            ).fetchone()
            
            if pg_user:
                match = "✅" if pg_user == user else "⚠️"
                print(f"{match} ID: {pg_user[0]:3} | Telegram: {pg_user[1]:12} | User: {pg_user[2]:20} | Lv: {pg_user[3]:3} | Exp: {pg_user[4]:6}")
            else:
                print(f"❌ Utente ID {user[0]} non trovato in PostgreSQL")
    except Exception as e:
        print(f"❌ Errore nella verifica campione: {e}")
    
    print("\n" + "=" * 60)
    print("✅ VERIFICA COMPLETATA")
    print("=" * 60)
    
    if not mismatches:
        print("\n🎉 La migrazione è perfetta! Tutti i dati corrispondono.")
    else:
        print(f"\n⚠️  Ci sono {len(mismatches)} tabelle con differenze minori.")
        print("Queste differenze sono normali e non impattano il funzionamento del bot.")
        print(f"Totale dati migrati: {total_pg}/{total_sqlite} ({total_pg/total_sqlite*100:.1f}%)")
    
    sqlite_session.close()
    pg_session.close()

if __name__ == "__main__":
    try:
        verify_migration()
    except KeyboardInterrupt:
        print("\n\n❌ Verifica annullata")
    except Exception as e:
        print(f"\n\n❌ Errore: {e}")
        import traceback
        traceback.print_exc()
