from telebot import types, util
from settings import *
import schedule
import time
import threading
import datetime
import os
from io import BytesIO

# Image processing for grayscale conversion
try:
    from PIL import Image, ImageEnhance
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("⚠️ PIL/Pillow not available, grayscale images will not work")

# Services
from services.user_service import UserService
from services.item_service import ItemService
from services.game_service import GameService
from services.shop_service import ShopService
from services.wish_service import WishService
from services.pve_service import PvEService
from services.character_service import CharacterService
from services.transformation_service import TransformationService
from services.stats_service import StatsService
from services.drop_service import DropService
import random

# Initialize Services
user_service = UserService()
item_service = ItemService()
game_service = GameService()
shop_service = ShopService()
wish_service = WishService()
pve_service = PvEService()
character_service = CharacterService()
transformation_service = TransformationService()
stats_service = StatsService()
drop_service = DropService()


@bot.message_handler(content_types=['left_chat_member'])
def esciDalGruppo(message):
    chatid = message.left_chat_member.id
    try:
        user_service.update_user(chatid, {'points': 0})
        bot.send_message(CANALE_LOG, f"I punti dell'utente {message.left_chat_member.first_name} sono stati azzerati perchè è uscito dal gruppo.")
    except Exception as e:
        print('Errore ', str(e))

@bot.message_handler(content_types=['new_chat_members'])
def newmember(message):
    # Welcome logic
    bot.reply_to(message, "Benvenuto su aROMa! Per te 5 " + PointsName + "!", reply_markup=types.ReplyKeyboardRemove())
    user_service.create_user(message.from_user.id, message.from_user.username, message.from_user.first_name, message.from_user.last_name)

@bot.message_handler(commands=['start'])
def start(message):
    user_service.create_user(message.from_user.id, message.from_user.username, message.from_user.first_name, message.from_user.last_name)
    bot.reply_to(message, "Cosa vuoi fare?", reply_markup=get_start_markup(message.from_user.id))

def get_start_markup(user_id):
    markup = types.ReplyKeyboardMarkup()
    markup.add('📦 Inventario', '📦 Compra Box Wumpa (50 🍑)')
    markup.add('🧪 Negozio Pozioni', '👤 Profilo')
    markup.add('👤 Scegli il personaggio')
    markup.add('📄 Classifica', '❓ Aiuto')
    return markup

def get_character_image(character, is_locked=False):
    """Get character image, converted to grayscale if locked"""
    char_name_lower = character.nome.lower().replace(" ", "_")
    image_path = f"images/characters/{char_name_lower}.png"
    
    if not os.path.exists(image_path):
        return None
    
    if not is_locked or not PIL_AVAILABLE:
        # Return normal image
        with open(image_path, 'rb') as f:
            return f.read()
    
    # Convert to grayscale
    try:
        img = Image.open(image_path)
        # Convert to grayscale
        grayscale = img.convert('L')
        # Convert back to RGB for Telegram
        grayscale_rgb = Image.merge('RGB', (grayscale, grayscale, grayscale))
        # Reduce brightness slightly for locked effect
        enhancer = ImageEnhance.Brightness(grayscale_rgb)
        darkened = enhancer.enhance(0.7)
        
        # Save to BytesIO
        output = BytesIO()
        darkened.save(output, format='PNG')
        output.seek(0)
        return output.read()
    except Exception as e:
        print(f"Error converting image to grayscale: {e}")
        # Return normal image if conversion fails
        with open(image_path, 'rb') as f:
            return f.read()

# Global handler function for character selection (to avoid generator issues with class methods)
def process_character_selection(message):
    """Global function to handle character selection from next_step_handler"""
    try:
        print(f"[DEBUG] process_character_selection called with message type: {type(message)}")
        
        # Generator fix attempt
        import types as py_types
        if isinstance(message, py_types.GeneratorType):
            print("[DEBUG] Message is a generator, trying to get first item")
            try:
                message = next(message)
                print(f"[DEBUG] Extracted message type: {type(message)}")
            except StopIteration:
                print("[ERROR] Generator was empty")
                return

        print(f"[DEBUG] process_character_selection called with message: {message.text}")
        chatid = message.from_user.id
        print(f"[DEBUG] chatid: {chatid}")
        
        if message.text == "🔙 Indietro":
            print("[DEBUG] User selected back button")
            bot.reply_to(message, "Menu principale", reply_markup=get_start_markup(chatid))
            return

        character_name = message.text
        print(f"[DEBUG] Character name: {character_name}")
        utente = user_service.get_user(chatid)
        print(f"[DEBUG] User found: {utente is not None}")
        
        if not utente:
            bot.reply_to(message, "❌ Errore: utente non trovato", reply_markup=get_start_markup(chatid))
            return
        
        session = user_service.db.get_session()
        from models.system import Livello
        livello = session.query(Livello).filter_by(nome=character_name).first()
        print(f"[DEBUG] Character found in DB: {livello is not None}")
        session.close()
        
        if not livello:
            bot.reply_to(message, f"❌ Personaggio '{character_name}' non trovato nel database", reply_markup=get_start_markup(chatid))
            return
        
        # Verify availability again using service
        available = character_service.get_available_characters(utente)
        print(f"[DEBUG] Available characters count: {len(available)}")
        print(f"[DEBUG] Checking if character id {livello.id} is in available list")
        
        if any(c.id == livello.id for c in available):
            print(f"[DEBUG] Character is available, updating user")
            user_service.update_user(chatid, {'livello_selezionato': livello.id})
            
            # Show info/image
            msg_text = f"✅ Personaggio {character_name} equipaggiato!\n"
            if livello.special_attack_name:
                msg_text += f"✨ Skill: {livello.special_attack_name} ({livello.special_attack_damage} DMG, {livello.special_attack_mana_cost} Mana)"
            
            print(f"[DEBUG] Sending success message")
            bot.reply_to(message, msg_text, reply_markup=get_start_markup(chatid))
        else:
            print(f"[DEBUG] Character not in available list")
            bot.reply_to(message, f"❌ Non possiedi questo personaggio o livello insufficiente", reply_markup=get_start_markup(chatid))
    except Exception as e:
        print(f"[ERROR] Error in process_character_selection: {e}")
        import traceback
        traceback.print_exc()
        try:
            chatid = message.from_user.id
            bot.reply_to(message, f"❌ Errore durante la selezione: {str(e)}", reply_markup=get_start_markup(chatid))
        except:
            pass

