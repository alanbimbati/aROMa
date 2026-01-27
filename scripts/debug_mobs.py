import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.append(os.getcwd())

from models.pve import Mob
from models.dungeon import Dungeon, DungeonParticipant
from database import Database

def debug_mobs():
    db = Database()
    session = db.get_session()
    
    print("--- Active Mobs ---")
    active_mobs = session.query(Mob).filter_by(is_dead=False).all()
    for mob in active_mobs:
        print(f"ID: {mob.id}, Name: {mob.name}, Chat: {mob.chat_id}, Dungeon: {mob.dungeon_id}")
        if mob.dungeon_id:
            dungeon = session.query(Dungeon).filter_by(id=mob.dungeon_id).first()
            if dungeon:
                print(f"  -> Dungeon: {dungeon.name}, Chat: {dungeon.chat_id}, Status: {dungeon.status}")
                participants = session.query(DungeonParticipant).filter_by(dungeon_id=dungeon.id).all()
                print(f"  -> Participants: {[p.user_id for p in participants]}")
            else:
                print(f"  -> Dungeon {mob.dungeon_id} NOT FOUND!")
    
    session.close()

if __name__ == "__main__":
    debug_mobs()
