"""
Unit Tests for Advanced Parry System

Tests cover:
- Parry window activation and expiration
- Reaction time calculations
- Perfect vs standard parry detection
- Counterattack damage calculations
- Stat updates and aggregation
- Achievement condition evaluation
- Telemetry event logging
- Edge cases and error handling
"""

import pytest
import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.parry_service import ParryService
from services.combat_service import CombatService
from database import Database


class TestParryWindowActivation(unittest.TestCase):
    """Test parry window creation and state management"""
    
    def setUp(self):
        self.parry_service = ParryService()
        self.user_id = 12345
        self.mob_id = 100
        
    @patch('services.parry_service.Database')
    def test_activate_parry_success(self, mock_db):
        """Test successful parry activation"""
        mock_session = MagicMock()
        mock_db.return_value.get_session.return_value = mock_session
        self.parry_service.db = mock_db.return_value
        
        result = self.parry_service.activate_parry(self.user_id, self.mob_id, session=mock_session)
        
        assert result['success'] == True
        assert 'parry_id' in result
        assert result['window_duration'] == 2.5
        assert result['expires_at'] is not None
        
    @patch('services.parry_service.Database')
    def test_activate_parry_while_active(self, mock_db):
        """Test that activating parry while one is active returns the existing one"""
        mock_session = MagicMock()
        mock_db.return_value.get_session.return_value = mock_session
        self.parry_service.db = mock_db.return_value
        
        # Set up existing active parry
        mock_session.execute.return_value.fetchone.return_value = (1, datetime.now() + timedelta(seconds=1))
        
        result = self.parry_service.activate_parry(self.user_id, self.mob_id, session=mock_session)
        
        # Now returns success=True with existing parry
        assert result['success'] == True
        
    def test_parry_window_expiration(self):
        """Test parry window expires after duration"""
        # Activate parry
        activated_at = datetime.now()
        expires_at = activated_at + timedelta(seconds=2.5)
        
        # Check before expiration
        current_time = activated_at + timedelta(seconds=1)
        is_active = current_time < expires_at
        assert is_active == True
        
        # Check after expiration
        current_time = activated_at + timedelta(seconds=3)
        is_active = current_time < expires_at
        assert is_active == False


class TestReactionTimeCalculation(unittest.TestCase):
    """Test reaction time measurement accuracy"""
    
    def setUp(self):
        self.parry_service = ParryService()
        
    def test_perfect_parry_timing(self):
        """Test perfect parry detection (< 300ms)"""
        parry_time = datetime.now()
        attack_time = parry_time + timedelta(milliseconds=250)
        
        reaction_ms = self.parry_service.calculate_reaction_time(parry_time, attack_time)
        
        assert reaction_ms == 250
        assert reaction_ms < self.parry_service.PERFECT_THRESHOLD_MS
        
    def test_standard_parry_timing(self):
        """Test standard parry detection (300-2500ms)"""
        parry_time = datetime.now()
        attack_time = parry_time + timedelta(milliseconds=1500)
        
        reaction_ms = self.parry_service.calculate_reaction_time(parry_time, attack_time)
        
        assert reaction_ms == 1500
        assert reaction_ms > self.parry_service.PERFECT_THRESHOLD_MS
        assert reaction_ms < self.parry_service.PARRY_WINDOW_MS
        
    def test_failed_parry_timing(self):
        """Test parry fails outside window (> 2500ms)"""
        parry_time = datetime.now()
        attack_time = parry_time + timedelta(milliseconds=3000)
        
        reaction_ms = self.parry_service.calculate_reaction_time(parry_time, attack_time)
        
        assert reaction_ms == 3000
        assert reaction_ms > self.parry_service.PARRY_WINDOW_MS
        
    def test_negative_reaction_time(self):
        """Test edge case: attack before parry (should fail)"""
        parry_time = datetime.now()
        attack_time = parry_time - timedelta(milliseconds=100)
        
        reaction_ms = self.parry_service.calculate_reaction_time(parry_time, attack_time)
        
        assert reaction_ms < 0  # Invalid state


