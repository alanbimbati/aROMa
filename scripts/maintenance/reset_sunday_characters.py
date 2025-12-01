"""
Script to run every Sunday to reset all character ownerships
Can be run manually or scheduled via cron
"""
from database import Database
from sqlalchemy import text
import datetime

def reset_sunday_characters():
    """Reset all character ownerships and return everyone to Chocobo"""
    db = Database()
    session = db.get_session()
    
    try:
        print("🔄 Starting Sunday character reset...")
        
        # Get Chocobo character ID (should be ID 1)
        result = session.execute(text("SELECT id FROM livello WHERE nome = 'Chocobo' LIMIT 1"))
        chocobo_row = result.fetchone()
        
        if not chocobo_row:
            print("❌ Error: Chocobo character not found!")
            session.close()
            return False
        
        chocobo_id = chocobo_row[0]
        print(f"✅ Found Chocobo (ID: {chocobo_id})")
        
        # Clear all character ownerships
        session.execute(text("DELETE FROM character_ownership"))
        print("✅ Cleared all character ownerships")
        
        # Reset all users to Chocobo
        session.execute(text(f"UPDATE utente SET livello_selezionato = {chocobo_id}"))
        result = session.execute(text("SELECT COUNT(*) FROM utente"))
        user_count = result.fetchone()[0]
        
        session.commit()
        print(f"✅ Reset {user_count} users to Chocobo")
        print("\n🎉 Sunday reset completed successfully!")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Error during Sunday reset: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
        session.close()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("SUNDAY CHARACTER RESET")
    print("=" * 60)
    today = datetime.date.today()
    print(f"Date: {today.strftime('%Y-%m-%d')}")
    print(f"Day: {today.strftime('%A')}")
    print("=" * 60)
    
    reset_sunday_characters()
