
import sys
import os
from datetime import datetime

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Database
from models.items import Collezionabili
from sqlalchemy import text

def give_items():
    db = Database()
    session = db.get_session()
    
    # Target User ID (Alan's ID from logs)
    user_id = 62716473 
    
    items_to_add = [
        # Potions (match names in main.py logic/potions.csv)
        # In main.py: "Pozione Salute" and "Pozione Mana"
        # BUT in potions.csv names are "Pozione Piccola", "Pozione Media", etc.
        # Wait, handle_profile in main.py looked for 'Pozione Salute' and 'Pozione Mana'.
        # Let's check main.py again. 
        # Ah, main.py lines 2728-2729: 
        # hp_pot_count = item_service.get_item_by_user(..., 'Pozione Salute')
        # This implies there is an item simply called "Pozione Salute".
        # But potions.csv has specific names.
        # If the shop sells 'Pozione Piccola', then the user has 'Pozione Piccola'.
        # If main.py looks for 'Pozione Salute', it might be looking for a GENERIC item or the code is wrong.
        # Let's check handle_shop_potions in main.py or similar to see what is sold.
        # OR I can just give "Pozione Salute" generic item if that's what the button expects.
        # The button callback `handle_potion_use_callback` maps `health_potion` -> `Pozione Salute`.
        # So I MUST give "Pozione Salute". 
        # It seems the system might have been simplified or inconsistent.
        # I will give "Pozione Salute" and "Pozione Mana" as generic items.
        
        ("Pozione Piccola", 5),
        ("Pozione Mana Piccola", 5),
        
        # Dragon Balls
        ("La Sfera del Drago Shenron 1", 1),
        ("La Sfera del Drago Shenron 2", 1),
        ("La Sfera del Drago Shenron 3", 1),
        ("La Sfera del Drago Shenron 4", 1),
        ("La Sfera del Drago Shenron 5", 1),
        ("La Sfera del Drago Shenron 6", 1),
        ("La Sfera del Drago Shenron 7", 1),
        
        ("La Sfera del Drago Porunga 1", 1),
        ("La Sfera del Drago Porunga 2", 1),
        ("La Sfera del Drago Porunga 3", 1),
        ("La Sfera del Drago Porunga 4", 1),
        ("La Sfera del Drago Porunga 5", 1),
        ("La Sfera del Drago Porunga 6", 1),
        ("La Sfera del Drago Porunga 7", 1),
    ]
    
    print(f"Adding items to user {user_id}...")
    
    for item_name, qty in items_to_add:
        for _ in range(qty):
            c = Collezionabili()
            c.id_telegram = str(user_id)
            c.oggetto = item_name
            c.data_acquisizione = datetime.today()
            c.quantita = 1
            c.data_utilizzo = None
            session.add(c)
            
    session.commit()
    print("Items added successfully!")
    session.close()

if __name__ == '__main__':
    give_items()
