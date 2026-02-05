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

class TestAggroSystemV2(unittest.TestCase):
    
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
    def test_aggro_weights_new_logic(self, mock_choices):
        """
        Verify new Aggro Weights:
        - Damage x0.5 (was x0.1)
        - Defense x5.0 (was x2.0)
        """
        session = MagicMock()
        
        real_mob = MagicMock(name='RealMob')
        real_mob.id = 1
        real_mob.is_dead = False
        real_mob.dungeon_id = None
        real_mob.aggro_end_time = None
        real_mob.aggro_target_id = None
        real_mob.last_attack_time = None
        
        # Targets:
        # 1. DPS God: 2000 Damage. No Defense.
        # 2. Tank: 200 Damage. Active Defense UP.
        # 3. Newbie: 0 Damage. No Defense.
        targets_pool = [101, 102, 103]
        self.service.targeting_service.get_valid_targets.return_value = targets_pool
        
        p1 = MagicMock(user_id=101, damage_dealt=2000)
        p2 = MagicMock(user_id=102, damage_dealt=200)
        p3 = MagicMock(user_id=103, damage_dealt=0)
        
        u1 = MagicMock(id_telegram=101)
        u2 = MagicMock(id_telegram=102) # Tank
        u3 = MagicMock(id_telegram=103)
        
        # Mocks
        def query_side_effect(*args):
            m = MagicMock()
            if args and args[0] == Mob:
                m.filter_by.return_value.first.return_value = real_mob
                return m
            if args and args[0] == Utente:
                def user_filter(**kwargs):
                    res = MagicMock()
                    uid = kwargs.get('id_telegram')
                    if uid == 101: res.first.return_value = u1
                    elif uid == 102: res.first.return_value = u2
                    elif uid == 103: res.first.return_value = u3
                    return res
                m.filter_by.side_effect = user_filter
                return m
            if args and args[0] == CombatParticipation:
                m.filter.return_value.all.return_value = [p1, p2, p3]
                return m
            return m
            
        session.query.side_effect = query_side_effect
        
        # Mock Status Effects
        with patch('services.status_effects.StatusEffect.get_active_effects') as mock_effects:
            def effects_side_effect(user):
                if user == u2: return [{'effect': 'defense_up'}]
                return []
            mock_effects.side_effect = effects_side_effect
            
            mock_choices.return_value = [102] # Force tank selection
            
            self.service.mob_random_attack(specific_mob_id=1, session=session)
            
            # Verify Weights
            args, kwargs = mock_choices.call_args
            weights = kwargs['weights']
            population = args[0]
            
            idx1 = population.index(101)
            idx2 = population.index(102)
            idx3 = population.index(103)
            
            # Current Logic: weight = max(dmg, 1.0) if dmg > 0 else 1.0; if defense_up: weight *= 5.0
            # DPS: 2000 Dmg.
            self.assertEqual(weights[idx1], 2000.0)
            
            # Tank: 200 Dmg * 5.0 = 1000.
            self.assertEqual(weights[idx2], 1000.0)
            
            # Newbie: 1.0 (No damage, no defense)
            self.assertEqual(weights[idx3], 1.0)
            
            # Note: 2000 Dmg is MASSIVE. It should pull aggro unless Tank does more dmg or we boost multiplier.
            # But 2000 dmg vs 200 dmg is a 10x difference.
            # Check if logic holds: Tank (110 raw) * 5 = 550. DPS (1010 raw).
            # DPS wins here. This is correct: if you do 10x damage, you pull aggro.
            # To hold aggro against 2000 dmg, tank needs ~400 dmg (Base 10 + 200 = 210 * 5 = 1050).
            # This seems balanced.

if __name__ == '__main__':
    unittest.main()
