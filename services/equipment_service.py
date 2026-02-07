from database import Database
from models.equipment import Equipment, UserEquipment
from models.item import ItemSet
from sqlalchemy import func
import random
import json

class EquipmentService:
    def __init__(self):
        self.db = Database()
        
    def get_user_inventory(self, user_id):
        """Get all items owned by user"""
        session = self.db.get_session()
        try:
            # Join UserEquipment and Equipment
            items = session.query(UserEquipment, Equipment).join(Equipment, UserEquipment.equipment_id == Equipment.id)\
                .filter(UserEquipment.user_id == user_id).all()
            return items # Returns list of (UserEquipment, Equipment) tuples
        finally:
            session.close()
            
    def get_equipped_items(self, user_id, session=None):
        """Get currently equipped items"""
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
        try:
            items = session.query(UserEquipment, Equipment).join(Equipment, UserEquipment.equipment_id == Equipment.id)\
                .filter(UserEquipment.user_id == user_id, UserEquipment.equipped == True).all()
            return items
        finally:
            if local_session:
                session.close()
            
    def equip_item(self, user_id, user_item_id):
        """Equip an item, unequip conflicting slot if needed"""
        session = self.db.get_session()
        try:
            # Get the item to equip
            target = session.query(UserEquipment, Equipment).join(Equipment, UserEquipment.equipment_id == Equipment.id)\
                .filter(UserEquipment.id == user_item_id, UserEquipment.user_id == user_id).first()
                
            if not target:
                return False, "Oggetto non trovato."
                
            user_item, item = target
            
            if user_item.equipped:
                return False, "Oggetto già equipaggiato."
                
            # Check slot restrictions
            slot = item.slot
            
            # Logic for slots
            # If Ring or Earring, we might have 2 slots: "Ring_1", "Ring_2"
            # Logic: If 1 ring equipped, go to slot 2. If 2 equipped, replace oldest/first?
            # Or ask user? For now, auto-replace logic.
            
            to_unequip = []
            target_slot_in_db = slot # Default
            
            # Get currently equipped in that generic slot type
            equipped = session.query(UserEquipment, Equipment).join(Equipment, UserEquipment.equipment_id == Equipment.id)\
                .filter(UserEquipment.user_id == user_id, UserEquipment.equipped == True, Equipment.slot == slot).all()
            
            if slot in ["Ring", "Earring"]:
                 if len(equipped) >= 2:
                     # Unequip the first one found
                     to_unequip.append(equipped[0][0])
                     target_slot_in_db = f"{slot}_1" # Fallback or keep same
                 elif len(equipped) == 1:
                     target_slot_in_db = f"{slot}_2" # Use second slot
                 else:
                     target_slot_in_db = f"{slot}_1"
            else:
                # 1 max for others
                if len(equipped) >= 1:
                    to_unequip.append(equipped[0][0])
                target_slot_in_db = slot
            
            # Unequip old
            for old_item in to_unequip:
                old_item.equipped = False
                old_item.slot_equipped = None
                
            # Equip new
            user_item.equipped = True
            user_item.slot_equipped = target_slot_in_db
            session.commit()
            
            return True, f"Hai equipaggiato: {item.name}"
        except Exception as e:
            session.rollback()
            return False, str(e)
        finally:
            session.close()
            
    def unequip_item(self, user_id, user_item_id):
        """Unequip an item"""
        session = self.db.get_session()
        try:
            user_item = session.query(UserEquipment).filter_by(id=user_item_id, user_id=user_id).first()
            if not user_item:
                return False, "Oggetto non trovato."
                
            if not user_item.equipped:
                return False, "Oggetto non equipaggiato."
                
            user_item.equipped = False
            user_item.slot_equipped = None
            session.commit()
            return True, "Oggetto rimosso."
        finally:
            session.close()
            
    def calculate_equipment_stats(self, user_id, session=None):
        """Calculate total stats from all equipped items + sets"""
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
            
        try:
            # Query UserEquipment joined with Equipment
            equipped = session.query(UserEquipment, Equipment).join(Equipment, UserEquipment.equipment_id == Equipment.id)\
                .filter(UserEquipment.user_id == user_id, UserEquipment.equipped == True).all()
                
            total_stats = {}
            set_counts = {}
            
            # 1. Sum Item Stats
            for u_item, item in equipped:
                # Base stats from JSON
                stats = item.stats_json
                if isinstance(stats, str):
                    try:
                        stats = json.loads(stats)
                    except:
                        stats = {}
                elif not isinstance(stats, dict):
                    stats = {}
                
                for stat, value in stats.items():
                    # Map legacy/external stat names to internal ones
                    if stat == 'health':
                        total_stats['max_health'] = total_stats.get('max_health', 0) + value
                    elif stat == 'mana':
                        total_stats['max_mana'] = total_stats.get('max_mana', 0) + value
                    elif stat == 'attack':
                        total_stats['base_damage'] = total_stats.get('base_damage', 0) + value
                    elif stat == 'defense':
                        total_stats['resistance'] = total_stats.get('resistance', 0) + value
                    elif stat in ['crit', 'perception', 'luck']:
                        total_stats['crit_chance'] = total_stats.get('crit_chance', 0) + value
                    elif stat == 'wisdom':
                        total_stats['max_mana'] = total_stats.get('max_mana', 0) + value
                    elif stat == 'all_stats':
                        # Valid for "Anello del Tempo" etc.
                        total_stats['max_health'] = total_stats.get('max_health', 0) + (value * 10)
                        total_stats['max_mana'] = total_stats.get('max_mana', 0) + (value * 5)
                        total_stats['base_damage'] = total_stats.get('base_damage', 0) + (value * 2)
                        total_stats['resistance'] = total_stats.get('resistance', 0) + value
                        total_stats['crit_chance'] = total_stats.get('crit_chance', 0) + value
                        total_stats['speed'] = total_stats.get('speed', 0) + value
                    else:
                        # Standard stat (max_health, base_damage, etc.)
                        total_stats[stat] = total_stats.get(stat, 0) + value
                    
                # No level scaling usually for equipment unless it's upgraded (+1)
                # Assuming 'min_level' is requirement, not item level
                
                # Count sets (by Name)
                if item.set_name:
                    set_counts[item.set_name] = set_counts.get(item.set_name, 0) + 1
            
            # 2. Apply Set Bonuses
            for set_name, count in set_counts.items():
                # Look up ItemSet by Name
                item_set = session.query(ItemSet).filter_by(name=set_name).first()
                if item_set and item_set.bonuses:
                    # Check thresholds (e.g. "2", "4", "6")
                    for threshold, bonus_stats in item_set.bonuses.items():
                        if count >= int(threshold):
                            for stat, value in bonus_stats.items():
                                total_stats[stat] = total_stats.get(stat, 0) + value
                                
            return total_stats
        finally:
            if local_session:
                session.close()

    def add_item_to_user(self, user_id, equipment_id):
        """Give an item to a user"""
        session = self.db.get_session()
        try:
            new_item = UserEquipment(user_id=user_id, equipment_id=equipment_id)
            session.add(new_item)
            session.commit()
            return True
        finally:
            session.close()
