
import sys
import os
import unittest
import json
import datetime
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path = [os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))] + sys.path

from services.pve_service import PvEService
from services.status_effects import StatusEffect
from services.combat_service import CombatService
from models.user import Utente
from models.pve import Mob
from models.combat import CombatParticipation

class TestDungeonFixes(unittest.TestCase):
    def setUp(self):
        self.pve_service = PvEService()
        self.mock_session = MagicMock()
        self.pve_service.db = MagicMock()
        self.pve_service.db.get_session.return_value = self.mock_session
        self.pve_service.user_service = MagicMock()
        # Prevent early returns from checks
        self.pve_service.user_service.check_fatigue.return_value = False
        self.pve_service.user_service.get_resting_status.return_value = None
        
        self.pve_service.reward_service = MagicMock()
        self.pve_service.achievement_tracker = MagicMock()
        self.pve_service.season_manager = MagicMock()
        self.pve_service.equipment_service = MagicMock()
        self.pve_service.mob_ai = MagicMock()

    def test_distribute_boss_rewards_crash_fix(self):
        """Verify distribute_boss_rewards returns 3 values even on failure"""
        print("\n[TEST] Verifying Boss Reward Crash Fix...")
        # Setup: Query returns None (boss not found)
        self.mock_session.query().filter_by().first.return_value = None
        
        # Call the function
        try:
            rewards, wumpa, xp = self.pve_service.distribute_boss_rewards(
                mob_id=999, 
                killer_user=MagicMock(), 
                final_damage=100, 
                session=self.mock_session
            )
            print(f"Result: rewards={rewards}, wumpa={wumpa}, xp={xp}")
            self.assertEqual(rewards, [])
            self.assertEqual(wumpa, 0)
            self.assertEqual(xp, 0)
            print("[PASS] Function returned safe default values.")
        except Exception as e:
            self.fail(f"Function crashed with: {e}")

    def test_status_effect_source_id(self):
        """Verify apply_status correctly stores source_id"""
        print("\n[TEST] Verifying Status Effect Source ID Tracking...")
        target = MagicMock()
        target.active_status_effects = '[]'
        
        # Test applying effect with source_id
        source_id = 12345
        # Use 'stun' as defined in EFFECTS dict, not 'stunned'
        success = StatusEffect.apply_status(target, 'stun', duration=1, source_id=source_id)
        
        self.assertTrue(success)
        
        # Parse result
        effects = json.loads(target.active_status_effects)
        self.assertEqual(len(effects), 1)
        self.assertEqual(effects[0]['effect'], 'stun')
        self.assertEqual(effects[0].get('source_id'), source_id)
        print(f"[PASS] Status effect stored source_id: {effects[0].get('source_id')}")

    def test_battle_service_passes_source_id(self):
        """Verify BattleService returns source_id in effect dict"""
        print("\n[TEST] Verifying BattleService Source ID Propagation...")
        bs = CombatService()
        ability = MagicMock()
        ability.status_effect = 'stun' # Use valid effect
        ability.status_chance = 100
        ability.status_duration = 1
        
        source_id = 999
        result = bs.apply_status_effect(MagicMock(), ability, source_id=source_id)
        
        self.assertIsNotNone(result)
        self.assertEqual(result.get('source_id'), source_id)
        print(f"[PASS] BattleService returned dict with source_id: {result.get('source_id')}")

    @patch('services.dungeon_service.DungeonService')
    def test_attack_mob_dungeon_progression(self, MockDungeonService):
        """Verify attack_mob attempts dungeon progression even if rewards fail"""
        print("\n[TEST] Verifying Dungeon Progression Resilience...")
        
        # Setup mocks
        mock_ds_instance = MockDungeonService.return_value
        mock_ds_instance.check_step_completion.return_value = ("Step Complete", [])
        
        # Mock distribute_rewards to raise exception
        self.pve_service.reward_service = MagicMock()
        self.pve_service.reward_service.distribute_rewards = MagicMock(side_effect=Exception("Simulated Reward Crash"))
        self.pve_service.reward_service.calculate_rewards = MagicMock(return_value=[])
        
        # Use real objects to avoid MagicMock comparison errors
        user = Utente(id_telegram=123, nome="TestUser", health=100, max_health=100, mana=100, max_mana=100, speed=10)
        user.livello = 1
        user.livello_selezionato = 1
        user.last_attack_time = None
        user.active_status_effects = '[]'
        
        mob = Mob(id=555, name="TestMob", health=100, max_health=100, is_boss=True, dungeon_id="test_dungeon")
        mob.mob_level = 1
        mob.resistance = 0
        mob.last_message_id = 999
        mob.attack_damage = 10
        mob.attack_type = "Normal"
        mob.spawn_time = datetime.datetime.now()
        
        # Setup participants and combat result
        participant = MagicMock()
        participant.user_id = 123
        mock_ds_instance.get_dungeon_participants.return_value = [participant]
        mock_ds_instance.get_user_active_dungeon.return_value = None
        
        self.pve_service.combat_service.calculate_damage = MagicMock(return_value={
            'damage': 1000,
            'is_crit': False,
            'effectiveness': 1.0,
            'type': 'Normal'
        })
        
        # Setup specific query return values
        def query_side_effect(*args, **kwargs):
            if not args: return MagicMock()
            model = args[0]
            m = MagicMock()
            if model == Mob:
                m.filter_by.return_value.first.return_value = mob
            elif model == CombatParticipation:
                m.filter_by.return_value.first.return_value = None
            elif model == Utente:
                m.filter_by.return_value.first.return_value = user
            return m
            
        self.mock_session.query.side_effect = query_side_effect
        self.pve_service.get_combat_participants = MagicMock(return_value=[])
        
        # Ensure reward calculations don't return MagicMocks that crash comparisons
        self.pve_service.reward_service.calculate_rewards.return_value = []
        self.pve_service.reward_service.distribute_rewards.side_effect = Exception("Simulated Reward Crash")
        
        # Mock Character Loader to avoid MagicMock comparison errors in attack_mob
        with patch('services.character_loader.get_character_loader') as MockCharLoader:
            MockCharLoader.return_value.get_character_by_id.return_value = {
                'mana_cost': 0,
                'special_attack_mana_cost': 0,
                'crit_chance': 5,
                'crit_multiplier': 1.5,
                'name': 'TestChar'
            }
            
            # Execute
            try:
                # Correct call: base_damage is 2nd arg, mob_id is 5th or keyword
                self.pve_service.attack_mob(user, base_damage=1000, mob_id=mob.id, session=self.mock_session)
            except Exception as e:
                print(f"Exception during attack_mob: {e}")
            
        # Verify DungeonService instantiation
        if not MockDungeonService.called:
             print("[FAIL] DungeonService was NOT instantiated.")
        else:
             print("[PASS] DungeonService was instantiated.")

        # Verify check_step_completion was called
        if mock_ds_instance.check_step_completion.called:
             print("[PASS] check_step_completion was called.")
        else:
             print("[FAIL] check_step_completion was NOT called.")
             
        mock_ds_instance.check_step_completion.assert_called()
        print("[PASS] check_step_completion assertion passed.")

if __name__ == '__main__':
    unittest.main()
