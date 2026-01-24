from database import Database
from models.item import Item, ItemSet
import json

def populate_items():
    db = Database()
    session = db.get_session()
    
    # 1. Create Sets
    sets = [
        {
            "name": "Turtle School Set",
            "description": "The uniform of Master Roshi's students.",
            "bonuses": {
                "2": {"exp_bonus": 10},
                "3": {"max_mana": 50, "max_health": 100}
            }
        },
        {
            "name": "Saiyan Elite Set",
            "description": "Armor worn by the elite warriors of Planet Vegeta.",
            "bonuses": {
                "2": {"base_damage": 10},
                "4": {"crit_chance": 10, "resistance": 10}
            }
        },
        {
            "name": "Android Set",
            "description": "Cybernetic enhancements from Dr. Gero.",
            "bonuses": {
                "2": {"speed": 10},
                "4": {"hp_regen": 5} # Special stat handling needed later
            }
        }
    ]
    
    created_sets = {}
    for s in sets:
        existing = session.query(ItemSet).filter_by(name=s["name"]).first()
        if not existing:
            new_set = ItemSet(name=s["name"], description=s["description"], bonuses=s["bonuses"])
            session.add(new_set)
            session.commit()
            created_sets[s["name"]] = new_set.id
            print(f"Created Set: {s['name']}")
        else:
            created_sets[s["name"]] = existing.id
            
    # 2. Create Items
    items = [
        # Turtle School
        {"name": "Turtle Hermit Gi", "slot": "Chest", "rarity": "Uncommon", "stats": {"max_health": 50}, "set": "Turtle School Set"},
        {"name": "Turtle Hermit Pants", "slot": "Pants", "rarity": "Uncommon", "stats": {"speed": 2}, "set": "Turtle School Set"},
        {"name": "Weighted Wristbands", "slot": "Gloves", "rarity": "Rare", "stats": {"base_damage": 5}, "set": "Turtle School Set"},
        
        # Saiyan Elite
        {"name": "Saiyan Battle Armor", "slot": "Chest", "rarity": "Rare", "stats": {"resistance": 15, "max_health": 100}, "set": "Saiyan Elite Set"},
        {"name": "Saiyan Leggings", "slot": "Pants", "rarity": "Rare", "stats": {"speed": 5, "max_health": 50}, "set": "Saiyan Elite Set"},
        {"name": "Saiyan Boots", "slot": "Shoes", "rarity": "Rare", "stats": {"speed": 8}, "set": "Saiyan Elite Set"},
        {"name": "Saiyan Scouter", "slot": "Helmet", "rarity": "Epic", "stats": {"crit_chance": 5}, "set": "Saiyan Elite Set", "special_effect": "scouter_scan"},
        {"name": "Saiyan Shoulder Pads", "slot": "Shoulders", "rarity": "Uncommon", "stats": {"resistance": 5}, "set": "Saiyan Elite Set"},
        
        # Android
        {"name": "Red Ribbon Chip", "slot": "Earring", "rarity": "Rare", "stats": {"max_mana": 30}, "set": "Android Set"},
        {"name": "Android Gloves", "slot": "Gloves", "rarity": "Rare", "stats": {"base_damage": 8}, "set": "Android Set"},
        
        # Legendaries / Misc
        {"name": "Potara Earring (L)", "slot": "Earring", "rarity": "Legendary", "stats": {"max_health": 200, "max_mana": 100}, "special_effect": "potara_fusion"},
        {"name": "Potara Earring (R)", "slot": "Earring", "rarity": "Legendary", "stats": {"base_damage": 20}, "special_effect": "potara_fusion"},
        {"name": "Z Sword", "slot": "Gloves", "rarity": "Legendary", "stats": {"base_damage": 50, "speed": -10}}, # Weapon slot? Using Gloves for now as 'Hand'
        {"name": "Halo", "slot": "Helmet", "rarity": "Epic", "stats": {"max_mana": 100, "resistance": -5}},
        {"name": "Time Ring", "slot": "Ring", "rarity": "Mythic", "stats": {"speed": 20, "crit_chance": 5}},
        {"name": "Capsule Corp Ring", "slot": "Ring", "rarity": "Rare", "stats": {"max_health": 50}},
    ]
    
    for i in items:
        existing = session.query(Item).filter_by(name=i["name"]).first()
        if not existing:
            set_id = created_sets.get(i.get("set"))
            new_item = Item(
                name=i["name"],
                slot=i["slot"],
                rarity=i["rarity"],
                stats=i["stats"],
                set_id=set_id,
                special_effect_id=i.get("special_effect")
            )
            session.add(new_item)
            print(f"Created Item: {i['name']}")
            
    session.commit()
    session.close()

if __name__ == "__main__":
    populate_items()
