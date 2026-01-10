from database import Database
from models.items import Collezionabili
from models.user import Utente
from services.user_service import UserService
import datetime
import random
from settings import PointsName

class ItemService:
    def __init__(self):
        self.db = Database()
        self.user_service = UserService()

    def get_inventory(self, id_telegram):
        session = self.db.get_session()
        from sqlalchemy import func
        inventario = session.query(
            Collezionabili.oggetto,
            func.count(Collezionabili.oggetto).label('quantita')
        ).filter_by(
            id_telegram=str(id_telegram),
            data_utilizzo=None
        ).group_by(
            Collezionabili.oggetto
        ).order_by(
            Collezionabili.oggetto
        ).all()
        session.close()
        return inventario

    def add_item(self, id_telegram, item, quantita=1):
        session = self.db.get_session()
        try:
            for _ in range(quantita):
                collezionabile = Collezionabili()
                collezionabile.id_telegram = str(id_telegram)
                collezionabile.oggetto = item
                collezionabile.data_acquisizione = datetime.datetime.today()
                collezionabile.quantita = 1 # Each row is 1 item in this schema? No, schema has quantita.
                # Wait, original code had quantita column but also inserted multiple rows?
                # Original code: collezionabile.quantita = quantita.
                # But getInventarioUtente does count(Collezionabili.oggetto).
                # This implies one row per item instance, or grouped?
                # "func.count(Collezionabili.oggetto)" implies multiple rows.
                # But "collezionabile.quantita = quantita" implies one row with count.
                # Let's check original code again.
                # Original CreateCollezionabile sets quantita=quantita.
                # Original getInventarioUtente counts rows.
                # This is inconsistent. If I insert 1 row with quantita=5, count is 1.
                # I should probably insert N rows or change getInventarioUtente to sum(quantita).
                # Let's stick to inserting 1 row with quantita for now, but fix getInventarioUtente to sum.
                # Actually, looking at original code: "func.count(Collezionabili.oggetto)"
                # This counts how many rows have that object name.
                # So if I have 5 apples, I should have 5 rows?
                # But CreateCollezionabile inserts 1 row with quantita=N.
                # This seems like a bug in original code or I misunderstood.
                # Let's assume 1 row per item for now to be safe with "count".
                # Or better, let's fix it to be consistent.
                # I will insert N rows if quantita > 1.
                pass
            
            # Let's follow the original CreateCollezionabile logic but be careful.
            # Original: collezionabile.quantita = quantita.
            # If I insert 1 row with quantita=5.
            # getInventarioUtente: count(*) group by oggetto. -> returns 1.
            # So the user sees 1 item.
            # So the original code was likely buggy or I am misinterpreting "quantita" column usage.
            # Let's just insert N rows.
            
            for _ in range(quantita):
                 c = Collezionabili()
                 c.id_telegram = str(id_telegram)
                 c.oggetto = item
                 c.data_acquisizione = datetime.datetime.today()
                 c.quantita = 1
                 c.data_utilizzo = None
                 session.add(c)
            
            session.commit()
            return True
        except Exception as e:
            print(e)
            session.rollback()
            return False
        finally:
            session.close()

    def use_item(self, id_telegram, oggetto):
        session = self.db.get_session()
        collezionabile = session.query(Collezionabili).filter_by(id_telegram=str(id_telegram), oggetto=oggetto, data_utilizzo=None).first()
        if collezionabile:
            collezionabile.data_utilizzo = datetime.datetime.today()
            session.commit()
            session.close()
            return True
        session.close()
        return False

    def get_item_by_user(self, id_telegram, nome_oggetto):
        session = self.db.get_session()
        from sqlalchemy import func
        # This logic in original code was also weird.
        # It did count() but returned .first().
        # Let's just count rows.
        count = session.query(Collezionabili).filter_by(
            id_telegram=str(id_telegram), 
            oggetto=nome_oggetto,
            data_utilizzo=None
        ).count()
        session.close()
        return count

    def load_items_from_csv(self):
        items = []
        try:
            with open('items.csv', 'r') as f:
                lines = f.readlines()[1:] # Skip header
                for line in lines:
                    parts = line.strip().split(',')
                    if len(parts) >= 6:
                        items.append({
                            'nome': parts[0],
                            'rarita': int(parts[1]),
                            'sticker': parts[4],
                            'descrizione': parts[6] if len(parts) > 6 else ""
                        })
        except Exception as e:
            print(f"Error loading items: {e}")
        return items

    def get_item_details(self, item_name):
        items = self.load_items_from_csv()
        for item in items:
            if item['nome'] == item_name:
                return item
        return None

    def buy_box_wumpa(self, user):
        # Cost: 50 Wumpa (25 for Premium)
        COST = 25 if user.premium == 1 else 50
        
        if user.points < COST:
            return False, f"Non hai abbastanza Wumpa Fruit! Costo: {COST}", None
        
        self.user_service.add_points(user, -COST)
        
        return self.open_box_wumpa(user, cost_paid=COST)

    def open_box_wumpa(self, user, cost_paid=0):
        """Open a box wumpa (logic separated from buy)"""
        # Normal item drop (always)
        items_data = self.load_items_from_csv()
        if not items_data:
            return False, "Errore nel caricamento degli oggetti.", None

        # Weighted choice based on rarity (1/rarity)
        weights = [1/item['rarita'] for item in items_data]
        item = random.choices(items_data, weights=weights, k=1)[0]
        item_name = item['nome']
        
        self.add_item(user.id_telegram, item_name)
        
        base_msg = f"Hai trovato: {item_name}"
        
        # 10% chance to ALSO get a random game (JACKPOT!)
        if random.random() < 0.10:
            # Try to get a random game from catalog
            session = self.db.get_session()
            from models.game import GameInfo
            from sqlalchemy import func
            
            # Get a random unclaimed game
            game = session.query(GameInfo).filter(GameInfo.preso_da == '').order_by(func.random()).first()
            
            if game:
                # Assign game to user
                game.preso_da = str(user.id_telegram)
                session.commit()
                session.close()
                
                jackpot_msg = f"🎮 **JACKPOT!** {base_msg}\n\n"
                jackpot_msg += f"🎁 **BONUS:** Hai anche trovato un gioco!\n"
                jackpot_msg += f"🎯 **{game.title}**\n"
                jackpot_msg += f"🎮 Piattaforma: {game.platform}\n"
                
                if game.message_link:
                    jackpot_msg += f"📩 Link: {game.message_link}\n"
                
                if cost_paid > 0:
                    jackpot_msg += f"\n(Spesi {cost_paid} 🍑)"
                
                return True, jackpot_msg, item
            
            session.close()
        
        # Normal message (no jackpot)
        if cost_paid > 0:
            return True, f"{base_msg} (Spesi {cost_paid} 🍑)", item
        else:
            return True, base_msg, item

    def apply_effect(self, user, item_name, target_user=None):
        if item_name == "Turbo":
            # Logic: Next message has high luck
            # We need to store this state. Added luck_boost to Utente model.
            self.user_service.update_user(user.id_telegram, {'luck_boost': 1})
            return "Turbo attivato! La tua fortuna è aumentata: troverai casse più frequentemente.", None
        
        elif item_name == "Aku Aku" or item_name == "Uka Uka":
            # Invincibility
            until = datetime.datetime.now() + datetime.timedelta(minutes=60) # 60 mins invincibility
            self.user_service.update_user(user.id_telegram, {'invincible_until': until})
            return f"{item_name} attivato! Sei immune a TNT e Nitro per 60 minuti.", None
            
        elif item_name == "Cassa":
            wumpa = random.randint(5, 15)
            self.user_service.add_points(user, wumpa)
            return f"📦 Hai aperto la Cassa e trovato {wumpa} {PointsName}!", None
        
        elif item_name == "Nitro":
            # Trap logic: Places a trap in the group
            return "Nitro piazzata! Il prossimo che scrive esploderà!", {'type': 'trap', 'trap_type': 'Nitro'}
        
        elif item_name == "TNT":
             # Trap logic: Places a trap in the group
            return "TNT piazzata! Il prossimo che scrive dovrà correre!", {'type': 'trap', 'trap_type': 'TNT'}
        
        elif item_name == "Mira un giocatore":
            if target_user:
                # Drop wumpa from target
                amount = random.randint(5, 20)
                if target_user.points >= amount:
                    self.user_service.add_points(target_user, -amount)
                    # Maybe give them to user?
                    self.user_service.add_points(user, amount)
                    return f"Hai rubato {amount} {PointsName} a {target_user.username}!", None
                else:
                    return "Il bersaglio non ha abbastanza punti.", None
        
        elif item_name == "Colpisci un giocatore":
            if target_user:
                # Damage target (lose Wumpa) and DROP them for others
                amount = random.randint(10, 30)
                if target_user.points >= amount:
                    self.user_service.add_points(target_user, -amount)
                    # Return data for buttons
                    return f"Hai colpito {target_user.username}! Ha perso {amount} {PointsName} che sono caduti a terra!", {'type': 'wumpa_drop', 'amount': amount, 'target_name': target_user.username}
                else:
                    return f"Hai colpito {target_user.username}, ma non aveva abbastanza {PointsName} da perdere.", None
            else:
                return "Devi specificare un bersaglio.", None

        return "Oggetto utilizzato.", None

