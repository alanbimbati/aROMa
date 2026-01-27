#!/usr/bin/env python3
"""
Script to clean up ghost dungeons and participants from the database.
"""
import os
import sys
sys.path.append(os.getcwd())

from database import Database
from models.dungeon import Dungeon, DungeonParticipant

def cleanup_ghost_dungeons():
    """Remove ghost dungeons and participants"""
    db = Database()
    session = db.get_session()
    
    try:
        # Find all dungeons
        dungeons = session.query(Dungeon).all()
        print(f"Found {len(dungeons)} total dungeons")
        
        for dungeon in dungeons:
            participants = session.query(DungeonParticipant).filter_by(dungeon_id=dungeon.id).all()
            print(f"\nDungeon ID {dungeon.id}: {dungeon.name}")
            print(f"  Chat ID: {dungeon.chat_id}")
            print(f"  Status: {dungeon.status}")
            print(f"  Participants: {len(participants)}")
            for p in participants:
                print(f"    - User ID: {p.user_id}")
        
        # Ask for confirmation
        print("\n" + "="*50)
        choice = input("Do you want to delete ALL dungeons? (yes/no): ")
        
        if choice.lower() == 'yes':
            # Delete all participants first
            deleted_participants = session.query(DungeonParticipant).delete()
            print(f"Deleted {deleted_participants} participants")
            
            # Delete all dungeons
            deleted_dungeons = session.query(Dungeon).delete()
            print(f"Deleted {deleted_dungeons} dungeons")
            
            session.commit()
            print("✅ All dungeons cleaned up!")
        else:
            print("Cancelled.")
            
    except Exception as e:
        session.rollback()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    cleanup_ghost_dungeons()
