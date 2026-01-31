from database import Database
from models.item import Item, ItemSet, ItemSlot
from models.inventory import UserItem
from sqlalchemy import func
import random

class EquipmentService:
    def __init__(self):
        self.db = Database()
        
    def get_user_inventory(self, user_id):
        """Get all items owned by user"""
        session = self.db.get_session()
        try:
            items = session.query(UserItem, Item).join(Item, UserItem.item_id == Item.id)\
                .filter(UserItem.user_id == user_id).all()
            return items # Returns list of (UserItem, Item) tuples
        finally:
            session.close()
            
    def get_equipped_items(self, user_id, session=None):
        """Get currently equipped items"""
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
        try:
            items = session.query(UserItem, Item).join(Item, UserItem.item_id == Item.id)\
                .filter(UserItem.user_id == user_id, UserItem.is_equipped == True).all()
            return items
        finally:
            if local_session:
                session.close()
            
    def equip_item(self, user_id, user_item_id):
        """Equip an item, unequip conflicting slot if needed"""
        session = self.db.get_session()
        try:
            # Get the item to equip
            target = session.query(UserItem, Item).join(Item, UserItem.item_id == Item.id)\
                .filter(UserItem.id == user_item_id, UserItem.user_id == user_id).first()
                
            if not target:
                return False, "Oggetto non trovato."
                
            user_item, item = target
            
            if user_item.is_equipped:
                return False, "Oggetto già equipaggiato."
                
            # Check slot restrictions
            slot = item.slot
            
            # Get currently equipped in that slot
            equipped = session.query(UserItem, Item).join(Item, UserItem.item_id == Item.id)\
                .filter(UserItem.user_id == user_id, UserItem.is_equipped == True, Item.slot == slot).all()
            
            # Logic for slots
            to_unequip = []
            
            if slot in ["Ring", "Earring"]:
                # Allow 2 max
                if len(equipped) >= 2:
                    # Unequip the first one (or oldest?)
                    to_unequip.append(equipped[0][0])
            else:
                # Allow 1 max
                if len(equipped) >= 1:
                    to_unequip.append(equipped[0][0])
            
            # Unequip old
            for old_item in to_unequip:
                old_item.is_equipped = False
                
            # Equip new
            user_item.is_equipped = True
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
            user_item = session.query(UserItem).filter_by(id=user_item_id, user_id=user_id).first()
            if not user_item:
                return False, "Oggetto non trovato."
                
            if not user_item.is_equipped:
                return False, "Oggetto non equipaggiato."
                
            user_item.is_equipped = False
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
            equipped = session.query(UserItem, Item).join(Item, UserItem.item_id == Item.id)\
                .filter(UserItem.user_id == user_id, UserItem.is_equipped == True).all()
                
            total_stats = {}
            set_counts = {}
            
            # 1. Sum Item Stats
            for u_item, item in equipped:
                # Base stats
                for stat, value in item.stats.items():
                    total_stats[stat] = total_stats.get(stat, 0) + value
                    
                # Level scaling (e.g. +5% per level? or flat?)
                # Let's say +10% stats per upgrade level for now
                if u_item.level > 0:
                    multiplier = 1 + (u_item.level * 0.1)
                    for stat in total_stats:
                        # Only apply to stats from this item? 
                        # Simpler: Apply to total? No, that's wrong.
                        # Re-calculate:
                        pass 
                
                # Count sets
                if item.set_id:
                    set_counts[item.set_id] = set_counts.get(item.set_id, 0) + 1
            
            # 2. Apply Set Bonuses
            for set_id, count in set_counts.items():
                item_set = session.query(ItemSet).filter_by(id=set_id).first()
                if item_set and item_set.bonuses:
                    # Check thresholds (e.g. "2", "4")
                    for threshold, bonus_stats in item_set.bonuses.items():
                        if count >= int(threshold):
                            for stat, value in bonus_stats.items():
                                total_stats[stat] = total_stats.get(stat, 0) + value
                                
            return total_stats
        finally:
            if local_session:
                session.close()

    def add_item_to_user(self, user_id, item_id):
        """Give an item to a user"""
        session = self.db.get_session()
        try:
            new_item = UserItem(user_id=user_id, item_id=item_id)
            session.add(new_item)
            session.commit()
            return True
        finally:
            session.close()
