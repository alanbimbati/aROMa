from sqlalchemy import create_engine, text
import sys
import os

# Add parent directory to path to import database settings if needed
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def migrate():
    print("Starting migration: Adding new stats columns...")
    
    # Connect to database
    engine = create_engine('sqlite:///aroma.db')
    
    with engine.connect() as conn:
        # 1. Add columns to utente table
        try:
            conn.execute(text("ALTER TABLE utente ADD COLUMN allocated_speed INTEGER DEFAULT 0"))
            print("Added allocated_speed to utente")
        except Exception as e:
            print(f"allocated_speed might already exist: {e}")
            
        try:
            conn.execute(text("ALTER TABLE utente ADD COLUMN allocated_resistance INTEGER DEFAULT 0"))
            print("Added allocated_resistance to utente")
        except Exception as e:
            print(f"allocated_resistance might already exist: {e}")
            
        try:
            conn.execute(text("ALTER TABLE utente ADD COLUMN allocated_crit_rate INTEGER DEFAULT 0"))
            print("Added allocated_crit_rate to utente")
        except Exception as e:
            print(f"allocated_crit_rate might already exist: {e}")
            
        try:
            conn.execute(text("ALTER TABLE utente ADD COLUMN last_attack_time DATETIME"))
            print("Added last_attack_time to utente")
        except Exception as e:
            print(f"last_attack_time might already exist: {e}")

        # 2. Add columns to mob table
        try:
            conn.execute(text("ALTER TABLE mob ADD COLUMN last_attack_time DATETIME"))
            print("Added last_attack_time to mob")
        except Exception as e:
            print(f"last_attack_time might already exist: {e}")
            
        conn.commit()
        
    print("Migration completed successfully!")

if __name__ == "__main__":
    migrate()
