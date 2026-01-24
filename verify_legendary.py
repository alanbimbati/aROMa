from database import Database
from models.item import Item
from models.inventory import UserItem
from models.user import Utente
from services.user_service import UserService
from services.equipment_service import EquipmentService
from services.transformation_service import TransformationService
from services.pve_service import PvEService
from models.pve import Mob
import sys
import os

def verify_legendary():
    print(f"DEBUG: TransformationService file: {TransformationService.__module__}")
    # Actually need to inspect the class or module
    import services.transformation_service
    print(f"DEBUG: TransformationService file path: {services.transformation_service.__file__}")
    print("Initializing Database...")
    db = Database()
    us = UserService()
    es = EquipmentService()
    ts = TransformationService()
    ps = PvEService()
    session = db.get_session()
    
    user_id = 666666
    # Cleanup
    session.query(UserItem).filter_by(user_id=user_id).delete()
    session.query(Utente).filter_by(id_telegram=user_id).delete()
    session.commit()
    
    u = Utente(id_telegram=user_id, username="LegendTester", nome="Tester", livello=50)
    session.add(u)
    session.commit()
    us.recalculate_stats(user_id)
    
    # 1. Test Potara
    print("--- Testing Potara Fusion ---")
    potara_l = session.query(Item).filter_by(name="Potara Earring (L)").first()
    potara_r = session.query(Item).filter_by(name="Potara Earring (R)").first()
    
    es.add_item_to_user(user_id, potara_l.id)
    es.add_item_to_user(user_id, potara_r.id)
    
    inv = es.get_user_inventory(user_id)
    ui_l = [x[0] for x in inv if x[1].id == potara_l.id][0]
    ui_r = [x[0] for x in inv if x[1].id == potara_r.id][0]
    
    us.equip_item(user_id, ui_l.id)
    us.equip_item(user_id, ui_r.id)
    
    # Simulate /fusion command logic
    trans_id = ts.get_transformation_id_by_name("Potara Fusion")
    
    # Mock wrapper
    class UserWrapper:
        def __init__(self, uid): self.id_telegram = uid
        
    success, msg = ts.activate_temporary_transformation(UserWrapper(user_id), trans_id)
    print(f"Fusion Result: {success} - {msg}")
    
    if success:
        bonuses = ts.get_transformation_bonuses(UserWrapper(user_id))
        print(f"Fusion Bonuses: {bonuses}")
        if bonuses['health'] == 500:
            print("✅ Potara Fusion Verified!")
        else:
            print("❌ Potara Fusion Stats Mismatch.")
    else:
        print("❌ Potara Fusion Failed.")
        
    # 2. Test Scouter
    print("--- Testing Scouter ---")
    scouter = session.query(Item).filter_by(name="Saiyan Scouter").first()
    es.add_item_to_user(user_id, scouter.id)
    inv = es.get_user_inventory(user_id)
    ui_scouter = [x[0] for x in inv if x[1].id == scouter.id][0]
    
    us.equip_item(user_id, ui_scouter.id)
    
    # Create dummy mob
    mob = Mob(name="Test Mob", health=1000, max_health=1000, attack_damage=10, attack_type="physical")
    
    card = ps.get_status_card(mob, is_user=False, user_id=user_id)
    print("Card Output:")
    print(card)
    
    if "Scouter Active" in card:
        print("✅ Scouter Verified!")
    else:
        print("❌ Scouter Failed (No 'Scouter Active' text).")
        
    session.close()

if __name__ == "__main__":
    verify_legendary()