class BotCommands:
    def __init__(self, message, bot):
        self.bot = bot
        self.message = message
        self.chatid = message.from_user.id if message.from_user else message.chat.id
        
        self.comandi_privati = {
            "🎫 Compra un gioco steam": self.handle_buy_steam_game,
            "👤 Scegli il personaggio": self.handle_choose_character,
            "👤 Profilo": self.handle_profile,
            "🛒 Negozio Personaggi": self.handle_shop_characters,
            "🧪 Negozio Pozioni": self.handle_shop_potions,
            "Compra abbonamento Premium (1 mese)": self.handle_buy_premium,
            "✖️ Disattiva rinnovo automatico": self.handle_disattiva_abbonamento_premium,
            "✅ Attiva rinnovo automatico": self.handle_attiva_abbonamento_premium,
            "classifica": self.handle_classifica,
            "compro un altro mese": self.handle_buy_another_month,
            "📦 Inventario": self.handle_inventario,
            "📦 Compra Box Wumpa (50 🍑)": self.handle_buy_box_wumpa,
            "/search": self.handle_search_game,
            "/help": self.handle_help,
            "aiuto": self.handle_help,
            "help": self.handle_help,
        }

        self.comandi_admin = {
            "addLivello": self.handle_add_livello,
            "+": self.handle_plus_minus,
            "-": self.handle_plus_minus,
            "restore": self.handle_restore,
            "backup": self.handle_backup,
            "broadcast": self.handle_broadcast,
            "/spawn": self.handle_spawn_mob,
        }
        
        self.comandi_generici = {
            "!dona": self.handle_dona,
            "/me": self.handle_me,
            "/profile": self.handle_profile,
            "!profile": self.handle_profile,
            "!status": self.handle_status,
            "!classifica": self.handle_classifica,
            "!stats": self.handle_stats,
            "!livell": self.handle_livell,
            "album": self.handle_album,
            "!inventario": self.handle_inventario,
            "/inventario": self.handle_inventario,
            "/wish": self.handle_wish,
            "attacca": self.handle_attack,
            "/attacca": self.handle_attack,
            "⚔️ Attacca": self.handle_attack,
            "/search": self.handle_search_game,
            "/givedragonballs": self.handle_give_dragonballs,  # Admin only
            "/testchar": self.handle_test_char,  # Debug
            "attacco speciale": self.handle_special_attack,
            "🔮 attacco speciale": self.handle_special_attack,
            "/help": self.handle_help,
            "!help": self.handle_help,
        }

    def handle_help(self):
        msg = """📚 *GUIDA AROMA BOT* 📚

🔹 *GENERALE*
Guadagna *Frutti Wumpa* (🍑) e *EXP* scrivendo in chat!
Ogni messaggio ti dà punti. Sali di livello per sbloccare nuovi personaggi.

🔹 *PERSONAGGI*
Usa '👤 Scegli il personaggio' per equipaggiare un eroe.
Ogni personaggio ha abilità uniche e statistiche diverse.
Alcuni personaggi si sbloccano livellando, altri si comprano nel '🛒 Negozio Personaggi'.

🔹 *INVENTARIO & OGGETTI*
Usa '📦 Inventario' per vedere i tuoi oggetti.
- *Aku Aku / Uka Uka*: Ti rendono immune a TNT e Nitro per 60 minuti.
- *Turbo*: Aumenta la fortuna (trovi più casse wumpa).
- *Nitro / Colpisci*: Danneggia un altro giocatore (toglie Wumpa).
- *Sfere del Drago*: Raccogline 7 per esprimere un desiderio!

🔹 *COMBATTIMENTO (PvE)*
Ogni giorno appaiono mostri selvatici!
- Scrivi `attacca` per colpire il mostro.
- Il mostro contrattacca! Stai attento alla tua vita.
- Ogni 10 minuti, il mostro attacca un utente a caso!
- Usa `attacco speciale` per usare l'abilità del tuo personaggio (costa Mana).
- La Domenica alle 20:00 appare un *RAID BOSS* molto potente!

🔹 *COMANDI UTILI*
- `info`: Visualizza le tue statistiche.
- `Nome in Game`: Imposta il tuo nickname di gioco.
- `classifica`: Vedi la top 10.
"""
        self.bot.reply_to(self.message, msg, parse_mode='markdown')

    def handle_spawn_mob(self):
        """Admin command to manually spawn a mob"""
        utente = user_service.get_user(self.chatid)
        if not user_service.is_admin(utente):
            return
            
        mob_id = pve_service.spawn_daily_mob()
        if mob_id:
            mob = pve_service.get_current_mob_status()
            self.bot.reply_to(self.message, f"⚠️ Un {mob['name']} selvatico è apparso! Salute: {mob['health']} HP. Scrivi 'attacca' per sconfiggerlo!")
        else:
            self.bot.reply_to(self.message, "C'è già un mob attivo o errore nello spawn.")

    def handle_special_attack(self):
        utente = user_service.get_user(self.chatid)
        success, msg = pve_service.use_special_attack(utente)
        self.bot.reply_to(self.message, msg)

    def handle_test_char(self):
        """Test character selection directly"""
        utente = user_service.get_user(self.chatid)
        # Force select Crash Bandicoot
        user_service.update_user(self.chatid, {'livello_selezionato': 1})
        self.bot.reply_to(self.message, "✅ Test: Crash Bandicoot equipaggiato direttamente! Prova ora a usare '👤 Scegli il personaggio' normalmente.")

    def handle_give_dragonballs(self):
        """Admin command to give all dragon balls for testing"""
        utente = user_service.get_user(self.chatid)
        if not user_service.is_admin(utente):
            self.bot.reply_to(self.message, "❌ Comando disponibile solo per gli admin!")
            return
        
        # Give all 7 Shenron balls
        for i in range(1, 8):
            item_service.add_item(self.chatid, f"La Sfera del Drago Shenron {i}")
        
        # Give all 7 Porunga balls
        for i in range(1, 8):
            item_service.add_item(self.chatid, f"La Sfera del Drago Porunga {i}")
        
        self.bot.reply_to(self.message, "✅ Ti ho dato tutte le 14 sfere del drago (7 Shenron + 7 Porunga) per testare!\n\nUsa /wish o vai in inventario per evocarli.")

    def handle_attack(self):
        utente = user_service.get_user(self.chatid)
        damage = random.randint(10, 30) # Base damage
        
        # Check for luck boost
        if utente.luck_boost > 0:
             damage *= 2
             user_service.update_user(self.chatid, {'luck_boost': 0}) # Consume boost
        
        # Try attacking mob first
        success, msg = pve_service.attack_mob(utente, damage)
        if not success:
            # Try attacking raid boss
            success, msg = pve_service.attack_raid_boss(utente, damage)
            
        self.bot.reply_to(self.message, msg)

    def handle_buy_box_wumpa(self):
        utente = user_service.get_user(self.chatid)
        success, msg, item = item_service.buy_box_wumpa(utente)
        
        if success and item:
            # Send sticker/image
            try:
                sticker_path = f"Stickers/{item['sticker']}"
                if item['sticker'].endswith('.png'):
                    with open(sticker_path, 'rb') as photo:
                        self.bot.send_photo(self.chatid, photo, caption=msg)
                else:
                    with open(sticker_path, 'rb') as sticker:
                        self.bot.send_sticker(self.chatid, sticker)
                        self.bot.send_message(self.chatid, msg)
            except Exception as e:
                print(f"Error sending image: {e}")
                self.bot.reply_to(self.message, msg)
        else:
            self.bot.reply_to(self.message, msg, reply_markup=get_start_markup(self.chatid))

    def handle_shop_potions(self):
        """Show potion shop"""
        utente = user_service.get_user(self.chatid)
        
        msg = "🧪 **Negozio Pozioni**\n\n"
        msg += "Recupera la tua vita e mana con le pozioni!\n\n"
        
        # Load potions using PotionService
        from services.potion_service import PotionService
        potion_service = PotionService()
        potions = potion_service.potions
        
        markup = types.InlineKeyboardMarkup()
        
        # Group by type
        health_potions = [p for p in potions if p['tipo'] == 'health_potion']
        mana_potions = [p for p in potions if p['tipo'] == 'mana_potion']
        special_potions = [p for p in potions if p['tipo'] == 'full_restore']
        
        # Health potions
        if health_potions:
            for potion in health_potions:
                price = int(potion['prezzo'] * 0.5) if utente.premium == 1 else potion['prezzo']
                btn_text = f"💚 {potion['nome']} - {price}🍑"
                markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"buy_potion|{potion['nome']}"))
        
        # Mana potions
        if mana_potions:
            for potion in mana_potions:
                price = int(potion['prezzo'] * 0.5) if utente.premium == 1 else potion['prezzo']
                btn_text = f"💙 {potion['nome']} - {price}🍑"
                markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"buy_potion|{potion['nome']}"))
        
        # Special potions
        if special_potions:
            for potion in special_potions:
                price = int(potion['prezzo'] * 0.5) if utente.premium == 1 else potion['prezzo']
                btn_text = f"✨ {potion['nome']} - {price}🍑"
                markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"buy_potion|{potion['nome']}"))
        
        self.bot.reply_to(self.message, msg, reply_markup=markup, parse_mode='markdown')

    def handle_wish(self):
        utente = user_service.get_user(self.chatid)
        has_shenron, has_porunga = wish_service.check_dragon_balls(utente)
        
        if has_shenron:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(f"💰 {PointsName} (300-500)", callback_data="wish|Shenron|wumpa"))
            markup.add(types.InlineKeyboardButton("⭐ EXP (300-500)", callback_data="wish|Shenron|exp"))
            self.bot.reply_to(self.message, "🐉 Shenron è stato evocato!\n\nEsprimi il tuo desiderio!", reply_markup=markup)
            
        elif has_porunga:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(f"💰 {PointsName} (50-100)", callback_data="pwish|1|wumpa"))
            markup.add(types.InlineKeyboardButton("🎁 Oggetto Raro", callback_data="pwish|1|item"))
            self.bot.reply_to(self.message, "🐲 Porunga è stato evocato!\n\nEsprimi 3 desideri!\n\n[Desiderio 1/3]", reply_markup=markup)
            
        else:
            self.bot.reply_to(self.message, "❌ Non hai tutte le sfere del drago!\nRaccogli 7 sfere di Shenron o Porunga per evocarli.")

    def handle_search_game(self):
        msg = self.bot.reply_to(self.message, "🔍 Scrivi il nome del gioco che cerchi:")
        self.bot.register_next_step_handler(msg, self.process_search_game)

    def process_search_game(self, message):
        results = game_service.search_games(message.text)
        if results:
            markup = types.InlineKeyboardMarkup()
            for game in results[:5]:
                markup.add(types.InlineKeyboardButton(f"{game.title}", callback_data=f"sg|{game.title}"))
            self.bot.reply_to(message, "🎮 Risultati ricerca:", reply_markup=markup)
        else:
            self.bot.reply_to(message, "Nessun gioco trovato.")

    def handle_info(self):
        utente = user_service.get_user(self.chatid)
        msg = user_service.info_user(utente)
        
        # Add Game Info
        if utente.platform and utente.game_name:
            msg += f"\n🎮 {utente.platform}: {utente.game_name}"
        
        # Check for character image
        session = user_service.db.get_session()
        from models.system import Livello
        selected_level = session.query(Livello).filter_by(id=utente.livello_selezionato).first()
        
        image_sent = False
        if selected_level:
            # Try using cached file_id first
            if selected_level.telegram_file_id:
                try:
                    self.bot.send_photo(self.chatid, selected_level.telegram_file_id, caption=msg, parse_mode='markdown', reply_markup=get_start_markup(self.chatid))
                    session.close()
                    image_sent = True
                except Exception as e:
                    print(f"Error sending cached image: {e}")
                    # If error (e.g. file_id invalid), clear it
                    selected_level.telegram_file_id = None
                    session.commit()
            
            if not image_sent:
                # Try to find local image file
                image_map = {
                    "Crash Bandicoot": "images/characters/crash_bandicoot.png",
                    "Spyro": "images/characters/spyro.png"
                }
                
                image_path = image_map.get(selected_level.nome)
                
                if image_path:
                    try:
                        with open(image_path, 'rb') as photo:
                            sent_msg = self.bot.send_photo(self.chatid, photo, caption=msg, parse_mode='markdown', reply_markup=get_start_markup(self.chatid))
                            
                            # Save file_id for future use
                            if sent_msg.photo:
                                file_id = sent_msg.photo[-1].file_id  # Get largest photo
                                selected_level.telegram_file_id = file_id
                                session.commit()
                                print(f"Saved file_id for {selected_level.nome}: {file_id}")
                            
                            image_sent = True
                    except Exception as e:
                        print(f"Error sending char image: {e}")
        
        session.close()
        
        if not image_sent:
            self.bot.reply_to(self.message, msg, parse_mode='markdown', reply_markup=get_start_markup(self.chatid))

    def handle_profile(self):
        """Show comprehensive user profile with stats and transformations"""
        utente = user_service.get_user(self.chatid)
        
        # Check for expired transformations
        # Transformation check removed - handled automatically
        
        # Get character info
        session = user_service.db.get_session()
        from models.system import Livello
        character = session.query(Livello).filter_by(id=utente.livello_selezionato).first()
        
        # Build new profile format
        msg = ""
        
        # Premium status - ONLY show if user is actually premium
        if utente.premium == 1:
            msg += "🎖 Utente Premium\n"
            if utente.abbonamento_attivo == 1:
                # Calculate subscription end date
                if hasattr(utente, 'scadenza_premium') and utente.scadenza_premium:
                    msg += f"✅ Abbonamento attivo (fino al {utente.scadenza_premium.strftime('%Y-%m-%d')})\n"
                else:
                    msg += "✅ Abbonamento attivo\n"
            else:
                msg += "⏸️ Abbonamento in pausa\n"
        
        # Username, Wumpa, Exp, Level, Character
        username = utente.username or utente.nome or "Utente"
        msg += f"👤 {username}: {utente.points} Frutti Wumpa 🍑\n"
        
        # Calculate exp for next level using character's exp_required



    def handle_profile(self):
        """Show comprehensive user profile with stats and transformations"""
        utente = user_service.get_user(self.chatid)
        
        # Check for expired transformations
        # Transformation check removed - handled automatically in get_active_transformation
        
        # Get character info
        session = user_service.db.get_session()
        from models.system import Livello
        character = session.query(Livello).filter_by(id=utente.livello_selezionato).first()
        
        # Build new profile format
        msg = ""
        
        # Premium status - ONLY show if user is actually premium
        if utente.premium == 1:
            msg += "🎖 **Utente Premium**\n"
        if utente.abbonamento_attivo == 1:
            msg += f"✅ Abbonamento attivo (fino al {str(utente.scadenza_premium)[:11]})\n"
            
        nome_utente = utente.nome if utente.username is None else utente.username
        msg += f"👤 **{nome_utente}**: {utente.points} {PointsName}\n"
        
        # Calculate next level exp
        next_lv_num = utente.livello + 1
        next_lv_row = session.query(Livello).filter_by(livello=next_lv_num).first()
        
        if next_lv_row:
            exp_req = next_lv_row.exp_required if hasattr(next_lv_row, 'exp_required') else next_lv_row.exp_to_lv
        else:
            # Formula for levels beyond DB (e.g. up to 80)
            exp_req = 100 * (next_lv_num ** 2)
            
        msg += f"💪🏻 **Exp**: {utente.exp}/{exp_req}\n"
        # Character name with saga
        char_display = character.nome if character else 'N/A'
        if character and character.character_group:
            char_display = f"{character.nome} - {character.character_group}"
        msg += f"🎖 **Lv.** {utente.livello} - {char_display}\n"
        
        # RPG Stats
        current_hp = utente.current_hp if hasattr(utente, 'current_hp') and utente.current_hp is not None else utente.health
        msg += f"\n❤️ **Vita**: {current_hp}/{utente.max_health}\n"
        msg += f"💙 **Mana**: {utente.mana}/{utente.max_mana}\n"
        msg += f"⚔️ **Danno Base**: {utente.base_damage}\n"
        
        if utente.stat_points > 0:
            msg += f"📊 **Punti Stat**: {utente.stat_points} (usa /stats)\n"
            
        # Check fatigue
        if user_service.check_fatigue(utente):
            msg += "\n⚠️ **SEI AFFATICATO!** Riposa per recuperare vita.\n"
            
        # Skills/Abilities info
        if character:
            from services.skill_service import SkillService
            skill_service = SkillService()
            abilities = skill_service.get_character_abilities(character.id)
            
            if abilities:
                msg += f"\n✨ **Abilità:**\n"
                for ability in abilities:
                    msg += f"🔮 {ability['name']}: {ability['damage']} DMG, {ability['mana_cost']} Mana, Crit {ability['crit_chance']}% (x{ability['crit_multiplier']})\n"
            elif character.special_attack_name:
                # Fallback to legacy special attack
                msg += f"\n✨ **Attacco Speciale**: {character.special_attack_name}\n"
                msg += f"  Danno: {character.special_attack_damage} | Mana: {character.special_attack_mana_cost}\n"
            
        # Transformations
        active_trans = transformation_service.get_active_transformation(utente)
        if active_trans:
            time_left = active_trans['expires_at'] - datetime.datetime.now()
            if time_left.total_seconds() > 0:
                hours_left = int(time_left.total_seconds() / 3600)
                msg += f"✨ **Trasformazione Attiva:**\n"
                msg += f"└ {active_trans['name']}\n"
                msg += f"└ Scade tra: {hours_left}h\n\n"
        
        # Inline buttons
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📊 Alloca Statistiche", callback_data="stats_menu"))
        markup.add(types.InlineKeyboardButton(f"🔄 Reset Stats (500 {PointsName})", callback_data="reset_stats_confirm"))
        if character:
            markup.add(types.InlineKeyboardButton("✨ Attacco Speciale", callback_data="special_attack_mob"))
            
        # Try to send with character image
        image_sent = False
        if character:
            # Try using helper function
            image_data = get_character_image(character, is_locked=False)
            
            if image_data:
                try:
                    self.bot.send_photo(self.chatid, image_data, caption=msg, parse_mode='markdown', reply_markup=markup)
                    image_sent = True
                except Exception as e:
                    print(f"Error sending character image: {e}")
        
        session.close()
        
        if not image_sent:
            self.bot.reply_to(self.message, msg, parse_mode='markdown', reply_markup=markup)


    def handle_nome_in_game(self):
        markup = types.ReplyKeyboardMarkup()
        markup.add('Steam', 'PlayStation', 'Xbox', 'Switch', 'Battle.net')
        markup.add('🔙 Indietro')
        msg = self.bot.reply_to(self.message, "Seleziona la tua piattaforma:", reply_markup=markup)
        self.bot.register_next_step_handler(msg, self.process_platform_selection)

    def process_platform_selection(self, message):
        if message.text == "🔙 Indietro":
            self.bot.reply_to(message, "Menu principale", reply_markup=get_start_markup(self.chatid))
            return
            
        platform = message.text
        msg = self.bot.reply_to(message, f"Hai selezionato {platform}.\nOra scrivi il tuo nome in game:", reply_markup=types.ReplyKeyboardRemove())
        self.bot.register_next_step_handler(msg, self.process_gamename_input, platform)

    def process_gamename_input(self, message, platform):
        gamename = message.text
        user_service.update_user(self.chatid, {'platform': platform, 'game_name': gamename})
        self.bot.reply_to(message, f"✅ Salvato! {platform}: {gamename}", reply_markup=get_start_markup(self.chatid))

    def handle_inventario(self):
        inventario = item_service.get_inventory(self.chatid)
        utente = user_service.get_user(self.chatid)
        msg = "📦 Inventario 📦\n\n"
        if inventario:
            for oggetto in inventario:
                item_details = item_service.get_item_details(oggetto.oggetto)
                desc = f" - {item_details['descrizione']}" if item_details else ""
                msg += f"🧷 *{oggetto.oggetto}*{desc}"
                if oggetto.quantita > 1:
                    msg += f" (x{oggetto.quantita})"
                msg += "\n"
            
            # Add buttons to use items
            markup = types.InlineKeyboardMarkup()
            
            # Emoji mapping for items
            item_emoji = {
                "Turbo": "🏎️",
                "Aku Aku": "🎭",
                "Uka Uka": "😈",
                "Nitro": "💣",
                "Mira un giocatore": "🎯",
                "Colpisci un giocatore": "💥"
            }
            
            for oggetto in inventario:
                # Only add button if item is usable
                if oggetto.oggetto in item_emoji:
                    emoji = item_emoji.get(oggetto.oggetto, "🔹")
                    markup.add(types.InlineKeyboardButton(f"{emoji} Usa {oggetto.oggetto}", callback_data=f"use|{oggetto.oggetto}"))
            
            # Check for dragon balls
            has_shenron, has_porunga = wish_service.check_dragon_balls(utente)
            if has_shenron:
                markup.add(types.InlineKeyboardButton("🐉 Evoca Shenron", callback_data="invoke|shenron"))
            if has_porunga:
                markup.add(types.InlineKeyboardButton("🐲 Evoca Porunga", callback_data="invoke|porunga"))
            
            self.bot.reply_to(self.message, msg, reply_markup=markup, parse_mode='markdown')
        else:
            self.bot.reply_to(self.message, "Il tuo inventario è vuoto.")

    def handle_buy_steam_game(self):
        markup = types.ReplyKeyboardMarkup()
        markup.add('🥉 Bronze Coin (10% di chance di vincere un titolone casuale)')        
        markup.add('🥈 Silver Coin (50% di chance di vincere un titolone casuale)')        
        markup.add('🥇 Gold Coin (100% di chance di vincere un titolone casuale)')        
        markup.add('🎖 Platinum Coin (Gioco a scelta)')
        msg = self.bot.reply_to(self.message, "Scegli il coin:", reply_markup=markup)
        self.bot.register_next_step_handler(msg, self.process_steam_coin)

    def process_steam_coin(self, message):
        utente = user_service.get_user(self.chatid)
        coin_type = message.text.split(' (')[0] # Extract coin name
        success, result = shop_service.buy_steam_game(utente, coin_type)
        
        if success:
            if result == "Platinum":
                # Ask for game name logic here (simplified for now)
                self.bot.reply_to(message, "Hai scelto Platinum! Contatta un admin per il tuo gioco.")
            else:
                self.bot.reply_to(message, f"Hai vinto: {result.titolo}\nKey: {result.steam_key}")
        else:
            self.bot.reply_to(message, f"Errore: {result}")

    def handle_buy_premium(self):
        utente = user_service.get_user(self.chatid)
        success, msg = shop_service.buy_premium(utente)
        self.bot.reply_to(self.message, msg)

    def handle_disattiva_abbonamento_premium(self):
        # Logic to stop auto-renewal
        user_service.update_user(self.chatid, {'abbonamento_attivo': 0})
        self.bot.reply_to(self.message, "Rinnovo automatico disattivato.")

    def handle_attiva_abbonamento_premium(self):
        user_service.update_user(self.chatid, {'abbonamento_attivo': 1})
        self.bot.reply_to(self.message, "Rinnovo automatico attivato.")

    def handle_classifica(self):
        users = user_service.get_users()
        # Sort logic
        users.sort(key=lambda x: x.points, reverse=True)
        msg = "🏆 Classifica 🏆\n\n"
        for i, u in enumerate(users[:10]):
            msg += f"{i+1}. {u.username or u.nome}: {u.points} {PointsName}\n"
        self.bot.reply_to(self.message, msg)

    def handle_nome_in_game(self):
        # Logic for game names
        pass

    def handle_buy_another_month(self):
        # Logic for extending premium
        pass

    def handle_add_livello(self):
        # Admin command
        pass

    def handle_plus_minus(self):
        # Admin command to add/remove points
        pass

    def handle_restore(self):
        pass

    def handle_backup(self):
        pass

    def handle_broadcast(self):
        pass

    def handle_dona(self):
        pass

    def handle_me(self):
        self.handle_info()

    def handle_status(self):
        pass

    def handle_stats(self):
        pass

    def handle_livell(self):
        pass

    def handle_album(self):
        pass

    def handle_choose_character(self):
        """Character selection with improved navigation"""
        utente = user_service.get_user(self.chatid)
        if not utente:
            return
        
        is_admin = user_service.is_admin(utente)
        
        # Get all levels
        levels = character_service.get_character_levels()
        if not levels:
            self.bot.reply_to(self.message, "Nessun personaggio trovato!")
            return
            
        # Determine starting level (closest to user's level)
        start_level = character_service.get_closest_level(utente.livello)
        
        # Find index of start_level
        try:
            level_idx = levels.index(start_level)
        except ValueError:
            level_idx = 0
            
        current_level = levels[level_idx]
        
        # Check visibility restriction
        if not is_admin and current_level > utente.livello:
            # If closest level is higher than user level (e.g. user lv 4, closest char lv 5),
            # we should show the highest level <= user level
            valid_levels = [l for l in levels if l <= utente.livello]
            if valid_levels:
                current_level = valid_levels[-1]
                level_idx = levels.index(current_level)
            else:
                # User is lower than lowest char level? Show first level anyway (locked)
                level_idx = 0
                current_level = levels[0]
        
        level_chars = character_service.get_characters_by_level(current_level)
        if not level_chars:
            self.bot.reply_to(self.message, "Nessun personaggio trovato!")
            return
            
        char_idx = 0
        char = level_chars[char_idx]
        
        is_unlocked = character_service.is_character_unlocked(utente, char.id)
        is_equipped = (utente.livello_selezionato == char.id)
        
        # Format character card
        lock_icon = "" if is_unlocked else "🔒 "
        saga_info = f" - {char.character_group}" if char.character_group else ""
        type_info = f" ({char.elemental_type})" if char.elemental_type else ""
        msg = f"**{lock_icon}{char.nome}{saga_info}{type_info}**"
        
        if is_equipped:
            msg += " ⭐ *EQUIPAGGIATO*"
        
        msg += "\n\n"
        msg += f"📊 Livello Richiesto: {char.livello}\n"
        
        if char.lv_premium == 1:
            msg += f"👑 Richiede Premium\n"
        elif char.lv_premium == 2 and char.price > 0:
            price = char.price
            if utente.premium == 1:
                price = int(price * 0.5)
            msg += f"💰 Prezzo: {price} {PointsName}"
            if utente.premium == 1:
                msg += f" ~~{char.price}~~"
            msg += "\n"
        
        
        # Show skills with crit stats
        from services.skill_service import SkillService
        skill_service = SkillService()
        abilities = skill_service.get_character_abilities(char.id)
        
        if abilities:
            msg += f"\n✨ **Abilità:**\n"
            for ability in abilities:
                msg += f"\n🔮 **{ability['name']}**\n"
                msg += f"   ⚔️ Danno: {ability['damage']}\n"
                msg += f"   💙 Mana: {ability['mana_cost']}\n"
                msg += f"   🎯 Crit: {ability['crit_chance']}% (x{ability['crit_multiplier']})\n"
        elif char.special_attack_name:
            # Fallback to legacy special attack
            msg += f"\n✨ **Abilità Speciale:**\n"
            msg += f"🔮 {char.special_attack_name}\n"
            msg += f"⚔️ Danno: {char.special_attack_damage}\n"
            msg += f"💙 Costo Mana: {char.special_attack_mana_cost}\n"
        
        if char.description:
            msg += f"\n📝 {char.description}\n"
        
        if not is_unlocked:
            msg += "\n🔒 **PERSONAGGIO BLOCCATO**\n"
            if char.livello > utente.livello:
                msg += f"Raggiungi livello {char.livello} per sbloccarlo!\n"
            elif char.lv_premium == 1:
                msg += "Richiede abbonamento Premium!\n"
        
        msg += f"\n📄 Livello {level_idx + 1}/{len(levels)} - Personaggio {char_idx + 1}/{len(level_chars)}"
        
        markup = types.InlineKeyboardMarkup()
        
        # Navigation Buttons
        # Row 1: Fast Up (-5) | Up (-1) | My Level | Down (+1) | Fast Down (+5)
        # Note: "Up" means higher level number (down in list) or lower?
        # Let's use arrows: ⬆️ (Next Level), ⬇️ (Prev Level)
        # Wait, usually Up is previous item in list, Down is next.
        # But for levels, Up usually means Higher Level.
        # Let's use explicit icons.
        
        nav_levels_row = []
        
        # -5 Levels
        if level_idx >= 5:
             nav_levels_row.append(types.InlineKeyboardButton("⏪ -5", callback_data=f"char_nav|{level_idx-5}|0"))
        
        # Prev Level
        if level_idx > 0:
             nav_levels_row.append(types.InlineKeyboardButton("⬇️", callback_data=f"char_nav|{level_idx-1}|0"))
             
        # My Level Button
        my_level_idx = -1
        try:
            my_level_char = character_service.get_closest_level(utente.livello)
            my_level_idx = levels.index(my_level_char)
        except:
            pass
            
        if my_level_idx != -1 and my_level_idx != level_idx:
             nav_levels_row.append(types.InlineKeyboardButton("🎯", callback_data=f"char_nav|{my_level_idx}|0"))
        
        # Next Level
        # Check visibility restriction for next button
        can_go_next = False
        if level_idx < len(levels) - 1:
            next_level_val = levels[level_idx+1]
            if is_admin or next_level_val <= utente.livello:
                can_go_next = True
        
        if can_go_next:
             nav_levels_row.append(types.InlineKeyboardButton("⬆️", callback_data=f"char_nav|{level_idx+1}|0"))
        
        # +5 Levels
        can_go_fast_next = False
        if level_idx < len(levels) - 5:
            next_5_val = levels[level_idx+5]
            if is_admin or next_5_val <= utente.livello:
                can_go_fast_next = True
                
        if can_go_fast_next:
             nav_levels_row.append(types.InlineKeyboardButton("⏩ +5", callback_data=f"char_nav|{level_idx+5}|0"))
             
        markup.row(*nav_levels_row)
        
        # Row 2: Left (Char -) | Info | Right (Char +)
        nav_char_row = []
        if char_idx > 0:
            nav_char_row.append(types.InlineKeyboardButton("◀️", callback_data=f"char_nav|{level_idx}|{char_idx-1}"))
        else:
            nav_char_row.append(types.InlineKeyboardButton("⏺️", callback_data="ignore"))
            
        nav_char_row.append(types.InlineKeyboardButton(f"Lv {current_level}", callback_data="ignore"))
        
        if char_idx < len(level_chars) - 1:
            nav_char_row.append(types.InlineKeyboardButton("▶️", callback_data=f"char_nav|{level_idx}|{char_idx+1}"))
        else:
            nav_char_row.append(types.InlineKeyboardButton("⏺️", callback_data="ignore"))
            
        markup.row(*nav_char_row)
        
        if is_unlocked:
            if not is_equipped:
                markup.add(types.InlineKeyboardButton("✅ Equipaggia", callback_data=f"char_select|{char.id}"))
            else:
                markup.add(types.InlineKeyboardButton("⭐ Già Equipaggiato", callback_data="char_already_equipped"))
        elif char.lv_premium == 2 and char.price > 0:
             markup.add(types.InlineKeyboardButton(f"🛒 Compra ({price} 🍑)", callback_data=f"char_buy|{char.id}"))
        
        # Send image if available
        image_data = get_character_image(char, is_locked=not is_unlocked)
        if image_data:
            self.bot.send_photo(self.chatid, image_data, caption=msg, reply_markup=markup, parse_mode='markdown')
        else:
            self.bot.send_message(self.chatid, msg, reply_markup=markup, parse_mode='markdown')


    def handle_shop_characters(self):
        utente = user_service.get_user(self.chatid)
        purchasable = character_service.get_purchasable_characters()
        
        # Filter out owned
        available = character_service.get_available_characters(utente)
        owned_ids = [c.id for c in available]
        
        markup = types.ReplyKeyboardMarkup()
        count = 0
        for char in purchasable:
            if char.id not in owned_ids:
                markup.add(f"{char.nome} ({char.price} 🍑)")
                count += 1
        
        markup.add("🔙 Indietro")
        
        if count == 0:
            self.bot.reply_to(self.message, "Hai già acquistato tutti i personaggi disponibili!", reply_markup=get_start_markup(self.chatid))
        else:
            msg = self.bot.reply_to(self.message, f"Benvenuto nel Negozio Personaggi!\nHai {utente.points} {PointsName}.\nScegli chi acquistare:", reply_markup=markup)
            self.bot.register_next_step_handler(msg, self.process_buy_character)

    def process_buy_character(self, message):
        if message.text == "🔙 Indietro":
            self.bot.reply_to(message, "Menu principale", reply_markup=get_start_markup(self.chatid))
            return

        text = message.text
        # Extract name (remove price)
        if "(" in text:
            char_name = text.split(" (")[0]
        else:
            char_name = text
            
        utente = user_service.get_user(self.chatid)
        session = user_service.db.get_session()
        from models.system import Livello
        char = session.query(Livello).filter_by(nome=char_name).first()
        session.close()
        
        if char:
            success, msg = character_service.purchase_character(utente, char.id)
            if success:
                self.bot.reply_to(message, f"🎉 {msg}", reply_markup=get_start_markup(self.chatid))
            else:
                self.bot.reply_to(message, f"⛔ {msg}")
                # Re-show shop
                self.handle_shop_characters()
        else:
            self.bot.reply_to(message, "Personaggio non trovato.")
            self.handle_shop_characters()

    def handle_all_commands(self):
        message = self.message
        utente = user_service.get_user(self.chatid)
        
        if message.chat.type == "private":
            for command, handler in self.comandi_privati.items():
                if command.lower() in message.text.lower():
                    handler()
                    return

        if utente and user_service.is_admin(utente):
            for command, handler in self.comandi_admin.items():
                if command.lower() in message.text.lower():
                    handler()
                    return

        for command, handler in self.comandi_generici.items():
            if command.lower() in message.text.lower():
                handler()
                return

