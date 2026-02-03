from database import Database
from sqlalchemy import text

db = Database()
session = db.get_session()

print("Updating schema for Inn...")

try:
    # Add last_beer_usage column
    try:
        session.execute(text("ALTER TABLE utente ADD COLUMN last_beer_usage TIMESTAMP WITHOUT TIME ZONE DEFAULT NULL"))
        print("Added 'last_beer_usage' column.")
    except Exception as e:
        print(f"last_beer_usage column check/add: {e}")
        session.rollback()

    # Add last_brothel_usage column
    try:
        session.execute(text("ALTER TABLE utente ADD COLUMN last_brothel_usage TIMESTAMP WITHOUT TIME ZONE DEFAULT NULL"))
        print("Added 'last_brothel_usage' column.")
    except Exception as e:
        print(f"last_brothel_usage column check/add: {e}")
        session.rollback()

    session.commit()
    print("Inn Schema update committed.")
except Exception as e:
    print(f"Critical error: {e}")
    session.rollback()
finally:
    session.close()
