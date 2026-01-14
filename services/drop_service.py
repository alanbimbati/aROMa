"""
Random Drop System - TNT, Nitro, Casse
Handles random drops while users write in chat
"""
from database import Database
from services.user_service import UserService
from services.item_service import ItemService
import random
from settings import PointsName

class DropService:
    def __init__(self):
        self.db = Database()
        self.user_service = UserService()
        self.item_service = ItemService()
        self.active_traps = {} # {chat_id: {'type': 'TNT'/'Nitro', 'owner_id': user_id}}

    def set_trap(self, chat_id, trap_type, owner_id):
        """Set a trap in the chat"""
        self.active_traps[chat_id] = {'type': trap_type, 'owner_id': owner_id}

    def check_traps(self, user, bot, message):
        """Check if message triggers a trap"""
        # Check invincibility
        if self.user_service.is_invincible(user):
            return False

        chat_id = message.chat.id
        if chat_id in self.active_traps:
            trap = self.active_traps.pop(chat_id)
            trap_type = trap['type']
            owner_id = trap['owner_id']
            
            # Don't trigger own trap? Or yes? User said "il prossimo a scrivere".
            # Usually own traps don't trigger, but "il prossimo" implies anyone.
            # Let's assume anyone including self if they write next.
            
            if trap_type == 'TNT':
                self.handle_tnt(user, bot, message)
            elif trap_type == 'Nitro':
                self.handle_nitro(user, bot, message)
            return True
        return False

    def maybe_drop(self, user, bot, message):
        """
        Random chance to drop TNT, Nitro, or Cassa while writing in chat
        """
        # Only in groups
        if message.chat.type not in ['group', 'supergroup']:
            return
            
        # DISABLE RANDOM DROPS - Only Monsters spawn now
        return
        
        # Global drop chance (e.g., 15% per message) to reduce frequency
        if random.random() > 0.15:
            return
        
        # Load items from CSV
        items_data = self.item_service.load_items_from_csv()
        if not items_data:
            return
        
        # Check each item for drop
        for item in items_data:
            # Calculate drop chance (1 in rarity)
            if random.randint(1, item['rarita']) == item['rarita']:
                # Item dropped!
                item_name = item['nome']
                
                # Send sticker if available
                try:
                    sticker_path = f"Stickers/{item['sticker']}"
                    with open(sticker_path, 'rb') as sti:
                        bot.send_sticker(message.chat.id, sti)
                except:
                    pass
                
                # Handle special items
                if item_name == 'TNT':
                    self.handle_tnt(user, bot, message)
                    return  # Only one drop per message
                    
                elif item_name == 'Nitro':
                    self.handle_nitro(user, bot, message)
                    return
                    
                elif item_name == 'Cassa':
                    self.handle_cassa(user, bot, message)
                    return
                    
                else:
                    # Normal item drop - STRICTLY 1 item
                    quantita = 1
                    self.item_service.add_item(user.id_telegram, item_name, quantita)
                    bot.reply_to(message, f"✨ Hai trovato: {item_name}!")
                    return
    
    def handle_tnt(self, user, bot, message):
        """
        TNT: User has 3 seconds to write or loses Wumpa
        """
        import datetime
        
        bot.reply_to(message, "💣 Ops!... Hai calpestato una Cassa TNT! Scrivi entro 3 secondi per evitarla!")
        
        # Set TNT timer
        timestamp = datetime.datetime.now()
        self.user_service.update_user(user.id_telegram, {
            'start_tnt': timestamp,
            'end_tnt': None
        })
    
    def handle_nitro(self, user, bot, message):
        """
        Nitro: Explodes immediately, user loses Wumpa
        """
        wumpa_persi = random.randint(1, 5)
        self.user_service.add_points(user, -wumpa_persi)
        
        bot.reply_to(message, 
            f"💥 Ops!... Hai calpestato una Cassa Nitro! Hai perso {wumpa_persi} {PointsName}!\n\n"
            f"{self.user_service.format_user_info(user)}",
            parse_mode='markdown'
        )
    
    def handle_cassa(self, user, bot, message):
        """
        Cassa: User finds extra Wumpa
        """
        wumpa_extra = random.randint(1, 5)
        self.user_service.add_points(user, wumpa_extra)
        
        bot.reply_to(message,
            f"📦 Hai trovato una cassa con {wumpa_extra} {PointsName}!\n\n"
            f"{self.user_service.format_user_info(user)}",
            parse_mode='markdown'
        )
    
    def check_tnt_timer(self, user, bot, message):
        """
        Check if user wrote in time to avoid TNT explosion
        """
        import datetime
        
        if not user.start_tnt:
            return False
        
        # Check if TNT already exploded
        if user.end_tnt:
            return False
        
        # Check if 3 seconds passed
        elapsed = (datetime.datetime.now() - user.start_tnt).total_seconds()
        
        if elapsed <= 3:
            # User wrote in time!
            self.user_service.update_user(user.id_telegram, {
                'end_tnt': datetime.datetime.now()
            })
            bot.reply_to(message, "✅ Sei riuscito ad evitare la TNT! Salvo!")
            return True
        else:
            # TNT exploded!
            wumpa_persi = random.randint(5, 15)
            self.user_service.add_points(user, -wumpa_persi)
            self.user_service.update_user(user.id_telegram, {
                'end_tnt': datetime.datetime.now()
            })
            bot.reply_to(message,
                f"💥 BOOM! La TNT è esplosa! Hai perso {wumpa_persi} {PointsName}!\n\n"
                f"{self.user_service.format_user_info(user)}",
                parse_mode='markdown'
            )
            return True
