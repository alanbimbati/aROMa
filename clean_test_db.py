#!/usr/bin/env python3
"""
Rebuild test database schema between test runs to eliminate pollution.
Usage: Call this before running specific test files or test classes.
"""
import os
import sys

# Force test mode
os.environ['TEST_DB'] = '1'
os.environ['TEST'] = '1'

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import Database
from models.user import Utente
from models.pve import Mob
from models.dungeon import Dungeon, DungeonParticipant
from models.resources import UserResource
from models.market import MarketListing
from models.items import Collezionabili
from models.guild import Guild, GuildMember
from models.combat import CombatParticipation
from models.equipment import UserEquipment

def clean_test_db():
    """Clean all test data from the test database."""
    print("[CLEANUP] Cleaning test database...")
    db = Database()
    session = db.get_session()
    
    try:
        # Delete in correct order (children first, respecting FK constraints)
        session.query(CombatParticipation).delete()
        session.query(UserEquipment).delete()
        session.query(MarketListing).delete()
        session.query(Collezionabili).delete()
        session.query(DungeonParticipant).delete()
        session.query(Mob).delete()  # Delete mobs before dungeons (mob has FK to dungeon)
        session.query(Dungeon).delete()
        session.query(GuildMember).delete()
        session.query(Guild).delete()
        session.query(UserResource).delete()
        session.query(Utente).delete()
        
        session.commit()
        print("[CLEANUP] Test database cleaned successfully!")
        return True
    except Exception as e:
        print(f"[CLEANUP ERROR] Failed to clean database: {e}")
        session.rollback()
        return False
    finally:
        session.close()

if __name__ == "__main__":
    success = clean_test_db()
    sys.exit(0 if success else 1)
