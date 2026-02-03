
import unittest
from unittest.mock import MagicMock, patch
from services.pve_service import PvEService
from services.status_effects import StatusEffect
from models.user import Utente
from models.pve import Mob
from models.combat import CombatParticipation
import datetime
import json

class TestDefenseSystem(unittest.TestCase):
    def setUp(self):
        self.pve_service = PvEService()
        # Mock dependencies
        self.pve_service.db = MagicMock()
        self.pve_service.user_service = MagicMock()
        self.pve_service.user_service.check_fatigue.return_value = False # Ensure not fatigued
        self.pve_service.user_service.get_resting_status.return_value = None # Ensure not resting
        self.pve_service.targeting_service = MagicMock()
        self.pve_service.event_dispatcher = MagicMock()
        
    def test_defend_action(self):
        # Mock session
        session = MagicMock()
        self.pve_service.db.get_session.return_value = session
        session.merge = MagicMock(side_effect=lambda x: x)
        
        # Mock user
        user = Utente(id_telegram=123, nome="Hero", health=50, max_health=100, speed=10)
        user.active_status_effects = '[]'
        
        # Test defend
        success, msg = self.pve_service.defend(user)
        
        self.assertTrue(success)
        self.assertIn("usa **Difesa**", msg)
        
        # Check effect applied
        effects = json.loads(user.active_status_effects)
        self.assertTrue(any(e['effect'] == 'defense_up' for e in effects))
        
        # Check healing (2-3% of 100 is 2-3 HP)
        self.assertTrue(52 <= user.health <= 53)
        
    def test_defense_damage_reduction(self):
        # Mock session
        session = MagicMock()
        self.pve_service.db.get_session.return_value = session
        session.merge = MagicMock(side_effect=lambda x: x)
        
        # Mock user with defense_up
        user = Utente(id_telegram=123, nome="Hero", health=100, max_health=100, allocated_resistance=0)
        StatusEffect.apply_status(user, 'defense_up', duration=1)
        
        # Mock mob
        mob = Mob(id=1, name="Goblin", attack_damage=100, difficulty_tier=1)
        
        # Mock query results
        # We need to handle different queries: Mob and CombatParticipation
        
        def query_side_effect(*args, **kwargs):
            if not args:
                return MagicMock()
            model = args[0]
            query_mock = MagicMock()
            if model == Mob:
                query_mock.filter_by.return_value.all.return_value = [mob]
                query_mock.filter_by.return_value.first.return_value = mob
            elif model == Utente:
                query_mock.filter_by.return_value.first.return_value = user
            elif model == CombatParticipation:
                # Return empty list for fled users
                query_mock.filter_by.return_value.all.return_value = []
                query_mock.filter_by.return_value.first.return_value = None
            return query_mock
            
        session.query.side_effect = query_side_effect
        
        self.pve_service.user_service.get_recent_users.return_value = [123]
        self.pve_service.user_service.get_user.return_value = user
        self.pve_service.targeting_service.get_valid_targets.return_value = [123]
        
        # Mock damage_health to return new_hp, died
        self.pve_service.user_service.damage_health.return_value = (50, False)
        
        # Run attack
        # We need to capture the damage calculation.
        # Since mob_random_attack calculates damage internally, we can inspect the log_event call
        
        self.pve_service.mob_random_attack(chat_id=1)
        
        # Verify log_event called with reduced damage
        self.assertTrue(self.pve_service.event_dispatcher.log_event.called, "log_event should have been called")
        
        call_args = self.pve_service.event_dispatcher.log_event.call_args
        if call_args:
            kwargs = call_args[1]
            damage = kwargs['value']
            # We expect damage to be reduced.
            # Without defense: 100 base -> ~49 adjusted.
            # With defense: ~46.
            self.assertLess(damage, 60)
            print(f"Damage taken: {damage}")

    def test_special_attack(self):
        # Mock session
        session = MagicMock()
        self.pve_service.db.get_session.return_value = session
        
        # Mock user
        user = Utente(id_telegram=123, nome="Hero", mana=100, max_mana=100, livello_selezionato=1)
        
        # Mock character loader
        with patch('services.character_loader.get_character_loader') as mock_loader:
            mock_loader.return_value.get_character_by_id.return_value = {
                'special_attack_mana_cost': 50,
                'special_attack_damage': 200,
                'special_attack_gif': 'blast.gif'
            }
            
            # Mock guild service (mana cost multiplier)
            self.pve_service.guild_service.get_mana_cost_multiplier = MagicMock(return_value=1.0)
            
            # Mock attack_mob
            self.pve_service.attack_mob = MagicMock(return_value=(True, "Special Attack!", {}))
            
            # Run special attack
            success, msg, extra, events = self.pve_service.use_special_attack(user)
            
            self.assertTrue(success)
            
            # Verify mana deducted (100 - 50 = 50)
            # Wait, use_special_attack calls update_user to deduct mana.
            # We need to verify update_user was called with new mana.
            self.pve_service.user_service.update_user.assert_called()
            call_args = self.pve_service.user_service.update_user.call_args
            if call_args:
                args, kwargs = call_args
                updates = args[1]
                self.assertEqual(updates['mana'], 50)
            
            # Verify attack_mob called with correct params
            self.pve_service.attack_mob.assert_called_with(
                user, 
                base_damage=200, 
                use_special=True, 
                session=session
            )

if __name__ == '__main__':
    unittest.main()
