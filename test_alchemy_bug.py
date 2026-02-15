#!/usr/bin/env python3
"""
Test script to verify alchemy resource consumption
"""
from services.alchemy_service import AlchemyService
from services.crafting_service import CraftingService
from database import Database
from models.resources import UserResource, Resource

db = Database()
alchemy_service = AlchemyService()
crafting_service = CraftingService()

# Test user ID
TEST_USER_ID = 999999999

session = db.get_session()

try:
    # 1. Give test user some resources
    print("=== Setting up test resources ===")
    crafting_service.add_resource_drop(TEST_USER_ID, resource_id=14, quantity=10, source="test", session=session)  # Erba Gialla
    crafting_service.add_resource_drop(TEST_USER_ID, resource_id=6, quantity=10, source="test", session=session)  # Polvere di Stelle
    crafting_service.add_resource_drop(TEST_USER_ID, resource_id=7, quantity=10, source="test", session=session)  # Essenza Vitale
    session.commit()
    
    # 2. Check resources before
    print("\n=== Resources BEFORE brewing ===")
    for res_id, res_name in [(14, "Erba Gialla"), (6, "Polvere di Stelle"), (7, "Essenza Vitale")]:
        ur = session.query(UserResource).filter_by(user_id=TEST_USER_ID, resource_id=res_id).first()
        print(f"{res_name}: {ur.quantity if ur else 0}")
    
    # 3. Brew an Elisir (requires: Erba Gialla x2, Polvere di Stelle x1, Essenza Vitale x1)
    print("\n=== Attempting to brew Elisir ===")
    success, msg = alchemy_service.brew_potion(TEST_USER_ID, "Elisir")
    print(f"Result: {success} - {msg}")
    
    # 4. Check resources after
    session.expire_all()  # Refresh from DB
    print("\n=== Resources AFTER brewing ===")
    for res_id, res_name in [(14, "Erba Gialla"), (6, "Polvere di Stelle"), (7, "Essenza Vitale")]:
        ur = session.query(UserResource).filter_by(user_id=TEST_USER_ID, resource_id=res_id).first()
        print(f"{res_name}: {ur.quantity if ur else 0}")
    
    # 5. Try brewing again
    print("\n=== Attempting to brew SECOND Elisir ===")
    success2, msg2 = alchemy_service.brew_potion(TEST_USER_ID, "Elisir")
    print(f"Result: {success2} - {msg2}")
    
    # 6. Check resources after second attempt
    session.expire_all()
    print("\n=== Resources AFTER second brew ===")
    for res_id, res_name in [(14, "Erba Gialla"), (6, "Polvere di Stelle"), (7, "Essenza Vitale")]:
        ur = session.query(UserResource).filter_by(user_id=TEST_USER_ID, resource_id=res_id).first()
        print(f"{res_name}: {ur.quantity if ur else 0}")
    
    # Cleanup
    print("\n=== Cleaning up test data ===")
    session.query(UserResource).filter_by(user_id=TEST_USER_ID).delete()
    from models.alchemy import AlchemyQueue
    session.query(AlchemyQueue).filter_by(user_id=TEST_USER_ID).delete()
    session.commit()
    print("Test complete!")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    session.rollback()
finally:
    session.close()
