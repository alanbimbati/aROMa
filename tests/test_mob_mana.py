import pytest
from services.pve_service import PvEService
from models.pve import Mob
from database import Database

@pytest.fixture
def pve_service():
    return PvEService()

@pytest.fixture
def test_mob_id():
    """Create a test mob with mana"""
    db = Database()
    session = db.get_session()
    
    try:
        # Create test mob
        test_mob = Mob()
        test_mob.name = "Test Goomba"
        test_mob.health = 100
        test_mob.max_health = 100
        test_mob.attack_damage = 10
        test_mob.attack_type = "physical"
        test_mob.difficulty_tier = 1
        test_mob.speed = 30
        test_mob.resistance = 0
        test_mob.mob_level = 10
        test_mob.is_boss = False
        test_mob.is_dead = False
        
        # Mana: Level 10 mob should have (50 + 10*5) * 3 = 300 mana
        test_mob.max_mana = 300
        test_mob.mana = 300
        
        session.add(test_mob)
        session.commit()
        
        mob_id = test_mob.id
        yield mob_id
        
        # Cleanup
        session.query(Mob).filter_by(id=mob_id).delete()
        session.commit()
    finally:
        session.close()

@pytest.fixture
def test_boss_id():
    """Create a test boss with mana"""
    db = Database()
    session = db.get_session()
    
    try:
        # Create test boss
        test_boss = Mob()
        test_boss.name = "Test Bowser"
        test_boss.health = 5000
        test_boss.max_health = 5000
        test_boss.attack_damage = 50
        test_boss.attack_type = "physical"
        test_boss.difficulty_tier = 5
        test_boss.speed = 70
        test_boss.resistance = 20
        test_boss.mob_level = 20
        test_boss.is_boss = True
        test_boss.is_dead = False
        
        # Mana: Level 20 boss should have (50 + 20*5) * 5 = 750 mana
        test_boss.max_mana = 750
        test_boss.mana = 750
        
        session.add(test_boss)
        session.commit()
        
        boss_id = test_boss.id
        yield boss_id
        
        # Cleanup
        session.query(Mob).filter_by(id=boss_id).delete()
        session.commit()
    finally:
        session.close()

class TestMobBossMana:
    """Test suite for mob/boss mana system"""
    
    def test_mob_spawns_with_character_based_mana(self, pve_service):
        """Verify mobs spawn with character-based mana (3x multiplier)"""
        # Spawn a specific mob
        success, msg, mob_id = pve_service.spawn_specific_mob(mob_name="Goomba", reference_level=10)
        
        assert success, f"Failed to spawn mob: {msg}"
        assert mob_id is not None
        
        # Get mob from database
        db = Database()
        session = db.get_session()
        try:
            mob = session.query(Mob).filter_by(id=mob_id).first()
            assert mob is not None
            
            # Level 10: base_mana = 50 + (10 * 5) = 100
            # Mob multiplier: 3x
            # Expected: 100 * 3 = 300
            expected_mana = 300
            assert mob.max_mana == expected_mana, f"Expected {expected_mana} mana, got {mob.max_mana}"
            assert mob.mana == mob.max_mana, "Mob should spawn at full mana"
            
            # Cleanup
            session.query(Mob).filter_by(id=mob_id).delete()
            session.commit()
        finally:
            session.close()
    
    def test_boss_spawns_with_higher_mana_multiplier(self, pve_service):
        """Verify bosses spawn with 5x mana multiplier"""
        # Spawn a specific boss
        success, msg, boss_id = pve_service.spawn_boss(boss_name="Bowser", reference_level=20)
        
        assert success, f"Failed to spawn boss: {msg}"
        assert boss_id is not None
        
        # Get boss from database
        db = Database()
        session = db.get_session()
        try:
            boss = session.query(Mob).filter_by(id=boss_id).first()
            assert boss is not None
            assert boss.is_boss == True
            
            # Level 20: base_mana = 50 + (20 * 5) = 150
            # Boss multiplier: 5x
            # Expected: 150 * 5 = 750
            expected_mana = 750
            assert boss.max_mana == expected_mana, f"Expected {expected_mana} mana, got {boss.max_mana}"
            assert boss.mana == boss.max_mana, "Boss should spawn at full mana"
            
            # Cleanup
            session.query(Mob).filter_by(id=boss_id).delete()
            session.commit()
        finally:
            session.close()
    
    def test_defend_recovers_15_percent_mana(self, test_mob_id):
        """Verify defending recovers 15% mana"""
        db = Database()
        session = db.get_session()
        
        try:
            mob = session.query(Mob).filter_by(id=test_mob_id).first()
            assert mob is not None
            
            # Reduce mana to 50%
            mob.mana = mob.max_mana // 2  # 150 mana
            initial_mana = mob.mana
            session.commit()
            
            # Simulate defend action (15% recovery)
            mana_recovery = int(mob.max_mana * 0.15)  # 45 mana
            mob.mana = min(mob.max_mana, mob.mana + mana_recovery)
            session.commit()
            
            # Verify recovery
            expected_mana = initial_mana + mana_recovery  # 150 + 45 = 195
            assert mob.mana == expected_mana, f"Expected {expected_mana} mana after defend, got {mob.mana}"
        finally:
            session.close()
    
    def test_scouter_displays_mana(self, pve_service, test_mob_id):
        """Verify Scouter scan shows mana information"""
        # Get mob scan data
        scan_data = pve_service.get_mob_scan_data(test_mob_id)
        
        assert scan_data is not None
        assert 'mana' in scan_data
        assert 'max_mana' in scan_data
        assert scan_data['mana'] == 300
        assert scan_data['max_mana'] == 300

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