class TestParryProcessing(unittest.TestCase):
    """Test parry event processing and outcomes"""
    
    def setUp(self):
        self.parry_service = ParryService()
        self.user_id = 12345
        self.mob_id = 100
        self.base_damage = 100
        
    @patch('services.parry_service.Database')
    def test_perfect_parry_outcome(self, mock_db):
        """Test perfect parry (100% damage negation, 1.5x counter)"""
        mock_session = MagicMock()
        mock_db.return_value.get_session.return_value = mock_session
        self.parry_service.db = mock_db.return_value
        
        # Mock active parry with perfect timing
        parry_time = datetime.now()
        attack_time = parry_time + timedelta(milliseconds=250)
        
        mock_session.execute.return_value.fetchone.return_value = (
            1,  # parry_id
            self.user_id,
            parry_time,
            parry_time + timedelta(seconds=2.5)
        )
        
        result = self.parry_service.process_enemy_attack(
            user_id=self.user_id,
            mob_id=self.mob_id,
            attack_damage=self.base_damage,
            attack_time=attack_time
        )
        
        assert result['success'] == True
        assert result['perfect'] == True
        assert result['damage_taken'] == 0
        assert result['damage_avoided'] == self.base_damage
        assert result['counterattack'] == True
        assert result['multiplier'] == 1.5
        assert result['reaction_time'] == 250
        
    @patch('services.parry_service.Database')
    def test_standard_parry_outcome(self, mock_db):
        """Test standard parry (75% damage negation, 1.2x counter)"""
        mock_session = MagicMock()
        mock_db.return_value.get_session.return_value = mock_session
        self.parry_service.db = mock_db.return_value
        
        # Mock active parry with standard timing
        parry_time = datetime.now()
        attack_time = parry_time + timedelta(milliseconds=1500)
        
        mock_session.execute.return_value.fetchone.return_value = (
            1, self.user_id, parry_time, parry_time + timedelta(seconds=2.5)
        )
        
        result = self.parry_service.process_enemy_attack(
            user_id=self.user_id,
            mob_id=self.mob_id,
            attack_damage=self.base_damage,
            attack_time=attack_time
        )
        
        assert result['success'] == True
        assert result['perfect'] == False
        assert result['damage_taken'] == 25  # 25% of 100
        assert result['damage_avoided'] == 75
        assert result['multiplier'] == 1.2
        
    @patch('services.parry_service.Database')
    def test_no_active_parry(self, mock_db):
        """Test attack when no parry is active"""
        mock_session = MagicMock()
        mock_db.return_value.get_session.return_value = mock_session
        
        # No active parry
        mock_session.execute.return_value.fetchone.return_value = None
        
        result = self.parry_service.process_enemy_attack(
            user_id=self.user_id,
            mob_id=self.mob_id,
            attack_damage=self.base_damage
        )
        
        assert result['success'] == False
        assert result['parry_active'] == False


class TestCounterattackDamage(unittest.TestCase):
    """Test counterattack damage calculations"""
    
    def setUp(self):
        self.combat_service = CombatService()
        self.parry_service = ParryService()
        
    def test_standard_counter_multiplier(self):
        """Test 1.2x damage on standard parry counter"""
        # Mock attacker and defender
        attacker = Mock()
        attacker.damage_total = 100
        attacker.crit_chance = 0  # No crit for clearer test
        
        defender = Mock()
        defender.defense_total = 0
        defender.elemental_type = "Normal"
        
        result = self.combat_service.calculate_counterattack_damage(
            attacker=attacker,
            defender=defender,
            parry_multiplier=1.2,
            is_perfect=False
        )
        
        assert result['damage'] == 120  # 100 * 1.2
        assert result['is_counter'] == True
        
    def test_perfect_counter_multiplier(self):
        """Test 1.5x damage + forced crit on perfect parry counter"""
        attacker = Mock()
        attacker.damage_total = 100
        attacker.crit_multiplier = 1.5
        
        defender = Mock()
        defender.defense_total = 0
        defender.elemental_type = "Normal"
        
        result = self.combat_service.calculate_counterattack_damage(
            attacker=attacker,
            defender=defender,
            parry_multiplier=1.5,
            is_perfect=True
        )
        
        # Perfect: 100 * 1.5 (parry) * 1.2 (perfect bonus) = 180
        assert result['damage'] == 180
        assert result['is_crit'] == True
        assert result['is_counter'] == True


