#!/usr/bin/env python3
"""
Test script per verificare i preset stats funzionano correttamente
"""

from database import Database
from models.user import Utente
from services.user_service import UserService
import json

def test_stat_presets():
    print("🧪 Testing Stat Presets...")
    
    db = Database()
    user_service = UserService()
    session = db.get_session()
    
    try:
        # Get a test user
        user = session.query(Utente).first()
        if not user:
            print("❌ No users found in database")
            return
        
        print(f"\n👤 Testing with user: {user.nome} (Level {user.livello})")
        print(f"📊 Available points: {user.livello * 2}")
        
        # Load presets
        import os
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        preset_path = os.path.join(BASE_DIR, 'data', 'stat_presets.json')
        
        with open(preset_path, 'r') as f:
            data = json.load(f)
            presets = data['presets']
        
        print(f"\n📋 Found {len(presets)} presets:")
        for preset in presets:
            print(f"  {preset['icon']} {preset['name']}: {preset['description']}")
        
        # Test applying preset
        test_preset = presets[0]  # Mage
        print(f"\n🧙 Applying preset: {test_preset['name']}")
        
        success, msg = user_service.apply_stat_preset(user, test_preset['id'], session=session)
        
        if success:
            print(f"✅ {msg}")
            
            # Re-fetch user to see changes
            session.refresh(user)
            
            print("\n📈 New stat allocations:")
            print(f"  ❤️  Health: {user.allocated_health}")
            print(f"  💙 Mana: {user.allocated_mana}")
            print(f"  ⚔️  Damage: {user.allocated_damage}")
            print(f"  🛡️  Resistance: {user.allocated_resistance}")
            print(f"  ✨ Crit: {user.allocated_crit}")
            print(f"  ⚡ Speed: {user.allocated_speed}")
            print(f"\n💎 Remaining points: {user.stat_points}")
            
            total_allocated = (
                user.allocated_health +
                user.allocated_mana +
                user.allocated_damage +
                user.allocated_resistance +
                user.allocated_crit +
                user.allocated_speed
            )
            print(f"📊 Total allocated: {total_allocated}/{user.livello * 2}")
            
            if total_allocated + user.stat_points == user.livello * 2:
                print("✅ Point allocation is correct!")
            else:
                print("❌ Point allocation mismatch!")
        else:
            print(f"❌ {msg}")
        
        session.rollback()  # Don't actually save changes
        print("\n🔄 Test complete (changes rolled back)")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    test_stat_presets()
