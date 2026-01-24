from database import Database
from models.item import Item, ItemSet
from models.inventory import UserItem
from models.user import Utente
from services.user_service import UserService
from services.equipment_service import EquipmentService
import time

def verify_equipment():
    # Ensure models are registered
    print("Initializing Database...")
    db = Database()
    us = UserService()
    es = EquipmentService()
    session = db.get_session()
    
    # 1. Create Test User
    user_id = 555555
    # Clean up old test user
    session.query(UserItem).filter_by(user_id=user_id).delete()
    session.query(Utente).filter_by(id_telegram=user_id).delete()
    session.commit()
    
    u = Utente(id_telegram=user_id, username="EquipTester", nome="Tester", livello=10)
    session.add(u)
    session.commit()
    
    # Initial Recalculate to set base stats
    us.recalculate_stats(user_id)
    
    u = session.query(Utente).filter_by(id_telegram=user_id).first()
    print(f"Base Stats (Lv 10): HP {u.max_health}, Dmg {u.base_damage}")
    # Lv 10: HP = 100 + 50 = 150. Dmg = 10 + 10 = 20.
    
    # 2. Add Items
    # Turtle Hermit Gi (Chest, Uncommon, HP+50, Set: Turtle School)
    item1 = session.query(Item).filter_by(name="Turtle Hermit Gi").first()
    # Weighted Wristbands (Gloves, Rare, Dmg+5, Set: Turtle School)
    item2 = session.query(Item).filter_by(name="Weighted Wristbands").first()
    
    if not item1 or not item2:
        print("❌ Items not found! Did you run populate_items.py?")
        return

    es.add_item_to_user(user_id, item1.id)
    es.add_item_to_user(user_id, item2.id)
    
    # Get UserItem IDs
    inv = es.get_user_inventory(user_id)
    ui1 = [x[0] for x in inv if x[1].id == item1.id][0]
    ui2 = [x[0] for x in inv if x[1].id == item2.id][0]
    
    print(f"Added items: {item1.name} (ID {ui1.id}), {item2.name} (ID {ui2.id})")
    
    # 3. Equip Item 1 (Gi)
    print("Equipping Gi...")
    us.equip_item(user_id, ui1.id)
    
    session.expire_all() # Force reload from DB
    u = session.query(Utente).filter_by(id_telegram=user_id).first()
    print(f"Stats after Gi: HP {u.max_health} (Expected 200), Dmg {u.base_damage} (Expected 20)")
    
    if u.max_health != 200:
        print("❌ HP mismatch!")
    else:
        print("✅ HP correct.")
        
    # Let's try Saiyan Elite Set which gives Damage.
    # Saiyan Battle Armor (Chest, Rare, Res+15, HP+100)
    # Saiyan Leggings (Pants, Rare, Speed+5, HP+50)
    # Set Bonus (2): base_damage + 10
    
    item3 = session.query(Item).filter_by(name="Saiyan Battle Armor").first()
    item4 = session.query(Item).filter_by(name="Saiyan Leggings").first()
    
    es.add_item_to_user(user_id, item3.id)
    es.add_item_to_user(user_id, item4.id)
    
    inv = es.get_user_inventory(user_id)
    ui3 = [x[0] for x in inv if x[1].id == item3.id][0]
    ui4 = [x[0] for x in inv if x[1].id == item4.id][0]
    
    print("Equipping Saiyan Armor (Replacing Gi)...")
    us.equip_item(user_id, ui3.id)
    
    session.expire_all()
    u = session.query(Utente).filter_by(id_telegram=user_id).first()
    print(f"Stats after Armor: HP {u.max_health} (Expected 250)")
    
    print("Equipping Saiyan Leggings...")
    us.equip_item(user_id, ui4.id)
    
    session.expire_all()
    u = session.query(Utente).filter_by(id_telegram=user_id).first()
    print(f"Stats after Set (2pc): Dmg {u.base_damage} (Expected 30)")
    
    if u.base_damage == 30:
        print("✅ Set Bonus Applied!")
    else:
        print(f"❌ Set Bonus Failed. Got {u.base_damage}")
        
    # 5. Unequip
    print("Unequipping Armor...")
    us.unequip_item(user_id, ui3.id)
    
    session.expire_all()
    u = session.query(Utente).filter_by(id_telegram=user_id).first()
    
    print(f"Stats after unequip: HP {u.max_health} (Expected 200), Dmg {u.base_damage} (Expected 20)")
    
    if u.max_health == 200 and u.base_damage == 20:
        print("✅ Unequip Logic Correct.")
    else:
        print("❌ Unequip Logic Failed.")
        
    session.close()

if __name__ == "__main__":
    verify_equipment()
