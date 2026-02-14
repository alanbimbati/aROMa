
from database import Database
from sqlalchemy import text

def migrate():
    db = Database()
    session = db.get_session()
    try:
        print("Migrating refinery_daily table...")
        session.execute(text("ALTER TABLE refinery_daily ADD COLUMN IF NOT EXISTS category VARCHAR(20) DEFAULT 'equipment';"))
        session.commit()
        print("✅ Migration successful!")
    except Exception as e:
        session.rollback()
        print(f"❌ Migration failed: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    migrate()
