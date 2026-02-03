from database import Database
from models.user import Utente
from services.user_service import UserService
import sys

def fix_base_stats():
    print("Starting fix for Base Stats using UserService.recalculate_stats...")
    db = Database()
    user_service = UserService()
    session = db.get_session()
    
    try:
        users = session.query(Utente).all()
        count = 0
        for user in users:
            print(f"Recalculating stats for {user.username or user.id_telegram} (Level {user.livello})...")
            user_service.recalculate_stats(user.id_telegram, session=session)
            count += 1
                
        session.commit()
        print(f"Fixed {count} users.")
    except Exception as e:
        print(f"Error: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    fix_base_stats()