@bot.message_handler(content_types=util.content_type_media)
def any(message):
    # Check Sunday, etc.
    utente = user_service.get_user(message.from_user.id)
    if not utente:
        user_service.create_user(message.from_user.id, message.from_user.username, message.from_user.first_name, message.from_user.last_name)
        utente = user_service.get_user(message.from_user.id)
    
    # Sunday reset removed - characters persist
    
    # Sunday bonus: 10 Wumpa when you write on Sunday
    import datetime
    if datetime.datetime.today().weekday() == 6:  # Sunday
        session = user_service.db.get_session()
        from models.system import Domenica
        
        today = datetime.date.today()
        sunday_bonus = session.query(Domenica).filter_by(utente=utente.id_telegram).first()
        
        if not sunday_bonus or sunday_bonus.last_day != today:
            # Give Sunday bonus
            user_service.add_points(utente, 10)
            
            # Update or create record
            if sunday_bonus:
                sunday_bonus.last_day = today
            else:
                sunday_bonus = Domenica(utente=utente.id_telegram, last_day=today)
                session.add(sunday_bonus)
            
            session.commit()
            bot.send_message(message.chat.id, "🎉 Bonus Domenicale! Hai ricevuto 10 🍑 Wumpa Fruits!")
        
        session.close()
    
    # Random exp
    if message.chat.type in ['group', 'supergroup']:
        user_service.add_exp(utente, 1)
        
        # Check TNT timer first (if user is avoiding TNT)
        drop_service.check_tnt_timer(utente, bot, message)
        
        # Random drops: TNT, Nitro, Cassa
        drop_service.maybe_drop(utente, bot, message)
        
        # Random Mob Spawn (0.5% chance per message)
        if random.random() < 0.005:
            mob_id = pve_service.spawn_daily_mob()
            if mob_id:
                mob = pve_service.get_current_mob_status()
                if mob:
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton("⚔️ Attacca", callback_data="attack_mob"), 
                               types.InlineKeyboardButton("✨ Attacco Speciale", callback_data="special_attack_mob"))
                    
                    bot.send_message(message.chat.id, f"⚠️ Un {mob['name']} selvatico è apparso!\n❤️ Salute: {mob['health']}/{mob['max_health']} HP\n⚔️ Danno: {mob['attack']}\n\nSconfiggilo per ottenere ricompense!", reply_markup=markup)
                    
                    # Immediate attack on the user who triggered it
                    pve_service.mob_random_attack() # This picks random user, maybe should target 'utente'
                    # Let's make it target the user who sent the message
                    damage = mob['attack']
                    user_service.damage_health(utente, damage)
                    bot.send_message(message.chat.id, f"💥 {mob['name']} ha sorpreso @{utente.username if utente.username else utente.nome} infliggendo {damage} danni!")

    bothandler = BotCommands(message, bot)
    bothandler.handle_all_commands()