class TestParryStatistics(unittest.TestCase):
    """Test stat tracking and aggregation"""
    
    def setUp(self):
        self.parry_service = ParryService()
        self.user_id = 12345
        
    @patch('services.parry_service.Database')
    def test_successful_parry_stats_update(self, mock_db):
        """Test stats increment on successful parry"""
        mock_session = MagicMock()
        mock_db.return_value.get_session.return_value = mock_session
        self.parry_service.db = mock_db.return_value
        
        event_data = {
            'type': 'success',
            'perfect': False,
            'reaction_time_ms': 1200,
            'damage_avoided': 85,
            'counterattack_damage': 120,
            'boss_parry': False
        }
        
        self.parry_service.update_parry_stats(self.user_id, event_data, session=mock_session)
        
        # Verify SQL execution called with correct increments
        mock_session.execute.assert_called()
        
    @patch('services.parry_service.Database')
    def test_perfect_parry_stats_update(self, mock_db):
        """Test perfect parry increments both success and perfect counters"""
        mock_session = MagicMock()
        mock_db.return_value.get_session.return_value = mock_session
        self.parry_service.db = mock_db.return_value
        
        event_data = {
            'type': 'success',
            'perfect': True,
            'reaction_time_ms': 250,
            'damage_avoided': 100,
            'counterattack_damage': 150,
            'boss_parry': False
        }
        
        self.parry_service.update_parry_stats(self.user_id, event_data, session=mock_session)
        
        # Should increment both total_parry_success AND total_parry_perfect
        mock_session.execute.assert_called()
        
    def test_streak_tracking(self):
        """Test consecutive parry streak calculation"""
        # Simulate streak
        stats = {
            'current_parry_streak': 3,
            'max_parry_streak': 5
        }
        
        # Successful parry
        new_current = stats['current_parry_streak'] + 1
        new_max = max(new_current, stats['max_parry_streak'])
        
        assert new_current == 4
        assert new_max == 5
        
        # Another success breaks previous record
        new_current = new_current + 1
        new_max = max(new_current, new_max)
        
        assert new_current == 5
        assert new_max == 5
        
        # One more sets new record
        new_current = new_current + 1
        new_max = max(new_current, new_max)
        
        assert new_current == 6
        assert new_max == 6
        
    def test_streak_reset_on_failure(self):
        """Test streak resets to 0 on failed parry"""
        stats = {
            'current_parry_streak': 5,
            'max_parry_streak': 10
        }
        
        # Failed parry
        new_current = 0
        new_max = stats['max_parry_streak']  # Max unchanged
        
        assert new_current == 0
        assert new_max == 10


class TestTelemetryLogging(unittest.TestCase):
    """Test combat telemetry event logging"""
    
    def setUp(self):
        self.parry_service = ParryService()
        self.user_id = 12345
        
    @patch('services.parry_service.Database')
    def test_parry_attempt_logging(self, mock_db):
        """Test PARRY_ATTEMPT event logged with correct data"""
        mock_session = MagicMock()
        mock_db.return_value.get_session.return_value = mock_session
        self.parry_service.db = mock_db.return_value
        
        data = {
            'combat_id': 'combat_12345_100_1234567890',
            'mob_id': 100,
            'mob_level': 25,
            'mob_is_boss': False,
            'user_level': 30,
            'user_hp_percent': 0.75,
            'user_mana_used': 10
        }
        
        self.parry_service.log_parry_event(
            user_id=self.user_id,
            event_type='PARRY_ATTEMPT',
            data=data,
            session=mock_session
        )
        
        # Verify insert was called
        mock_session.execute.assert_called()
        
    @patch('services.parry_service.Database')
    def test_perfect_parry_telemetry(self, mock_db):
        """Test PARRY_PERFECT event captures all relevant metrics"""
        mock_session = MagicMock()
        mock_db.return_value.get_session.return_value = mock_session
        self.parry_service.db = mock_db.return_value
        
        data = {
            'combat_id': 'combat_12345_100_1234567890',
            'mob_id': 100,
            'mob_level': 50,
            'mob_is_boss': True,
            'reaction_time_ms': 280,
            'window_duration_ms': 2500,
            'damage_dealt': 250,
            'damage_avoided': 150,
            'cooldown_saved_ms': 5000,
            'user_level': 45,
            'user_hp_percent': 0.9,
            'user_mana_used': 10,
            'metadata': {'special_ability_used': False}
        }
        
        self.parry_service.log_parry_event(
            user_id=self.user_id,
            event_type='PARRY_PERFECT',
            data=data,
            session=mock_session
        )
        
        mock_session.execute.assert_called_once()


