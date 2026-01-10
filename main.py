from telebot import types, util
from settings import *
import schedule
import time
import threading
import datetime
import os
import random
import socket
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

# Track last viewed character for admins (for image upload feature)
admin_last_viewed_character = {}

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

@bot.message_handler(commands=['achievements', 'ach'])
def handle_achievements_cmd(message, page=0):
    """Show user achievements with pagination"""
    user_id = message.from_user.id
    
    from services.achievement_tracker import AchievementTracker
    tracker = AchievementTracker()
    
    stats = tracker.get_achievement_stats(user_id)
    all_achievements = tracker.get_all_achievements_with_progress(user_id)
    
    # Sort: Unlocked first, then by tier, then by name
    tier_map = {'bronze': 1, 'silver': 2, 'gold': 3, 'platinum': 4}
    all_achievements.sort(key=lambda x: (not x['is_completed'], -tier_map.get(x['achievement'].tier, 0), x['achievement'].name))
    
    ITEMS_PER_PAGE = 5
    total_pages = (len(all_achievements) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    
    if total_pages == 0:
        bot.reply_to(message, "Nessun achievement disponibile.")
        return

    if page >= total_pages: page = total_pages - 1
    if page < 0: page = 0
    
    start_idx = page * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    page_items = all_achievements[start_idx:end_idx]
    
    msg = f"🏆 **I TUOI ACHIEVEMENT** ({stats['completed']}/{stats['total_achievements']})\n"
    msg += f"📊 Progresso: `{stats['completion_rate']:.1f}%` | Punti: `{stats['points_earned']}`\n\n"
    
    for item in page_items:
        a = item['achievement']
        unlocked = item['is_completed']
        progress = item['progress']
        max_progress = a.max_progress
        
        status_emoji = "✅" if unlocked else "🔒"
        tier_emoji = {'bronze': '🥉', 'silver': '🥈', 'gold': '🥇', 'platinum': '💎'}.get(a.tier, "🏆")
        
        msg += f"{status_emoji} {tier_emoji} **{a.name}**\n"
        msg += f"_{a.description}_\n"
        
        if not unlocked:
            # Progress bar
            percent = int((progress / max_progress) * 10) if max_progress > 0 else 0
            bar = "▰" * percent + "▱" * (10 - percent)
            msg += f"[{bar}] `{progress}/{max_progress}`\n"
            msg += f"🎯 *Obiettivo:* {a.description}\n"
        else:
            msg += "✨ *Completato!*\n"
        msg += "\n"
        
    msg += f"📄 Pagina {page + 1} di {total_pages}"
    
    markup = types.InlineKeyboardMarkup()
    buttons = []
    if page > 0:
        buttons.append(types.InlineKeyboardButton("⬅️ Indietro", callback_data=f"ach_page|{page-1}"))
    if page < total_pages - 1:
        buttons.append(types.InlineKeyboardButton("Avanti ➡️", callback_data=f"ach_page|{page+1}"))
    
    if buttons:
        markup.row(*buttons)
        
    # Check if it's a callback or a command
    if hasattr(message, 'message_id') and not hasattr(message, 'text'): # Likely a callback
        bot.edit_message_text(msg, message.chat.id, message.message_id, reply_markup=markup, parse_mode='markdown')
    else:
        bot.reply_to(message, msg, reply_markup=markup, parse_mode='markdown')

@bot.message_handler(commands=['titles', 'titoli'])
def handle_titles_cmd(message):
    """Show user earned titles and allow selection"""
    user_id = message.from_user.id
    utente = user_service.get_user(user_id)
    
    if not utente:
        bot.reply_to(message, "Utente non trovato. Usa /start prima.")
        return
    
    import json
    titles = []
    if hasattr(utente, 'titles') and utente.titles:
        try:
            titles = json.loads(utente.titles)
        except:
            titles = []
    
    if not titles:
        bot.reply_to(message, "Non hai ancora guadagnato nessun titolo! Sblocca achievement per ottenerne.")
        return
    
    msg = "👑 **I TUOI TITOLI**\n\nSeleziona un titolo da mostrare nel tuo profilo:"
    markup = types.InlineKeyboardMarkup()
    
    for title in titles:
        is_active = (utente.title == title)
        label = f"⭐ {title}" if is_active else title
        markup.add(types.InlineKeyboardButton(label, callback_data=f"set_title|{title}"))
    
    bot.reply_to(message, msg, reply_markup=markup, parse_mode='markdown')

@bot.message_handler(commands=['stagione', 'season', 'pass'])
def handle_season_cmd(message, page=0):
    """Show seasonal progression and rewards with pagination"""
    user_id = message.from_user.id
    
    try:
        from services.season_manager import SeasonManager
        manager = SeasonManager()
        
        status = manager.get_season_status(user_id)
        if not status:
            bot.reply_to(message, "Nessuna stagione attiva al momento.")
            return
            
        # Get active season to get all rewards
        season = manager.get_active_season()
        all_rewards = manager.get_all_season_rewards(season.id)
        
        ITEMS_PER_PAGE = 5
        total_pages = (len(all_rewards) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
        
        if page >= total_pages: page = total_pages - 1
        if page < 0: page = 0
        
        start_idx = page * ITEMS_PER_PAGE
        end_idx = start_idx + ITEMS_PER_PAGE
        page_rewards = all_rewards[start_idx:end_idx]
        
        progress = status['progress']
        msg = f"🏆 **{status['season_name']}**\n"
        msg += f"⏰ Scade il: {status['end_date'].strftime('%d/%m/%Y')}\n\n"
        
        msg += f"⭐ **Livello {progress['level']}**\n"
        
        # Progress bar
        exp_per_lv = status['exp_per_level']
        percent = int((progress['exp'] / exp_per_lv) * 10)
        bar = "▰" * percent + "▱" * (10 - percent)
        msg += f"[{bar}] {progress['exp']}/{exp_per_lv} EXP\n\n"
        
        if progress['has_premium']:
            msg += "👑 **Pass Premium Attivo**\n\n"
        else:
            msg += "🆓 **Pass Gratuito** (Usa /premium per sbloccare tutto!)\n\n"
            
        msg += f"🎁 **RICOMPENSE (Pagina {page+1}/{total_pages}):**\n"
        for r in page_rewards:
            type_icon = r.icon or '🎁'
            status_icon = "✅" if progress['level'] >= r.level_required else "🔒"
            premium_tag = "👑 [PREMIUM]" if r.is_premium else "🆓 [FREE]"
            msg += f"{status_icon} • Lv {r.level_required}: {premium_tag} {type_icon} {r.reward_name}\n"
            
        markup = types.InlineKeyboardMarkup()
        
        # Navigation buttons
        nav_buttons = []
        if page > 0:
            nav_buttons.append(types.InlineKeyboardButton("⬅️ Indietro", callback_data=f"season_page|{page-1}"))
        if page < total_pages - 1:
            nav_buttons.append(types.InlineKeyboardButton("Avanti ➡️", callback_data=f"season_page|{page+1}"))
        
        if nav_buttons:
            markup.row(*nav_buttons)
            
        if not progress['has_premium']:
            markup.add(types.InlineKeyboardButton("🛒 Acquista Season Pass (1000 🍑)", callback_data="buy_season_pass"))
        
        if hasattr(message, 'message_id') and not hasattr(message, 'text'): # Callback
            bot.edit_message_text(msg, message.chat.id, message.message_id, reply_markup=markup, parse_mode='markdown')
        else:
            bot.reply_to(message, msg, reply_markup=markup, parse_mode='markdown')
            
    except Exception as e:
        print(f"Error showing season: {e}")
        bot.reply_to(message, "❌ Errore nel caricamento della stagione.")

def get_start_markup(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('📦 Inventario', '📦 Compra Box Wumpa (50 🍑)')
    markup.add('🧪 Negozio Pozioni', '👤 Profilo')
    markup.add('👤 Scegli il personaggio', '💰 Listino & Guida')
    markup.add('🏆 Achievement', '🌟 Stagione')
    markup.add('📄 Classifica', '❓ Aiuto')
    return markup

def get_character_image(character, is_locked=False):
    """Helper to get character image from filesystem"""
    if not character:
        return None
    
    try:
        # Check if character is a dict (from CSV) or object (from DB)
        if isinstance(character, dict):
            char_name_lower = character['nome'].lower().replace(" ", "_")
        else:
            char_name_lower = character.nome.lower().replace(" ", "_")
        
        # Try PNG first, then JPG
        for ext in ['.png', '.jpg', '.jpeg']:
            image_path = f"character_images/{char_name_lower}{ext}"
            if os.path.exists(image_path):
                with open(image_path, 'rb') as img:
                    return img.read()
        
        # Try without saga suffix (e.g., "goku.png" instead of "goku_dragon_ball.png")
        # This is for backward compatibility
        if isinstance(character, dict):
            base_name = character['nome'].split('-')[0].strip().lower().replace(" ", "_")
        else:
            base_name = character.nome.split('-')[0].strip().lower().replace(" ", "_")
            
        for ext in ['.png', '.jpg', '.jpeg']:
            image_path = f"character_images/{base_name}{ext}"
            if os.path.exists(image_path):
                with open(image_path, 'rb') as img:
                    return img.read()
    except Exception as e:
        print(f"Error loading character image: {e}")
    
    return None

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
        
        from services.character_loader import get_character_loader
        char_loader = get_character_loader()
        livello = char_loader.get_character_by_name(character_name)
        print(f"[DEBUG] Character found: {livello is not None}")
        
        if not livello:
            bot.reply_to(message, f"❌ Personaggio '{character_name}' non trovato nel database", reply_markup=get_start_markup(chatid))
            return
        
        # Verify availability again using service
        available = character_service.get_available_characters(utente)
        print(f"[DEBUG] Available characters count: {len(available)}")
        print(f"[DEBUG] Checking if character id {livello['id']} is in available list")
        
        if any(c['id'] == livello['id'] for c in available):
            print(f"[DEBUG] Character is available, updating user")
            user_service.update_user(chatid, {'livello_selezionato': livello['id']})
            
            # Show info/image
            msg_text = f"✅ Personaggio {character_name} equipaggiato!\n"
            if livello.get('special_attack_name'):
                msg_text += f"✨ Skill: {livello['special_attack_name']} ({livello['special_attack_damage']} DMG, {livello['special_attack_mana_cost']} Mana)"
            
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
            "💰 Listino & Guida": self.handle_guide_costs,
            "🏆 Achievement": self.handle_achievements,
            "🌟 Stagione": self.handle_season,
            "🌐 Dashboard Web": self.handle_web_dashboard,
            "📄 Classifica": self.handle_classifica,
        }

        self.comandi_admin = {
            "addLivello": self.handle_add_livello,
            "+": self.handle_plus_minus,
            "-": self.handle_plus_minus,
            "restore": self.handle_restore,
            "backup": self.handle_backup,
            "broadcast": self.handle_broadcast,
            "/spawn": self.handle_spawn_mob,
            "/boss": self.handle_spawn_boss,
            "/kill": self.handle_kill_user,
            "/kill": self.handle_kill_user,
            "/killall": self.handle_kill_all_enemies,
            "/missing_image": self.handle_find_missing_image,
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
- La Domenica alle 20:00 appare un *BOSS* molto potente!

🔹 *COMANDI UTILI*
- `info`: Visualizza le tue statistiche.
- `Nome in Game`: Imposta il tuo nickname di gioco.
- `classifica`: Vedi la top 10.
"""
        self.bot.reply_to(self.message, msg, parse_mode='markdown')

    def handle_guide_costs(self):
        msg = """💰 *LISTINO & GUIDA ACQUISTI* 💰

🎮 *COME COMPRARE GIOCHI*
Per acquistare un gioco che vedi in un canale o gruppo:
1. **Inoltra** il messaggio del gioco a questo bot.
2. Il bot ti scalerà i punti e ti invierà il gioco (e i file successivi).

💎 *COSTI*
🔸 **Gioco da Canale/Inoltro**:
   - Utenti Premium: **50** 🍑
   - Utenti Normali: **150** 🍑

🔸 **Steam Games (Gacha)**:
   - 🥉 Bronze Coin: **200** 🍑 (10% chance)
   - 🥈 Silver Coin: **400** 🍑 (50% chance)
   - 🥇 Gold Coin: **600** 🍑 (100% chance)
   - 🎖 Platinum Coin: **800** 🍑 (Gioco a scelta)

🔸 **Altro**:
   - 📦 Box Wumpa: **50** 🍑
   - 👑 Premium (1 mese): **1000** 🍑
   - 🔄 Reset Stats: **500** 🍑

🌟 *VANTAGGI PREMIUM*
✅ Sconto 50% su Pozioni
✅ Sconto 50% su Personaggi
✅ Sconto su acquisto giochi (50 invece di 150)
✅ Accesso a personaggi esclusivi
✅ Badge "Utente Premium" nel profilo
"""
        self.bot.reply_to(self.message, msg, parse_mode='markdown')

    def handle_spawn_mob(self):
        """Admin command to manually spawn a mob"""
        utente = user_service.get_user(self.chatid)
        if not user_service.is_admin(utente):
            return
            
        mob_id, attack_events = pve_service.spawn_daily_mob()
        if mob_id:
            mob = pve_service.get_current_mob_status()
            if mob:
                # Use new button format with specific mob ID
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("⚔️ Attacca", callback_data=f"attack_enemy|mob|{mob_id}"))
                markup.add(types.InlineKeyboardButton("✨ Attacco Speciale", callback_data=f"special_attack_enemy|mob|{mob_id}"))
                
                msg_text = f"⚠️ Un {mob['name']} selvatico è apparso!\n📊 Lv. {mob.get('level', 1)} | ⚡ Vel: {mob.get('speed', 30)} | 🛡️ Res: {mob.get('resistance', 0)}%\n❤️ Salute: {mob['health']}/{mob['max_health']} HP\n⚔️ Danno: {mob['attack']}"
                
                # Send with image if available
                if mob.get('image') and os.path.exists(mob['image']):
                    try:
                        with open(mob['image'], 'rb') as photo:
                            self.bot.reply_to(self.message, photo, caption=msg_text, reply_markup=markup, )
                    except:
                        self.bot.reply_to(self.message, msg_text, reply_markup=markup)
                else:
                    self.bot.reply_to(self.message, msg_text, reply_markup=markup)
                
                # Send immediate attack messages if any
                if attack_events:
                    for event in attack_events:
                        msg = event['message']
                        image_path = event['image']
                        try:
                            if image_path and os.path.exists(image_path):
                                with open(image_path, 'rb') as photo:
                                    self.bot.send_photo(self.message.chat.id, photo, caption=msg, reply_markup=markup, )
                            else:
                                self.bot.send_message(self.message.chat.id, msg, reply_markup=markup, )
                        except:
                            self.bot.send_message(self.message.chat.id, msg, reply_markup=markup, )
            else:
                self.bot.reply_to(self.message, "Mob spawnato ma impossibile recuperare i dettagli.")
        else:
            self.bot.reply_to(self.message, "Errore nello spawn del mob.")
    
    def handle_spawn_boss(self):
        """Admin command to manually spawn a boss (Mob with is_boss=True)"""
        utente = user_service.get_user(self.chatid)
        if not user_service.is_admin(utente):
            return
        
        # Extract boss name from command if provided
        # Expected format: /boss [boss_name]
        text = self.message.text.strip()
        parts = text.split(maxsplit=1)
        boss_name = parts[1] if len(parts) > 1 else None
        
        success, msg, boss_id = pve_service.spawn_boss(boss_name)
        if success and boss_id:
            boss = pve_service.get_current_boss_status()
            if boss:
                # Create attack buttons
                markup = types.InlineKeyboardMarkup()
                markup.add(
                    types.InlineKeyboardButton("⚔️ Attacca", callback_data=f"attack_enemy|mob|{boss_id}"),
                    types.InlineKeyboardButton("✨ Attacco Speciale", callback_data=f"special_attack_enemy|mob|{boss_id}")
                )
                
                msg_text = f"☠️ **IL BOSS {boss['name']} È ARRIVATO!**\n\n"
                msg_text += f"📊 Lv. {boss.get('level', 5)} | ⚡ Vel: {boss.get('speed', 70)} | 🛡️ Res: {boss.get('resistance', 0)}%\n"
                msg_text += f"❤️ Salute: {boss['health']}/{boss['max_health']} HP\n"
                msg_text += f"⚔️ Danno: {boss['attack']}\n"
                if boss['description']:
                    msg_text += f"📜 {boss['description']}\n"
                msg_text += "\nUNITI PER SCONFIGGERLO!"
                
                # Send with image if available
                if boss.get('image') and os.path.exists(boss['image']):
                    try:
                        with open(boss['image'], 'rb') as photo:
                            self.bot.reply_to(self.message, photo, caption=msg_text, reply_markup=markup, parse_mode='markdown')
                    except:
                        self.bot.reply_to(self.message, msg_text, reply_markup=markup, parse_mode='markdown')
                else:
                    self.bot.reply_to(self.message, msg_text, reply_markup=markup, parse_mode='markdown')
        else:
            self.bot.reply_to(self.message, f"❌ {msg}")
    
    def handle_kill_user(self):
        """dmin command to kill user or enemy. Usage: /kill (reply to user) OR /kill mob|boss [id/name]"""
        utente = user_service.get_user(self.chatid)
        if not user_service.is_admin(utente):
            return
        
        # Parse command
        text = self.message.text.strip()
        parts = text.split(maxsplit=2)
        
        # Check if killing enemy: /kill mob 123 or /kill boss N.Gin
        if len(parts) >= 3:
            target_type = parts[1].lower()
            target_id_or_name = parts[2]
            
            if target_type == "mob":
                from database import Database
                from models.pve import Mob
                db = Database()
                session = db.get_session()
                
                try:
                    mob_id = int(target_id_or_name)
                    mob = session.query(Mob).filter_by(id=mob_id).first()
                except ValueError:
                    mob = session.query(Mob).filter_by(name=target_id_or_name, is_dead=False).first()
                
                if mob:
                    mob.is_dead = True
                    mob.health = 0
                    session.commit()
                    self.bot.reply_to(self.message, f"💀 Mob '{mob.name}' eliminato!")
                else:
                    self.bot.reply_to(self.message, "❌ Mob non trovato!")
                session.close()
                return
                
            elif target_type in ["boss", "raid"]:
                from database import Database
                from models.pve import Mob
                db = Database()
                session = db.get_session()
                
                try:
                    mob_id = int(target_id_or_name)
                    boss = session.query(Mob).filter_by(id=mob_id, is_boss=True).first()
                except ValueError:
                    boss = session.query(Mob).filter_by(name=target_id_or_name, is_boss=True, is_dead=False).first()
                
                if boss:
                    boss.is_dead = True
                    boss.health = 0
                    session.commit()
                    self.bot.reply_to(self.message, f"💀 Boss '{boss.name}' eliminato!")
                else:
                    self.bot.reply_to(self.message, "❌ Boss non trovato!")
                session.close()
                return
        
        # Original: reply to user message to kill user
        if not self.message.reply_to_message:
            self.bot.reply_to(self.message, "❌ Uso: /kill (rispondi ad utente) O /kill mob|boss [id/nome]")
            return
        
        target_id = self.message.reply_to_message.from_user.id
        target_user = user_service.get_user(target_id)
        
        if not target_user:
            self.bot.reply_to(self.message, "❌ Utente non trovato!")
            return
        
        user_service.update_user(target_id, {'health': 0})
        self.bot.reply_to(self.message, f"💀 {target_user.nome} eliminato!")
    
    def handle_find_missing_image(self):
        """Find a random character or mob without an image"""
        utente = user_service.get_user(self.chatid)
        if not user_service.is_admin(utente):
            return

        missing_images = []

        # 1. Check Characters
        all_chars = character_service.get_all_characters()
        for char in all_chars:
            # Check if image exists
            found = False
            # Check dict or object
            if isinstance(char, dict):
                char_name = char['nome']
            else:
                char_name = char.nome
                
            char_name_clean = char_name.lower().replace(" ", "_").replace("'", "")
            
            # Try standard extensions
            for ext in ['.png', '.jpg', '.jpeg']:
                if os.path.exists(f"images/characters/{char_name_clean}{ext}"):
                    found = True
                    break
            
            # Try without saga suffix
            if not found:
                base_name = char_name.split('-')[0].strip().lower().replace(" ", "_")
                for ext in ['.png', '.jpg', '.jpeg']:
                    if os.path.exists(f"images/characters/{base_name}{ext}"):
                        found = True
                        break
            
            if not found:
                missing_images.append({'name': char_name, 'type': 'character'})

        # 2. Check Mobs
        try:
            import csv
            with open('data/mobs.csv', 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    mob_name = row['nome']
                    mob_name_clean = mob_name.lower().replace(" ", "_").replace("'", "")
                    
                    found = False
                    for ext in ['.png', '.jpg', '.jpeg']:
                        if os.path.exists(f"images/mobs/{mob_name_clean}{ext}"):
                            found = True
                            break
                    
                    if not found:
                        missing_images.append({'name': mob_name, 'type': 'mob'})
        except Exception as e:
            print(f"Error checking mobs: {e}")

        if not missing_images:
            self.bot.reply_to(self.message, "✅ Tutti i personaggi e i mob hanno un'immagine!")
            return

        # Pick random missing
        import random
        target = random.choice(missing_images)
        
        # Track it
        admin_last_viewed_character[self.chatid] = {
            'character_name': target['name'],
            'timestamp': datetime.datetime.now(),
            'type': target['type']
        }
        
        msg = f"🔍 **Immagine Mancante Trovata!**\n\n"
        msg += f"Nome: **{target['name']}**\n"
        msg += f"Tipo: **{target['type'].title()}**\n\n"
        msg += f"📸 Invia una foto ORA per caricarla!"
        
        self.bot.reply_to(self.message, msg, parse_mode='markdown')

    def handle_kill_all_enemies(self):
        """Admin command to kill all active enemies"""
        utente = user_service.get_user(self.chatid)
        if not user_service.is_admin(utente):
            return
        
        from database import Database
        from models.pve import Mob
        db = Database()
        session = db.get_session()
        
        # Get all active enemies (not dead)
        active_enemies = session.query(Mob).filter_by(is_dead=False).all()
        
        if not active_enemies:
            session.close()
            self.bot.reply_to(self.message, "✅ Nessun nemico attivo!")
            return
        
        killed_count = 0
        bosses_killed = 0
        mobs_killed = 0
        
        for enemy in active_enemies:
            enemy.is_dead = True
            enemy.health = 0
            killed_count += 1
            if enemy.is_boss:
                bosses_killed += 1
            else:
                mobs_killed += 1
        
        session.commit()
        session.close()
        
        msg = f"💀 **Tutti i nemici eliminati!**\n\n"
        msg += f"📊 Totale: {killed_count}\n"
        if mobs_killed > 0:
            msg += f"👹 Mob: {mobs_killed}\n"
        if bosses_killed > 0:
            msg += f"☠️ Boss: {bosses_killed}\n"
        
        self.bot.reply_to(self.message, msg, parse_mode='markdown')

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
        self.bot.reply_to(self.message, "❌ Per attaccare devi usare i pulsanti sotto il messaggio del mostro!")

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
        from services.character_loader import get_character_loader
        char_loader = get_character_loader()
        selected_level = char_loader.get_character_by_id(utente.livello_selezionato)
        
        image_sent = False
        if selected_level:
            # Try using cached file_id first (not available in CSV, skip this)
            # Character images would need separate handling
            if False:  # Disabled telegram_file_id caching for CSV-based chars
                try:
                    pass
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

    def handle_achievements(self):
        """Show user achievements via button"""
        handle_achievements_cmd(self.message)

    def handle_season(self):
        """Show seasonal progression via button"""
        handle_season_cmd(self.message)

    def handle_web_dashboard(self):
        """Show link to web dashboard via button"""
        user_id = self.chatid
        dashboard_url = f"{DASHBOARD_BASE_URL}/?user_id={user_id}"
        msg = "🌐 **DASHBOARD WEB**\n\nAccedi alla tua dashboard personale per vedere achievement, statistiche e progressi stagionali con una grafica avanzata!"
        
        from telebot import types
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🌐 Apri Dashboard Web", url=dashboard_url))
        
        self.bot.reply_to(self.message, msg, reply_markup=markup, parse_mode='markdown')

    def handle_profile(self, target_user=None):
        """Show comprehensive user profile with stats and transformations"""
        if target_user:
            utente = target_user
        else:
            utente = user_service.get_user(self.chatid)
        
        if not utente:
            self.bot.reply_to(self.message, "Utente non trovato.")
            return
        
        # Get character info
        from services.character_loader import get_character_loader
        char_loader = get_character_loader()
        character = char_loader.get_character_by_id(utente.livello_selezionato)
        
        # Build new profile format
        msg = ""
        
        # Premium status - ONLY show if user is actually premium
        if utente.premium == 1:
            msg += "🎖 **Utente Premium**\n"
        if utente.abbonamento_attivo == 1:
            msg += f"✅ Abbonamento attivo (fino al {str(utente.scadenza_premium)[:11]})\n"
            
        nome_utente = utente.nome if utente.username is None else utente.username
        msg += f"👤 **{nome_utente}**: {utente.points} {PointsName}\n"
        
        # Show title if user has one
        if hasattr(utente, 'title') and utente.title:
            msg += f"👑 **{utente.title}**\n"
        
        # Calculate next level exp
        next_lv_num = utente.livello + 1
        next_lv_row = char_loader.get_characters_by_level(next_lv_num)
        next_lv_row = next_lv_row[0] if next_lv_row else None
        
        if next_lv_row:
            exp_req = next_lv_row.get('exp_required', next_lv_row.get('exp_to_lv', 100))
        else:
            # Formula for levels beyond DB (e.g. up to 80)
            exp_req = 100 * (next_lv_num ** 2)
            
        msg += f"💪🏻 **Exp**: {utente.exp}/{exp_req}\n"
        # Character name with saga
        char_display = character['nome'] if character else 'N/A'
        if character and character.get('character_group'):
            char_display = f"{character['nome']} - {character['character_group']}"
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
            abilities = skill_service.get_character_abilities(character['id'])
            
            if abilities:
                msg += f"\n✨ **Abilità:**\n"
                for ability in abilities:
                    msg += f"🔮 {ability['name']}: {ability['damage']} DMG, {ability['mana_cost']} Mana, Crit {ability['crit_chance']}% (x{ability['crit_multiplier']})\n"
            elif character.get('special_attack_name'):
                # Fallback to legacy special attack
                msg += f"\n✨ **Attacco Speciale**: {character['special_attack_name']}\n"
                msg += f"  Danno: {character['special_attack_damage']} | Mana: {character['special_attack_mana_cost']}\n"
            
        # Transformations
        active_trans = transformation_service.get_active_transformation(utente)
        if active_trans:
            time_left = active_trans['expires_at'] - datetime.datetime.now()
            if time_left.total_seconds() > 0:
                hours_left = int(time_left.total_seconds() / 3600)
                msg += f"✨ **Trasformazione Attiva:**\n"
                msg += f"└ {active_trans['name']}\n"
                msg += f"└ Scade tra: {hours_left}h\n\n"
        
        markup = types.InlineKeyboardMarkup()
        # Only show action buttons if viewing own profile
        if not target_user or target_user.id_telegram == self.chatid:
            markup.add(types.InlineKeyboardButton("📊 Alloca Statistiche", callback_data="stats_menu"))
            markup.add(types.InlineKeyboardButton(f"🔄 Reset Stats (500 {PointsName})", callback_data="reset_stats_confirm"))
        if character:
            markup.add(types.InlineKeyboardButton("✨ Attacco Speciale", callback_data="special_attack_mob"))
            
            # Add transform button if transformations are available for this character
            transforms = char_loader.get_transformation_chain(character['id'])
            if transforms:
                markup.add(types.InlineKeyboardButton("🔥 Trasformati", callback_data=f"transform_menu|{character['id']}"))
            
        # Try to send with character image
        image_sent = False
        if character:
            # Try using helper function
            from services.character_loader import get_character_image
            image_data = get_character_image(character, is_locked=False)
            
            if image_data:
                try:
                    self.bot.send_photo(self.message.chat.id, image_data, caption=msg, parse_mode='markdown', reply_markup=markup)
                    image_sent = True
                except Exception as e:
                    print(f"Error sending character image: {e}")
        

        
        if not image_sent:
            self.bot.send_message(self.message.chat.id, msg, parse_mode='markdown', reply_markup=markup)


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

    def process_item_target(self, message, item_name):
        """Handle target selection for items"""
        target_username = message.text.strip()
        target_user = user_service.get_user(target_username)
        
        if not target_user:
            self.bot.reply_to(message, f"❌ Utente {target_username} non trovato. Operazione annullata.")
            return
            
        # Use the item on the target
        if item_service.use_item(self.chatid, item_name):
            utente = user_service.get_user(self.chatid)
            msg, data = item_service.apply_effect(utente, item_name, target_user)
            
            if data and data.get('type') == 'wumpa_drop':
                # Create buttons for stealing
                amount = data['amount']
                markup = types.InlineKeyboardMarkup()
                buttons = []
                import uuid
                for i in range(amount):
                    uid = str(uuid.uuid4())[:8]
                    buttons.append(types.InlineKeyboardButton("🍑", callback_data=f"steal|{uid}"))
                
                # Add rows of 5
                for i in range(0, len(buttons), 5):
                    markup.row(*buttons[i:i+5])
                
                # Send to GROUP if possible
                try:
                    self.bot.send_message(GRUPPO_AROMA, msg, reply_markup=markup)
                    self.bot.reply_to(message, "Oggetto usato! Controlla il gruppo.")
                except:
                    self.bot.reply_to(message, msg, reply_markup=markup)
            else:
                self.bot.reply_to(message, msg)
        else:
            self.bot.reply_to(message, "❌ Non hai questo oggetto o è già stato usato.")

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
                "Colpisci un giocatore": "💥",
                "Cassa": "📦"
            }
            
            # Load potions to check which items are potions
            from services.potion_service import PotionService
            potion_service = PotionService()
            all_potions = potion_service.get_all_potions()
            potion_names = [p['nome'] for p in all_potions]
            
            for oggetto in inventario:
                # Check if it's a potion
                if oggetto.oggetto in potion_names:
                    # Add potion button with appropriate emoji
                    if 'Mana' in oggetto.oggetto:
                        emoji = "💙"
                    elif 'Elisir' in oggetto.oggetto:
                        emoji = "✨"
                    else:
                        emoji = "💚"
                    markup.add(types.InlineKeyboardButton(f"{emoji} Usa {oggetto.oggetto}", callback_data=f"use_potion|{oggetto.oggetto}"))
                # Check if it's a regular item
                elif oggetto.oggetto in item_emoji:
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
        # Sort logic: EXP (descending)
        users.sort(key=lambda x: x.exp, reverse=True)
        
        msg = "🏆 **CLASSIFICA** 🏆\n\n"
        
        # Pre-load character data to avoid N queries
        from services.character_loader import get_character_loader
        char_loader = get_character_loader()
        
        for i, u in enumerate(users[:15]): # Show top 15
            # Get character name
            char_name = "N/A"
            if u.livello_selezionato:
                char = char_loader.get_character_by_id(u.livello_selezionato)
                if char:
                    char_name = char['nome']
            
            nome_display = u.username if u.username else u.nome
            # Escape markdown in name
            if nome_display:
                nome_display = nome_display.replace("_", "\\_").replace("*", "\\*").replace("[", "\\[")
            
            msg += f"{i+1}. **{nome_display}**\n"
            msg += f"   Lv. {u.livello} - {char_name}\n"
            msg += f"   ✨ EXP: {u.exp} | 🍑 {u.points}\n\n"
            
        self.bot.reply_to(self.message, msg, parse_mode='markdown')

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
        """Admin command to add/remove points: +15 @username or -10 @username"""
        utente = user_service.get_user(self.chatid)
        if not user_service.is_admin(utente):
            return

        text = self.message.text.strip()
        try:
            parts = text.split()
            if len(parts) < 2:
                return
            
            amount_str = parts[0]
            target_str = parts[1]
            
            amount = int(amount_str)
            target_user = user_service.get_user(target_str)
            
            if target_user:
                user_service.add_points(target_user, amount)
                action = "aggiunti" if amount > 0 else "rimossi"
                self.bot.reply_to(self.message, f"✅ {abs(amount)} {PointsName} {action} a {target_user.username or target_user.nome}!")
            else:
                self.bot.reply_to(self.message, f"❌ Utente {target_str} non trovato.")
        except ValueError:
            pass
        except Exception as e:
            print(f"Error in handle_plus_minus: {e}")

    def handle_restore(self):
        pass

    def handle_backup(self):
        pass

    def handle_broadcast(self):
        pass

    def handle_dona(self):
        pass

    def handle_me(self):
        self.handle_profile()

    def handle_status(self):
        """Show profile of tagged user: !status @username"""
        text = self.message.text.strip()
        parts = text.split()
        
        if len(parts) < 2:
            self.bot.reply_to(self.message, "❌ Uso: !status @username")
            return
            
        target_username = parts[1]
        target_user = user_service.get_user(target_username)
        
        if target_user:
            self.handle_profile(target_user=target_user)
        else:
            self.bot.reply_to(self.message, f"❌ Utente {target_username} non trovato.")

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
        
        # CSV returns dicts, so use dict access
        char_id = char['id']
        char_name = char['nome']
        char_group = char.get('character_group', '')
        char_element = char.get('elemental_type', '')
        char_level = char['livello']
        char_lv_premium = char.get('lv_premium', 0)
        char_price = char.get('price', 0)
        
        is_unlocked = character_service.is_character_unlocked(utente, char_id)
        is_equipped = (utente.livello_selezionato == char_id)
        
        # Format character card
        lock_icon = "" if is_unlocked else "🔒 "
        saga_info = f" - {char_group}" if char_group else ""
        type_info = f" ({char_element})" if char_element else ""
        msg = f"**{lock_icon}{char_name}{saga_info}{type_info}**"
        
        if is_equipped:
            msg += " ⭐ *EQUIPAGGIATO*"
        
        msg += "\n\n"
        msg += f"📊 Livello Richiesto: {char_level}\n"
        
        if char_lv_premium == 1:
            msg += f"👑 Richiede Premium\n"
        elif char_lv_premium == 2 and char_price > 0:
            price = char_price
            if utente.premium == 1:
                price = int(price * 0.5)
            msg += f"💰 Prezzo: {price} {PointsName}"
            if utente.premium == 1:
                msg += f" ~~{char_price}~~"
            msg += "\n"
        
        
        # Show skills with crit stats
        from services.skill_service import SkillService
        skill_service = SkillService()
        abilities = skill_service.get_character_abilities(char_id)
        
        if abilities:
            msg += f"\n✨ **Abilità:**\n"
            for ability in abilities:
                msg += f"\n🔮 **{ability['name']}**\n"
                msg += f"   ⚔️ Danno: {ability['damage']}\n"
                msg += f"   💙 Mana: {ability['mana_cost']}\n"
                msg += f"   🎯 Crit: {ability['crit_chance']}% (x{ability['crit_multiplier']})\n"
        elif char.get('special_attack_name'):
            # Fallback to legacy special attack
            msg += f"\n✨ **Abilità Speciale:**\n"
            msg += f"🔮 {char.get('special_attack_name')}\n"
            msg += f"⚔️ Danno: {char.get('special_attack_damage')}\n"
            msg += f"💙 Costo Mana: {char.get('special_attack_mana_cost')}\n"
        
        if char.get('description'):
            msg += f"\n📝 {char.get('description')}\n"
        
        if not is_unlocked:
            msg += "\n🔒 **PERSONAGGIO BLOCCATO**\n"
            if char_level > utente.livello:
                msg += f"Raggiungi livello {char_level} per sbloccarlo!\n"
            elif char_lv_premium == 1:
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
        
        # Row 3: Saga navigation button
        saga_row = []
        saga_row.append(types.InlineKeyboardButton(f"📚 {char_group}", callback_data=f"saga_nav|{char_group}|0"))
        markup.row(*saga_row)
        
        if is_unlocked:
            if not is_equipped:
                markup.add(types.InlineKeyboardButton("✅ Equipaggia", callback_data=f"char_select|{char_id}"))
            else:
                markup.add(types.InlineKeyboardButton("⭐ Già Equipaggiato", callback_data="char_already_equipped"))
        elif char_lv_premium == 2 and char_price > 0:
             markup.add(types.InlineKeyboardButton(f"🛒 Compra ({price} 🍑)", callback_data=f"char_buy|{char_id}"))
        
        # Send image if available
        # Ensure get_character_image is imported or available
        from services.character_loader import get_character_image
        image_data = get_character_image(char, is_locked=not is_unlocked)
        
        # Track this character for admin image upload feature
        if user_service.is_admin(utente):
            admin_last_viewed_character[self.chatid] = {
                'character_id': char_id,
                'character_name': char_name,
                'timestamp': datetime.datetime.now()
            }
        
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
        from services.character_loader import get_character_loader
        char_loader = get_character_loader()
        char = char_loader.get_character_by_name(char_name)
        
        if char:
            success, msg = character_service.purchase_character(utente, char['id'])
            if success:
                self.bot.reply_to(message, f"🎉 {msg}", reply_markup=get_start_markup(self.chatid))
            else:
                self.bot.reply_to(message, f"❌ {msg}", reply_markup=get_start_markup(self.chatid))
        else:
            self.bot.reply_to(message, "Personaggio non trovato.", reply_markup=get_start_markup(self.chatid))
            self.handle_shop_characters()

    def handle_spawn(self):
        utente = user_service.get_user(self.chatid)
        if not user_service.is_admin(utente):
            return

        # Extract mob name if provided
        # Command format: /spawn [mob_name]
        parts = self.message.text.split(' ', 1)
        mob_name = parts[1] if len(parts) > 1 else None
        
        success, msg, mob_id = pve_service.spawn_specific_mob(mob_name)
        
        if success:
            # Announce spawn
            mob = pve_service.get_current_mob_status()
            if mob:
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("⚔️ Attacca", callback_data=f"attack_enemy|mob|{mob_id}"), 
                           types.InlineKeyboardButton("✨ Attacco Speciale", callback_data=f"special_attack_enemy|mob|{mob_id}"))
                
                msg_text = f"⚠️ Un {mob['name']} selvatico è apparso!\n📊 Lv. {mob.get('level', 1)} | ⚡ Vel: {mob.get('speed', 30)} | 🛡️ Res: {mob.get('resistance', 0)}%\n❤️ Salute: {mob['health']}/{mob['max_health']} HP\n⚔️ Danno: {mob['attack']}\n\nSconfiggilo per ottenere ricompense!"
                
                # Send with image if available
                if mob.get('image') and os.path.exists(mob['image']):
                    try:
                        with open(mob['image'], 'rb') as photo:
                            self.bot.send_photo(GRUPPO_AROMA, photo, caption=msg_text, reply_markup=markup, )
                    except:
                        self.bot.send_message(GRUPPO_AROMA, msg_text, reply_markup=markup)
                else:
                    self.bot.send_message(GRUPPO_AROMA, msg_text, reply_markup=markup)
                
                # Immediate attack
                attack_events = pve_service.mob_random_attack(specific_mob_id=mob_id)
                if attack_events:
                    for event in attack_events:
                        msg = event['message']
                        image_path = event['image']
                        try:
                            if image_path and os.path.exists(image_path):
                                with open(image_path, 'rb') as photo:
                                    self.bot.send_photo(GRUPPO_AROMA, photo, caption=msg, reply_markup=markup, )
                            else:
                                self.bot.send_message(GRUPPO_AROMA, msg, reply_markup=markup, )
                        except:
                            self.bot.send_message(GRUPPO_AROMA, msg, reply_markup=markup, )
        else:
            self.bot.reply_to(self.message, f"❌ {msg}")

    def handle_all_commands(self):
        message = self.message
        utente = user_service.get_user(self.chatid)
        
        if not message.text:
            return
            
        if message.chat.type == "private":
            for command, handler in self.comandi_privati.items():
                if command.lower() in message.text.lower():
                    handler()
                    return

        if utente and user_service.is_admin(utente):
            # Check specific commands first (to avoid partial matches)
            if message.text.startswith("/killall"):
                self.handle_kill_all_enemies()
                return
            if message.text.startswith("/spawn"):
                self.handle_spawn()
                return
            if message.text.startswith("/boss"):
                self.handle_spawn_boss()
                return
            if message.text.startswith("/kill"):
                self.handle_kill_user()
                return
                
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
    # Check if message is a forward (Game Purchase)
    if message.forward_from_chat or message.forward_from:
        # RESTRICTION: Only allow purchases in private chat
        if message.chat.type != 'private':
            return

        # RESTRICTION: Check if forward source is valid (bot must be member)
        # If forwarded from a user (no forward_from_chat), we block it
        if not message.forward_from_chat:
             return
             
        # Check membership in source channel
        try:
            # We need bot's ID. get_me() makes an API call, but it's acceptable here.
            bot_user = bot.get_me()
            member = bot.get_chat_member(message.forward_from_chat.id, bot_user.id)
            if member.status not in ['member', 'administrator', 'creator']:
                # Bot is not in the channel, so it's not an authorized channel
                return
        except Exception as e:
            print(f"Error checking membership for source {message.forward_from_chat.id}: {e}")
            return
        utente = user_service.get_user(message.from_user.id)
        if not utente:
             user_service.create_user(message.from_user.id, message.from_user.username, message.from_user.first_name, message.from_user.last_name)
             utente = user_service.get_user(message.from_user.id)
             
        # Determine cost
        costo = 50 if utente.premium == 1 else 150
        
        if utente.points < costo:
            bot.reply_to(message, f"❌ Non hai abbastanza {PointsName}! Ti servono {costo} {PointsName}.")
            return

        # Deduct points
        user_service.add_points(utente, -costo)
        bot.reply_to(message, f"✅ Gioco acquistato per {costo} {PointsName}!\nInizio download...")
        
        # Forwarding loop
        try:
            source_chat_id = message.forward_from_chat.id if message.forward_from_chat else message.forward_from.id
            start_msg_id = message.forward_from_message_id
            
            # Forward the first message (the one user forwarded)
            # Actually, the user already forwarded it, but we want to "download" it aka forward it back to them?
            # Or does the user forward a message from a channel, and we continue forwarding from THAT channel?
            # "In pratica deve andare sulla fonte originale, e far comprare il gioco, cioè inoltrare di nuovo quel messaggio e tutti quelli con id successivo"
            
            current_msg_id = start_msg_id
            count = 0
            max_messages = 20 # Safety limit
            
            while count < max_messages:
                try:
                    # Forward message from source to user
                    fwd_msg = bot.forward_message(message.chat.id, source_chat_id, current_msg_id)
                    
                    # Check if sticker (Stop condition)
                    if fwd_msg.sticker:
                        break
                        
                    current_msg_id += 1
                    count += 1
                    time.sleep(0.5) # Avoid flood limits
                except Exception as e:
                    print(f"Error forwarding message {current_msg_id}: {e}")
                    # If we can't forward a message (deleted?), maybe try next one?
                    # But if we fail too many times, stop.
                    current_msg_id += 1
                    count += 1
                    
        except Exception as e:
            bot.reply_to(message, f"⚠️ Errore durante il download: {e}")
            
        return

    # Admin Character Image Upload Feature
    if message.content_type == 'photo' and message.from_user:
        user_id = message.from_user.id
        utente = user_service.get_user(user_id)
        
        # Check if admin
        if utente and user_service.is_admin(utente):
            # Check if has recently viewed a character
            if user_id in admin_last_viewed_character:
                char_data = admin_last_viewed_character[user_id]
                
                # Check if view was recent (within last 5 minutes)
                time_diff = datetime.datetime.now() - char_data['timestamp']
                if time_diff.total_seconds() < 300:  # 5 minutes
                    try:
                        # Download the photo
                        file_info = bot.get_file(message.photo[-1].file_id)
                        downloaded_file = bot.download_file(file_info.file_path)
                        
                        # Save with character name
                        char_name = char_data['character_name']
                        char_type = char_data.get('type', 'character') # Default to character for backward compatibility
                        
                        file_name = char_name.lower().replace(' ', '_').replace("'", "") + ".png"
                        
                        if char_type == 'mob':
                            # Ensure directory exists
                            os.makedirs('images/mobs', exist_ok=True)
                            file_path = os.path.join('images', 'mobs', file_name)
                        else:
                            file_path = os.path.join('images', 'characters', file_name)
                        
                        with open(file_path, 'wb') as f:
                            f.write(downloaded_file)
                        
                        bot.reply_to(message, f"✅ Immagine aggiornata per {char_name}!\nSalvata in: {file_path}")
                        
                        # Clear the tracking
                        del admin_last_viewed_character[user_id]
                        return
                    except Exception as e:
                        bot.reply_to(message, f"❌ Errore nell'aggiornamento dell'immagine: {e}")
                        return
                else:
                    bot.reply_to(message, f"⏱️ Tempo scaduto! Sono passati {int(time_diff.total_seconds())} secondi.\nVisualizza nuovamente il personaggio e riprova entro 5 minuti.")
                    del admin_last_viewed_character[user_id]
                    return
            else:
                # Only show info if it LOOKS like they might be trying to upload (e.g. caption contains character name?)
                # Or just ignore if not tracking. 
                # The user complaint was that forwarding a game triggered this.
                # Now that we handle forwards above, this should be safe.
                pass
    
    # Check Sunday, etc.
    utente = user_service.get_user(message.from_user.id)
    if not utente:
        user_service.create_user(message.from_user.id, message.from_user.username, message.from_user.first_name, message.from_user.last_name)
        utente = user_service.get_user(message.from_user.id)
    
    # Track activity
    user_service.track_activity(message.from_user.id, message.chat.id)
    
    # Sunday reset removed - characters persist
    
    # Sunday bonus: 10 Wumpa when you write on Sunday
    if datetime.datetime.today().weekday() == 6:  # Sunday
        session = user_service.db.get_session()
        from models.system import Domenica
        
        today = datetime.date.today()
        sunday_bonus = session.query(Domenica).filter_by(utente=utente.id_telegram).first()
        
        if not sunday_bonus or sunday_bonus.last_day != today:
            # Give Sunday bonus - Box Wumpa
            success, box_msg, item = item_service.open_box_wumpa(utente)
            
            # Update or create record
            if sunday_bonus:
                sunday_bonus.last_day = today
            else:
                sunday_bonus = Domenica(utente=utente.id_telegram, last_day=today)
                session.add(sunday_bonus)
            
            session.commit()
            bot.send_message(message.chat.id, f"🎉 **BUONA DOMENICA!**\nEcco il tuo regalo settimanale:\n\n{box_msg}")
        
        session.close()
    
    # Random exp
    if message.chat.type in ['group', 'supergroup']:
        user_service.add_exp(utente, 1)
        
        # Check TNT timer first (if user is avoiding TNT)
        drop_service.check_tnt_timer(utente, bot, message)
        
        # Check for active traps (TNT/Nitro placed by users)
        if drop_service.check_traps(utente, bot, message):
            return # Trap triggered, stop processing drops/spawns

        # Random drops: TNT, Nitro, Cassa
        drop_service.maybe_drop(utente, bot, message)
        
        # Random Mob Spawn (5% chance per message)
        if random.random() < 0.05:
            mob_id, attack_events = pve_service.spawn_daily_mob(chat_id=message.chat.id)
            if mob_id:
                mob = pve_service.get_current_mob_status()
                if mob:
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton("⚔️ Attacca", callback_data=f"attack_enemy|mob|{mob_id}"), 
                               types.InlineKeyboardButton("✨ Attacco Speciale", callback_data=f"special_attack_enemy|mob|{mob_id}"))
                    
                    msg_text = f"⚠️ Un {mob['name']} selvatico è apparso!\n📊 Lv. {mob.get('level', 1)} | ⚡ Vel: {mob.get('speed', 30)} | 🛡️ Res: {mob.get('resistance', 0)}%\n❤️ Salute: {mob['health']}/{mob['max_health']} HP\n⚔️ Danno: {mob['attack']}\n\nSconfiggilo per ottenere ricompense!"
                    
                    # Send with image if available
                    if mob.get('image') and os.path.exists(mob['image']):
                        try:
                            with open(mob['image'], 'rb') as photo:
                                bot.send_photo(message.chat.id, photo, caption=msg_text, reply_markup=markup, )
                        except:
                            bot.send_message(message.chat.id, msg_text, reply_markup=markup)
                    else:
                        bot.send_message(message.chat.id, msg_text, reply_markup=markup, parse_mode='markdown')
                    
                    # Send immediate attack messages if any
                    if attack_events:
                        for event in attack_events:
                            msg = event['message']
                            image_path = event['image']
                            try:
                                if image_path and os.path.exists(image_path):
                                    with open(image_path, 'rb') as photo:
                                        bot.send_photo(message.chat.id, photo, caption=msg, reply_markup=markup, )
                                else:
                                    bot.send_message(message.chat.id, msg, reply_markup=markup, )
                            except:
                                bot.send_message(message.chat.id, msg, reply_markup=markup, parse_mode='markdown')

    bothandler = BotCommands(message, bot)
    bothandler.handle_all_commands()

@bot.callback_query_handler(func=lambda call: True)
def handle_inline_buttons(call):
    action = call.data
    user_id = call.from_user.id
    utente = user_service.get_user(user_id)
    
    # TITLE SELECTION
    if action.startswith("set_title|"):
        new_title = action.split("|")[1]
        
        from database import Database
        from models.user import Utente
        db = Database()
        session = db.get_session()
        
        try:
            db_user = session.query(Utente).filter_by(id_telegram=user_id).first()
            if db_user:
                db_user.title = new_title
                session.commit()
                bot.answer_callback_query(call.id, f"✅ Titolo impostato: {new_title}")
                bot.edit_message_text(f"✅ Titolo impostato con successo: **{new_title}**", user_id, call.message.message_id, parse_mode='markdown')
            else:
                bot.answer_callback_query(call.id, "❌ Utente non trovato")
        except Exception as e:
            session.rollback()
            print(f"Error setting title in callback: {e}")
            bot.answer_callback_query(call.id, "❌ Errore nel salvataggio")
        finally:
            session.close()
        return

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
        
        # CSV returns dicts, so use dict access
        char_id = char['id']
        char_name = char['nome']
        char_group = char.get('character_group', '')
        char_element = char.get('elemental_type', '')
        char_level = char['livello']
        char_lv_premium = char.get('lv_premium', 0)
        char_price = char.get('price', 0)
        
        is_unlocked = character_service.is_character_unlocked(utente, char_id)
        is_equipped = (utente.livello_selezionato == char_id)
        
        # Format character card
        lock_icon = "" if is_unlocked else "🔒 "
        saga_info = f"[{char_group}] " if char_group else ""
        type_info = f" ({char_element})" if char_element else ""
        msg = f"**{lock_icon}{saga_info}{char_name}{type_info}**"
        
        if is_equipped:
            msg += " ⭐ *EQUIPAGGIATO*"
        
        msg += "\n\n"
        msg += f"📊 Livello Richiesto: {char_level}\n"
        
        if char_lv_premium == 1:
            msg += f"👑 Richiede Premium\n"
        elif char_lv_premium == 2 and char_price > 0:
            price = char_price
            if utente.premium == 1:
                price = int(price * 0.5)
            msg += f"💰 Prezzo: {price} {PointsName}"
            if utente.premium == 1:
                msg += f" ~~{char_price}~~"
            msg += "\n"
        
        if char.get('special_attack_name'):
            msg += f"\n✨ **Abilità Speciale:**\n"
            msg += f"🔮 {char.get('special_attack_name')}\n"
            msg += f"⚔️ Danno: {char.get('special_attack_damage')}\n"
            msg += f"💙 Costo Mana: {char.get('special_attack_mana_cost')}\n"
        
        if char.get('description'):
            msg += f"\n📝 {char.get('description')}\n"
        
        if not is_unlocked:
            msg += "\n🔒 **PERSONAGGIO BLOCCATO**\n"
            if char_level > utente.livello:
                msg += f"Raggiungi livello {char_level} per sbloccarlo!\n"
            elif char_lv_premium == 1:
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
        
        # Row 3: Saga navigation button
        saga_row = []
        saga_row.append(types.InlineKeyboardButton(f"📚 {char_group}", callback_data=f"saga_nav|{char_group}|0"))
        markup.row(*saga_row)
        
        if is_unlocked:
            if not is_equipped:
                markup.add(types.InlineKeyboardButton("✅ Equipaggia", callback_data=f"char_select|{char_id}"))
            else:
                markup.add(types.InlineKeyboardButton("⭐ Già Equipaggiato", callback_data="char_already_equipped"))
        elif char_lv_premium == 2 and char_price > 0:
             markup.add(types.InlineKeyboardButton(f"🛒 Compra ({price} 🍑)", callback_data=f"char_buy|{char_id}"))
        
        # Send image if available
        # Ensure get_character_image is imported or available
        from services.character_loader import get_character_image
        image_data = get_character_image(char, is_locked=not is_unlocked)
        
        # Track this character for admin image upload feature
        if user_service.is_admin(utente):
            admin_last_viewed_character[user_id] = {
                'character_id': char_id,
                'character_name': char_name,
                'timestamp': datetime.datetime.now()
            }
        
        if image_data:
            try:
                # Use edit_message_media if possible, but for now we are editing text/caption
                # If the previous message was a photo, we need edit_message_media
                # If it was text, we might need to delete and send new photo
                # For simplicity in this callback handler, let's try to edit the caption if it's a photo,
                # or delete and resend if type changes.
                
                # Actually, standard practice for these menus is often deleting and resending 
                # to avoid "message not modified" or type mismatch errors, 
                # BUT that causes flickering.
                
                # Let's assume the previous message was a photo (since we send photos in handle_choose_character)
                # We need to create an InputMediaPhoto
                media = types.InputMediaPhoto(image_data, caption=msg, parse_mode='markdown')
                bot.delete_message(user_id, call.message.message_id)
                if image_data:
                     bot.send_photo(user_id, image_data, caption=msg, reply_markup=markup, parse_mode='markdown')
                else:
                     bot.send_message(user_id, msg, reply_markup=markup, parse_mode='markdown')
            except Exception as e2:
                print(f"Error in fallback send: {e2}")

        bot.answer_callback_query(call.id)
        return
    
    elif action.startswith("saga_nav|"):
        # saga_nav|saga_name|char_index
        parts = action.split("|")
        saga_name = parts[1]
        char_idx = int(parts[2])
        
        utente = user_service.get_user(user_id)
        is_admin = user_service.is_admin(utente)
        
        # Get character loader
        from services.character_loader import get_character_loader, get_character_image
        char_loader = get_character_loader()
        
        # Get all sagas for navigation
        all_sagas = char_loader.get_all_sagas()
        saga_idx = all_sagas.index(saga_name) if saga_name in all_sagas else 0
        
        # Get characters for this saga
        saga_chars = char_loader.get_characters_by_saga(saga_name)
        
        if not saga_chars:
            bot.answer_callback_query(call.id, f"Nessun personaggio nella saga {saga_name}!")
            return
        
        # Filter by user access (unless admin)
        if not is_admin:
            saga_chars = [c for c in saga_chars if c['livello'] <= utente.livello or c['lv_premium'] == 2]
        
        if not saga_chars:
            bot.answer_callback_query(call.id, f"Nessun personaggio sbloccato in {saga_name}!")
            return
        
        # Validate char index
        if char_idx < 0: char_idx = 0
        if char_idx >= len(saga_chars): char_idx = len(saga_chars) - 1
        
        char = saga_chars[char_idx]
        
        # CSV returns dicts
        char_id = char['id']
        char_name = char['nome']
        char_group = char.get('character_group', '')
        char_element = char.get('elemental_type', '')
        char_level = char['livello']
        char_lv_premium = char.get('lv_premium', 0)
        char_price = char.get('price', 0)
        
        is_unlocked = character_service.is_character_unlocked(utente, char_id)
        is_equipped = (utente.livello_selezionato == char_id)
        
        # Format character card
        lock_icon = "" if is_unlocked else "🔒 "
        type_info = f" ({char_element})" if char_element else ""
        msg = f"**{lock_icon}{char_name}{type_info}**"
        
        if is_equipped:
            msg += " ⭐ *EQUIPAGGIATO*"
        
        msg += "\n\n"
        msg += f"📊 Livello Richiesto: {char_level}\n"
        
        if char_lv_premium == 1:
            msg += f"👑 Richiede Premium\n"
        elif char_lv_premium == 2 and char_price > 0:
            price = char_price
            if utente.premium == 1:
                price = int(price * 0.5)
            msg += f"💰 Prezzo: {price} {PointsName}"
            if utente.premium == 1:
                msg += f" ~~{char_price}~~"
            msg += "\n"
        
        if char.get('special_attack_name'):
            msg += f"\n✨ **Abilità Speciale:**\n"
            msg += f"🔮 {char.get('special_attack_name')}\n"
            msg += f"⚔️ Danno: {char.get('special_attack_damage')}\n"
            msg += f"💙 Costo Mana: {char.get('special_attack_mana_cost')}\n"
        
        if char.get('description'):
            msg += f"\n📝 {char.get('description')}\n"
        
        if not is_unlocked:
            msg += "\n🔒 **PERSONAGGIO BLOCCATO**\n"
            if char_level > utente.livello:
                msg += f"Raggiungi livello {char_level} per sbloccarlo!\n"
            elif char_lv_premium == 1:
                msg += "Richiede abbonamento Premium!\n"
        
        msg += f"\n📚 **{saga_name}** - {char_idx + 1}/{len(saga_chars)}"
        
        markup = types.InlineKeyboardMarkup()
        
        # Row 1: Saga navigation (prev/next saga)
        saga_nav_row = []
        if saga_idx > 0:
            saga_nav_row.append(types.InlineKeyboardButton("⏮️", callback_data=f"saga_nav|{all_sagas[saga_idx-1]}|0"))
        if saga_idx < len(all_sagas) - 1:
            saga_nav_row.append(types.InlineKeyboardButton("⏭️", callback_data=f"saga_nav|{all_sagas[saga_idx+1]}|0"))
        if saga_nav_row:
            markup.row(*saga_nav_row)
        
        # Row 2: Character navigation within saga
        char_nav_row = []
        if char_idx > 0:
            char_nav_row.append(types.InlineKeyboardButton("◀️", callback_data=f"saga_nav|{saga_name}|{char_idx-1}"))
        else:
            char_nav_row.append(types.InlineKeyboardButton("⏺️", callback_data="ignore"))
            
        char_nav_row.append(types.InlineKeyboardButton(f"📚 {saga_name[:12]}", callback_data="ignore"))
        
        if char_idx < len(saga_chars) - 1:
            char_nav_row.append(types.InlineKeyboardButton("▶️", callback_data=f"saga_nav|{saga_name}|{char_idx+1}"))
        else:
            char_nav_row.append(types.InlineKeyboardButton("⏺️", callback_data="ignore"))
            
        markup.row(*char_nav_row)
        
        # Row 3: Back to level nav
        markup.add(types.InlineKeyboardButton("🔙 Torna a Livelli", callback_data=f"char_nav|0|0"))
        
        if is_unlocked:
            if not is_equipped:
                markup.add(types.InlineKeyboardButton("✅ Equipaggia", callback_data=f"char_select|{char_id}"))
            else:
                markup.add(types.InlineKeyboardButton("⭐ Già Equipaggiato", callback_data="char_already_equipped"))
        elif char_lv_premium == 2 and char_price > 0:
             markup.add(types.InlineKeyboardButton(f"🛒 Compra ({price} 🍑)", callback_data=f"char_buy|{char_id}"))
        
        # Delete old message and send new with image
        try:
            bot.delete_message(user_id, call.message.message_id)
            image_data = get_character_image(char, is_locked=not is_unlocked)
            if image_data:
                bot.send_photo(user_id, image_data, caption=msg, reply_markup=markup, parse_mode='markdown')
            else:
                bot.send_message(user_id, msg, reply_markup=markup, parse_mode='markdown')
        except Exception as e:
            print(f"Error in saga_nav: {e}")
            bot.send_message(user_id, msg, reply_markup=markup, parse_mode='markdown')
        
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
                # Get character data from CSV
                from services.character_loader import get_character_loader, get_character_image
                char_loader = get_character_loader()
                char = char_loader.get_character_by_id(char_id)
                
                if char:
                    # Construct unlocked message (simplified version of handle_inline_buttons logic)
                    lock_icon = "" 
                    char_name = char['nome']
                    char_level = char['livello']
                    
                    new_msg = f"**{lock_icon}{char_name}**\n\n"
                    new_msg += f"📊 Livello Richiesto: {char_level}\n"
                    
                    if char.get('special_attack_name'):
                        new_msg += f"\n✨ **Abilità Speciale:**\n🔮 {char.get('special_attack_name')}\n⚔️ Danno: {char.get('special_attack_damage')}\n💙 Costo Mana: {char.get('special_attack_mana_cost')}\n"
                    
                    if char.get('description'):
                        new_msg += f"\n📝 {char.get('description')}\n"
                        
                    # Add navigation info if possible, or just leave it clean
                    # Ideally we should call the pagination logic again, but we don't have page info here easily
                    # So let's just show the card with "Equip" button
                    
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton("✅ Equipaggia questo personaggio", callback_data=f"char_select|{char['id']}"))
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
        
        # Check if this is a transformation
        from services.character_loader import get_character_loader
        char_loader = get_character_loader()
        
        if char_loader.is_transformation(char_id):
            # Get base character info
            char = char_loader.get_character_by_id(char_id)
            base_char = char_loader.get_base_character(char_id)
            
            if base_char:
                # Show message explaining transformation system
                msg = f"🔄 **{char['nome']}** è una trasformazione!\n\n"
                msg += f"Non puoi selezionarla direttamente.\n\n"
                msg += f"📋 **Come funziona:**\n"
                msg += f"1. Seleziona il personaggio base ({base_char['nome']})\n"
                msg += f"2. Acquista la trasformazione nel profilo\n"
                msg += f"3. Trasformati spendendo {char.get('transformation_mana_cost', 50)} mana\n\n"
                
                duration = char.get('transformation_duration_days', 0)
                if duration > 0:
                    msg += f"⏰ La trasformazione dura {duration} giorni\n"
                else:
                    msg += f"♾️ La trasformazione è permanente\n"
                
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton(f"✅ Seleziona {base_char['nome']}", callback_data=f"char_select|{base_char['id']}"))
                markup.add(types.InlineKeyboardButton("🔙 Indietro", callback_data="char_nav|0|0"))
                
                try:
                    bot.delete_message(user_id, call.message.message_id)
                except:
                    pass
                bot.send_message(user_id, msg, reply_markup=markup, parse_mode='markdown')
                bot.answer_callback_query(call.id)
                return
        
        success, msg = character_service.equip_character(utente, char_id)
        
        if success:
            bot.answer_callback_query(call.id, "✅ Personaggio equipaggiato!")
            bot.send_message(user_id, f"✅ {msg}", reply_markup=get_start_markup(user_id))
        else:
            bot.answer_callback_query(call.id, f"❌ {msg}")
        return
    
    elif action.startswith("transform_menu|"):
        base_char_id = int(action.split("|")[1])
        
        from services.character_loader import get_character_loader
        char_loader = get_character_loader()
        
        # Get available transformations
        transforms = char_loader.get_transformation_chain(base_char_id)
        base_char = char_loader.get_character_by_id(base_char_id)
        
        if not transforms:
            bot.answer_callback_query(call.id, "❌ Nessuna trasformazione disponibile!")
            return
        
        # Check which ones user owns
        from models.system import UserCharacter
        session = user_service.db.get_session()
        
        msg = f"🔥 **TRASFORMAZIONI per {base_char['nome']}**\n\n"
        msg += f"💙 Mana attuale: {utente.mana}/{utente.max_mana}\n\n"
        msg += "📋 **Opzioni disponibili:**\n"
        
        markup = types.InlineKeyboardMarkup()
        
        for t in transforms:
            owned = session.query(UserCharacter).filter_by(user_id=utente.id_telegram, character_id=t['id']).first()
            is_free = t.get('lv_premium', 0) == 0
            
            mana_cost = t.get('transformation_mana_cost', 50)
            duration = t.get('transformation_duration_days', 0)
            duration_str = f"{duration}g" if duration > 0 else "♾️"
            
            # Add info to message text
            status_icon = "✅" if owned or is_free else "🔒"
            msg += f"{status_icon} **{t['nome']}**\n"
            msg += f"   ├ Costo Mana: {mana_cost} 💙\n"
            msg += f"   └ Durata: {duration_str}\n"
            
            if owned or is_free:
                # Can transform
                can_afford = utente.mana >= mana_cost
                btn_text = f"🔥 Trasformati in {t['nome']}"
                if can_afford:
                    markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"activate_transform|{t['id']}"))
                else:
                    markup.add(types.InlineKeyboardButton(f"❌ {t['nome']} (No Mana)", callback_data="no_mana"))
            else:
                # Need to buy
                price = t.get('price', 0)
                msg += f"   └ Prezzo: {price} 🍑\n"
                markup.add(types.InlineKeyboardButton(f"🛒 Compra {t['nome']} ({price} 🍑)", callback_data=f"buy_transform|{t['id']}"))
            
            msg += "\n"
        
        session.close()
        
        markup.add(types.InlineKeyboardButton("🔙 Indietro", callback_data="back_to_profile"))
        
        try:
            bot.edit_message_text(msg, user_id, call.message.message_id, reply_markup=markup, parse_mode='markdown')
        except:
            bot.send_message(user_id, msg, reply_markup=markup, parse_mode='markdown')
        bot.answer_callback_query(call.id)
        return
    
    elif action.startswith("activate_transform|"):
        trans_id = int(action.split("|")[1])
        
        from services.character_loader import get_character_loader
        char_loader = get_character_loader()
        
        trans_char = char_loader.get_character_by_id(trans_id)
        if not trans_char:
            bot.answer_callback_query(call.id, "❌ Trasformazione non trovata!")
            return
        
        mana_cost = trans_char.get('transformation_mana_cost', 50)
        duration_days = trans_char.get('transformation_duration_days', 0)
        
        # Check mana
        if utente.mana < mana_cost:
            bot.answer_callback_query(call.id, f"❌ Mana insufficiente! Serve: {mana_cost}, hai: {utente.mana}")
            return
        
        # Deduct mana and apply transformation
        session = user_service.db.get_session()
        from models.user import Utente
        db_user = session.query(Utente).filter_by(id_telegram=user_id).first()
        db_user.mana -= mana_cost
        db_user.livello_selezionato = trans_id  # Change to transformed character
        remaining_mana = db_user.mana  # Capture value before close
        session.commit()
        session.close()
        
        duration_str = f"per {duration_days} giorni" if duration_days > 0 else "permanentemente"
        
        msg = f"🔥 **TRASFORMAZIONE COMPLETATA!**\n\n"
        msg += f"Ti sei trasformato in **{trans_char['nome']}** {duration_str}!\n"
        msg += f"💙 Mana speso: {mana_cost}\n"
        msg += f"💙 Mana rimanente: {remaining_mana}"
        
        bot.send_message(user_id, msg, reply_markup=get_start_markup(user_id), parse_mode='markdown')
        bot.answer_callback_query(call.id, f"🔥 Trasformato in {trans_char['nome']}!")
        return
    
    elif action.startswith("buy_transform|"):
        trans_id = int(action.split("|")[1])
        
        # Use character_service to purchase
        success, msg = character_service.purchase_character(utente, trans_id)
        
        if success:
            bot.answer_callback_query(call.id, "✅ Trasformazione acquistata!")
            bot.send_message(user_id, f"✅ {msg}\n\nOra puoi trasformarti dal profilo!", reply_markup=get_start_markup(user_id))
        else:
            bot.answer_callback_query(call.id, f"❌ {msg}")
        return
    
    elif action == "no_mana":
        bot.answer_callback_query(call.id, "❌ Non hai abbastanza mana! Rigenera +10 ogni ora.")
        return
    
    elif action == "back_to_profile":
        # Redirect to profile
        bot.answer_callback_query(call.id)
        try:
            bot.delete_message(user_id, call.message.message_id)
        except:
            pass
        # The user should use the profile button again
        bot.send_message(user_id, "Usa il pulsante 👤 Profilo per vedere il tuo profilo.", reply_markup=get_start_markup(user_id))
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
            markup.add(types.InlineKeyboardButton(f"⚡ +Velocità (+{stats_service.SPEED_PER_POINT} vel)", callback_data="stat_alloc|speed"))
            markup.add(types.InlineKeyboardButton(f"🛡️ +Resistenza (+{stats_service.RESISTANCE_PER_POINT}% res)", callback_data="stat_alloc|resistance"))
            markup.add(types.InlineKeyboardButton(f"🎯 +Crit Rate (+{stats_service.CRIT_RATE_PER_POINT}% crit)", callback_data="stat_alloc|crit_rate"))
        else:
            msg += "\n\n⚠️ Non hai punti disponibili!"
        
        try:
            bot.edit_message_text(msg, user_id, call.message.message_id, reply_markup=markup, parse_mode='markdown')
        except Exception as e:
            # If message can't be edited (e.g., it's an image), delete and send new one
            try:
                bot.delete_message(user_id, call.message.message_id)
            except:
                pass
            bot.send_message(user_id, msg, reply_markup=markup, parse_mode='markdown')
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
                markup.add(types.InlineKeyboardButton(f"⚡ +Velocità (+{stats_service.SPEED_PER_POINT} vel)", callback_data="stat_alloc|speed"))
                markup.add(types.InlineKeyboardButton(f"🛡️ +Resistenza (+{stats_service.RESISTANCE_PER_POINT}% res)", callback_data="stat_alloc|resistance"))
                markup.add(types.InlineKeyboardButton(f"🎯 +Crit Rate (+{stats_service.CRIT_RATE_PER_POINT}% crit)", callback_data="stat_alloc|crit_rate"))
            else:
                msg += "\n\n⚠️ Non hai punti disponibili!"
            
            try:
                bot.edit_message_text(msg, user_id, call.message.message_id, reply_markup=markup, parse_mode='markdown')
            except Exception as e:
                # If message can't be edited (e.g., it's an image), delete and send new one
                try:
                    bot.delete_message(user_id, call.message.message_id)
                except:
                    pass
                bot.send_message(user_id, msg, reply_markup=markup, parse_mode='markdown')
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
            
            try:
                bot.edit_message_text(msg, user_id, call.message.message_id, reply_markup=markup, parse_mode='markdown')
            except Exception as e:
                # If message can't be edited (e.g., it's an image), delete and send new one
                try:
                    bot.delete_message(user_id, call.message.message_id)
                except:
                    pass
                bot.send_message(user_id, msg, reply_markup=markup, parse_mode='markdown')
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
    
    
    elif action.startswith("use_potion|"):
        parts = action.split("|")
        potion_name = parts[1]
        
        utente = user_service.get_user(user_id)
        
        from services.potion_service import PotionService
        potion_service = PotionService()
        
        success, msg = potion_service.use_potion(utente, potion_name)
        
        if success:
            bot.answer_callback_query(call.id, "✅ Pozione usata!")
            bot.send_message(user_id, msg)
        else:
            bot.answer_callback_query(call.id, f"❌ {msg}", show_alert=True)
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


    elif action.startswith("attack_enemy|"):
        # New unified attack system: attack_enemy|{type}|{id}
        # Type can be 'mob' or 'raid'
        parts = action.split("|")
        if len(parts) != 3:
            bot.answer_callback_query(call.id, "❌ Formato callback non valido", show_alert=True)
            return
        
        enemy_type = parts[1]
        enemy_id = int(parts[2])
        
        utente = user_service.get_user(user_id)
        damage = random.randint(10, 30) + utente.base_damage
        
        # Check for luck boost
        if utente.luck_boost > 0:
             damage *= 2
             user_service.update_user(user_id, {'luck_boost': 0})
        
        # Check if enemy is dead before attacking
        from database import Database
        from models.pve import Mob
        db = Database()
        session = db.get_session()
        
        enemy_dead = False
        if enemy_type == "mob":
            mob = session.query(Mob).filter_by(id=enemy_id).first()
            if not mob:
                session.close()
                bot.answer_callback_query(call.id, "❌ Nemico non trovato!", show_alert=True)
                return
            enemy_dead = mob.is_dead
        else:
            session.close()
            bot.answer_callback_query(call.id, "❌ Tipo nemico non valido", show_alert=True)
            return
        session.close()
        
        if enemy_dead:
            bot.answer_callback_query(call.id, "💀 Questo nemico è già morto!", show_alert=True)
            return
        
        # Attack the specific target (all are mobs now, bosses are just mobs with is_boss=True)
        success, msg = pve_service.attack_mob(utente, damage, mob_id=enemy_id)
        
        # Send response
        if success:
            try:
                bot.answer_callback_query(call.id, "⚔️ Attacco effettuato!")
            except Exception:
                pass
            
            # Check if enemy died
            db = Database()
            session = db.get_session()
            mob = session.query(Mob).filter_by(id=enemy_id).first()
            enemy_died = mob.is_dead if mob else True
            session.close()
            
            if enemy_died:
                # Enemy died - no buttons, just show death message
                bot.send_message(call.message.chat.id, f"@{utente.username if utente.username else utente.nome}\n{msg}", )
            else:
                # Re-create markup to persist buttons
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("⚔️ Attacca", callback_data=f"attack_enemy|{enemy_type}|{enemy_id}"))
                markup.add(types.InlineKeyboardButton("✨ Attacco Speciale", callback_data=f"special_attack_enemy|{enemy_type}|{enemy_id}"))

                # Always show the full message with damage
                bot.send_message(call.message.chat.id, f"@{utente.username if utente.username else utente.nome}\n{msg}", reply_markup=markup, )
        else:
            try:
                bot.answer_callback_query(call.id, msg, show_alert=True)
            except Exception:
                pass
        return

    elif action.startswith("special_attack_enemy|"):
        # Special attack on specific enemy: special_attack_enemy|{type}|{id}
        parts = action.split("|")
        if len(parts) != 3:
            bot.answer_callback_query(call.id, "❌ Formato non valido", show_alert=True)
            return
        
        enemy_type = parts[1]
        enemy_id = int(parts[2])
        utente = user_service.get_user(user_id)
        
        # Get character
        from services.character_loader import get_character_loader
        char_loader = get_character_loader()
        character = char_loader.get_character_by_id(utente.livello_selezionato)
        
        if not character:
            bot.answer_callback_query(call.id, "❌ Personaggio non selezionato!", show_alert=True)
            return
        
        # Check mana
        mana_cost = character.get('special_attack_mana_cost', 0)
        if utente.mana < mana_cost:
            bot.answer_callback_query(call.id, f"❌ Mana insufficiente! Serve: {mana_cost}", show_alert=True)
            return
        
        # Deduct mana and calculate damage
        user_service.update_user(user_id, {'mana': utente.mana - mana_cost})
        damage = character.get('special_attack_damage', 0) + utente.base_damage
        
        # Check if enemy is dead before attacking
        from database import Database
        from models.pve import Mob
        db = Database()
        session = db.get_session()
        
        enemy_dead = False
        if enemy_type == "mob":
            mob = session.query(Mob).filter_by(id=enemy_id).first()
            if not mob:
                session.close()
                bot.answer_callback_query(call.id, "❌ Nemico non trovato!", show_alert=True)
                return
            enemy_dead = mob.is_dead
        else:
            session.close()
            bot.answer_callback_query(call.id, "❌ Tipo non valido", show_alert=True)
            return
        session.close()
        
        if enemy_dead:
            bot.answer_callback_query(call.id, "💀 Questo nemico è già morto!", show_alert=True)
            return
        
        # Attack (all are mobs now, bosses are just mobs with is_boss=True)
        success, msg = pve_service.attack_mob(utente, damage, use_special=True, mob_id=enemy_id)
        
        if success:
            try:
                bot.answer_callback_query(call.id, "✨ Attacco Speciale!")
            except:
                pass
            
            # Check if enemy died
            db = Database()
            session = db.get_session()
            mob = session.query(Mob).filter_by(id=enemy_id).first()
            enemy_died = mob.is_dead if mob else True
            session.close()
            
            special_name = character.get('special_attack_name', 'Attacco Speciale')
            msg = f"✨ **{special_name}!** ✨\n{msg}"
            
            if enemy_died:
                # Enemy died - no buttons, just show death message
                bot.send_message(call.message.chat.id, f"@{utente.username if utente.username else utente.nome}\n{msg}", )
            else:
                markup = types.InlineKeyboardMarkup()
                markup.add(
                    types.InlineKeyboardButton("⚔️ Attacca", callback_data=f"attack_enemy|{enemy_type}|{enemy_id}"),
                    types.InlineKeyboardButton("✨ Attacco Speciale", callback_data=f"special_attack_enemy|{enemy_type}|{enemy_id}")
                )
                bot.send_message(call.message.chat.id, f"@{utente.username if utente.username else utente.nome}\n{msg}", reply_markup=markup, )
        else:
            try:
                bot.answer_callback_query(call.id, msg, show_alert=True)
            except:
                pass
        return

    # Legacy attack handlers - keeping for backward compatibility but should not be used
    elif action == "attack_mob":
        # Try to find any active mob to attack
        utente = user_service.get_user(user_id)
        damage = random.randint(10, 30) + utente.base_damage
        
        # Check for luck boost
        if utente.luck_boost > 0:
             damage *= 2
             user_service.update_user(user_id, {'luck_boost': 0})
        
        # Try attacking any active mob (no specific ID)
        success, msg = pve_service.attack_mob(utente, damage)
        
        if success:
            try:
                bot.answer_callback_query(call.id, "⚔️ Attacco effettuato!")
            except Exception:
                pass
                
            # Get current mob status to recreate buttons
            mob = pve_service.get_current_mob_status()
            if mob:
                # Try to get mob ID from database
                from database import Database
                from models.pve import Mob
                db = Database()
                session = db.get_session()
                active_mob = session.query(Mob).filter_by(name=mob['name'], is_dead=False).first()
                mob_id = active_mob.id if active_mob else None
                session.close()
                
                if mob_id:
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton("⚔️ Attacca", callback_data=f"attack_enemy|mob|{mob_id}"), 
                               types.InlineKeyboardButton("✨ Attacco Speciale", callback_data=f"special_attack_enemy|mob|{mob_id}"))
                else:
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton("⚔️ Attacca", callback_data="attack_mob"), 
                               types.InlineKeyboardButton("✨ Attacco Speciale", callback_data="special_attack_mob"))
            else:
                markup = None

            # Always show the full message with damage
            bot.send_message(call.message.chat.id, f"@{utente.username if utente.username else utente.nome}\n{msg}", reply_markup=markup, )
        else:
            try:
                bot.answer_callback_query(call.id, msg, show_alert=True)
            except Exception:
                pass
        return

    elif action == "special_attack_mob":
        utente = user_service.get_user(user_id)
        
        # Try special attack on any active mob
        success, msg = pve_service.use_special_attack(utente)
        
        if success:
            try:
                bot.answer_callback_query(call.id, "✨ Attacco Speciale effettuato!")
            except Exception:
                pass
                
            # Get current mob status to recreate buttons
            mob = pve_service.get_current_mob_status()
            if mob:
                # Try to get mob ID from database
                from database import Database
                from models.pve import Mob
                db = Database()
                session = db.get_session()
                active_mob = session.query(Mob).filter_by(name=mob['name'], is_dead=False).first()
                mob_id = active_mob.id if active_mob else None
                session.close()
                
                if mob_id:
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton("⚔️ Attacca", callback_data=f"attack_enemy|mob|{mob_id}"), 
                               types.InlineKeyboardButton("✨ Attacco Speciale", callback_data=f"special_attack_enemy|mob|{mob_id}"))
                else:
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton("⚔️ Attacca", callback_data="attack_mob"), 
                               types.InlineKeyboardButton("✨ Attacco Speciale", callback_data="special_attack_mob"))
            else:
                markup = None
                       
            bot.send_message(call.message.chat.id, f"@{utente.username if utente.username else utente.nome}\n{msg}", reply_markup=markup, )
        else:
            try:
                bot.answer_callback_query(call.id, msg, show_alert=True)
            except Exception:
                pass
        return
    
    
    # EXISTING HANDLERS BELOW
    if action.startswith("use|"):
        item_name = action.split("|")[1]
        
        # Check if item requires a target
        targeted_items = ["Colpisci un giocatore", "Mira un giocatore"]
        
        if item_name in targeted_items:
            bot.answer_callback_query(call.id)
            msg = bot.send_message(user_id, f"🎯 Hai scelto di usare **{item_name}**.\n\nScrivi il @username del giocatore che vuoi colpire:", parse_mode='markdown')
            
            # Instantiate BotCommands to use its method
            cmd_handler = BotCommands(call.message, bot)
            bot.register_next_step_handler(msg, cmd_handler.process_item_target, item_name)
            return
            
        # Use item logic (immediate effect)
        if item_service.use_item(user_id, item_name):
            msg, data = item_service.apply_effect(utente, item_name)
            
            if data and data.get('type') == 'trap':
                # Set trap in the chat
                drop_service.set_trap(call.message.chat.id, data['trap_type'], user_id)
                
            bot.send_message(user_id, msg)
            bot.answer_callback_query(call.id, "✅ Oggetto usato!")
        else:
            bot.send_message(user_id, "Non hai questo oggetto o è già stato usato.")
            bot.answer_callback_query(call.id, "❌ Errore")

    elif action.startswith("steal|"):
        # Give 1 wumpa
        user_service.add_points(utente, 1)
        bot.answer_callback_query(call.id, "Hai rubato 1 Wumpa!")
        
        # Remove the button
        current_markup = call.message.reply_markup
        new_markup = types.InlineKeyboardMarkup()
        
        buttons_left = 0
        if current_markup and current_markup.keyboard:
            for row in current_markup.keyboard:
                new_row = []
                for btn in row:
                    if btn.callback_data != action:
                        new_row.append(btn)
                        buttons_left += 1
                if new_row:
                    new_markup.row(*new_row)
        
        if buttons_left == 0:
            bot.edit_message_text(f"{call.message.text}\n\n(Tutti i Wumpa sono stati rubati!)", call.message.chat.id, call.message.message_id, reply_markup=None)
        else:
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=new_markup)
        return

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
        return

    # ACHIEVEMENT PAGINATION
    elif action.startswith("ach_page|"):
        page = int(action.split("|")[1])
        handle_achievements_cmd(call.message, page=page)
        bot.answer_callback_query(call.id)
        return

    # SEASON PAGINATION
    elif action.startswith("season_page|"):
        page = int(action.split("|")[1])
        handle_season_cmd(call.message, page=page)
        bot.answer_callback_query(call.id)
        return

    # SEASON PASS PURCHASE
    elif action == "buy_season_pass":
        from services.season_manager import SeasonManager
        manager = SeasonManager()
        success, msg = manager.purchase_season_pass(user_id)
        
        if success:
            bot.answer_callback_query(call.id, "✅ Acquisto completato!")
            # Update the season message to show the new status
            handle_season_cmd(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ Errore")
            bot.send_message(user_id, msg, parse_mode='markdown')
        return

def bot_polling_thread():
    bot.infinity_polling()

def regenerate_mana_job():
    """Hourly job to regenerate mana for all users (+10 capped at max_mana)"""
    try:
        session = user_service.db.get_session()
        from models.user import Utente
        
        # Get all users with mana < max_mana
        users = session.query(Utente).filter(Utente.mana < Utente.max_mana).all()
        
        count = 0
        for user in users:
            new_mana = min(user.mana + 10, user.max_mana)
            user.mana = new_mana
            count += 1
        
        session.commit()
        session.close()
        
        if count > 0:
            print(f"[MANA REGEN] Restored +10 mana for {count} users")
    except Exception as e:
        print(f"[MANA REGEN ERROR] {e}")

def spawn_daily_mob_job():
    # Random check to spawn between 9 and 18
    now = datetime.datetime.now()
    if 9 <= now.hour <= 18:
        # 10% chance every check (if run every hour? or minute?)
        # Let's assume this runs every hour.
        if random.random() < 0.2: 
            mob_id, attack_events = pve_service.spawn_daily_mob(chat_id=GRUPPO_AROMA)
            if mob_id:
                mob = pve_service.get_current_mob_status() # This might get the wrong mob if multiple?
                # Better to get by ID if possible, but get_current_mob_status gets the first one.
                # Since we just spawned it, it should be fine or we can fetch by ID.
                # But for the announcement message, we need mob details.
                # Let's use get_mob_by_id if available or just rely on current status.
                # Actually, pve_service.get_current_mob_status() returns the first non-dead mob.
                # If we have multiple, it might return an old one.
                # But let's assume for now it's okay or we should fetch by ID.
                # pve_service doesn't have get_mob_by_id exposed easily in this context without session.
                # Let's stick to get_current_mob_status() for now, or improve it later.
                
                if mob:
                    # Get the actual mob ID from spawn_daily_mob return value
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton("⚔️ Attacca", callback_data=f"attack_enemy|mob|{mob_id}"))
                    
                    msg_text = f"⚠️ Un {mob['name']} selvatico è apparso!\n📊 Lv. {mob.get('level', 1)} | ⚡ Vel: {mob.get('speed', 30)} | 🛡️ Res: {mob.get('resistance', 0)}%\n❤️ Salute: {mob['health']}/{mob['max_health']} HP\n⚔️ Danno: {mob['attack']}\n\nSconfiggilo per ottenere ricompense!"
                    
                    # Send with image if available
                    if mob.get('image') and os.path.exists(mob['image']):
                        try:
                            with open(mob['image'], 'rb') as photo:
                                bot.send_photo(GRUPPO_AROMA, photo, caption=msg_text, reply_markup=markup, )
                        except:
                            bot.send_message(GRUPPO_AROMA, msg_text, reply_markup=markup)
                    else:
                        bot.send_message(GRUPPO_AROMA, msg_text, reply_markup=markup, parse_mode='markdown')
                    
                    # Send immediate attack messages with buttons
                    if attack_events:
                        for event in attack_events:
                            msg = event['message']
                            image_path = event['image']
                            try:
                                if image_path and os.path.exists(image_path):
                                    with open(image_path, 'rb') as photo:
                                        bot.send_photo(GRUPPO_AROMA, photo, caption=msg, reply_markup=markup, )
                                else:
                                    bot.send_message(GRUPPO_AROMA, msg, reply_markup=markup, )
                            except:
                                bot.send_message(GRUPPO_AROMA, msg, reply_markup=markup, parse_mode='markdown')

def spawn_weekly_boss_job():
    success, msg, boss_id = pve_service.spawn_boss()
    if success and boss_id:
        boss = pve_service.get_current_boss_status()
        if boss:
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("⚔️ Attacca", callback_data=f"attack_enemy|mob|{boss_id}"),
                types.InlineKeyboardButton("✨ Attacco Speciale", callback_data=f"special_attack_enemy|mob|{boss_id}")
            )
            
            msg_text = f"☠️ **IL BOSS {boss['name']} È ARRIVATO!**\n\n"
            msg_text += f"📊 Lv. {boss.get('level', 5)} | ⚡ Vel: {boss.get('speed', 70)} | 🛡️ Res: {boss.get('resistance', 0)}%\n"
            msg_text += f"❤️ Salute: {boss['health']}/{boss['max_health']} HP\n"
            msg_text += f"⚔️ Danno: {boss['attack']}\n"
            if boss['description']:
                msg_text += f"📜 {boss['description']}\n"
            msg_text += "\nUNITI PER SCONFIGGERLO!"
            
            # Send with image if available
            if boss.get('image') and os.path.exists(boss['image']):
                try:
                    with open(boss['image'], 'rb') as photo:
                        bot.send_photo(GRUPPO_AROMA, photo, caption=msg_text, reply_markup=markup, parse_mode='markdown')
                except:
                    bot.send_message(GRUPPO_AROMA, msg_text, reply_markup=markup, parse_mode='markdown')
            else:
                bot.send_message(GRUPPO_AROMA, msg_text, reply_markup=markup, parse_mode='markdown')

def mob_attack_job():
    # Both mobs and bosses auto-attack periodically (all are Mob now, bosses have is_boss=True)
    
    # Process all enemy attacks (mobs and bosses)
    from database import Database
    from models.pve import Mob
    db = Database()
    session = db.get_session()
    active_enemies = session.query(Mob).filter_by(is_dead=False).all()
    session.close()
    
    if active_enemies:
        for enemy in active_enemies:
            attack_events = pve_service.mob_random_attack(specific_mob_id=enemy.id)
            if attack_events:
                markup = types.InlineKeyboardMarkup()
                markup.add(
                    types.InlineKeyboardButton("⚔️ Attacca", callback_data=f"attack_enemy|mob|{enemy.id}"),
                    types.InlineKeyboardButton("✨ Attacco Speciale", callback_data=f"special_attack_enemy|mob|{enemy.id}")
                )
                
                for event in attack_events:
                    msg = event['message']
                    image_path = event['image']
                    try:
                        if image_path and os.path.exists(image_path):
                            with open(image_path, 'rb') as photo:
                                bot.send_photo(GRUPPO_AROMA, photo, caption=msg, reply_markup=markup, )
                        else:
                            bot.send_message(GRUPPO_AROMA, msg, reply_markup=markup, )
                    except Exception as e:
                        print(f"Error sending enemy attack: {e}")
                        try:
                            bot.send_message(GRUPPO_AROMA, msg, reply_markup=markup)
                        except Exception as e2:
                            print(f"Error sending enemy attack (no markdown): {e2}")

if __name__ == "__main__":
    polling_thread = threading.Thread(target=bot_polling_thread)
    polling_thread.start()
    
    # Schedule jobs
    schedule.every().hour.do(spawn_daily_mob_job)
    schedule.every().hour.do(regenerate_mana_job)  # +10 mana every hour for all users
    schedule.every(10).seconds.do(mob_attack_job)
    schedule.every().sunday.at("20:00").do(spawn_weekly_boss_job)
    
    # Sunday reset removed - characters persist permanently
    # Sunday reset removed - characters persist permanently
    
    while True:
        schedule.run_pending()
        time.sleep(1)