@bot.callback_query_handler(func=lambda call: True)
def handle_inline_buttons(call):
    action = call.data
    user_id = call.from_user.id
    utente = user_service.get_user(user_id)
    
    # NEW HANDLERS - Character Selection & Stats
    if action.startswith("char_nav|"):
        parts = action.split("|")
        # char_nav|level_index|char_index
        level_idx = int(parts[1])
        char_idx = int(parts[2])
        
        utente = user_service.get_user(user_id)
        is_admin = user_service.is_admin(utente)
        
        levels = character_service.get_character_levels()
        
        # Validate level index
        if level_idx < 0: level_idx = 0
        if level_idx >= len(levels): level_idx = len(levels) - 1
        
        current_level = levels[level_idx]
        
        # Check visibility restriction
        if not is_admin and current_level > utente.livello:
            # Revert to max allowed level
            valid_levels = [l for l in levels if l <= utente.livello]
            if valid_levels:
                current_level = valid_levels[-1]
                level_idx = levels.index(current_level)
            else:
                level_idx = 0
                current_level = levels[0]
        
        level_chars = character_service.get_characters_by_level(current_level)
        
        # Validate char index
        if char_idx < 0: char_idx = 0
        if char_idx >= len(level_chars): char_idx = len(level_chars) - 1
        
        char = level_chars[char_idx]
        
        is_unlocked = character_service.is_character_unlocked(utente, char.id)
        is_equipped = (utente.livello_selezionato == char.id)
        
        # Format character card
        lock_icon = "" if is_unlocked else "🔒 "
        saga_info = f"[{char.character_group}] " if char.character_group else ""
        type_info = f" ({char.elemental_type})" if char.elemental_type else ""
        msg = f"**{lock_icon}{saga_info}{char.nome}{type_info}**"
        
        if is_equipped:
            msg += " ⭐ *EQUIPAGGIATO*"
        
        msg += "\n\n"
        msg += f"📊 Livello Richiesto: {char.livello}\n"
        
        if char.lv_premium == 1:
            msg += f"👑 Richiede Premium\n"
        elif char.lv_premium == 2 and char.price > 0:
            price = char.price
            if utente.premium == 1:
                price = int(price * 0.5)
            msg += f"💰 Prezzo: {price} {PointsName}"
            if utente.premium == 1:
                msg += f" ~~{char.price}~~"
            msg += "\n"
        
        if char.special_attack_name:
            msg += f"\n✨ **Abilità Speciale:**\n"
            msg += f"🔮 {char.special_attack_name}\n"
            msg += f"⚔️ Danno: {char.special_attack_damage}\n"
            msg += f"💙 Costo Mana: {char.special_attack_mana_cost}\n"
        
        if char.description:
            msg += f"\n📝 {char.description}\n"
        
        if not is_unlocked:
            msg += "\n🔒 **PERSONAGGIO BLOCCATO**\n"
            if char.livello > utente.livello:
                msg += f"Raggiungi livello {char.livello} per sbloccarlo!\n"
            elif char.lv_premium == 1:
                msg += "Richiede abbonamento Premium!\n"
        
        msg += f"\n📄 Livello {level_idx + 1}/{len(levels)} - Personaggio {char_idx + 1}/{len(level_chars)}"
        
        markup = types.InlineKeyboardMarkup()
        
        nav_levels_row = []
        
        # -5 Levels
        if level_idx >= 5:
             nav_levels_row.append(types.InlineKeyboardButton("⏪ -5", callback_data=f"char_nav|{level_idx-5}|0"))
        
        # Prev Level
        if level_idx > 0:
             nav_levels_row.append(types.InlineKeyboardButton("⬇️", callback_data=f"char_nav|{level_idx-1}|0"))
             
        # My Level Button
        my_level_idx = -1
        try:
            my_level_char = character_service.get_closest_level(utente.livello)
            my_level_idx = levels.index(my_level_char)
        except:
            pass
            
        if my_level_idx != -1 and my_level_idx != level_idx:
             nav_levels_row.append(types.InlineKeyboardButton("🎯", callback_data=f"char_nav|{my_level_idx}|0"))
        
        # Next Level
        can_go_next = False
        if level_idx < len(levels) - 1:
            next_level_val = levels[level_idx+1]
            if is_admin or next_level_val <= utente.livello:
                can_go_next = True
        
        if can_go_next:
             nav_levels_row.append(types.InlineKeyboardButton("⬆️", callback_data=f"char_nav|{level_idx+1}|0"))
        
        # +5 Levels
        can_go_fast_next = False
        if level_idx < len(levels) - 5:
            next_5_val = levels[level_idx+5]
            if is_admin or next_5_val <= utente.livello:
                can_go_fast_next = True
                
        if can_go_fast_next:
             nav_levels_row.append(types.InlineKeyboardButton("⏩ +5", callback_data=f"char_nav|{level_idx+5}|0"))
             
        markup.row(*nav_levels_row)
        
        # Row 2: Left (Char -) | Info | Right (Char +)
        nav_char_row = []
        if char_idx > 0:
            nav_char_row.append(types.InlineKeyboardButton("◀️", callback_data=f"char_nav|{level_idx}|{char_idx-1}"))
        else:
            nav_char_row.append(types.InlineKeyboardButton("⏺️", callback_data="ignore"))
            
        nav_char_row.append(types.InlineKeyboardButton(f"Lv {current_level}", callback_data="ignore"))
        
        if char_idx < len(level_chars) - 1:
            nav_char_row.append(types.InlineKeyboardButton("▶️", callback_data=f"char_nav|{level_idx}|{char_idx+1}"))
        else:
            nav_char_row.append(types.InlineKeyboardButton("⏺️", callback_data="ignore"))
            
        markup.row(*nav_char_row)
        
        if is_unlocked:
            if not is_equipped:
                markup.add(types.InlineKeyboardButton("✅ Equipaggia", callback_data=f"char_select|{char.id}"))
            else:
                markup.add(types.InlineKeyboardButton("⭐ Già Equipaggiato", callback_data="char_already_equipped"))
        elif char.lv_premium == 2 and char.price > 0:
             markup.add(types.InlineKeyboardButton(f"🛒 Compra ({price} 🍑)", callback_data=f"char_buy|{char.id}"))
        
        # Send image if available
        image_data = get_character_image(char, is_locked=not is_unlocked)
        
        try:
            if image_data:
                media = types.InputMediaPhoto(image_data, caption=msg, parse_mode='markdown')
                bot.edit_message_media(media=media, chat_id=user_id, message_id=call.message.message_id, reply_markup=markup)
            else:
                # Fallback if no image
                bot.delete_message(user_id, call.message.message_id)
                bot.send_message(user_id, msg, reply_markup=markup, parse_mode='markdown')
                
        except Exception as e:
            print(f"Error editing message media: {e}")
            try:
                bot.delete_message(user_id, call.message.message_id)
                if image_data:
                     bot.send_photo(user_id, image_data, caption=msg, reply_markup=markup, parse_mode='markdown')
                else:
                     bot.send_message(user_id, msg, reply_markup=markup, parse_mode='markdown')
            except Exception as e2:
                print(f"Error in fallback send: {e2}")

        bot.answer_callback_query(call.id)
        return
    
    elif action.startswith("char_filter|"):
        filter_value = action.split("|")[1]
        level_filter = None if filter_value == "all" else int(filter_value)
        
        # Show first page with filter
        page_chars, total_pages, current_page = character_service.get_all_characters_paginated(utente, page=0, level_filter=level_filter)
        
        if not page_chars:
            bot.answer_callback_query(call.id, f"Nessun personaggio di livello {filter_value}!")
            return
        
        char = page_chars[0]
        is_unlocked = character_service.is_character_unlocked(utente, char.id)
        is_equipped = (utente.livello_selezionato == char.id)
        
        # Format character card (same as above)
        lock_icon = "" if is_unlocked else "🔒 "
        msg = f"**{lock_icon}{char.nome}**"
        
        if is_equipped:
            msg += " ⭐ *EQUIPAGGIATO*"
        
        msg += "\n\n"
        msg += f"📊 Livello Richiesto: {char.livello}\n"
        
        if char.lv_premium == 1:
            msg += f"👑 Richiede Premium\n"
        elif char.lv_premium == 2 and char.price > 0:
            price = char.price
            if utente.premium == 1:
                price = int(price * 0.5)
            msg += f"💰 Prezzo: {price} {PointsName}"
            if utente.premium == 1:
                msg += f" ~~{char.price}~~"
            msg += "\n"
        
        if char.special_attack_name:
            msg += f"\n✨ **Abilità Speciale:**\n"
            msg += f"🔮 {char.special_attack_name}\n"
            msg += f"⚔️ Danno: {char.special_attack_damage}\n"
            msg += f"💙 Costo Mana: {char.special_attack_mana_cost}\n"
        
        if char.description:
            msg += f"\n📝 {char.description}\n"
        
        if not is_unlocked:
            msg += "\n🔒 **PERSONAGGIO BLOCCATO**\n"
            if char.livello > utente.livello:
                msg += f"Raggiungi livello {char.livello} per sbloccarlo!\n"
            elif char.lv_premium == 1:
                msg += "Richiede abbonamento Premium!\n"
        
        msg += f"\n📄 Personaggio {current_page + 1} di {total_pages}"
        
        markup = types.InlineKeyboardMarkup()
        
        levels = character_service.get_character_levels()
        level_row = [types.InlineKeyboardButton("🔄 Tutti", callback_data="char_filter|all")]
        for level in levels[:5]:
            level_row.append(types.InlineKeyboardButton(f"Lv{level}", callback_data=f"char_filter|{level}"))
        markup.row(*level_row)
        
        nav_row = []
        if total_pages > 1:
            nav_row.append(types.InlineKeyboardButton("◀️", callback_data=f"char_page|{level_filter or 0}|{max(0, current_page - 1)}"))
        nav_row.append(types.InlineKeyboardButton(f"{current_page + 1}/{total_pages}", callback_data="char_page_info"))
        if total_pages > 1:
            nav_row.append(types.InlineKeyboardButton("▶️", callback_data=f"char_page|{level_filter or 0}|{min(total_pages - 1, current_page + 1)}"))
        
        markup.row(*nav_row)
        
        if is_unlocked:
            if not is_equipped:
                markup.add(types.InlineKeyboardButton("✅ Equipaggia questo personaggio", callback_data=f"char_select|{char.id}"))
            else:
                markup.add(types.InlineKeyboardButton("⭐ Già Equipaggiato", callback_data="char_already_equipped"))
        else:
            if char.lv_premium == 2 and char.price > 0:
                price = char.price
                if utente.premium == 1:
                    price = int(price * 0.5)
                markup.add(types.InlineKeyboardButton(f"🔓 Sblocca ({price} 🍑)", callback_data=f"char_buy|{char.id}"))
        
        bot.edit_message_text(msg, user_id, call.message.message_id, reply_markup=markup, parse_mode='markdown')
        bot.answer_callback_query(call.id, f"Filtrando per {'tutti i livelli' if filter_value == 'all' else f'livello {filter_value}'}")
        return
    
    elif action.startswith("char_buy|"):
        char_id = int(action.split("|")[1])
        
        success, msg = character_service.purchase_character(utente, char_id)
        
        if success:
            bot.answer_callback_query(call.id, "✅ Personaggio acquistato!")
            # Send confirmation message
            bot.send_message(user_id, f"🎉 {msg}\n\nOra puoi equipaggiarlo dalla selezione personaggi!", reply_markup=get_start_markup(user_id))
            
            # Refresh the current view to show it as unlocked
            # We can reuse the char_page logic to reload the current character card
            # Or just delete and resend the updated card
            try:
                # Get character info again
                session = user_service.db.get_session()
                from models.system import Livello
                char = session.query(Livello).filter_by(id=char_id).first()
                session.close()
                
                if char:
                    # Construct unlocked message (simplified version of handle_inline_buttons logic)
                    lock_icon = "" 
                    new_msg = f"**{lock_icon}{char.nome}**\n\n"
                    new_msg += f"📊 Livello Richiesto: {char.livello}\n"
                    
                    if char.special_attack_name:
                        new_msg += f"\n✨ **Abilità Speciale:**\n🔮 {char.special_attack_name}\n⚔️ Danno: {char.special_attack_damage}\n💙 Costo Mana: {char.special_attack_mana_cost}\n"
                    
                    if char.description:
                        new_msg += f"\n📝 {char.description}\n"
                        
                    # Add navigation info if possible, or just leave it clean
                    # Ideally we should call the pagination logic again, but we don't have page info here easily
                    # So let's just show the card with "Equip" button
                    
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton("✅ Equipaggia questo personaggio", callback_data=f"char_select|{char.id}"))
                    markup.add(types.InlineKeyboardButton("🔙 Torna alla lista", callback_data="char_page|0|0")) # Reset to first page
                    
                    # Update the message
                    image_data = get_character_image(char, is_locked=False)
                    if image_data:
                        media = types.InputMediaPhoto(image_data, caption=new_msg, parse_mode='markdown')
                        bot.edit_message_media(media=media, chat_id=user_id, message_id=call.message.message_id, reply_markup=markup)
                    else:
                        bot.edit_message_text(new_msg, user_id, call.message.message_id, reply_markup=markup, parse_mode='markdown')
                        
            except Exception as e:
                print(f"Error refreshing after purchase: {e}")
                
        else:
            bot.answer_callback_query(call.id, f"❌ {msg}", show_alert=True)
        return
    
    elif action == "char_already_equipped":
        bot.answer_callback_query(call.id, "⭐ Questo personaggio è già equipaggiato!")
        return
    
    elif action == "char_page_info":
        bot.answer_callback_query(call.id, "Usa le frecce per navigare")
        return
    
    elif action.startswith("char_select|"):
        char_id = int(action.split("|")[1])
        
        success, msg = character_service.equip_character(utente, char_id)
        
        if success:
            bot.answer_callback_query(call.id, "✅ Personaggio equipaggiato!")
            bot.send_message(user_id, f"✅ {msg}", reply_markup=get_start_markup(user_id))
        else:
            bot.answer_callback_query(call.id, f"❌ {msg}")
        return
    
    elif action == "stats_menu":
        points_info = stats_service.get_available_stat_points(utente)
        
        msg = f"📊 **ALLOCAZIONE STATISTICHE**\n\n"
        msg += f"🎯 Punti Disponibili: {points_info['available']}\n\n"
        msg += f"Scegli dove allocare i tuoi punti:"
        
        markup = types.InlineKeyboardMarkup()
        if points_info['available'] > 0:
            markup.add(types.InlineKeyboardButton(f"❤️ +Vita (+{stats_service.HEALTH_PER_POINT} HP max)", callback_data="stat_alloc|health"))
            markup.add(types.InlineKeyboardButton(f"💙 +Mana (+{stats_service.MANA_PER_POINT} mana max)", callback_data="stat_alloc|mana"))
            markup.add(types.InlineKeyboardButton(f"⚔️ +Danno (+{stats_service.DAMAGE_PER_POINT} danno)", callback_data="stat_alloc|damage"))
        else:
            msg += "\n\n⚠️ Non hai punti disponibili!"
        
        bot.edit_message_text(msg, user_id, call.message.message_id, reply_markup=markup, parse_mode='markdown')
        bot.answer_callback_query(call.id)
        return
    
    elif action.startswith("stat_alloc|"):
        stat_type = action.split("|")[1]
        
        success, msg = stats_service.allocate_stat_point(utente, stat_type)
        
        bot.answer_callback_query(call.id, msg if success else f"❌ {msg}")
        
        if success:
            # Refresh stats menu
            utente = user_service.get_user(user_id)  # Refresh user data
            points_info = stats_service.get_available_stat_points(utente)
            
            msg = f"📊 **ALLOCAZIONE STATISTICHE**\n\n"
            msg += f"🎯 Punti Disponibili: {points_info['available']}\n\n"
            msg += f"Scegli dove allocare i tuoi punti:"
            
            markup = types.InlineKeyboardMarkup()
            if points_info['available'] > 0:
                markup.add(types.InlineKeyboardButton(f"❤️ +Vita (+{stats_service.HEALTH_PER_POINT} HP max)", callback_data="stat_alloc|health"))
                markup.add(types.InlineKeyboardButton(f"💙 +Mana (+{stats_service.MANA_PER_POINT} mana max)", callback_data="stat_alloc|mana"))
                markup.add(types.InlineKeyboardButton(f"⚔️ +Danno (+{stats_service.DAMAGE_PER_POINT} danno)", callback_data="stat_alloc|damage"))
            else:
                msg += "\n\n⚠️ Non hai punti disponibili!"
            
            bot.edit_message_text(msg, user_id, call.message.message_id, reply_markup=markup, parse_mode='markdown')
        return
    
    elif action.startswith("reset_stats"):
        if action == "reset_stats_confirm":
            msg = f"⚠️ **CONFERMA RESET STATISTICHE**\n\n"
            msg += f"Vuoi davvero resettare tutte le statistiche allocate?\n"
            msg += f"Costo: {stats_service.RESET_COST} {PointsName}\n\n"
            msg += f"Tutti i punti allocati verranno restituiti."
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✅ Sì, Reset", callback_data="reset_stats_yes"))
            markup.add(types.InlineKeyboardButton("❌ Annulla", callback_data="reset_stats_no"))
            
            bot.edit_message_text(msg, user_id, call.message.message_id, reply_markup=markup, parse_mode='markdown')
            bot.answer_callback_query(call.id)
        
        elif action == "reset_stats_yes":
            success, msg = stats_service.reset_stat_points(utente)
            bot.answer_callback_query(call.id, "✅ Reset completato!" if success else f"❌ Errore")
            bot.send_message(user_id, msg)
        
        elif action == "reset_stats_no":
            bot.answer_callback_query(call.id, "Reset annullato")
            bot.delete_message(user_id, call.message.message_id)
        return
    
    elif action == "transform_menu":
        transformations = transformation_service.get_available_transformations(utente)
        active_trans = transformation_service.get_active_transformation(utente)
        
        msg = f"✨ **TRASFORMAZIONI**\n\n"
        
        if active_trans:
            time_left = active_trans['expires_at'] - datetime.datetime.now()
            hours_left = int(time_left.total_seconds() / 3600)
            msg += f"🔥 Trasformazione Attiva: {active_trans['name']}\n"
            msg += f"⏰ Scade tra: {hours_left}h\n\n"
        
        if transformations:
            msg += "**Trasformazioni Disponibili:**\n\n"
            markup = types.InlineKeyboardMarkup()
            
            for trans in transformations:
                status = "✅" if trans['can_activate'] else "🔒"
                btn_text = f"{status} {trans['name']} ({trans['wumpa_cost']} 🍑)"
                
                if trans['can_activate']:
                    markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"transform|{trans['id']}"))
                else:
                    markup.add(types.InlineKeyboardButton(btn_text, callback_data="transform_locked"))
            
            bot.edit_message_text(msg, user_id, call.message.message_id, reply_markup=markup, parse_mode='markdown')
        else:
            msg += "Nessuna trasformazione disponibile per questo personaggio."
            bot.edit_message_text(msg, user_id, call.message.message_id, parse_mode='markdown')
        
        bot.answer_callback_query(call.id)
        return
    
    elif action == "transform_locked":
        bot.answer_callback_query(call.id, "🔒 Non puoi attivare questa trasformazione!")
        return
    
    elif action.startswith("transform|"):
        trans_id = int(action.split("|")[1])
        
        success, msg = transformation_service.activate_transformation(utente, trans_id)
        
        bot.answer_callback_query(call.id, "✨ Trasformazione attivata!" if success else f"❌ Errore")
        bot.send_message(user_id, msg, parse_mode='markdown')
        return
    
    elif action.startswith("buy_potion|"):
        parts = action.split("|")
        potion_name = parts[1]
        
        utente = user_service.get_user(user_id)
        
        from services.potion_service import PotionService
        potion_service = PotionService()
        
        success, msg = potion_service.buy_potion(utente, potion_name)
        
        if success:
            bot.answer_callback_query(call.id, "✅ Acquisto effettuato!")
            bot.send_message(user_id, f"🛍️ {msg}\n\nPuoi usare la pozione dal tuo 📦 Inventario.")
        else:
            bot.answer_callback_query(call.id, f"❌ {msg}", show_alert=True)
        return

    elif action == "attack_mob":
        utente = user_service.get_user(user_id)
        damage = random.randint(10, 30) + utente.base_damage
        
        # Check for luck boost
        if utente.luck_boost > 0:
             damage *= 2
             user_service.update_user(user_id, {'luck_boost': 0})
        
        success, msg = pve_service.attack_mob(utente, damage)
        
        # Update message if possible, or send new one
        # For simplicity, send new message or alert
        if success:
            bot.answer_callback_query(call.id, "⚔️ Attacco effettuato!")
            
            # Check if mob is dead to update the message properly
            if "Hai ucciso" in msg:
                 bot.send_message(call.message.chat.id, f"@{utente.username if utente.username else utente.nome} {msg}")
            else:
                 # Just show alert or small message to avoid spam
                 # bot.send_message(call.message.chat.id, f"@{utente.username} {msg}")
                 # Better: update the mob status message if we could track it, but for now just send text
                 bot.send_message(call.message.chat.id, f"@{utente.username if utente.username else utente.nome} {msg}")
        else:
            bot.answer_callback_query(call.id, msg, show_alert=True)
        return

    elif action == "special_attack_mob":
        utente = user_service.get_user(user_id)
        success, msg = pve_service.use_special_attack(utente, target_type="mob")
        
        if success:
            bot.answer_callback_query(call.id, "✨ Attacco Speciale effettuato!")
            bot.send_message(call.message.chat.id, f"@{utente.username if utente.username else utente.nome} {msg}")
        else:
            bot.answer_callback_query(call.id, msg, show_alert=True)
        return
    
    elif action == "attack_raid":
        utente = user_service.get_user(user_id)
        damage = random.randint(10, 30) + utente.base_damage
        
        if utente.luck_boost > 0:
             damage *= 2
             user_service.update_user(user_id, {'luck_boost': 0})
        
        success, msg = pve_service.attack_raid_boss(utente, damage)
        
        if success:
            bot.answer_callback_query(call.id, "⚔️ Attacco Raid effettuato!")
            if "sconfitto" in msg:
                 bot.send_message(call.message.chat.id, f"@{utente.username if utente.username else utente.nome} {msg}")
            else:
                 # Optional: update message
                 pass
        else:
            bot.answer_callback_query(call.id, msg, show_alert=True)
        return

    elif action == "special_attack_raid":
        utente = user_service.get_user(user_id)
        success, msg = pve_service.use_special_attack(utente, target_type="raid")
        
        if success:
            bot.answer_callback_query(call.id, "✨ Attacco Speciale Raid effettuato!")
            bot.send_message(call.message.chat.id, f"@{utente.username if utente.username else utente.nome} {msg}")
        else:
            bot.answer_callback_query(call.id, msg, show_alert=True)
        return
    
    # EXISTING HANDLERS BELOW
    if action.startswith("use|"):
        item_name = action.split("|")[1]
        # Use item logic
        if item_service.use_item(user_id, item_name):
            msg = item_service.apply_effect(utente, item_name)
            bot.send_message(user_id, msg)
        else:
            bot.send_message(user_id, "Non hai questo oggetto o è già stato usato.")

    elif action.startswith("sg|"):
        # Show game details / send game
        game_title = action.split("|")[1]
        session = game_service.db.get_session()
        from models.game import GameInfo
        game = session.query(GameInfo).filter_by(title=game_title).first()
        session.close()
        
        if game:
            # Simulate sending the game file or link
            bot.send_message(user_id, f"🎮 Ecco a te {game.title}!\n\nLink: {game.message_link}\n\nBuon divertimento!")
        else:
            bot.send_message(user_id, "Gioco non trovato.")

    elif action.startswith("invoke|"):
        # Invoke dragon from inventory
        dragon = action.split("|")[1]
        has_shenron, has_porunga = wish_service.check_dragon_balls(utente)
        
        if dragon == "shenron" and has_shenron:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(f"💰 {PointsName} (300-500)", callback_data="wish|Shenron|wumpa"))
            markup.add(types.InlineKeyboardButton("⭐ EXP (300-500)", callback_data="wish|Shenron|exp"))
            bot.send_message(user_id, "🐉 Shenron è stato evocato!\n\nEsprimi il tuo desiderio!", reply_markup=markup)
        elif dragon == "porunga" and has_porunga:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(f"💰 {PointsName} (50-100)", callback_data="pwish|1|wumpa"))
            markup.add(types.InlineKeyboardButton("🎁 Oggetto Raro", callback_data="pwish|1|item"))
            bot.send_message(user_id, "🐲 Porunga è stato evocato!\n\nEsprimi 3 desideri!\n\n[Desiderio 1/3]", reply_markup=markup)
        else:
            bot.send_message(user_id, "❌ Non hai le sfere necessarie!")

    elif action.startswith("wish|"):
        # Shenron wish
        parts = action.split("|")
        dragon = parts[1]
        wish = parts[2]
        
        msg = wish_service.grant_wish(utente, wish, dragon)
        bot.send_message(user_id, msg)
        bot.answer_callback_query(call.id, "Desiderio esaudito!")

    elif action.startswith("pwish|"):
        # Porunga wish (multi-step)
        parts = action.split("|")
        wish_number = int(parts[1])
        wish_choice = parts[2]
        
        # Grant this wish
        msg = wish_service.grant_porunga_wish(utente, wish_choice, wish_number)
        
        # Check if there are more wishes
        if wish_number < 3:
            # Show next wish options
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(f"💰 {PointsName} (50-100)", callback_data=f"pwish|{wish_number+1}|wumpa"))
            markup.add(types.InlineKeyboardButton("🎁 Oggetto Raro", callback_data=f"pwish|{wish_number+1}|item"))
            bot.send_message(user_id, f"{msg}\n\n[Desiderio {wish_number+1}/3]", reply_markup=markup)
        else:
            # Final wish
            # Consume spheres now
            for i in range(1, 8):
                item_service.use_item(user_id, f"La Sfera del Drago Porunga {i}")
            bot.send_message(user_id, f"{msg}\n\n🐲 PORUNGA HA ESAUDITO I TUOI 3 DESIDERI!")
        
        bot.answer_callback_query(call.id)

