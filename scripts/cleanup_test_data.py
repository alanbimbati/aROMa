import sys
import os
sys.path.append(os.getcwd())
from database import Database
from models.user import Utente
from models.combat import CombatParticipation
from models.pve import Mob
from models.dungeon import Dungeon, DungeonParticipant

def cleanup():
    db = Database()
    session = db.get_session()
    
    test_user_ids = [54321, 66666, 999888777, 123456789]
    test_chat_ids = [777777, 666666, 123]
    
    print(f"Starting cleanup of test data...")
    
    try:
        # 1. Delete CombatParticipation for test users
        deleted_cp = session.query(CombatParticipation).filter(CombatParticipation.user_id.in_(test_user_ids)).delete(synchronize_session=False)
        print(f"Deleted {deleted_cp} CombatParticipation records.")
        
        # 2. Delete DungeonParticipants for test users
        deleted_dp = session.query(DungeonParticipant).filter(DungeonParticipant.user_id.in_(test_user_ids)).delete(synchronize_session=False)
        print(f"Deleted {deleted_dp} DungeonParticipant records.")
        
        # 3. Delete Mobs in test chats
        deleted_mobs = session.query(Mob).filter(Mob.chat_id.in_(test_chat_ids)).delete(synchronize_session=False)
        print(f"Deleted {deleted_mobs} Mob records.")
        
        # 4. Delete Dungeons in test chats
        deleted_dungeons = session.query(Dungeon).filter(Dungeon.chat_id.in_(test_chat_ids)).delete(synchronize_session=False)
        print(f"Deleted {deleted_dungeons} Dungeon records.")
        
        # 5. Delete Test Users
        deleted_users = session.query(Utente).filter(Utente.id_telegram.in_(test_user_ids)).delete(synchronize_session=False)
        print(f"Deleted {deleted_users} Utente records.")
        
        session.commit()
        print("Cleanup completed successfully.")
    except Exception as e:
        print(f"Error during cleanup: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    cleanup()
