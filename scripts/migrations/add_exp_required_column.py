"""
Script per aggiungere la colonna exp_required alla tabella livello
"""
import sys
import os
import sqlite3

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

DB_NAME = 'points.db'

def migrate():
    """Aggiunge la colonna exp_required se non esiste"""
    print(f"🔄 Verifica colonna exp_required in {DB_NAME}...")
    
    # Usa una connessione diretta a SQLite con timeout aumentato
    conn = sqlite3.connect(DB_NAME, timeout=30.0)
    cursor = conn.cursor()
    
    try:
        # Verifica se la colonna esiste
        cursor.execute("PRAGMA table_info(livello)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'exp_required' in columns:
            print("✅ La colonna 'exp_required' esiste già.")
        else:
            print("➕ Aggiungo la colonna 'exp_required'...")
            cursor.execute("ALTER TABLE livello ADD COLUMN exp_required INTEGER DEFAULT 100")
            conn.commit()
            print("✅ Colonna 'exp_required' aggiunta con successo!")
            
            # Aggiorna i livelli esistenti con valori di default se necessario
            cursor.execute("UPDATE livello SET exp_required = 100 WHERE exp_required IS NULL")
            conn.commit()
            print("✅ Valori di default aggiornati per i livelli esistenti.")
        
    except sqlite3.OperationalError as e:
        if "database is locked" in str(e):
            print("❌ Errore: Il database è bloccato. Ferma il bot prima di eseguire la migrazione.")
        else:
            print(f"❌ Errore durante la migrazione: {e}")
        conn.rollback()
    except Exception as e:
        print(f"❌ Errore inaspettato: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()

