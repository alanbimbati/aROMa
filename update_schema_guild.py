from database import Database
from sqlalchemy import text

db = Database()
session = db.get_session()

print("Updating schema for Guild Brewery...")

try:
    # Add brewery_level column
    try:
        session.execute(text("ALTER TABLE guilds ADD COLUMN brewery_level INTEGER DEFAULT 1"))
        print("Added 'brewery_level' column.")
    except Exception as e:
        print(f"brewery_level column check/add: {e}")
        session.rollback()

    session.commit()
    print("Guild Schema update committed.")
except Exception as e:
    print(f"Critical error: {e}")
    session.rollback()
finally:
    session.close()
