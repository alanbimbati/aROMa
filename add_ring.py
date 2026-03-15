import json
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from services.crafting_service import CraftingService
from models.equipment import Equipment

cs = CraftingService()
session = cs.db.get_session()

try:
    e = Equipment(
        id=42, 
        name='Anello del Sovrano', 
        slot='accessory1', 
        rarity=5, 
        min_level=50, 
        stats_json=json.dumps({'speed': 10, 'crit_chance': 10}),
        crafting_time=172800, 
        crafting_requirements=json.dumps({"Diamante": 100}), 
        description='Anello di potere incommensurabile in puro diamante.', 
        set_name='Set Supremo'
    )
    session.merge(e)
    session.commit()
    print("Item added successfully")
except Exception as e:
    print("Error:", e)
finally:
    session.close()
