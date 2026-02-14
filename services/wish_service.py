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

    def get_dragon_ball_counts(self, user):
        """Return counts of Shenron and Porunga balls"""
        shenron_count = 0
        porunga_count = 0
        
        for i in range(1, 8):
            if self.item_service.get_item_by_user(user.id_telegram, f"La Sfera del Drago Shenron {i}") > 0:
                shenron_count += 1
            if self.item_service.get_item_by_user(user.id_telegram, f"La Sfera del Drago Porunga {i}") > 0:
                porunga_count += 1
        
        return shenron_count, porunga_count

    def log_summon(self, user_id, dragon_type, session=None):
        """Log dragon summon event for achievements"""
        from services.event_dispatcher import EventDispatcher
        dispatcher = EventDispatcher()
        
        event_type = 'shenron_summons' if dragon_type.lower() == 'shenron' else 'porunga_summons'
        
        dispatcher.log_event(
            event_type=event_type,
            user_id=user_id,
            value=1,
            context={'dragon': dragon_type},
            session=session
        )

    def grant_wish(self, user, wish_type, dragon_type="Shenron"):
        """Grant a dragon wish (Shenron or Porunga)"""
        session = self.db.get_session()
        try:
            # Consume spheres in a single transaction
            if dragon_type.lower() == "shenron":
                # Check spheres first to be safe
                has_s, _ = self.check_dragon_balls(user)
                if not has_s:
                    return "❌ Non hai tutte le 7 sfere di Shenron!"

                # Consume spheres in a single transaction
                for i in range(1, 8):
                    success, _ = self.item_service.use_item(user.id_telegram, f"La Sfera del Drago Shenron {i}", session=session)
                    if not success:
                        session.rollback()
                        return "❌ Non hai tutte le 7 sfere di Shenron! Forse hai già esaudito questo desiderio?"
                
                # Shenron: 1 Big Wish
                if wish_type == "wumpa":
                    amount = random.randint(1000, 2000)
                    self.user_service.add_points_by_id(user.id_telegram, amount, session=session)
                    session.commit()
                    return f"🐉 SHENRON HA ESAUDITO IL TUO DESIDERIO!\n\n💰 HAI OTTENUTO {amount} {PointsName}!"
                elif wish_type == "exp":
                    amount = random.randint(1000, 2000)
                    self.user_service.add_exp_by_id(user.id_telegram, amount, session=session)
                    session.commit()
                    return f"🐉 SHENRON HA ESAUDITO IL TUO DESIDERIO!\n\n⭐ HAI OTTENUTO {amount} EXP!"
                    
            else:
                # Porunga: Consumes spheres and grants one wish (called via main.py)
                if wish_type == "wumpa":
                    amount = random.randint(300, 500)
                    self.user_service.add_points_by_id(user.id_telegram, amount, session=session)
                    session.commit()
                    return f"🐲 PORUNGA: Ricevi {amount} {PointsName}!"
                elif wish_type == "item":
                    # Give 1 random item
                    items_data = self.item_service.load_items_from_csv()
                    if not items_data:
                        session.rollback()
                        return "🐲 PORUNGA: Nessun oggetto trovato nel database!"
                        
                    weights = [1/item['rarita'] if item['rarita'] > 0 else 0.01 for item in items_data]
                    item = random.choices(items_data, weights=weights, k=1)[0]
                    self.item_service.add_item(user.id_telegram, item['nome'], session=session)
                    session.commit()
                    return f"🐲 PORUNGA: Ricevi {item['nome']}!"
            
            session.commit()
            return "Desiderio esaudito!"
        except Exception as e:
            session.rollback()
            print(f"[ERROR] grant_wish failed: {e}")
            return f"❌ Errore durante l'esaudimento del desiderio: {e}"
        finally:
            session.close()
    
    def grant_porunga_wish(self, user, wish_choice, wish_number=1):
        """Grant a single Porunga wish (called 3 times)"""
        session = self.db.get_session()
        try:
            # If it's the FIRST wish, consume the spheres immediately to prevent exploit
            if wish_number == 1:
                # Check spheres first
                _, has_p = self.check_dragon_balls(user)
                if not has_p:
                    return "❌ Non hai tutte le 7 sfere di Porunga!"

                for i in range(1, 8):
                    success, _ = self.item_service.use_item(user.id_telegram, f"La Sfera del Drago Porunga {i}", session=session)
                    if not success:
                        session.rollback()
                        return "❌ Non hai tutte le 7 sfere di Porunga! Forse hai già esaudito questo desiderio?"

            if wish_choice == "wumpa":
                amount = random.randint(300, 500)
                self.user_service.add_points_by_id(user.id_telegram, amount, session=session)
                session.commit()
                return f"Desiderio {wish_number}/3: Ricevi {amount} {PointsName}!"
            elif wish_choice == "item":
                items_data = self.item_service.load_items_from_csv()
                if not items_data:
                    session.rollback()
                    return f"Desiderio {wish_number}/3: Nessun oggetto trovato!"
                    
                weights = [1/item['rarita'] if item['rarita'] > 0 else 0.01 for item in items_data]
                item = random.choices(items_data, weights=weights, k=1)[0]
                self.item_service.add_item(user.id_telegram, item['nome'], session=session)
                session.commit()
                return f"Desiderio {wish_number}/3: Ricevi {item['nome']}!"
            
            session.commit()
            return f"Desiderio {wish_number}/3 esaudito!"
        except Exception as e:
            session.rollback()
            print(f"[ERROR] grant_porunga_wish failed: {e}")
            return f"❌ Errore desiderio {wish_number}: {e}"
        finally:
            session.close()
