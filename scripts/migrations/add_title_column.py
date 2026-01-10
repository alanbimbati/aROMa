"""
Add title column to utente table for achievement titles
"""

from sqlalchemy import create_engine, text

def add_title_column():
    """Add title column to utente table"""
    engine = create_engine('sqlite:///points.db')
    
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE utente ADD COLUMN title TEXT"))
            conn.commit()
            print("✅ Added 'title' column to utente table")
        except Exception as e:
            print(f"⚠️  Column might already exist or error: {e}")

if __name__ == "__main__":
    print("🔧 Adding title column...")
    add_title_column()
    print("✅ Done!")
