import sys
sys.path.append('/home/alan/Documenti/Coding/aroma')

from services.cultivation_service import CultivationService
from models.cultivation import GardenSlot
from models.user import Utente
from database import Database
import datetime

def test_clear_rotten_slot():
    """Test clearing rotten slots"""
    print("🧪 Testing Clear Rotten Slot Functionality...")
    
    cs = CultivationService()
    db = Database()
    session = db.get_session()
    
    # Use an existing user or create a test user
    test_user_id = 999999999
    
    try:
        # Clean up any existing test slots
        session.query(GardenSlot).filter_by(user_id=test_user_id).delete()
        session.commit()
        
        # Create a test user if needed
        existing_user = session.query(Utente).filter_by(id_telegram=test_user_id).first()
        if not existing_user:
            test_user = Utente(
                id_telegram=test_user_id,
                username="test_user_garden",
                points=1000,
                livello=1,
                exp=0
            )
            session.add(test_user)
            session.commit()
            print("✅ Test user created")
        
        # Create a rotten slot
        rotten_slot = GardenSlot(
            user_id=test_user_id,
            slot_id=1,
            seed_type="Semi di Wumpa",
            planted_at=datetime.datetime.now() - datetime.timedelta(hours=10),
            completion_time=datetime.datetime.now() - datetime.timedelta(hours=6),
            status="rotten",
            moisture=10,
            rot_time=datetime.datetime.now() - datetime.timedelta(hours=1)
        )
        session.add(rotten_slot)
        
        # Create a rotting slot
        rotting_slot = GardenSlot(
            user_id=test_user_id,
            slot_id=2,
            seed_type="Seme d'Erba Verde",
            planted_at=datetime.datetime.now() - datetime.timedelta(hours=5),
            completion_time=datetime.datetime.now() - datetime.timedelta(hours=1),
            status="rotting",
            moisture=30,
            rot_time=datetime.datetime.now() + datetime.timedelta(minutes=30)
        )
        session.add(rotting_slot)
        
        # Create a ready slot (should NOT be clearable)
        ready_slot = GardenSlot(
            user_id=test_user_id,
            slot_id=3,
            seed_type="Semi di Wumpa",
            planted_at=datetime.datetime.now() - datetime.timedelta(hours=4),
            completion_time=datetime.datetime.now() - datetime.timedelta(minutes=10),
            status="ready",
            moisture=80
        )
        session.add(ready_slot)
        
        session.commit()
        print("✅ Test slots created")
        
        # Test 1: Clear rotten slot (should work)
        print("\n📝 Test 1: Clearing ROTTEN slot...")
        success, msg = cs.clear_rotten_slot(test_user_id, 1)
        assert success, f"Expected success, got: {msg}"
        print(f"✅ {msg}")
        
        # Verify slot is now empty
        session.expire_all()
        slot = session.query(GardenSlot).filter_by(user_id=test_user_id, slot_id=1).first()
        assert slot.status == 'empty', f"Expected empty, got: {slot.status}"
        assert slot.seed_type is None, "Seed type should be None"
        print("✅ Slot is now empty with all fields reset")
        
        # Test 2: Clear rotting slot (should work)
        print("\n📝 Test 2: Clearing ROTTING slot...")
        success, msg = cs.clear_rotten_slot(test_user_id, 2)
        assert success, f"Expected success, got: {msg}"
        print(f"✅ {msg}")
        
        # Test 3: Try to clear a ready slot (should fail)
        print("\n📝 Test 3: Trying to clear READY slot (should fail)...")
        success, msg = cs.clear_rotten_slot(test_user_id, 3)
        assert not success, f"Expected failure, but got success: {msg}"
        print(f"✅ Correctly rejected: {msg}")
        
        # Test 4: Try to clear non-existent slot (should fail)
        print("\n📝 Test 4: Trying to clear non-existent slot...")
        success, msg = cs.clear_rotten_slot(test_user_id, 99)
        assert not success, f"Expected failure, but got success: {msg}"
        print(f"✅ Correctly rejected: {msg}")
        
        print("\n🎉 All tests passed! The clear_rotten_slot function works correctly.")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        session.query(GardenSlot).filter_by(user_id=test_user_id).delete()
        session.query(Utente).filter_by(id_telegram=test_user_id).delete()
        session.commit()
        session.close()
        print("\n🧹 Test cleanup completed")

if __name__ == "__main__":
    test_clear_rotten_slot()
