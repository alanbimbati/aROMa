from database import Database
from services.equipment_service import EquipmentService

# Test the has_equipped_scouter function
db = Database()
equipment_service = EquipmentService()

def has_equipped_scouter(user_id):
    """Check if the user has any item with 'scan' effect equipped"""
    try:
        equipped = equipment_service.get_equipped_items(user_id)
        for u_item, item in equipped:
            if item.effect_type in ['scan', 'scouter_scan']:
                return True
    except Exception as e:
        print(f"Error checking scan ability for {user_id}: {e}")
    return False

# Test with users who have scouters equipped (from debug output)
test_users = [71130078, 5617079061, 62716473]

print("Testing has_equipped_scouter function:")
for user_id in test_users:
    result = has_equipped_scouter(user_id)
    print(f"  User {user_id}: {'✅ HAS SCOUTER' if result else '❌ NO SCOUTER'}")
