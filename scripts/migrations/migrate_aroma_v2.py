from database import Database
from sqlalchemy import text

def migrate():
    db = Database()
    session = db.get_session()
    
    try:
        print("Adding 'platform' column to 'utente' table...")
        session.execute(text("ALTER TABLE utente ADD COLUMN platform VARCHAR(50)"))
        print("Done.")
    except Exception as e:
        print(f"Column 'platform' might already exist or error: {e}")

    try:
        print("Adding 'game_name' column to 'utente' table...")
        session.execute(text("ALTER TABLE utente ADD COLUMN game_name VARCHAR(100)"))
        print("Done.")
    except Exception as e:
        print(f"Column 'game_name' might already exist or error: {e}")

    session.commit()
    session.close()

if __name__ == "__main__":
    migrate()
