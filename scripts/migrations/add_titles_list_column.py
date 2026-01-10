"""
Add titles column to utente table for storing all earned achievement titles
"""

from sqlalchemy import create_engine, text

def add_titles_column():
    """Add titles column to utente table"""
    engine = create_engine('sqlite:///points.db')
    
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE utente ADD COLUMN titles TEXT"))
            conn.commit()
            print("✅ Added 'titles' column to utente table")
        except Exception as e:
            print(f"⚠️  Column might already exist or error: {e}")

if __name__ == "__main__":
    print("🔧 Adding titles column...")
    add_titles_column()
    print("✅ Done!")
