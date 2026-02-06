
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from database import Database
from models.items import Collezionabili
from services.item_service import ItemService
from services.user_service import UserService

def check_user_inv(user_id):
    item_service = ItemService()
    user_service = UserService()
    
    inventory = item_service.get_inventory(user_id)
    print(f"Inventory for {user_id}: {inventory}")
    
    inventory_dict = {name: count for name, count in inventory}
    print(f"Inventory Dict: {inventory_dict}")
    
    hp_hierarchy = [
        ('Pozione Completa', '🧪 Vita Max'), 
        ('Pozione Grande', '🧪 Vita G'), 
        ('Pozione Media', '🧪 Vita M'), 
        ('Pozione Salute', '🧪 Vita P'),
        ('Pozione Piccola', '🧪 Vita P'),
        ('Pozione d\'Amore', '🧪 Vita ❤️')
    ]
    
    pot_buttons = []
    for p_name, p_label in hp_hierarchy:
        count = inventory_dict.get(p_name, 0)
        if count > 0:
            print(f"Found HP Potion: {p_name} ({count})")
            pot_buttons.append(p_label)
            break
            
    if not pot_buttons:
        print("No HP Potions found in hierarchy.")

if __name__ == "__main__":
    check_user_inv(62716473)
