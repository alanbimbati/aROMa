
import unittest
import sys
import os
import datetime
import json

# Add project root to path
sys.path.append(os.getcwd())

# Set TEST_DB environment variable to use test database
os.environ['TEST_DB'] = '1'

from services.pve_service import PvEService
from services.user_service import UserService
from services.dungeon_service import DungeonService
from models.user import Utente
from models.pve import Mob
from models.combat import CombatParticipation
from models.dungeon import Dungeon, DungeonParticipant
from models.stats import UserStat
from models.achievements import Achievement, UserAchievement, GameEvent
from models.inventory import UserItem
from models.item import Item
from models.dungeon_progress import DungeonProgress
from database import Database

class TestRewardsAndLeveling(unittest.TestCase):
    def setUp(self):
        self.db = Database()
        self.session = self.db.get_session()
        self.pve_service = PvEService()
        self.user_service = UserService()
        self.dungeon_service = DungeonService()
        
        self.chat_id = 777
        self.user_id = 17001
        
        # Ensure clean state: delete if exists
        self.session.query(Utente).filter_by(id_telegram=self.user_id).delete()
        self.session.commit()
        
        # Create test user
        self.user = Utente(
            id_telegram=self.user_id, 
            nome="RewardTester", 
            username="rewardtester", 
            livello=1,
            exp=0,
            points=0,
            health=100,
            current_hp=100,
            max_health=100,
            mana=50,
            current_mana=50,
            max_mana=50,
            base_damage=10,
            stat_points=2,
            last_wumpa_reset=datetime.datetime.now()
        )
        self.session.add(self.user)
        self.session.commit()
        
    def tearDown(self):
        self.session.query(Utente).filter_by(id_telegram=self.user_id).delete()
        self.session.query(Mob).filter_by(chat_id=self.chat_id).delete()
        self.session.query(DungeonParticipant).delete()
        self.session.query(Dungeon).filter_by(chat_id=self.chat_id).delete()
        self.session.query(CombatParticipation).filter_by(user_id=self.user_id).delete()
        self.session.commit()
        self.session.close()

    def test_world_mob_rewards(self):
        """Test that killing a world mob gives EXP and Wumpa"""
        # Spawn a mob
        success, msg, mob_id = self.pve_service.spawn_specific_mob(chat_id=self.chat_id)
        self.assertTrue(success)
        
        # Attack and kill the mob
        # We need to ensure the user is in the session for attack_mob
        user = self.session.query(Utente).filter_by(id_telegram=self.user_id).first()
        success, msg, _ = self.pve_service.attack_mob(user, base_damage=1000, mob_id=mob_id)
        self.assertTrue(success)
        self.assertIn("sconfitto", msg.lower())
        
        # Verify rewards
        self.session.expire_all()
        updated_user = self.session.query(Utente).filter_by(id_telegram=self.user_id).first()
        self.assertGreater(updated_user.exp, 0, f"EXP should be greater than 0 after kill. Msg: {msg}")
        self.assertGreater(updated_user.points, 0, f"Wumpa should be greater than 0 after kill. Msg: {msg}")
        print(f"World Mob Rewards: EXP={updated_user.exp}, Wumpa={updated_user.points}")

    def test_dungeon_mob_rewards(self):
        """Test that killing a dungeon mob gives rewards to participants"""
        # Create and start dungeon
        d_id, msg = self.dungeon_service.create_dungeon(self.chat_id, 1, self.user_id)
        self.dungeon_service.start_dungeon(self.chat_id)
        
        # Get spawned mob
        mob = self.session.query(Mob).filter_by(dungeon_id=d_id, is_dead=False).first()
        self.assertIsNotNone(mob)
        mob_id = mob.id
        
        # Attack and kill
        user = self.session.query(Utente).filter_by(id_telegram=self.user_id).first()
        success, msg, _ = self.pve_service.attack_mob(user, base_damage=1000, mob_id=mob_id)
        self.assertTrue(success, f"Attack failed: {msg}")
        
        # Verify rewards
        self.session.expire_all()
        updated_user = self.session.query(Utente).filter_by(id_telegram=self.user_id).first()
        self.assertGreater(updated_user.exp, 0)
        self.assertGreater(updated_user.points, 0)
        print(f"Dungeon Mob Rewards: EXP={updated_user.exp}, Wumpa={updated_user.points}")

    def test_dungeon_completion_rewards(self):
        """Test that completing a dungeon gives final rewards to all participants"""
        # Create and start dungeon
        d_id, msg = self.dungeon_service.create_dungeon(self.chat_id, 1, self.user_id)
        self.dungeon_service.start_dungeon(self.chat_id)
        
        # Record initial stats
        initial_user = self.session.query(Utente).filter_by(id_telegram=self.user_id).first()
        initial_exp = initial_user.exp
        initial_points = initial_user.points
        
        # Complete the dungeon
        msg = self.dungeon_service.complete_dungeon(d_id)
        self.assertIn("COMPLETATO", msg)
        
        # Verify final rewards
        self.session.expire_all()
        updated_user = self.session.query(Utente).filter_by(id_telegram=self.user_id).first()
        self.assertGreater(updated_user.exp, initial_exp)
        self.assertGreater(updated_user.points, initial_points)
        print(f"Dungeon Completion Rewards: EXP Gain={updated_user.exp - initial_exp}, Wumpa Gain={updated_user.points - initial_points}")

    def test_level_up_logic(self):
        """Test that reaching EXP threshold triggers level up and full heal"""
        user = self.session.query(Utente).filter_by(id_telegram=self.user_id).first()
        
        # Damage the user first to test full heal
        user.current_hp = 10
        user.current_mana = 5
        self.session.commit()
        
        # Add enough EXP to level up (Level 1 -> 2 usually requires 100-400 EXP)
        # Level 2 requirement is 235 EXP.
        # We'll add 300 to be safe for Level 2
        result = self.user_service.add_exp_by_id(self.user_id, 300)
        
        self.assertTrue(result['leveled_up'])
        self.assertGreaterEqual(result['new_level'], 2)
        
        # Verify persistence and full heal
        self.session.expire_all()
        updated_user = self.session.query(Utente).filter_by(id_telegram=self.user_id).first()
        self.assertGreaterEqual(updated_user.livello, 2)
        self.assertEqual(updated_user.current_hp, updated_user.max_health, "HP should be full after level up")
        self.assertEqual(updated_user.current_mana, updated_user.max_mana, "Mana should be full after level up")
        self.assertGreater(updated_user.stat_points, 2, "Stat points should increase after level up")
        
        print(f"Level Up: New Level={updated_user.livello}, HP={updated_user.current_hp}/{updated_user.max_health}, Stat Points={updated_user.stat_points}")

if __name__ == "__main__":
    unittest.main()