def bot_polling_thread():
    bot.infinity_polling()

def spawn_daily_mob_job():
    # Random check to spawn between 9 and 18
    now = datetime.datetime.now()
    if 9 <= now.hour <= 18:
        # 10% chance every check (if run every hour? or minute?)
        # Let's assume this runs every hour.
        if random.random() < 0.2: 
            mob_id = pve_service.spawn_daily_mob()
            if mob_id:
                mob = pve_service.get_current_mob_status()
                if mob:
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton("⚔️ Attacca", callback_data="attack_mob"), 
                               types.InlineKeyboardButton("✨ Attacco Speciale", callback_data="special_attack_mob"))
                    
                    bot.send_message(GRUPPO_AROMA, f"⚠️ Un {mob['name']} selvatico è apparso!\n❤️ Salute: {mob['health']}/{mob['max_health']} HP\n⚔️ Danno: {mob['attack']}\n\nSconfiggilo per ottenere ricompense!", reply_markup=markup)

def spawn_weekly_raid_job():
    raid_id = pve_service.spawn_raid_boss()
    if raid_id:
        raid = pve_service.get_current_raid_status()
        if raid:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("⚔️ Attacca Raid", callback_data="attack_raid"), 
                       types.InlineKeyboardButton("✨ Attacco Speciale Raid", callback_data="special_attack_raid"))
            
            bot.send_message(GRUPPO_AROMA, f"☠️ **IL RAID BOSS {raid['name']} È ARRIVATO!**\n\n❤️ Salute: {raid['health']}/{raid['max_health']} HP\n⚔️ Danno: {raid['attack']}\n📜 {raid['description']}\n\nUNITI PER SCONFIGGERLO!", reply_markup=markup, parse_mode='markdown')

if __name__ == "__main__":
    polling_thread = threading.Thread(target=bot_polling_thread)
    polling_thread.start()
    
    # Schedule jobs
    schedule.every().hour.do(spawn_daily_mob_job)
    schedule.every(10).minutes.do(lambda: pve_service.mob_random_attack() if pve_service.get_current_mob_status() else None)
    schedule.every().sunday.at("20:00").do(spawn_weekly_raid_job)
    
    # Sunday reset removed - characters persist permanently
    # Sunday reset removed - characters persist permanently
    
    while True:
        schedule.run_pending()
        time.sleep(1)
