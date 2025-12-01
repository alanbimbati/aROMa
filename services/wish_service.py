from database import Database
from services.user_service import UserService
from services.item_service import ItemService
from settings import PointsName
import random

class WishService:
    def __init__(self):
        self.db = Database()
        self.user_service = UserService()
        self.item_service = ItemService()

    def check_dragon_balls(self, user):
        # Check if user has all 7 spheres of either type
        shenron_count = 0
        porunga_count = 0
        
        for i in range(1, 8):
            if self.item_service.get_item_by_user(user.id_telegram, f"La Sfera del Drago Shenron {i}") > 0:
                shenron_count += 1
            if self.item_service.get_item_by_user(user.id_telegram, f"La Sfera del Drago Porunga {i}") > 0:
                porunga_count += 1
        
        return shenron_count == 7, porunga_count == 7

    def grant_wish(self, user, wish_type, dragon_type="Shenron"):
        # Consume spheres
        if dragon_type == "Shenron":
            for i in range(1, 8):
                self.item_service.use_item(user.id_telegram, f"La Sfera del Drago Shenron {i}")
            
            # Shenron: 1 Big Wish
            if wish_type == "wumpa":
                amount = random.randint(300, 500)
                self.user_service.add_points(user, amount)
                return f"🐉 SHENRON HA ESAUDITO IL TUO DESIDERIO!\n\n💰 HAI OTTENUTO {amount} {PointsName}!"
            elif wish_type == "exp":
                amount = random.randint(300, 500)
                self.user_service.add_exp(user, amount)
                return f"🐉 SHENRON HA ESAUDITO IL TUO DESIDERIO!\n\n⭐ HAI OTTENUTO {amount} EXP!"
                
        else:
            # Porunga: Will handle 3 wishes via callbacks
            # For now just consume the spheres
            for i in range(1, 8):
                self.item_service.use_item(user.id_telegram, f"La Sfera del Drago Porunga {i}")
                
            # This shouldn't be called directly for Porunga, handled via callbacks
            if wish_type == "wumpa":
                amount = random.randint(50, 100)
                self.user_service.add_points(user, amount)
                return f"🐲 PORUNGA: Ricevi {amount} {PointsName}!"
            elif wish_type == "item":
                # Give 1 random item
                items_data = self.item_service.load_items_from_csv()
                weights = [1/item['rarita'] for item in items_data]
                item = random.choices(items_data, weights=weights, k=1)[0]
                self.item_service.add_item(user.id_telegram, item['nome'])
                return f"🐲 PORUNGA: Ricevi {item['nome']}!"
        
        return "Desiderio esaudito!"
    
    def grant_porunga_wish(self, user, wish_choice, wish_number=1):
        """Grant a single Porunga wish (called 3 times)"""
        if wish_choice == "wumpa":
            amount = random.randint(50, 100)
            self.user_service.add_points(user, amount)
            return f"Desiderio {wish_number}/3: Ricevi {amount} {PointsName}!"
        elif wish_choice == "item":
            items_data = self.item_service.load_items_from_csv()
            weights = [1/item['rarita'] for item in items_data]
            item = random.choices(items_data, weights=weights, k=1)[0]
            self.item_service.add_item(user.id_telegram, item['nome'])
            return f"Desiderio {wish_number}/3: Ricevi {item['nome']}!"
        return "Desiderio esaudito!"
