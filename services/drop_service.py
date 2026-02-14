"""
Random Drop System - TNT, Nitro, Casse
Handles random drops while users write in chat
"""
from database import Database
from services.user_service import UserService
from services.item_service import ItemService
from models.seasons import Season
from sqlalchemy import text
import os
import random
import datetime

# Dynamic path resolution
SERVICE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SERVICE_DIR)

class DropService:
    def __init__(self):
        self.db = Database()
        self.user_service = UserService()
        self.item_service = ItemService()
        from services.crafting_service import CraftingService
        self.crafting_service = CraftingService()
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

    def maybe_drop(self, user, bot, message, session=None):
        """
        Consolidated chat drop system:
        - Resources (20%)
        - Classic Items (1%)
        - Dragon Balls (5% during relevant season)
        
        Cooldown: 10 seconds to avoid flood.
        Min message length: 4 characters.
        """
        # Only in groups
        if message.chat.type not in ['group', 'supergroup']:
            return
            
        # Anti-spam check (min length)
        if not message.text or len(message.text) < 4:
            return

        # Anti-spam check (time) - Standard 10s cooldown
        now = datetime.datetime.now()
        if user.last_chat_drop_time:
            elapsed = (now - user.last_chat_drop_time).total_seconds()
            if elapsed < 10:
                return
            
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
            
        try:
            # 1. Get active season metadata BEFORE closing any potentially local session
            # We need theme and name for Dragon Ball checks.
            active_season = session.query(Season).filter_by(is_active=True).first()
            theme = active_season.theme if active_season else None
            season_name = active_season.name if active_season else ""
            
            # 2. Reserving the slot: Update last drop time immediately
            # We do this here using the active session to avoid detached errors and redundant updates
            self.user_service.update_user(user.id_telegram, {'last_chat_drop_time': now}, session=session)
            
            # 3. Roll for Dragon Balls (5% during Dragon Ball season)
            if theme == 'Dragon Ball' and ("Saga 1" in season_name or "Stagione 1" in season_name):
                if random.random() < 0.05:
                    items_data = self.item_service.load_items_from_csv()
                    dragon_balls = [item for item in items_data if "Sfera del Drago" in item['nome']]
                    if dragon_balls:
                        item = random.choice(dragon_balls)
                        item_name = item['nome']
                        self.item_service.add_item(user.id_telegram, item_name, 1, session=session)
                        bot.reply_to(message, f"🐉 **DRAGON BALL!**\nHai trovato: {item_name}!")
                        # Send sticker
                        try:
                            sticker_path = os.path.join(BASE_DIR, "Stickers", item['sticker'])
                            if os.path.exists(sticker_path):
                                with open(sticker_path, 'rb') as sti:
                                    bot.send_sticker(message.chat.id, sti)
                        except: pass
                        
                        if local_session: session.commit()
                        return

            # 4. Roll for Classic Items (1% chance)
            if random.random() < 0.01:
                items_data = self.item_service.load_items_from_csv()
                classic_items = [item for item in items_data if "Sfera del Drago" not in item['nome']]
                if classic_items:
                    # Weighted roll for items
                    weights = [1/float(i['rarita']) for i in classic_items]
                    item = random.choices(classic_items, weights=weights, k=1)[0]
                    item_name = item['nome']
                    self.item_service.add_item(user.id_telegram, item_name, 1, session=session)
                    bot.reply_to(message, f"✨ **OGGETTO!**\nHai trovato: {item_name}!")
                    
                    if local_session: session.commit()
                    return

            # 5. Roll for Resources (20% chance)
            # Use the already open session if possible, but roll_chat_drop opens its own.
            # However, we can use the current session for adding the drop.
            drops = self.crafting_service.roll_chat_drop(chance=20)
            if drops:
                drop_messages = []
                for resource_id, qty, image_path in drops:
                    # Get resource name using current session
                    resource_name = session.execute(
                        text("SELECT name FROM resources WHERE id = :id"), 
                        {"id": resource_id}
                    ).scalar()
                    
                    success = self.crafting_service.add_resource_drop(user.id_telegram, resource_id, quantity=qty, source="chat", session=session)
                    
                    if success and resource_name:
                        drop_messages.append(f"**{resource_name} x{qty}**")
                
                if drop_messages:
                    caption = "⚒️ **RISORSE!**\nHai trovato: " + ", ".join(drop_messages)
                    first_image = drops[0][2] # image from the first drop
                    
                    # Try to send photo, fallback to reply
                    sent = False
                    if first_image and os.path.exists(first_image):
                        try:
                            with open(first_image, 'rb') as photo:
                                bot.send_photo(message.chat.id, photo, caption=caption, reply_to_message_id=message.message_id, parse_mode='markdown')
                                sent = True
                        except: pass
                    
                    if not sent:
                        bot.reply_to(message, caption, parse_mode='markdown')
                    
                    if local_session: session.commit()
                    return

            # If no drop occurred, we still need to commit the update_user for the cooldown
            if local_session:
                session.commit()
                
        except Exception as e:
            if local_session:
                session.rollback()
            print(f"[ERROR] DropService.maybe_drop: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if local_session:
                session.close()
    
    def handle_tnt(self, user, bot, message):
        """
        TNT: User has 3 seconds to write or loses Wumpa
        """
        
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
