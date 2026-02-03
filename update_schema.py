from database import Database
from sqlalchemy import text

db = Database()
session = db.get_session()

print("Updating schema...")

try:
    # Add rarity column
    try:
        session.execute(text("ALTER TABLE user_equipment ADD COLUMN rarity INTEGER DEFAULT 1"))
        print("Added 'rarity' column.")
    except Exception as e:
        print(f"Rarity column check/add: {e}")
        session.rollback()

    # Add stats_json column
    try:
        session.execute(text("ALTER TABLE user_equipment ADD COLUMN stats_json JSON DEFAULT NULL"))
        print("Added 'stats_json' column.")
    except Exception as e:
        print(f"Stats_json column check/add: {e}")
        session.rollback()

    session.commit()
    print("Schema update committed.")
except Exception as e:
    print(f"Critical error: {e}")
    session.rollback()
finally:
    session.close()
