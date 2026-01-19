"""
Potion Service - Handle health and mana potions
"""
from database import Database
from services.user_service import UserService
import csv

class PotionService:
    def __init__(self):
        self.db = Database()
        self.user_service = UserService()
        self.potions = self.load_potions()
    
    def load_potions(self):
        """Load potions from CSV"""
        potions = []
        try:
            with open('data/potions.csv', 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    potions.append({
                        'nome': row['nome'],
                        'tipo': row['tipo'],
                        'effetto_valore': int(row['effetto_valore']),
                        'prezzo': int(row['prezzo']),
                        'descrizione': row['descrizione'],
                        'rarita': int(row['rarita'])
                    })
        except Exception as e:
            print(f"Error loading potions: {e}")
        return potions
    
    def get_potion_by_name(self, nome):
        """Get potion details by name"""
        for potion in self.potions:
            if potion['nome'] == nome:
                return potion
        return None
    
    def get_all_potions(self):
        """Get all available potions"""
        return self.potions
    
    def get_potions_by_type(self, tipo):
        """Get all potions of a specific type"""
        return [p for p in self.potions if p['tipo'] == tipo]
    
    def buy_potion(self, user, potion_name):
        """Buy a potion"""
        potion = self.get_potion_by_name(potion_name)
        
        if not potion:
            return False, "Pozione non trovata."
        
        # Apply premium discount
        price = potion['prezzo']
        if user.premium == 1:
            price = int(price * 0.5)
        
        if user.points < price:
            return False, f"Non hai abbastanza Wumpa Fruit! Costo: {price} 🍑"
        
        # Deduct cost
        self.user_service.add_points(user, -price)
        
        # Add to inventory
        from services.item_service import ItemService
        item_service = ItemService()
        item_service.add_item(user.id_telegram, potion_name)
        
        discount_msg = f" (Sconto Premium 50%: {potion['prezzo']} → {price} 🍑)" if user.premium == 1 else ""
        return True, f"Hai acquistato {potion_name} per {price} 🍑!{discount_msg}"
    
    def apply_potion_effect(self, user, potion_name):
        """Apply potion effect without consuming item (internal use)"""
        potion = self.get_potion_by_name(potion_name)
        if not potion:
            return False, "Pozione non trovata."
            
        tipo = potion['tipo']
        valore = potion['effetto_valore']
        
        if tipo == 'health_potion':
            restored = self.user_service.restore_health(user, valore)
            return True, f"💚 Hai recuperato {restored} HP!"
            
        elif tipo == 'mana_potion':
            restored = self.user_service.restore_mana(user, valore)
            return True, f"💙 Hai recuperato {restored} Mana!"
            
        elif tipo == 'full_restore':
            hp_restored = self.user_service.restore_health(user, 999)
            mana_restored = self.user_service.restore_mana(user, 999)
            return True, f"✨ Hai recuperato {hp_restored} HP e {mana_restored} Mana!"
            
        return False, "Tipo di pozione sconosciuto."

    def use_potion(self, user, potion_name):
        """Use a potion (consume + apply)"""
        # Check if user has it
        from services.item_service import ItemService
        item_service = ItemService()
        
        if item_service.get_item_by_user(user.id_telegram, potion_name) <= 0:
            return False, "Non possiedi questa pozione!"
        
        # Apply effect
        success, msg = self.apply_potion_effect(user, potion_name)
        
        if success:
            # Consume item
            item_service.use_item(user.id_telegram, potion_name)
            
        return success, msg
