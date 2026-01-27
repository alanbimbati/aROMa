
import unittest
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from services.user_service import UserService
from models.user import Utente
from database import Database

class TestProfileStats(unittest.TestCase):
    def setUp(self):
        self.db = Database()
        self.session = self.db.get_session()
        self.user_service = UserService()
        
        self.user = Utente(
            id_telegram=99999, 
            nome="StatTester", 
            username="stattester", 
            livello=10,
            stat_points=20
        )
        self.session.add(self.user)
        self.session.commit()
        
    def tearDown(self):
        self.session.query(Utente).filter_by(id_telegram=99999).delete()
        self.session.commit()
        self.session.close()
        
    def test_allocation(self):
        """Test allocating points to stats"""
        initial_points = self.user.stat_points
        
        # Allocate to Health
        success, msg = self.user_service.allocate_stat_point(self.user, "health")
        self.assertTrue(success)
        
        self.session.refresh(self.user)
        self.assertEqual(self.user.stat_points, initial_points - 1)
        self.assertEqual(self.user.allocated_health, 1)
        
        # Check if max_health increased
        # Base HP at lv 10 = 100 + (10*5) = 150
        # +1 alloc = +10 HP -> 160
        self.assertEqual(self.user.max_health, 160)
        
    def test_resistance_cap(self):
        """Test resistance cannot exceed 75%"""
        # Set resistance to 74
        self.user.allocated_resistance = 74
        self.user.stat_points = 10
        self.session.commit()
        self.user_service.recalculate_stats(self.user.id_telegram)
        
        # Allocate 1 point -> 75
        success, msg = self.user_service.allocate_stat_point(self.user, "resistance")
        self.assertTrue(success)
        self.session.refresh(self.user)
        self.assertEqual(self.user.resistance, 75)
        
        # Allocate another -> Should fail or cap
        # The service returns False if >= 75
        success, msg = self.user_service.allocate_stat_point(self.user, "resistance")
        self.assertFalse(success)
        self.assertIn("massima raggiunta", msg)
        
    def test_reset_stats(self):
        """Test resetting stats"""
        self.user.allocated_damage = 10
        self.user.stat_points = 0
        self.user.points = 1000 # Wumpa
        self.session.commit()
        
        success, msg = self.user_service.reset_stats(self.user, paid=True)
        self.assertTrue(success)
        
        self.session.refresh(self.user)
        self.assertEqual(self.user.allocated_damage, 0)
        # Level 10 * 2 = 20 points
        self.assertEqual(self.user.stat_points, 20)
        # Cost check (500)
        self.assertEqual(self.user.points, 500)
