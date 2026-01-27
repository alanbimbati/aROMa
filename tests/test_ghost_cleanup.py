
import unittest
import sys
import os
import datetime

# Add project root to path
sys.path.append(os.getcwd())

from services.dungeon_service import DungeonService
from models.dungeon import Dungeon, DungeonParticipant
from database import Database

class TestGhostCleanup(unittest.TestCase):
    def setUp(self):
        self.db = Database()
        self.session = self.db.get_session()
        self.dungeon_service = DungeonService()
        self.chat_id = 999999
        
        # Cleanup any existing dungeons for this chat
        self.session.query(DungeonParticipant).delete()
        self.session.query(Dungeon).filter_by(chat_id=self.chat_id).delete()
        self.session.commit()

    def tearDown(self):
        self.session.query(Dungeon).filter_by(chat_id=self.chat_id).delete()
        self.session.commit()
        self.session.close()

    def test_cleanup_ghost_registration(self):
        """Test that a registration dungeon with 0 participants is cleaned up"""
        # Create a ghost dungeon manually
        ghost = Dungeon(
            name="Ghost Dungeon",
            chat_id=self.chat_id,
            total_stages=3,
            status="registration",
            dungeon_def_id=1
        )
        self.session.add(ghost)
        self.session.commit()
        ghost_id = ghost.id
        
        # Verify it exists
        active = self.session.query(Dungeon).filter_by(id=ghost_id).first()
        self.assertEqual(active.status, "registration")
        
        # Call get_active_dungeon which should trigger cleanup
        result = self.dungeon_service.get_active_dungeon(self.chat_id)
        
        # Should be None because it was cleaned up
        self.assertIsNone(result)
        
        # Verify status in DB
        self.session.expire_all()
        ghost_db = self.session.query(Dungeon).filter_by(id=ghost_id).first()
        self.assertEqual(ghost_db.status, "failed")

    def test_create_dungeon_cleans_ghost(self):
        """Test that creating a new dungeon cleans up an existing ghost one"""
        # Create a ghost dungeon manually
        ghost = Dungeon(
            name="Old Ghost",
            chat_id=self.chat_id,
            total_stages=3,
            status="active",
            dungeon_def_id=1
        )
        self.session.add(ghost)
        self.session.commit()
        ghost_id = ghost.id
        
        # Try to create a new dungeon (creator_id=123)
        # This should succeed because the ghost is cleaned up
        new_id, msg = self.dungeon_service.create_dungeon(self.chat_id, 1, 123)
        
        self.assertIsNotNone(new_id)
        self.assertIn("Dungeon Creato", msg)
        
        # Verify old ghost is failed
        self.session.expire_all()
        ghost_db = self.session.query(Dungeon).filter_by(id=ghost_id).first()
        self.assertEqual(ghost_db.status, "failed")

if __name__ == '__main__':
    unittest.main()
