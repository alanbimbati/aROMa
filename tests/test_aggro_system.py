import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.pve_service import PvEService
from services.status_effects import StatusEffect
from models.pve import Mob
from models.user import Utente
from models.combat import CombatParticipation

class TestAggroSystem(unittest.TestCase):
    
    def setUp(self):
        # Patch __init__ to avoid DB connection
        with patch.object(PvEService, '__init__', return_value=None):
            self.service = PvEService()
            
        self.service.db = MagicMock()
        self.service.user_service = MagicMock()
        self.service.targeting_service = MagicMock()
        self.service.mob_data = []
        self.service.recent_mobs = []
        self.service.pending_mob_effects = {}
        self.service.combat_service = MagicMock()
        self.service.event_dispatcher = MagicMock()
        self.service.damage_calculator = MagicMock()
        self.service.achievement_tracker = MagicMock()
        self.service.mob_ai = MagicMock()

    @patch('random.choices')
    def test_aggro_logic_execution(self, mock_choices):
        """Mock random.choices to verify weights are passed correctly"""
        
        session = MagicMock()
        
        # Real Mob Mock
        real_mob = MagicMock(name='RealMob')
        real_mob.id = 1
        real_mob.is_dead = False
        real_mob.dungeon_id = None # Important: prevent dungeon checks
        real_mob.aggro_end_time = None # Important: prevent datetime comparison
        real_mob.aggro_target_id = None
        real_mob.last_attack_time = None # Important: prevent cooldown check error
        
        # Configure the Query Mock Chain
        query_mock = MagicMock(name='QueryMock')
        session.query.return_value = query_mock
        
        def filter_by_side_effect(**kwargs):
            result_mock = MagicMock(name='FilterResult')
            
            if 'id_telegram' in kwargs:
                uid = kwargs.get('id_telegram')
                if uid == 101: result_mock.first.return_value = u1_obj
                elif uid == 102: result_mock.first.return_value = u2_obj
                
            elif 'id' in kwargs:
                if kwargs.get('id') == 1: 
                    result_mock.first.return_value = real_mob
                    
            return result_mock
            
        query_mock.filter_by.side_effect = filter_by_side_effect
        
        # Setup targets
        targets_pool = [101, 102]
        self.service.targeting_service.get_valid_targets.return_value = targets_pool
        
        p1 = MagicMock(user_id=101, damage_dealt=1000)
        p2 = MagicMock(user_id=102, damage_dealt=0)
        
        # Mock Users
        u1_obj = MagicMock(id_telegram=101)
        u2_obj = MagicMock(id_telegram=102)
        
        # Complex Side Effect for different model types
        def complex_query_side_effect(*args):
            mock_returned = MagicMock()
            
            if args and args[0] == Mob:
                mock_returned.filter_by.side_effect = filter_by_side_effect
                return mock_returned
            
            if args and args[0] == CombatParticipation:
                mock_returned.filter.return_value.all.return_value = [p1, p2]
                return mock_returned
            
            if args and args[0] == Utente:
                def user_filter_by(**kwargs):
                    res = MagicMock()
                    if kwargs.get('id_telegram') == 101: res.first.return_value = u1_obj
                    if kwargs.get('id_telegram') == 102: res.first.return_value = u2_obj
                    return res
                mock_returned.filter_by.side_effect = user_filter_by
                return mock_returned
                
            return mock_returned
        
        session.query.side_effect = complex_query_side_effect

        # Mock Status Effects
        with patch('services.status_effects.StatusEffect.get_active_effects') as mock_get_effects:
            def effects_side_effect(user):
                if user == u2_obj: return [{'effect': 'defense_up'}] # Tank
                return []
            mock_get_effects.side_effect = effects_side_effect
            
            # Force choice
            mock_choices.return_value = [101]
            
            # Execute
            self.service.mob_random_attack(specific_mob_id=1, session=session)
            
            # Assertions
            self.assertTrue(mock_choices.called, "random.choices should have been called")
            args, kwargs = mock_choices.call_args
            population = args[0]
            weights = kwargs['weights']
            
            idx1 = population.index(101)
            idx2 = population.index(102)
            
            # Current logic: max(dmg, 1.0) and x5 Defense
            self.assertEqual(weights[idx1], 1000.0)
            self.assertEqual(weights[idx2], 5.0)

if __name__ == '__main__':
    unittest.main()