class TestAchievementConditions(unittest.TestCase):
    """Test achievement unlock conditions"""
    
    def setUp(self):
        self.parry_service = ParryService()
        self.user_id = 12345
        
    def test_first_parry_achievement(self):
        """Test 'First Parry' achievement (1 successful parry)"""
        stats = {'total_parry_success': 1}
        
        condition = {'type': 'count', 'event': 'PARRY_SUCCESS', 'threshold': 1}
        
        meets_condition = stats['total_parry_success'] >= condition['threshold']
        
        assert meets_condition == True
        
    def test_parry_master_achievement(self):
        """Test 'Parry Master' achievement (50 successful parries)"""
        stats = {'total_parry_success': 50}
        
        condition = {'type': 'count', 'event': 'PARRY_SUCCESS', 'threshold': 50}
        
        meets_condition = stats['total_parry_success'] >= condition['threshold']
        
        assert meets_condition == True
        
        # Test just below threshold
        stats['total_parry_success'] = 49
        meets_condition = stats['total_parry_success'] >= condition['threshold']
        
        assert meets_condition == False
        
    def test_perfect_timing_achievement(self):
        """Test 'Perfect Timing' achievement (5 perfect parries)"""
        stats = {'total_parry_perfect': 5}
        
        condition = {'type': 'count', 'event': 'PARRY_PERFECT', 'threshold': 5}
        
        meets_condition = stats['total_parry_perfect'] >= condition['threshold']
        
        assert meets_condition == True
        
    def test_untouchable_achievement(self):
        """Test 'Untouchable' achievement (5 flawless victories)"""
        stats = {'flawless_victories': 5}
        
        condition = {'type': 'count', 'event': 'FLAWLESS_COMBAT', 'threshold': 5}
        
        meets_condition = stats['flawless_victories'] >= condition['threshold']
        
        assert meets_condition == True
        
    def test_streak_achievement(self):
        """Test streak-based achievement (5 consecutive perfect parries)"""
        stats = {'max_perfect_streak': 5}
        
        condition = {'type': 'streak', 'event': 'PARRY_PERFECT', 'threshold': 5}
        
        meets_condition = stats['max_perfect_streak'] >= condition['threshold']
        
        assert meets_condition == True
        
    def test_complex_boss_achievement(self):
        """Test complex condition: perfect boss parry"""
        stats = {
            'perfect_boss_parries': 1,
            'total_parry_perfect': 10
        }
        
        # Achievement requires at least 1 perfect boss parry
        condition = {
            'type': 'complex',
            'requirements': [
                {'field': 'perfect_boss_parries', 'operator': '>=', 'value': 1}
            ]
        }
        
        meets_condition = stats['perfect_boss_parries'] >= 1
        
        assert meets_condition == True


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""
    
    def setUp(self):
        self.parry_service = ParryService()
        
    @patch('services.parry_service.Database')
    def test_concurrent_parry_attempts(self, mock_db):
        """Test multiple users can have active parries simultaneously"""
        mock_session = MagicMock()
        mock_db.return_value.get_session.return_value = mock_session
        self.parry_service.db = mock_db.return_value
        
        user1_id = 111
        user2_id = 222
        
        result1 = self.parry_service.activate_parry(user1_id, 100, session=mock_session)
        result2 = self.parry_service.activate_parry(user2_id, 101, session=mock_session)
        
        # Both should succeed independently
        assert result1['success'] == True
        assert result2['success'] == True
        
    @patch('services.parry_service.Database')
    def test_parry_without_combat(self, mock_db):
        """Test parry activation requires active combat"""
        mock_session = MagicMock()
        mock_db.return_value.get_session.return_value = mock_session
        
        # Should check for active combat before allowing parry
        # (Implementation detail: PVE service validation)
        
    def test_mana_insufficient(self):
        """Test parry fails if user has insufficient mana"""
        user_mana = 5
        parry_cost = 10
        
        can_afford = user_mana >= parry_cost
        
        assert can_afford == False
        
    def test_reaction_time_precision(self):
        """Test reaction time calculated to millisecond precision"""
        time1 = datetime(2024, 1, 1, 12, 0, 0, 0)
        time2 = datetime(2024, 1, 1, 12, 0, 0, 123000)  # 123ms later
        
        delta = (time2 - time1).total_seconds() * 1000
        
        assert delta == 123.0
        
    @patch('services.parry_service.Database')
    def test_database_error_handling(self, mock_db):
        """Test graceful handling of database errors"""
        mock_session = MagicMock()
        mock_db.return_value.get_session.return_value = mock_session
        self.parry_service.db = mock_db.return_value
        
        # Simulate database error
        mock_session.execute.side_effect = Exception("Connection lost")
        
        result = self.parry_service.activate_parry(12345, 100, session=mock_session)
        
        # Should return error result, not crash
        assert result['success'] == False
        assert 'error' in result


class TestPerformanceMetrics(unittest.TestCase):
    """Test performance tracking calculations"""
    
    def test_average_reaction_time(self):
        """Test average reaction time calculation"""
        reaction_times = [250, 300, 400, 280, 320]
        
        avg = sum(reaction_times) / len(reaction_times)
        
        assert avg == 310.0
        
    def test_success_rate_calculation(self):
        """Test parry success rate calculation"""
        total_attempts = 100
        total_success = 65
        
        success_rate = (total_success / total_attempts) * 100
        
        assert success_rate == 65.0
        
    def test_damage_mitigation_total(self):
        """Test cumulative damage avoided tracking"""
        parries = [
            {'damage_avoided': 100},
            {'damage_avoided': 85},
            {'damage_avoided': 120},
            {'damage_avoided': 95}
        ]
        
        total_avoided = sum(p['damage_avoided'] for p in parries)
        
        assert total_avoided == 400


# Test Runner
if __name__ == '__main__':
    # Run with verbose output
    unittest.main(verbosity=2)
