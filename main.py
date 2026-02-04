from telebot import types, util
from settings import *
import schedule
import time
import datetime
import threading
import os
import random
import socket
from io import BytesIO
from database import Database
from models.user import Utente

def escape_markdown(text):
    """Helper to escape markdown characters for Telegram"""
    if not text:
        return ""
    # Characters to escape for Markdown (V1)
    # _, *, [, `
    return str(text).replace("_", "\\_").replace("*", "\\*").replace("[", "\\[").replace("`", "\\`")

def safe_answer_callback(call_id, text=None, show_alert=False):
    """Safely answer a callback query, ignoring timeout errors"""
    try:
        bot.answer_callback_query(call_id, text=text, show_alert=show_alert)
    except Exception as e:
        # Ignore "query is too old" or "query ID is invalid" errors
        err_msg = str(e).lower()
        if "query is too old" in err_msg or "query id is invalid" in err_msg:
            pass
        else:
            print(f"[ERROR] Failed to answer callback {call_id}: {e}")

# Image processing for grayscale conversion
try:
    from PIL import Image, ImageEnhance
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("⚠️ PIL/Pillow not available, grayscale images will not work")

def format_mob_stats(mob, show_full=False):
    """Format mob stats, obscuring sensitive info if not authorized"""
    level = mob.get('level', 1)
    
    if show_full:
        # Full stats (Scouter active)
        hp_text = f"{mob['health']}/{mob['max_health']}"
        speed_text = f"{mob.get('speed', 30)}"
        res_text = f"{mob.get('resistance', 0)}%"
        atk_text = f"{mob['attack']}"
        # extra = "👁️ **Scouter Attivo**: Statistiche complete visibili!"
        extra = ""
    else:
        # Obscured stats (Default)
        hp_text = "???"
        speed_text = "???"
        res_text = "???"
        atk_text = "???"
        extra = ""

    return f"📊 Lv. {level} | ⚡ Vel: {speed_text} | 🛡️ Res: {res_text}\n❤️ Salute: {hp_text} HP\n⚔️ Danno: {atk_text}\n{extra}"

def get_rarity_emoji(rarity):
    """Get emoji for rarity level (1-5)"""
    rarity = int(rarity) if rarity else 1
    if rarity == 1: return "⚪" # Comune
    if rarity == 2: return "🟢" # Non Comune
    if rarity == 3: return "🔵" # Raro
    if rarity == 4: return "🟣" # Epico
    if rarity == 5: return "🟠" # Leggendario
    return "⚪"

def tnt_timeout(chat_id):
    """Callback when TNT timer expires. Sets trap to volatile."""
    try:
        bot.send_message(chat_id, "⚠️ **LA TNT È INSTABILE!**\n🔥 **IL PROSSIMO CHE PARLA ESPLODE!** 💥", parse_mode='markdown')
    except Exception as e:
        print(f"[ERROR] TNT Timeout send failed: {e}")

def nitro_timeout(chat_id):
    """Callback when Nitro activates"""
    try:
        bot.send_message(chat_id, "🟩 **LA NITRO È INSTABILE!**\n🔥 **IL PROSSIMO CHE PARLA ESPLODE!** 💥", parse_mode='markdown')
    except Exception as e:
        print(f"[ERROR] Nitro Timeout send failed: {e}")

# Trap Service
from services.trap_service import TrapService
from services.backup_service import BackupService
trap_service = TrapService()

# Services
from services.user_service import UserService
from services.item_service import ItemService
from services.game_service import GameService
from services.shop_service import ShopService
from services.wish_service import WishService
from services.pve_service import PvEService
from services.guild_service import GuildService
from services.character_service import CharacterService
from services.transformation_service import TransformationService
from services.stats_service import StatsService
from services.drop_service import DropService
from services.dungeon_service import DungeonService
from services.achievement_tracker import AchievementTracker
from services.crafting_service import CraftingService



from services.equipment_service import EquipmentService
from services.guide_service import GuideService
from utils.markup_utils import get_combat_markup

# Initialize Services
user_service = UserService()
item_service = ItemService()
game_service = GameService()
shop_service = ShopService()
wish_service = WishService()
pve_service = PvEService()
guild_service = GuildService()
character_service = CharacterService()
transformation_service = TransformationService()
stats_service = StatsService()
drop_service = DropService()
dungeon_service = DungeonService()
equipment_service = EquipmentService()
guide_service = GuideService()
crafting_service = CraftingService()
achievement_tracker = AchievementTracker()

# Track last viewed character for admins (for image upload feature)
admin_last_viewed_character = {}

# --- MONKEY PATCH: Auto-delete command messages ---
_original_message_handler = bot.message_handler

def _auto_delete_message_handler(*args, **kwargs):
    def decorator(handler):
        import functools
        @functools.wraps(handler)
        def wrapper(message, *a, **k):
            try:
                result = handler(message, *a, **k)
            except Exception as e:
                # If handler fails, still try to delete if it was a command
                # But re-raise exception after
                if hasattr(message, 'text') and message.text and message.text.startswith('/'):
                    try:
                        bot.delete_message(message.chat.id, message.message_id)
                    except:
                        pass
                raise e

            # Check if it's a command message (starts with /)
            if hasattr(message, 'text') and message.text and message.text.startswith('/'):
                try:
                    # Run deletion in a separate thread to not block execution? 
                    # Or just try/except. Telebot calls are synchronous usually.
                    # delete_message is fast.
                    bot.delete_message(message.chat.id, message.message_id)
                except Exception:
                    # Ignore errors (e.g. missing permissions, message already deleted)
                    pass
            return result
        
        return _original_message_handler(*args, **kwargs)(wrapper)
    return decorator

bot.message_handler = _auto_delete_message_handler
# --------------------------------------------------

@bot.message_handler(func=lambda m: trap_service.has_volatile_trap(m.chat.id), content_types=['text', 'photo', 'sticker', 'video', 'voice'])
def handle_trap_explosion(message):
    """Handle Trap explosion (TNT/Nitro)"""
    # Trigger and consume trap
    trap = trap_service.trigger_trap(message.chat.id, message.from_user.id)
    if not trap: return
    
    trap_type = trap.get('trap_type', 'TNT')
    
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    try:
        # Damage 30% HP
        db_user = user_service.get_user(user_id)
        if db_user:
            current_hp = db_user.current_hp if db_user.current_hp is not None else db_user.health
            damage = int(db_user.max_health * 0.30)
            new_hp = max(0, current_hp - damage)
            
            # Sync health/current_hp
            user_service.update_user(user_id, {'current_hp': new_hp, 'health': new_hp})
            
            icon = "🟩" if trap_type == 'NITRO' else "💥"
            trap_name = "la NITRO" if trap_type == 'NITRO' else "la TNT"
            
            msg = f"{icon} **BOOM!** @{username} ha fatto esplodere {trap_name}!\n💔 Hai perso {damage} HP (30%)!"
            if new_hp == 0:
                msg += "\n💀 Sei morto carbonizzato!"
            
            bot.reply_to(message, msg, parse_mode='markdown')
    except Exception as e:
        print(f"[ERROR] Trap Explosion: {e}")


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
def send_welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username
    nome = message.from_user.first_name
    cognome = message.from_user.last_name
    
    # Register or get user
    utente = user_service.get_user(user_id)
    if not utente:
        user_service.create_user(user_id, username, nome, cognome)
        utente = user_service.get_user(user_id)
        
        welcome_msg = f"🎮 Benvenuto in **aROMa RPG**, {nome}!\n\n"
        welcome_msg += "Sei stato registrato con successo. Usa i bottoni qui sotto per navigare nel gioco!\n\n"
        welcome_msg += "📖 Usa /help per vedere tutti i comandi disponibili."
    else:
        welcome_msg = f"👋 Bentornato, {utente.game_name or nome}!\n\n"
        welcome_msg += "Usa i bottoni qui sotto per navigare nel gioco!"
    
    # Send welcome message with main menu
    bot.send_message(message.chat.id, welcome_msg, reply_markup=get_main_menu(), parse_mode='markdown')

def get_main_menu():
    """Create the main menu with persistent keyboard buttons"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    # Row 1: Profilo e Scegli Personaggio
    markup.add(
        types.KeyboardButton("👤 Profilo"),
        types.KeyboardButton("👤 Scegli Personaggio")
    )
    
    # Row 2: Inventario e Negozio Pozioni
    markup.add(
        types.KeyboardButton("🎒 Inventario"),
        types.KeyboardButton("🧪 Negozio Pozioni")
    )

    # Row 2.5: Mercato
    markup.add(
        types.KeyboardButton("🏪 Mercato Globale")
    )
    
    # Row 3: Achievement e Stagione
    markup.add(
        types.KeyboardButton("🏆 Achievement"),
        types.KeyboardButton("🏆 Classifica")
    )
    
    markup.add(
        types.KeyboardButton("🌟 Stagione")
    )
    
    # Row 4: Gilda e Locanda
    markup.add(
        types.KeyboardButton("🏰 Gilda"),
        types.KeyboardButton("🏨 Locanda")
    )
    
    # Row 5: Guide only (Dungeon now runs automatically)
    markup.add(
        types.KeyboardButton("📖 Guida")
    )
    
    return markup

@bot.message_handler(commands=['menu'])
def show_menu(message):
    """Show the main menu keyboard"""
    bot.send_message(message.chat.id, "📱 **Menu Principale**\n\nUsa i bottoni qui sotto:", reply_markup=get_main_menu(), parse_mode='markdown')

@bot.message_handler(func=lambda message: message.text == "👤 Profilo")
def handle_profilo_button(message):
    cmd = BotCommands(message, bot)
    cmd.handle_profile()

@bot.message_handler(func=lambda message: message.text == "🎒 Inventario")
def handle_inventario_button(message):
    handle_inventario_cmd(message)

@bot.message_handler(func=lambda message: message.text == "🧪 Negozio Pozioni")
def handle_shop_potions_button(message):
    cmd = BotCommands(message, bot)
    cmd.handle_shop_potions()

@bot.message_handler(func=lambda message: message.text == "👤 Scegli Personaggio")
def handle_scegli_personaggio_button(message):
    cmd = BotCommands(message, bot)
    cmd.handle_choose_character()

@bot.message_handler(func=lambda message: message.text == "👤 Scegli il personaggio")
def handle_scegli_personaggio_old_button(message):
    """Backward compatibility for old button"""
    cmd = BotCommands(message, bot)
    cmd.handle_choose_character()

@bot.message_handler(func=lambda message: message.text == "🏆 Achievement")
def handle_achievement_button(message):
    handle_achievements_cmd(message)

@bot.message_handler(func=lambda message: message.text == "🌟 Stagione")
def handle_stagione_button(message):
    handle_season_cmd(message)

@bot.message_handler(func=lambda message: message.text == "🏰 Gilda")
def handle_gilda_button(message):
    handle_guild_cmd(message)

@bot.message_handler(func=lambda message: message.text == "🏨 Locanda")
def handle_locanda_button(message):
    handle_inn_cmd(message)

# Dungeon button removed - dungeons now start automatically
# @bot.message_handler(func=lambda message: message.text == "🏰 Dungeon")
# def handle_dungeon_button(message):
#     cmd = BotCommands(message, bot)
#     cmd.handle_dungeons_list()


@bot.message_handler(func=lambda message: message.text == "📖 Guida")
def handle_guide_button(message):
    # Show main guide menu
    categories = guide_service.get_categories()
    markup = types.InlineKeyboardMarkup()
    for key, title in categories:
        markup.add(types.InlineKeyboardButton(title, callback_data=f"guide_cat|{key}"))
    
    bot.send_message(message.chat.id, "📚 **Guida di aROMa**\n\nSeleziona un argomento per saperne di più:", reply_markup=markup, parse_mode='markdown')

@bot.message_handler(commands=['classifica', 'ranking', 'top'])
def handle_ranking_cmd(message):
    """Show ranking"""
    cmd = BotCommands(message, bot)
    cmd.handle_classifica()

@bot.message_handler(commands=['dungeons'])
def handle_dungeons_cmd(message):
    """Show dungeons list"""
    cmd = BotCommands(message, bot)
    cmd.handle_dungeons_list()

@bot.message_handler(commands=['info', 'profilo', 'me'])
def handle_info_cmd(message):
    """Show user profile using the original handler"""
    cmd = BotCommands(message, bot)
    cmd.handle_profile()

@bot.message_handler(commands=['inventario', 'inv'])
def handle_inventario_cmd(message):
    """Show user inventory with interactive buttons"""
    user_id = message.from_user.id
    inventory = item_service.get_inventory(user_id)
    
    if not inventory:
        bot.reply_to(message, "🎒 Il tuo inventario è vuoto!")
        return
    
    msg = "🎒 **Il tuo Inventario**\nClicca su un oggetto per usarlo.\n\n"
    for item, quantity in inventory:
        meta = item_service.get_item_metadata(item)
        emoji = meta.get('emoji', '🎒')
        desc = meta.get('descrizione', '')
        
        # If description is empty, check if it's a potion
        if not desc:
            from services.potion_service import PotionService
            potion_service = PotionService()
            potion = potion_service.get_potion_by_name(item)
            if potion:
                desc = potion.get('descrizione', '')
                p_type = potion.get('tipo', '')
                if p_type == 'health_potion':
                    emoji = '❤️'
                elif p_type == 'mana_potion':
                    emoji = '💙'
                elif p_type == 'full_restore':
                    emoji = '💖'
                elif emoji == '🎒': 
                    emoji = '🧪'

        msg += f"{emoji} {item} - {desc} (x{quantity})\n"
    
    # Create buttons for each item
    markup = types.InlineKeyboardMarkup()
    
    # Check Dragon Balls
    from services.wish_service import WishService
    wish_service = WishService()
    utente = user_service.get_user(user_id)
    shenron, porunga = wish_service.get_dragon_ball_counts(utente)
    
    if shenron >= 7:
        markup.add(types.InlineKeyboardButton("🐉 Evoca Shenron", callback_data="wish_summon|Shenron"))
    if porunga >= 7:
        markup.add(types.InlineKeyboardButton("🐲 Evoca Porunga", callback_data="wish_summon|Porunga"))
        
    for item, quantity in inventory:
        # Skip Dragon Balls in "Use" buttons
        if "Sfera del Drago" in item:
            continue
            
        # Get Emoji
        meta = item_service.get_item_metadata(item)
        emoji = meta.get('emoji', '🎒')
        
        # Check potion emoji
        from services.potion_service import PotionService
        potion_service = PotionService()
        potion = potion_service.get_potion_by_name(item)
        if potion:
            p_type = potion.get('tipo', '')
            if p_type == 'health_potion':
                emoji = '❤️'
            elif p_type == 'mana_potion':
                emoji = '💙'
            elif p_type == 'full_restore':
                emoji = '💖'
            elif emoji == '🎒': 
                emoji = '🧪'
            
        # Create a button for each item type (Emoji + Name)
        markup.add(types.InlineKeyboardButton(f"{emoji} {item}", callback_data=f"use_item|{item}"))
    
    bot.reply_to(message, msg, reply_markup=markup, parse_mode='markdown')

@bot.message_handler(commands=['achievements', 'ach'])
def handle_achievements_cmd(message, page=0, user_id=None, category=None):
    """Show user achievements with pagination"""
    if user_id is None:
        user_id = message.from_user.id
    
    if category is None or category == "menu":
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("🐉 Dragon Ball", callback_data="ach_cat|dragon_ball"),
            types.InlineKeyboardButton("🏆 Classici", callback_data="ach_cat|classici")
        )
        msg = "🏆 **I TUOI ACHIEVEMENT**\n\nSeleziona una categoria per visualizzare i tuoi progressi:"
        if hasattr(message, 'message_id') and not hasattr(message, 'text'):
            bot.edit_message_text(msg, message.chat.id, message.message_id, reply_markup=markup, parse_mode='markdown')
        else:
            bot.reply_to(message, msg, reply_markup=markup, parse_mode='markdown')
        return

    from services.achievement_tracker import AchievementTracker
    tracker = AchievementTracker()
    
    stats = tracker.get_achievement_stats(user_id)
    all_achievements = tracker.get_all_achievements_with_progress(user_id, category=category)
    
    # Sort: Unlocked first, then by tier, then by name
    tier_map = {'bronze': 1, 'silver': 2, 'gold': 3, 'platinum': 4, 'diamond': 5, 'legendary': 6}
    all_achievements.sort(key=lambda x: (not x['is_completed'], -tier_map.get(x['achievement'].tier, 0), x['achievement'].name))
    
    ITEMS_PER_PAGE = 5
    total_pages = (len(all_achievements) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    
    if total_pages == 0:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Indietro", callback_data="ach_cat|menu"))
        bot.edit_message_text("Nessun achievement disponibile in questa categoria.", message.chat.id, message.message_id, reply_markup=markup) if hasattr(message, 'message_id') and not hasattr(message, 'text') else bot.reply_to(message, "Nessun achievement disponibile in questa categoria.", reply_markup=markup)
        return

    if page >= total_pages: page = total_pages - 1
    if page < 0: page = 0
    
    start_idx = page * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    page_items = all_achievements[start_idx:end_idx]
    
    cat_name = "DRAGON BALL 🐉" if category == "dragon_ball" else "CLASSICI 🏆"
    msg = f"🏆 **ACHIEVEMENT: {cat_name}**\n"
    msg += f"📊 Progresso Totale: `{stats['completed']}/{stats['total_achievements']}`\n\n"
    
    for item in page_items:
        a = item['achievement']
        unlocked = item['is_completed']
        progress = item['progress']
        max_progress = a.max_progress
        
        status_emoji = "✅" if unlocked else "🔒"
        tier_emoji = {
            'bronze': '🥉', 
            'silver': '🥈', 
            'gold': '🥇', 
            'platinum': '🏅', 
            'diamond': '💎', 
            'legendary': '👑'
        }.get(a.tier, "🏆")
        
        msg += f"{status_emoji} {tier_emoji} **{a.name}**\n"
        msg += f"_{a.description}_\n"
        
        if not unlocked:
            # Progress bar
            max_p = max_progress if max_progress and max_progress > 0 else 1
            percent = int((progress / max_p) * 10)
            bar = "▰" * percent + "▱" * (10 - percent)
            msg += f"[{bar}] `{progress}/{max_progress}`\n"
        else:
            msg += "✨ *Completato!*\n"
        msg += "\n"
        
    msg += f"📄 Pagina {page + 1} di {total_pages}"
    
    markup = types.InlineKeyboardMarkup()
    nav_buttons = []
    if page > 0:
        nav_buttons.append(types.InlineKeyboardButton("⬅️ Indietro", callback_data=f"ach_page|{category}|{page-1}"))
    if page < total_pages - 1:
        nav_buttons.append(types.InlineKeyboardButton("Avanti ➡️", callback_data=f"ach_page|{category}|{page+1}"))
    
    if nav_buttons:
        markup.row(*nav_buttons)
    
    markup.row(types.InlineKeyboardButton("🔙 Menu Achievement", callback_data="ach_cat|menu"))
        
    # Check if it's a callback or a command
    if hasattr(message, 'message_id') and not hasattr(message, 'text'): # Likely a callback
        bot.edit_message_text(msg, message.chat.id, message.message_id, reply_markup=markup, parse_mode='markdown')
    else:
        bot.reply_to(message, msg, reply_markup=markup, parse_mode='markdown')

@bot.message_handler(commands=['guilds', 'gilde'])
def handle_guilds_list_cmd(message):
    """Show list of all guilds"""
    guilds = guild_service.get_guilds_list()
    if not guilds:
        bot.reply_to(message, "🏰 Non ci sono ancora gilde in aROMaLand. Fondane una con /found!")
        return
        
    msg = "🏰 **Gilde di aROMaLand**\n\n"
    markup = types.InlineKeyboardMarkup()
    for g in guilds:
        msg += f"🔹 **{g['name']}** (Lv. {g['level']})\n"
        msg += f"   👥 Membri: {g['members']}/{g['limit']}\n\n"
        
        # Add join button if not full
        if g['members'] < g['limit']:
             markup.add(types.InlineKeyboardButton(f"➕ Unisciti a {g['name']}", callback_data=f"guild_join|{g['id']}"))
        
    bot.reply_to(message, msg, reply_markup=markup, parse_mode='markdown')

def handle_guild_view(call):
    """Refresh the guild management view"""
    guild = guild_service.get_user_guild(call.from_user.id)
    if not guild or guild['role'] != "Leader":
        safe_answer_callback(call.id, "Solo il capogilda può accedere a questo menu!", show_alert=True)
        return
        
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(f"🏠 Locanda ({guild['inn_level'] * 500} W)", callback_data="guild_upgrade|inn"))
    markup.add(types.InlineKeyboardButton(f"⚔️ Armeria ({(guild['armory_level'] + 1) * 750} W)", callback_data="guild_upgrade|armory"))
    markup.add(types.InlineKeyboardButton(f"🏘️ Villaggio ({guild['village_level'] * 1000} W)", callback_data="guild_upgrade|village"))
    markup.add(types.InlineKeyboardButton(f"🔞 Bordello ({(guild['bordello_level'] + 1) * 1500} W)", callback_data="guild_upgrade|bordello"))
    
    # Visual button for Locanda
    markup.add(types.InlineKeyboardButton("🏨 Vai alla Locanda", callback_data="guild_inn_view"))
    
    markup.add(types.InlineKeyboardButton("✏️ Rinomina", callback_data="guild_rename_ask"),
               types.InlineKeyboardButton("🗑️ Elimina", callback_data="guild_delete_ask"))
    markup.add(types.InlineKeyboardButton("🔙 Indietro", callback_data="guild_back_main"))
    
    bot.edit_message_text(f"⚙️ **Gestione Gilda: {guild['name']}**\n\nBanca: {guild['wumpa_bank']} Wumpa", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='markdown')

# /bordello command removed in favor of buttons in Inn view

@bot.message_handler(commands=['guild', 'gilda'])
def handle_guild_cmd(message):
    """Show guild status or creation menu"""
    user_id = message.from_user.id
    guild = guild_service.get_user_guild(user_id)
    
    if not guild:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🏰 Fonda una Gilda", callback_data="guild_found_start"))
        markup.add(types.InlineKeyboardButton("📜 Lista Gilde", callback_data="guild_list_view"))
        bot.reply_to(message, "🛡️ **Sistema di Gilde**\n\nNon fai ancora parte di nessuna gilda. Al livello 10 puoi fondare il tuo villaggio in aROMaLand!", reply_markup=markup, parse_mode='markdown')
    else:
        # Show guild status
        msg = f"🏰 **Gilda: {guild['name']}**\n"
        leader = user_service.get_user(guild['leader_id'])
        leader_name = f"@{leader.username}" if leader and leader.username else (leader.nome if leader else f"{guild['leader_id']}")
        msg += f"👑 **Capo**: {leader_name}\n"
        msg += f"💰 **Banca**: {guild['wumpa_bank']} Wumpa\n"
        msg += f"👥 **Membri**: {guild['member_limit']} (max)\n\n"
        msg += f"🏠 **Locanda**: Lv. {guild['inn_level']}\n"
        msg += f"⚔️ **Armeria**: Lv. {guild['armory_level']}\n"
        msg += f"🏘️ **Villaggio**: Lv. {guild['village_level']}\n"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("👥 Membri", callback_data=f"guild_members|{guild['id']}"))
        markup.add(types.InlineKeyboardButton("🏨 Locanda", callback_data="guild_inn_view"))
        markup.add(types.InlineKeyboardButton("🔨 Armeria", callback_data="guild_armory_view"))
        markup.add(types.InlineKeyboardButton("📦 Magazzino", callback_data="guild_warehouse"))
        markup.add(types.InlineKeyboardButton("💰 Deposita Wumpa", callback_data="guild_deposit_start"))
        if guild['role'] == "Leader":
            markup.add(types.InlineKeyboardButton("⚙️ Gestisci Gilda", callback_data="guild_manage_menu"))
        else:
            markup.add(types.InlineKeyboardButton("🚪 Abbandona Gilda", callback_data="guild_leave_ask"))
        
        bot.send_message(message.chat.id, msg, reply_markup=markup, parse_mode='markdown')

@bot.message_handler(commands=['found', 'fonda'])
def handle_found_cmd(message):
    """Start guild creation flow"""
    user_id = message.from_user.id
    utente = user_service.get_user(user_id)
    
    if utente.livello < 10:
        bot.reply_to(message, "❌ Devi essere almeno al livello 10 per fondare una gilda!")
        return
        
    if utente.points < 1000:
        bot.reply_to(message, "❌ Ti servono 1000 Wumpa per fondare una gilda!")
        return
        
    msg = bot.reply_to(message, "🏰 **Fondazione Gilda**\n\nInserisci il nome della tua gilda (max 32 caratteri):")
    bot.register_next_step_handler(msg, process_guild_name)

def process_guild_name(message):
    name = message.text
    if not name or len(name) > 32:
        bot.reply_to(message, "❌ Nome non valido. Riprova con /found.")
        return
        
    # Show map selection (simulated for now)
    markup = types.InlineKeyboardMarkup()
    for i in range(3):
        row = []
        for j in range(3):
            x, y = i*30 + 10, j*30 + 10
            row.append(types.InlineKeyboardButton(f"📍 {x},{y}", callback_data=f"guild_create_final|{name}|{x}|{y}"))
        markup.row(*row)
    
    # Send the map selection message
    try:
        with open("/home/alan/.gemini/antigravity/brain/6760c513-3c30-43b9-a17f-21b2ff8f07a5/aroma_land_map_1768764144665.png", 'rb') as photo:
            bot.send_photo(message.chat.id, photo, caption=f"🗺️ **Scegli la posizione per {name}**\n\nSeleziona una coordinata sulla mappa:", reply_markup=markup, parse_mode='markdown')
    except Exception:
        bot.send_message(message.chat.id, f"🗺️ **Scegli la posizione per {name}**\n\nSeleziona una coordinata sulla mappa:", reply_markup=markup, parse_mode='markdown')

def process_guild_rename(message):
    new_name = message.text
    if not new_name or len(new_name) > 32:
        bot.reply_to(message, "❌ Nome non valido (max 32 caratteri).")
        return
        
    user_id = message.from_user.id
    success, msg = guild_service.rename_guild(user_id, new_name)
    bot.reply_to(message, msg)
        
def process_guild_deposit(message):
    try:
        amount = int(message.text)
        success, msg = guild_service.deposit_wumpa(message.from_user.id, amount)
        bot.reply_to(message, msg)
    except ValueError:
        bot.reply_to(message, "❌ Inserisci un numero valido.")

@bot.message_handler(commands=['inn', 'locanda'])
def handle_inn_cmd(message):
    """Access the public inn or guild inn"""
    # Restrict to private chat
    if message.chat.type != 'private':
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📩 Vai alla Locanda (Privato)", url=f"https://t.me/{bot.get_me().username}?start=inn"))
        bot.send_message(message.chat.id, "❌ La Locanda è disponibile solo in chat privata per evitare spam!", reply_markup=markup)
        return

    user_id = message.from_user.id
    status = user_service.get_resting_status(user_id)
    guild = guild_service.get_user_guild(user_id)
    
    msg = "🏨 **Locanda Pubblica di aROMaLand**\n\n"
    if status:
        utente = user_service.get_user(user_id)
        msg += f"🛌 Stai riposando da {status['minutes']} minuti.\n"
        
        # HP Status
        hp_msg = f"+{status['hp']} HP"
        current_hp = utente.current_hp if hasattr(utente, 'current_hp') and utente.current_hp is not None else utente.health
        if status['hp'] < status['minutes'] and (current_hp + status['hp'] >= utente.max_health):
             hp_msg += " (Max)"
             
        # Mana Status
        mana_msg = f"+{status['mana']} Mana"
        if status['mana'] < status['minutes'] and (utente.mana + status['mana'] >= utente.max_mana):
             mana_msg += " (Max)"
             
        msg += f"💖 Recupero stimato: {hp_msg}, {mana_msg}.\n\n"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🛑 Smetti di Riposare", callback_data="inn_rest_stop"))
    else:
        msg += "Qui chiunque può riposare gratuitamente. Recupererai **1 HP e 1 Mana al minuto**, ma non guadagnerai EXP.\n\n"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🛌 Riposa", callback_data="inn_rest_start"))
        if guild:
            markup.add(types.InlineKeyboardButton(f"🏰 Vai alla Locanda di {guild['name']}", callback_data="guild_inn_view"))
            
    try:
        file_id = getattr(bot, 'locanda_file_id', None)
        if file_id:
            bot.send_photo(message.chat.id, file_id, caption=msg, reply_markup=markup, parse_mode='markdown')
        else:
            with open("images/locanda.png", 'rb') as photo:
                res = bot.send_photo(message.chat.id, photo, caption=msg, reply_markup=markup, parse_mode='markdown')
                bot.locanda_file_id = res.photo[-1].file_id
        return
    except Exception:
        bot.reply_to(message, msg, reply_markup=markup, parse_mode='markdown')

@bot.callback_query_handler(func=lambda call: call.data == "guild_inn_view")
def handle_guild_inn_view(call):
    """Show the guild-specific inn view"""
    user_id = call.from_user.id
    guild = guild_service.get_user_guild(user_id)
    if not guild:
        safe_answer_callback(call.id, "Non fai parte di nessuna gilda!", show_alert=True)
        return
    
    # Defaults
    brewery_level = guild.get('brewery_level', 1) or 1
    bordello_level = guild.get('bordello_level', 0)
    
    # Bonuses
    beer_bonus = 15 + (brewery_level * 5)
    vigore_duration = 60 + (bordello_level - 1) * 15 if bordello_level > 0 else 60
        
    msg = f"🏠 **Locanda della Gilda: {guild['name']}** (Lv. {guild['inn_level']})\n\n"
    msg += "Qui puoi riposare, bere una birra o visitare le strutture annesse.\n\n"
    
    msg += f"🍻 **Birrificio (Lv. {brewery_level})**\n"
    msg += f"La Birra Artigianale potenzia le pozioni del **{beer_bonus}%** per 30 min.\n"
    
    if bordello_level > 0:
        msg += f"\n🔞 **Bordello delle Elfe (Lv. {bordello_level})**\n"
        msg += f"Il buff Vigore dura **{vigore_duration} minuti**.\n"
    else:
        msg += "\n🔞 **Bordello delle Elfe**: Non costruito.\n"
    
    # Check resting
    resting_status = user_service.get_resting_status(user_id)
    
    markup = types.InlineKeyboardMarkup()
    if resting_status:
        # Show resting stats
        mult = 1.0 + (guild['inn_level'] * 0.5)
        hp_min = int(1 * mult)
        mana_min = int(1 * mult)
        msg += f"\n💤 **Stai riposando!**\n⏱️ Tempo: {resting_status['minutes']} min\n"
        msg += f"💖 Recupero: {hp_min} HP/min, {mana_min} Mana/min\n"
        markup.add(types.InlineKeyboardButton("🛌 Svegliati", callback_data="guild_wakeup"))
    else:
        markup.add(types.InlineKeyboardButton("🛌 Riposa", callback_data="guild_rest"))

    markup.add(types.InlineKeyboardButton(f"🍺 Bevi Birra", callback_data="guild_buy_beer"))
    if bordello_level > 0:
        markup.add(types.InlineKeyboardButton(f"🔞 Bordello", callback_data="guild_buy_vigore"))
    
    # Leader Upgrades
    is_leader = guild_service.is_guild_leader(user_id)
    if is_leader:
        if brewery_level < 5:
            cost = (brewery_level + 1) * 600
            markup.add(types.InlineKeyboardButton(f"⬆️ Potenzia Birrificio ({cost} W)", callback_data="guild_upgrade_brewery"))
            
        if bordello_level < 5:
            if bordello_level == 0:
                cost = 2000
                lbl = "Costruisci Bordello"
            else:
                cost = (bordello_level + 1) * 1000
                lbl = "Potenzia Bordello"
            markup.add(types.InlineKeyboardButton(f"⬆️ {lbl} ({cost} W)", callback_data="guild_upgrade_brothel"))
            
    markup.add(types.InlineKeyboardButton("🔙 Torna alla Gilda", callback_data="guild_view"))
    
    image_path = guild_service.get_inn_image(guild['inn_level'])
    
    try:
        # Delete old message and send new one with photo
        bot.delete_message(call.message.chat.id, call.message.message_id)
        with open(image_path, 'rb') as photo:
            bot.send_photo(call.message.chat.id, photo, caption=msg, reply_markup=markup, parse_mode='markdown')
    except Exception as e:
        print(f"Error showing inn view: {e}")
        bot.send_message(call.message.chat.id, msg, reply_markup=markup, parse_mode='markdown')

@bot.callback_query_handler(func=lambda call: call.data == "guild_buy_beer")
def handle_guild_buy_beer(call):
    """Buy a craft beer via button"""
    user_id = call.from_user.id
    success, msg = guild_service.buy_craft_beer(user_id)
    safe_answer_callback(call.id, msg, show_alert=not success)
    
    if success:
        bot.send_message(call.message.chat.id, msg, parse_mode='markdown')
        # Refresh view? No, message is enough. Or refresh logic.
        handle_guild_inn_view(call)

@bot.callback_query_handler(func=lambda call: call.data == "guild_buy_vigore")
def handle_guild_buy_vigore(call):
    """Buy vigore bonus via button"""
    user_id = call.from_user.id
    success, msg = guild_service.apply_vigore_bonus(user_id)
    safe_answer_callback(call.id, msg, show_alert=not success)
    
    if success:
        bot.send_message(call.message.chat.id, msg, parse_mode='markdown')
        handle_guild_inn_view(call)

@bot.callback_query_handler(func=lambda call: call.data == "guild_upgrade_brewery")
def handle_guild_upgrade_brewery(call):
    """Upgrade brewery button"""
    user_id = call.from_user.id
    success, msg = guild_service.upgrade_brewery(user_id)
    safe_answer_callback(call.id, msg, show_alert=not success)
    if success:
        bot.send_message(call.message.chat.id, msg, parse_mode='markdown')
        handle_guild_inn_view(call)

@bot.callback_query_handler(func=lambda call: call.data == "guild_upgrade_brothel")
def handle_guild_upgrade_brothel(call):
    """Upgrade brothel button"""
    user_id = call.from_user.id
    success, msg = guild_service.upgrade_brothel(user_id)
    safe_answer_callback(call.id, msg, show_alert=not success)
    if success:
        bot.send_message(call.message.chat.id, msg, parse_mode='markdown')
        handle_guild_inn_view(call)

@bot.callback_query_handler(func=lambda call: call.data == "guild_armory_view")
def handle_guild_armory_view(call):
    """View guild armory and crafting queue"""
    safe_answer_callback(call.id)
    guild = guild_service.get_user_guild(call.from_user.id)
    
    if not guild:
        bot.answer_callback_query(call.id, "Non fai parte di nessuna gilda!", show_alert=True)
        return
    
    from services.crafting_service import CraftingService
    from sqlalchemy import text
    from datetime import datetime
    crafting_service = CraftingService()
        
    msg = f"🔨 **Armeria della Gilda: {guild['name']}** (Lv. {guild['armory_level']})\n\n"
    msg += f"**Slot Crafting**: {guild['armory_level']}\n"
    msg += f"**Velocità**: -{(1 - (0.65 + guild['armory_level'] * 0.05)) * 100:.0f}% tempo base\n\n"
    
    # Show active crafting jobs
    session = crafting_service.db.get_session()
    try:
        active_jobs = session.execute(text("""
            SELECT cq.id, cq.completion_time, e.name, cq.user_id
            FROM crafting_queue cq
            JOIN equipment e ON cq.equipment_id = e.id
            WHERE cq.guild_id = :gid AND cq.status = 'in_progress'
            ORDER BY cq.completion_time ASC
        """), {"gid": guild['id']}).fetchall()
        
        if active_jobs:
            msg += "🔧 **Crafting in Corso**:\n"
            now = datetime.now()
            for job_id, completion_time, eq_name, user_id in active_jobs:
                time_left = completion_time - now
                if time_left.total_seconds() > 0:
                    minutes = int(time_left.total_seconds() // 60)
                    seconds = int(time_left.total_seconds() % 60)
                    # Show username only if it's the current user
                    user_marker = "📌" if user_id == call.from_user.id else "👤"
                    msg += f"⏱️ {user_marker} {eq_name} - {minutes}m {seconds}s\n"
                else:
                    user_marker = "📌" if user_id == call.from_user.id else "👤"
                    msg += f"✅ {user_marker} {eq_name} - Pronto!\n"
            msg += "\n"
        else:
            msg += "💤 Nessun crafting in corso\n\n"
        
        # Get available equipment to craft
        equipment_list = session.execute(text("""
            SELECT id, name, rarity, min_level, crafting_time, crafting_requirements
            FROM equipment
            ORDER BY rarity ASC, min_level ASC
            LIMIT 10
        """)).fetchall()
        
        if equipment_list:
            msg += "📜 **Equipaggiamento Disponibile**:\n"
            rarity_symbols = {1: '●', 2: '◆', 3: '★', 4: '✦', 5: '✪'}
            for eq in equipment_list:
                eq_id, name, rarity, min_lvl, craft_time, requirements = eq
                symbol = rarity_symbols.get(rarity, '●')
                msg += f"{symbol} {name} (Lv.{min_lvl}, {craft_time//60}min)\n"
        else:
            msg += "_Nessun equipaggiamento disponibile._\n"
    finally:
        session.close()
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⚒️ Inizia Crafting", callback_data="craft_select_equipment"))
    markup.add(types.InlineKeyboardButton("📦 Risorse", callback_data="craft_view_resources"))
    
    # Add claim button if there are completed crafts
    completed_count = session.execute(text("""
        SELECT COUNT(*) FROM crafting_queue
        WHERE guild_id = :gid AND status = 'in_progress' 
        AND completion_time <= NOW()
    """), {"gid": guild['id']}).scalar() or 0
    
    if completed_count > 0:
        markup.add(types.InlineKeyboardButton(f"✅ Riscuoti {completed_count} Crafting Completati", callback_data="craft_claim_all"))
    
    markup.add(types.InlineKeyboardButton("🔙 Torna alla Gilda", callback_data="guild_back_main"))
    
    bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, 
                         reply_markup=markup, parse_mode='markdown')

def handle_craft_select_equipment(call):
    """Show Set selection for crafting (Filtered by Armory Level)"""
    print("[DEBUG] handle_craft_select_equipment called")
    safe_answer_callback(call.id)
    guild = guild_service.get_user_guild(call.from_user.id)
    
    if not guild:
        bot.answer_callback_query(call.id, "Non fai parte di nessuna gilda!", show_alert=True)
        return
        
    armory_level = guild['armory_level']
    
    from services.crafting_service import CraftingService
    from sqlalchemy import text
    crafting_service = CraftingService()
    session = crafting_service.db.get_session()
    
    try:
        # Get distinct sets that have at least one craftable item (rarity <= armory_level)
        sets = session.execute(text("""
            SELECT DISTINCT set_name FROM equipment 
            WHERE set_name IS NOT NULL AND rarity <= :lvl
            ORDER BY set_name ASC
        """), {"lvl": armory_level}).fetchall()
        
        # Count misc items craftable
        misc_count = session.execute(text("""
            SELECT COUNT(*) FROM equipment 
            WHERE set_name IS NULL AND rarity <= :lvl
        """), {"lvl": armory_level}).scalar()
        
        msg = f"🔨 **Armeria della Gilda (Lv. {armory_level})**\n\n"
        msg += "Ecco i Set che puoi craftare con il livello attuale dell'armeria.\n"
        msg += "Il Fabbro mostra solo ciò che è in grado di forgiare!\n\n"
        msg += "I **Set** forniscono bonus speciali se indossi 2, 4 o 6 pezzi dello stesso tipo!\n"
        
        markup = types.InlineKeyboardMarkup()
        
        if not sets and misc_count == 0:
             msg += "⚠️ _Nessun oggetto disponibile per questo livello di armeria._"
        
        # Add buttons for Sets
        for row in sets:
            set_name = row[0]
            # Emojis for flavor
            emoji = "🛡️" if "Kaioshin" in set_name else "⚔️" if "Saiyan" in set_name else "🔮" if "Androide" in set_name else "📦"
            
            safe_set_name = escape_markdown(set_name)
            markup.add(types.InlineKeyboardButton(f"{emoji} {set_name}", callback_data=f"craft_view_set|{set_name}"))
            
        if misc_count > 0:
            markup.add(types.InlineKeyboardButton("🎒 Equipaggiamento Vario", callback_data="craft_view_set|MISC"))
            
        markup.add(types.InlineKeyboardButton("🔙 Indietro", callback_data="guild_armory_view"))
        
        bot.edit_message_text(msg, call.message.chat.id, call.message.message_id,
                             reply_markup=markup, parse_mode='markdown')
    finally:
        session.close()

def handle_craft_view_set(call):
    """Show items in a specific Set (Filtered by Armory Level)"""
    print(f"[DEBUG] handle_craft_view_set called: {call.data}")
    safe_answer_callback(call.id)
    
    set_name_arg = call.data.split("|")[1]
    is_misc = (set_name_arg == "MISC")
    guild = guild_service.get_user_guild(call.from_user.id)
    armory_level = guild['armory_level'] if guild else 1
    
    from services.crafting_service import CraftingService
    from models.item import ItemSet
    from sqlalchemy import text
    import json
    
    crafting_service = CraftingService()
    session = crafting_service.db.get_session()
    
    try:
        msg = ""
        markup = types.InlineKeyboardMarkup()
        
        if is_misc:
            msg = f"🎒 **Equipaggiamento Vario** (Max Rarity {armory_level})\n\n"
            msg += "Oggetti singoli senza bonus set.\n\n"
            
            items = session.execute(text("""
                SELECT id, name, rarity, min_level, stats_json, slot
                FROM equipment
                WHERE set_name IS NULL AND rarity <= :lvl
                ORDER BY rarity ASC, min_level ASC
            """), {"lvl": armory_level}).fetchall()
        else:
            set_name = set_name_arg
            # Query ItemSet for bonuses
            item_set = session.query(ItemSet).filter_by(name=set_name).first()
            
            safe_set_name = escape_markdown(set_name)
            msg = f"🛡️ **{safe_set_name}**\n\n"
            if item_set and item_set.bonuses:
                msg += "**Bonus Set:**\n"
                for threshold, bonuses in item_set.bonuses.items():
                    bonus_list = []
                    for stat, val in bonuses.items():
                        bonus_list.append(f"+{val} {stat.title()}")
                    bonus_str = ", ".join(bonus_list)
                    msg += f"🔹 **{threshold} Pezzi**: {escape_markdown(bonus_str)}\n"
            else:
                msg += "_Nessun bonus set definito._\n"
            msg += "\n"
            
            # Get Items in Set filtered by rarity
            items = session.execute(text("""
                SELECT id, name, rarity, min_level, stats_json, slot
                FROM equipment
                WHERE set_name = :sname AND rarity <= :lvl
                ORDER BY min_level ASC, slot ASC
            """), {"sname": set_name, "lvl": armory_level}).fetchall()
            
        # Display Items
        rarity_symbols = {1: '●', 2: '◆', 3: '★', 4: '✦', 5: '✪'}
        slot_emoji = {
            'head': '🎩', 'chest': '👕', 'main_hand': '⚔️', 'off_hand': '🛡️',
            'legs': '👖', 'feet': '👞',
            'accessory1': '💍', 'accessory2': '🔗'
        }
        
        if not items:
            msg += "⚠️ _Nessun oggetto di questo set sbloccato a questo livello di armeria._\n"
            msg += f"Current Armory Lv. {armory_level}"
        
        for eq in items:
            eq_id, name, rarity, min_lvl, stats_json, slot = eq
            
            symbol = rarity_symbols.get(rarity, '●')
            slot_icon = slot_emoji.get(slot, '📦')
            
            # Parse stats
            if isinstance(stats_json, dict):
                stats = stats_json
            elif isinstance(stats_json, str):
                try:
                    stats = json.loads(stats_json) if stats_json else {}
                except:
                    stats = {}
            else:
                stats = {}
            
            stats_str = ", ".join([f"+{v} {escape_markdown(k.title())}" for k, v in stats.items()])
            
            safe_name = escape_markdown(name)
            msg += f"{symbol} {slot_icon} **{safe_name}** (Lv.{min_lvl})\n"
            msg += f"   └ {stats_str}\n"
            
            markup.add(types.InlineKeyboardButton(f"🔨 Crafta {name}", callback_data=f"craft_item|{eq_id}"))
            
        markup.add(types.InlineKeyboardButton("🔙 Lista Set", callback_data="craft_select_equipment"))
        
        bot.edit_message_text(msg, call.message.chat.id, call.message.message_id,
                             reply_markup=markup, parse_mode='markdown')
                             
    except Exception as e:
        print(f"Error viewing set: {e}")
        import traceback
        traceback.print_exc()
        bot.answer_callback_query(call.id, "Errore caricamento set", show_alert=True)
    finally:
        session.close()

def handle_craft_item(call):
    print(f"[DEBUG] handle_craft_item called with data: {call.data}")
    """Show crafting confirmation for specific item"""
    safe_answer_callback(call.id)
    equipment_id = int(call.data.split("|")[1])
    print(f"[DEBUG] Parsed equipment_id: {equipment_id}")
    
    from services.crafting_service import CraftingService
    from sqlalchemy import text
    crafting_service = CraftingService()
    
    # Start crafting
    guild = guild_service.get_user_guild(call.from_user.id)
    if not guild:
        print(f"[DEBUG] User not in guild")
        bot.answer_callback_query(call.id, "Non fai parte di nessuna gilda!", show_alert=True)
        return
    
    print(f"[DEBUG] Guild found: {guild['id']}, calling start_crafting...")
    
    # Attempt to start crafting
    try:
        result = crafting_service.start_crafting(guild['id'], call.from_user.id, equipment_id)
        print(f"[DEBUG] start_crafting returned: {result}")
        
        if result.get('success'):
            print(f"[DEBUG] Crafting SUCCESS")
            bot.answer_callback_query(call.id, "✅ Crafting avviato!", show_alert=False)
            completion_time = result['completion_time'].strftime('%H:%M:%S')
            msg_result = f"⚒️ **Crafting Avviato!**\n\n"
            msg_result += f"🎯 Item: {result['equipment_name']}\n"
            msg_result += f"⏱️ Completamento: {completion_time} ({result['crafting_time']//60}min)\n"
            bot.send_message(call.message.chat.id, msg_result, parse_mode='markdown')
            # Return to armory view
            handle_guild_armory_view(call)
        else:
            error_msg = result.get('error', 'Unknown error')
            print(f"[DEBUG] Crafting FAILED: {error_msg}")
            
            # For long error messages, send as message instead of alert
            if len(error_msg) > 100 or '\n' in error_msg:
                bot.answer_callback_query(call.id, "❌ Impossibile craftare", show_alert=False)
                bot.send_message(call.message.chat.id, error_msg, parse_mode='markdown')
            else:
                bot.answer_callback_query(call.id, error_msg, show_alert=True)
    except Exception as e:
        print(f"[DEBUG] Exception in handle_craft_item: {e}")
        import traceback
        traceback.print_exc()
        bot.answer_callback_query(call.id, f"❌ Errore: {str(e)}", show_alert=True)

def handle_craft_view_resources(call):
    print("[DEBUG] handle_craft_view_resources called")
    """Show user's crafting resources"""
    safe_answer_callback(call.id)
    
    from services.crafting_service import CraftingService
    from sqlalchemy import text
    crafting_service = CraftingService()
    session = crafting_service.db.get_session()
    
    try:
        resources = session.execute(text("""
            SELECT r.name, ur.quantity
            FROM user_resources ur
            JOIN resources r ON ur.resource_id = r.id
            WHERE ur.user_id = :uid AND ur.quantity > 0
            ORDER BY r.rarity ASC
        """), {"uid": call.from_user.id}).fetchall()
        
        msg = "📦 **Le Tue Risorse**\n\n"
        if resources:
            for name, quantity in resources:
                emoji_display = '📦' # Default emoji since r.emoji is no longer selected
                msg += f"{emoji_display} {name}: **x{quantity}**\n"
        else:
            msg += "_Nessuna risorsa disponibile._\n"
    finally:
        session.close()
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Indietro", callback_data="guild_armory_view"))
    
    bot.edit_message_text(msg, call.message.chat.id, call.message.message_id,
                         reply_markup=markup, parse_mode='markdown')

def handle_craft_claim_all(call):
    """Claim all completed crafting jobs"""
    print("[DEBUG] handle_craft_claim_all called")
    safe_answer_callback(call.id)
    
    guild = guild_service.get_user_guild(call.from_user.id)
    if not guild:
        bot.answer_callback_query(call.id, "Non fai parte di nessuna gilda!", show_alert=True)
        return
    
    # Process the queue manually
    from services.crafting_service import CraftingService
    crafting_service = CraftingService()
    
    try:
        results = crafting_service.process_queue()
        
        if results:
            msg = f"✅ **Crafting Riscossi!**\n\n"
            msg += f"Hai riscosso {len(results)} item craftati:\n\n"
            
            for res in results:
                if res.get('success'):
                    item_name = res.get('item_name')
                    quality = res.get('quality', 'Normal')
                    msg += f"🎯 {item_name} ({quality})\n"
            
            msg += f"\n📦 Gli item sono stati aggiunti al tuo inventario!"
            bot.send_message(call.message.chat.id, msg, parse_mode='markdown')
            bot.answer_callback_query(call.id, f"✅ {len(results)} item riscossi!", show_alert=False)
        else:
            bot.answer_callback_query(call.id, "Nessun crafting da riscuotere", show_alert=True)
        
        # Refresh armory view
        handle_guild_armory_view(call)
        
    except Exception as e:
        print(f"[DEBUG] Error claiming crafts: {e}")
        import traceback
        traceback.print_exc()
        bot.answer_callback_query(call.id, f"❌ Errore: {str(e)}", show_alert=True)

@bot.message_handler(commands=['armory', 'armeria'])
def handle_armory_cmd(message):
    """Access the guild armory for crafting"""
    user_id = message.from_user.id
    guild = guild_service.get_user_guild(user_id)
    
    if not guild:
        bot.reply_to(message, "❌ Non fai parte di nessuna gilda!")
        return
        
    if guild['armory_level'] == 0:
        bot.reply_to(message, "❌ La tua gilda non ha ancora un'armeria! Il capogilda può costruirla dal menu gestione.")
        return
        
    msg = f"⚔️ **Armeria della Gilda: {guild['name']}** (Lv. {guild['armory_level']})\n\n"
    msg += "Qui puoi fabbricare armi potenti per i membri della gilda.\n\n"
    msg += "🔨 **Forgia**: Crea nuove armi (ci vuole tempo) (funzione in aggiornamento...)"
    
    bot.reply_to(message, msg, parse_mode='markdown')
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
def handle_season_cmd(message, page=0, user_id=None):
    """Show seasonal progression and rewards with pagination"""
    if user_id is None:
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
        
        msg += f"⭐ **Grado {progress['level']}**\n"
        
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
            msg += f"{status_icon} • Grado {r.level_required}: {premium_tag} {type_icon} {r.reward_name}\n"
            
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
        
        # Try consolidated images directory first
        for ext in ['.png', '.jpg', '.jpeg']:
            image_path = f"images/{char_name_lower}{ext}"
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
            bot.reply_to(message, "Menu principale", reply_markup=get_main_menu())
            return

        character_name = message.text
        print(f"[DEBUG] Character name: {character_name}")
        utente = user_service.get_user(chatid)
        print(f"[DEBUG] User found: {utente is not None}")
        
        if not utente:
            bot.reply_to(message, "❌ Errore: utente non trovato", reply_markup=get_main_menu())
            return
        
        from services.character_loader import get_character_loader
        char_loader = get_character_loader()
        livello = char_loader.get_character_by_name(character_name)
        print(f"[DEBUG] Character found: {livello is not None}")
        
        if not livello:
            bot.reply_to(message, f"❌ Personaggio '{character_name}' non trovato nel database", reply_markup=get_main_menu())
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
            bot.reply_to(message, msg_text, reply_markup=get_main_menu())
        else:
            print(f"[DEBUG] Character not in available list")
            bot.reply_to(message, f"❌ Non possiedi questo personaggio o livello insufficiente", reply_markup=get_main_menu())
    except Exception as e:
        print(f"[ERROR] Error in process_character_selection: {e}")
        import traceback
        traceback.print_exc()
        try:
            chatid = message.from_user.id
            bot.reply_to(message, f"❌ Errore durante la selezione: {str(e)}", reply_markup=get_main_menu())
        except:
            pass
@bot.callback_query_handler(func=lambda call: call.data == "dungeon_leave_global")
def handle_dungeon_leave_global(call):
    """Handle leaving dungeon from global menu"""
    user_id = call.from_user.id
    
    # Find user's dungeon
    user_dungeon = dungeon_service.get_user_active_dungeon(user_id)
    if not user_dungeon:
        safe_answer_callback(call.id, "Non sei in nessun dungeon!", show_alert=True)
        # Update message to remove outdated info
        bot.edit_message_text("✅ Non sei in nessun dungeon.", call.message.chat.id, call.message.message_id)
        return
        
    # Leave dungeon using its chat_id
    success, msg = dungeon_service.leave_dungeon(user_dungeon.chat_id, user_id)
    
    if success:
        safe_answer_callback(call.id, "Hai abbandonato il dungeon!")
        bot.edit_message_text(f"🏃 **Hai abbandonato il dungeon {user_dungeon.name}!**\n\n{msg}", call.message.chat.id, call.message.message_id, parse_mode='markdown')
    else:
        safe_answer_callback(call.id, "Errore durante la fuga!", show_alert=True)
        bot.send_message(call.message.chat.id, f"❌ Errore: {msg}")


class BotCommands:
    def __init__(self, message, bot, user_id=None):
        self.bot = bot
        self.message = message
        # In callbacks, message.from_user is the bot. We need to be careful.
        # But BotCommands is usually instantiated with the original message if possible.
        if user_id:
            self.user_id = user_id
        else:
            self.user_id = message.from_user.id if message.from_user else message.chat.id
            
        print(f"[DEBUG] BotCommands Init: user_id={self.user_id}, message_from={message.from_user.id if message.from_user else 'None'}")
        
        self.chat_id = message.chat.id
        self.chatid = self.user_id # Keep for backward compatibility during transition
        
        # Track activity for mob targeting
        # If it's a private chat, chatid and chat.id are the same.
        user_service.track_activity(self.chatid, message.chat.id)
        
        self.comandi_privati = {
            "🎫 Compra un gioco steam": self.handle_buy_steam_game,
            "👤 Scegli il personaggio": self.handle_choose_character,
            "👤 Profilo": self.handle_profile,
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
            "🏆 Classifica": self.handle_classifica,
            "🌐 Dashboard Web": self.handle_web_dashboard,
            "📄 Classifica": self.handle_classifica,
            "🏪 Mercato Globale": self.handle_market,
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
            "/spawn": self.handle_spawn_mob,
            "/boss": self.handle_spawn_boss,
            "/kill": self.handle_kill_user,
            "/killall": self.handle_kill_all_enemies,
            "/missing_image": self.handle_find_missing_image,
            "/dungeon": self.handle_dungeon,
            "/start_dungeon": self.handle_start_dungeon,
        }
        
        self.comandi_generici = {
            "/dungeons": self.handle_dungeons_list,
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
            "/search": self.handle_search_game,
            "/givedragonballs": self.handle_give_dragonballs,  # Admin only
            "/testchar": self.handle_test_char,  # Debug
            "/help": self.handle_help,
            "!help": self.handle_help,
            "/join": self.handle_join_dungeon,
            "🏆 Classifica": self.handle_classifica,
            "📄 Classifica": self.handle_classifica,
            "/stopdungeon": self.handle_stop_dungeon,
            "/killdungeon": self.handle_stop_dungeon,
        }

    def safe_answer_callback(self, call_id, text=None, show_alert=False):
        """Safely answer a callback query, ignoring timeout errors"""
        try:
            self.bot.answer_callback_query(call_id, text=text, show_alert=show_alert)
        except Exception as e:
            # Ignore "query is too old" or "query ID is invalid" errors
            err_msg = str(e).lower()
            if "query is too old" in err_msg or "query id is invalid" in err_msg:
                pass
            else:
                print(f"[ERROR] Failed to answer callback {call_id}: {e}")
        

    def handle_help(self):
        # Redirect to improved guide system
        self.handle_guide()

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

    def handle_daily_mob(self):
        """Handle the daily scheduled mob spawn (manually triggered via command for test)"""
        if not user_service.is_admin(user_service.get_user(self.chatid)):
            return

        mob_id, attack_events = pve_service.spawn_daily_mob(chat_id=self.chat_id)
        if mob_id:
            # Apply pending effects
            applied = pve_service.apply_pending_effects(mob_id, self.chat_id)
            for app in applied:
                self.bot.send_message(self.chat_id, f"💥 **{app['effect']}** esplode sul nuovo arrivato! Danni: {app['damage']}")
            
            mob = pve_service.get_mob_status_by_id(mob_id)
            if mob:
                markup = get_combat_markup("mob", mob_id, self.chatid)
                
                msg_text = f"⚠️ Un {mob['name']} selvatico è apparso!\n{format_mob_stats(mob, show_full=False)}"
                
                # Send with image if available
                if mob.get('image') and os.path.exists(mob['image']):
                    try:
                        with open(mob['image'], 'rb') as photo:
                            self.bot.reply_to(self.message, photo, caption=msg_text, reply_markup=markup, parse_mode='markdown')
                    except:
                        self.bot.reply_to(self.message, msg_text, reply_markup=markup, parse_mode='markdown')
                else:
                    self.bot.reply_to(self.message, msg_text, reply_markup=markup, parse_mode='markdown')
            else:
                 self.bot.reply_to(self.message, "Errore mob id")
        else:
             self.bot.reply_to(self.message, "Nessun mob spawnato.")

    def handle_spawn_mob(self):
        """Admin command to manually spawn a mob"""
        utente = user_service.get_user(self.chatid)
        if not user_service.is_admin(utente):
            return
            
            mob = pve_service.get_mob_status_by_id(mob_id)
            if mob:
                markup = get_combat_markup("mob", mob_id, self.chatid)
                
                msg_text = f"⚠️ Un {mob['name']} selvatico è apparso!\n{format_mob_stats(mob, show_full=False)}"
                
                # Send with image if available
                if mob.get('image') and os.path.exists(mob['image']):
                    try:
                        with open(mob['image'], 'rb') as photo:
                            self.bot.reply_to(self.message, photo, caption=msg_text, reply_markup=markup, parse_mode='markdown')
                    except:
                        self.bot.reply_to(self.message, msg_text, reply_markup=markup, parse_mode='markdown')
                else:
                    self.bot.reply_to(self.message, msg_text, reply_markup=markup, parse_mode='markdown')
                
                # Send immediate attack messages if any
                if attack_events:
                    for event in attack_events:
                        msg = event['message']
                        image_path = event['image']
                        try:
                            if image_path and os.path.exists(image_path):
                                with open(image_path, 'rb') as photo:
                                    self.bot.send_photo(self.chat_id, photo, caption=msg, reply_markup=markup, )
                            else:
                                self.bot.send_message(self.chat_id, msg, reply_markup=markup, )
                        except:
                            self.bot.send_message(self.chat_id, msg, reply_markup=markup)
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
        
        success, msg, boss_id = pve_service.spawn_boss(boss_name, chat_id=self.chat_id)
        if success and boss_id:
            boss = pve_service.get_mob_status_by_id(boss_id)
            if boss:
                # Create attack buttons
                markup = get_combat_markup("mob", boss_id, self.chat_id)
                
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

                # Send immediate attack messages if any (bosses might also attack immediately)
                # Note: spawn_boss doesn't currently return attack_events, but let's be consistent
                # Actually, pve_service.spawn_boss only returns success, msg, boss_id.
                # If we want bosses to attack immediately, we should call mob_random_attack.
                attack_events = pve_service.mob_random_attack(specific_mob_id=boss_id, chat_id=self.chat_id)
                if attack_events:
                    for event in attack_events:
                        msg = event['message']
                        image_path = event['image']
                        try:
                            if image_path and os.path.exists(image_path):
                                with open(image_path, 'rb') as photo:
                                    self.bot.send_photo(self.chat_id, photo, caption=msg, reply_markup=markup, parse_mode='markdown')
                            else:
                                self.bot.send_message(self.chat_id, msg, reply_markup=markup, parse_mode='markdown')
                        except:
                            self.bot.send_message(self.chat_id, msg, reply_markup=markup, parse_mode='markdown')
        else:
            self.bot.reply_to(self.message, f"❌ {msg}")

    def handle_dungeons_list(self):
        """Show list of available dungeons or active lobby"""
        # Use a shared session for all database operations
        from database import Database
        db = Database()
        session = db.get_session()
        
        try:
            # 1. Check if user is in a dungeon (Global check)
            user_dungeon = dungeon_service.get_user_active_dungeon(self.user_id, session=session)
            if user_dungeon:
                 # Check if it's in THIS chat
                 if user_dungeon.chat_id == self.message.chat.id:
                     # User is in the dungeon of this chat, show normal flow
                     pass
                 else:
                     # User is in a dungeon in ANOTHER chat
                     markup = types.InlineKeyboardMarkup()
                     markup.add(types.InlineKeyboardButton("🏃 Abbandona Dungeon", callback_data="dungeon_leave_global"))
                     
                     msg = f"⚠️ **SEI IN UN DUNGEON IN UN'ALTRA CHAT!**\n\n"
                     msg += f"🏰 **{user_dungeon.name}**\n"
                     msg += f"Stato: {user_dungeon.status}\n"
                     msg += f"Piano: {user_dungeon.current_stage}/{user_dungeon.total_stages}\n\n"
                     msg += "Non puoi unirti ad altri dungeon finché non completi o abbandoni questo."
                     
                     session.close()
                     self.bot.reply_to(self.message, msg, reply_markup=markup, parse_mode='markdown')
                     return

            # Check for active dungeon
            print(f"[DEBUG] handle_dungeons_list called for chat_id: {self.message.chat.id} (type: {self.message.chat.type})")
            active_dungeon = dungeon_service.get_active_dungeon(self.message.chat.id, session=session)
            
            if active_dungeon:
                # Show Lobby UI
                markup = types.InlineKeyboardMarkup()
                if active_dungeon.status == "registration":
                    markup.add(types.InlineKeyboardButton("➕ Unisciti", callback_data=f"dungeon_join|{active_dungeon.id}"))
                    markup.add(types.InlineKeyboardButton("▶️ Avvia (Admin)", callback_data=f"dungeon_start|{active_dungeon.id}"))
                elif active_dungeon.status == "active":
                    markup.add(types.InlineKeyboardButton("👁️ Mostra Nemici", callback_data=f"dungeon_show_mobs|{active_dungeon.id}"))
                    markup.add(types.InlineKeyboardButton("🏃 Fuggire", callback_data="flee"))
                
                msg = f"🏰 **DUNGEON ATTIVO: {active_dungeon.name}**\n"
                msg += f"Status: {active_dungeon.status}\n"
                    
                # Get participants
                participants = dungeon_service.get_dungeon_participants(active_dungeon.id, session=session)
                msg += f"\n👥 Partecipanti ({len(participants)}):\n"
                for p in participants:
                    u = user_service.get_user(p.user_id)
                    name = f"@{u.username}" if u and u.username else (u.nome if u else f"Utente {p.user_id}")
                    msg += f"- {name}\n"
                        
                session.close()
                self.bot.reply_to(self.message, msg, reply_markup=markup, parse_mode='markdown')
                return


            # Show List
            dungeons = dungeon_service.dungeons_cache
            if not dungeons:
                session.close()
                self.bot.reply_to(self.message, "Nessun dungeon disponibile.")
                return
            
            progress = dungeon_service.get_user_progress(self.chatid, session=session)
            completed_ids = [p.dungeon_def_id for p in progress]
            
            msg = "🏰 **DUNGEON DISPONIBILI**\n\n"
            msg += "Seleziona un dungeon per hostare una partita:\n"
            
            markup = types.InlineKeyboardMarkup()
            
            # Sort by ID
            sorted_ids = sorted(dungeons.keys())
            
            for d_id in sorted_ids:
                d = dungeons[d_id]
                is_unlocked = dungeon_service.can_access_dungeon(self.chatid, d_id, session=session)
                
                status_icon = "🔒"
                if is_unlocked:
                    status_icon = "🔓"
                if d_id in completed_ids:
                    status_icon = "✅"
                    
                # Get best rank
                rank = ""
                p = next((x for x in progress if x.dungeon_def_id == d_id), None)
                if p and p.best_rank:
                    rank = f" (Rango: {p.best_rank})"
                    
                btn_text = f"{status_icon} {d['name']} (Diff: {d['difficulty']}){rank}"
                if is_unlocked:
                    markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"dungeon_host|{d_id}"))
                else:
                    markup.add(types.InlineKeyboardButton(f"🔒 {d['name']} (Bloccato)", callback_data="ignore"))
            
            session.commit()
            self.bot.reply_to(self.message, msg, reply_markup=markup, parse_mode='markdown')
            
        except Exception as e:
            session.rollback()
            print(f"[ERROR] handle_dungeons_list: {e}")
            import traceback
            traceback.print_exc()
            self.bot.reply_to(self.message, "Errore nel caricamento dei dungeon.")
        finally:
            session.close()

    def handle_flee(self):
        """Allow user to flee from dungeon"""
        success, msg = dungeon_service.leave_dungeon(self.message.chat.id, self.chatid)
        self.bot.reply_to(self.message, msg, parse_mode='markdown')



    def handle_dungeon(self):
        """Start dungeon registration"""
        # Parse ID
        text = self.message.text.strip()
        parts = text.split(maxsplit=1)
        
        if len(parts) < 2:
            self.bot.reply_to(self.message, "⚠️ Usa: `/dungeon <ID>` (es. `/dungeon 1`)")
            return
            
        try:
            d_id = int(parts[1])
        except ValueError:
            self.bot.reply_to(self.message, "⚠️ ID non valido.")
            return
            
        d_real_id, msg = dungeon_service.create_dungeon(self.message.chat.id, d_id, self.chatid)
        self.bot.reply_to(self.message, f"❌ {msg}", parse_mode='markdown')

    # @bot.message_handler(commands=['join'])
    # def handle_join_dungeon_cmd(self, message):
    #    """Deprecated: Dungeons are now auto-join"""
    #    bot.reply_to(message, "I dungeon ora sono automatici! Non serve più fare /join.")

    # Modified to just show a message if users try to use it
    def handle_join_dungeon(self):
        """User command to join current dungeon registration"""
        self.bot.reply_to(self.message, "⚠️ **Novità!** ⚠️\n\nI Dungeon ora sono eventi automatici!\nTi unirai automaticamente quando il dungeon emerge.\nNon serve più usare comandi.")

    def handle_start_dungeon(self):
        """Start the dungeon (Creator or Admin)"""
        # Check if user is creator or admin
        # For simplicity, we let anyone start it if they are in the group, 
        # but ideally we check if they are the creator.
        # DungeonService.start_dungeon checks if registration exists.
        
        success, msg, events = dungeon_service.start_dungeon(self.message.chat.id)
        
        if success:
            self.bot.send_message(self.message.chat.id, "🚀 **Dungeon Iniziato!**", parse_mode='markdown')
            # Process events (dialogues, delays, spawns)
            self.process_dungeon_events(events, self.message.chat.id)
        else:
            self.bot.send_message(self.message.chat.id, msg, parse_mode='markdown')
    
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
    
    def process_dungeon_events(self, events, chat_id):
        """Process a list of dungeon events (messages, delays, spawns)"""
        process_dungeon_events(events, chat_id)

    # process_dungeon_events moved to global scope at end of file

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
        # 1. Check Characters
        all_chars = character_service.get_all_characters()
        for char in all_chars:
            # Check dict or object
            if isinstance(char, dict):
                char_name = char['nome']
            else:
                char_name = char.nome
                
            char_name_clean = char_name.lower().replace(" ", "_").replace("'", "")
            
            # Try standard extensions
            found = False
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
        

    def handle_stop_dungeon(self):
        """Admin command to force stop the current dungeon"""
        utente = user_service.get_user(self.chatid)
        if not user_service.is_admin(utente):
            self.bot.reply_to(self.message, "❌ Comando disponibile solo per gli admin!")
            return
            
        success, msg = dungeon_service.force_close_dungeon(self.message.chat.id)
        self.bot.reply_to(self.message, f"{'✅' if success else '❌'} {msg}")


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
            self.bot.reply_to(self.message, msg, reply_markup=get_main_menu())

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
            wish_service.log_summon(self.chatid, "Shenron")
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(f"💰 {PointsName} (300-500)", callback_data="wish|Shenron|wumpa"))
            markup.add(types.InlineKeyboardButton("⭐ EXP (300-500)", callback_data="wish|Shenron|exp"))
            self.bot.reply_to(self.message, "🐉 Shenron è stato evocato!\n\nEsprimi il tuo desiderio!", reply_markup=markup)
            
        elif has_porunga:
            wish_service.log_summon(self.chatid, "Porunga")
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
                            sent_msg = self.bot.send_photo(self.chatid, photo, caption=msg, parse_mode='markdown', reply_markup=get_main_menu())
                            
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
            self.bot.reply_to(self.message, msg, parse_mode='markdown', reply_markup=get_main_menu())

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

    def handle_market(self):
        """Show market menu"""
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📜 Mostra Annunci", callback_data="market_list|1"))
        markup.add(types.InlineKeyboardButton("➕ Vendi Oggetto", callback_data="market_sell_menu"))
        
        self.bot.send_message(self.chatid, "🏪 **MERCATO GLOBALE**\n\nBenvenuto nel mercato globale dei giocatori!\nQui puoi vendere i tuoi oggetti o acquistare quelli degli altri.", reply_markup=markup, parse_mode='markdown')

    def handle_market_callback(self, call):
        """Handle market callbacks"""
        action = call.data
        user_id = call.from_user.id
        self.chatid = user_id
        
        from services.market_service import MarketService
        market_service = MarketService()
        
        if action.startswith("market_list|"):
            try:
                page_str = action.split("|")[1]
                page = int(page_str)
            except (IndexError, ValueError):
                page = 1
                
            limit = 5
            listings, total = market_service.get_active_listings(page, limit)
            
            msg = f"🏪 **MERCATO GLOBALE (Pagina {page})**\n\n"
            
            if not listings:
                msg += "Nessun annuncio disponibile al momento."
            
            markup = types.InlineKeyboardMarkup()
            
            for l in listings:
                try:
                    seller_name = "Utente"
                    is_owner = False
                    if l.seller:
                        seller_name = l.seller.username if l.seller.username else l.seller.nome
                        if l.seller.id_telegram == str(user_id) or l.seller_id == user_id:
                            is_owner = True
                    
                    price_tot = l.price_per_unit * l.quantity
                    btn_text = f"{l.quantity}x {l.item_name} - {price_tot}🍑 ({seller_name})"
                    
                    if is_owner:
                        markup.add(types.InlineKeyboardButton(f"❌ Ritira {l.item_name}", callback_data=f"cancel_listing|{l.id}"))
                    else:
                        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"buy_item|{l.id}"))
                except Exception as e:
                    print(f"Error rendering listing {l.id}: {e}")
                    continue
                
            import math
            total_pages = math.ceil(total / limit)
            nav_row = []
            if page > 1:
                nav_row.append(types.InlineKeyboardButton("⬅️ Prec", callback_data=f"market_list|{page-1}"))
            if page < total_pages:
                nav_row.append(types.InlineKeyboardButton("Succ ➡️", callback_data=f"market_list|{page+1}"))
            
            if nav_row:
                markup.row(*nav_row)
            
            markup.add(types.InlineKeyboardButton("🔙 Menu Mercato", callback_data="market_menu"))
            
            try:
                self.bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='markdown')
            except:
                self.bot.send_message(call.message.chat.id, msg, reply_markup=markup, parse_mode='markdown')
        
        elif action == "market_menu":
             markup = types.InlineKeyboardMarkup()
             markup.add(types.InlineKeyboardButton("📜 Mostra Annunci", callback_data="market_list|1"))
             markup.add(types.InlineKeyboardButton("➕ Vendi Oggetto", callback_data="market_sell_menu"))
             msg = "🏪 **MERCATO GLOBALE**"
             try:
                self.bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='markdown')
             except:
                self.bot.send_message(call.message.chat.id, msg, reply_markup=markup, parse_mode='markdown')
    
        elif action.startswith("buy_item|"):
            try:
                listing_id = int(action.split("|")[1])
                success, result_msg = market_service.buy_item(user_id, listing_id)
                
                if success:
                    self.safe_answer_callback(call.id, "Acquisto effettuato!")
                    self.bot.send_message(call.message.chat.id, result_msg)
                    call.data = "market_list|1"
                    self.handle_market_callback(call)
                else:
                    self.safe_answer_callback(call.id, result_msg, show_alert=True)
            except Exception as e:
                print(f"Error buying item: {e}")
                self.safe_answer_callback(call.id, "Errore durante l'acquisto.")

        elif action.startswith("cancel_listing|"):
            try:
                listing_id = int(action.split("|")[1])
                success, result_msg = market_service.cancel_listing(user_id, listing_id)
                
                if success:
                    self.safe_answer_callback(call.id, "Annuncio ritirato!")
                    self.bot.send_message(call.message.chat.id, result_msg)
                    call.data = "market_list|1"
                    self.handle_market_callback(call)
                else:
                    self.safe_answer_callback(call.id, result_msg, show_alert=True)
            except Exception as e:
                print(f"Error cancelling listing: {e}")
                self.safe_answer_callback(call.id, "Errore durante la cancellazione.")

        elif action == "market_sell_menu":
             # Implementation for seamless sell flow
             from services.item_service import ItemService
             item_svc = ItemService()
             inventory = item_svc.get_inventory(user_id)
             
             if not inventory:
                 self.safe_answer_callback(call.id, "Non hai oggetti da vendere!", show_alert=True)
                 return
                 
             msg = "🎒 **SELEZIONA OGGETTO DA VENDERE**\n\nScegli cosa vuoi mettere sul mercato:"
             markup = types.InlineKeyboardMarkup()
             
             # Emoji mapping (reused)
             item_emoji = {
                "Turbo": "🏎️", "Aku Aku": "🎭", "Uka Uka": "😈", "Nitro": "💣",
                "Mira un giocatore": "🎯", "Colpisci un giocatore": "💥", "Cassa": "📦"
             }
             
             for item in inventory:
                 emoji = item_emoji.get(item.oggetto, "🔹")
                 if "Pozione" in item.oggetto or "Elisir" in item.oggetto:
                     emoji = "🧪"
                     
                 btn_text = f"{emoji} {item.oggetto} (x{item.quantita})"
                 markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"market_sell_select|{item.oggetto}"))
             
             markup.add(types.InlineKeyboardButton("🔙 Menu Mercato", callback_data="market_menu"))
             
             try:
                self.bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='markdown')
             except:
                self.bot.send_message(call.message.chat.id, msg, reply_markup=markup, parse_mode='markdown')

        elif action.startswith("market_sell_select|"):
             item_name = action.split("|")[1]
             # Start sale wizard
             msg = self.bot.send_message(call.message.chat.id, f"💰 Hai scelto di vendere **{item_name}**.\n\nQuanti ne vuoi vendere? (Scrivi un numero, es: 1)", parse_mode='markdown')
             
             # Store temp context? Or just pass item_name in next_step
             self.bot.register_next_step_handler(msg, self.process_market_sell_quantity, item_name)

    def process_market_sell_quantity(self, message, item_name):
        """Step 1: Quantity"""
        try:
            qty = int(message.text.strip())
            if qty <= 0:
                self.bot.reply_to(message, "❌ Quantità non valida.")
                return
                
            msg = self.bot.reply_to(message, f"💰 Prezzo totale per {qty}x {item_name}?\n(Inserisci il prezzo TOTALE in Wumpa, es: 100)")
            self.bot.register_next_step_handler(msg, self.process_market_sell_price, item_name, qty)
        except ValueError:
             self.bot.reply_to(message, "❌ Inserisci un numero valido.")

    def process_market_sell_price(self, message, item_name, qty):
        """Step 2: Price and Confirm"""
        try:
            print(f"[DEBUG] Market Sell Price: User ID in msg: {message.from_user.id}, Text: {message.text}")
            price_total = int(message.text.strip())
            if price_total <= 0:
                self.bot.reply_to(message, "❌ Prezzo non valido.")
                return
            
            # Calculate price per unit
            price_per_unit = price_total // qty
            if price_per_unit < 1:
                price_per_unit = 1 # Min 1 wumpa per item
            
            from services.market_service import MarketService
            ms = MarketService()
            user_id = message.from_user.id # or self.chatid? in next_step self.chatid might not be set correctly if class reused? 
            # self.chatid is instance var. check if reliable. BotCommands is re-instantiated usually? Yes in 'any' it is.
            # But register_next_step_handler keeps the handler method bound to the *original* instance? 
            # Actually, `register_next_step_handler` takes a function. `self.process...` is a bound method.
            # So `self` is the OLD instance. 
            # `message` is the NEW message.
            # `user_id` should be taken from `message.from_user.id`.
            
            success, res = ms.list_item(message.from_user.id, item_name, qty, price_per_unit)
            
            self.bot.reply_to(message, res)
            
        except ValueError:
             self.bot.reply_to(message, "❌ Inserisci un numero valido.")

    def handle_choose_character(self):
        """Show character selection menu"""
        utente = user_service.get_user(self.chatid)
        if not utente:
             self.bot.reply_to(self.message, "Utente non trovato.")
             return
             
        available = character_service.get_available_characters(utente)
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        
        btns = []
        for c in available:
            name = c.get('nome', 'Unknown')
            btns.append(types.KeyboardButton(name))
            
        markup.add(*btns)
        markup.add(types.KeyboardButton("🔙 Indietro"))
        
        msg = f"👤 **SCEGLI IL TUO PERSONAGGIO**\n\nEcco i personaggi che hai sbloccato. Selezionane uno per equipaggiarlo:"
        
        self.bot.send_message(self.chatid, msg, reply_markup=markup, parse_mode='markdown')
        self.bot.register_next_step_handler(self.message, process_character_selection)

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
            
        msg += "\n╔═══🕹═══╗\n"
        nome_utente = utente.nome if utente.username is None else utente.username
        msg += f"👤 **{escape_markdown(nome_utente)}**: {utente.points} {PointsName}\n"
        
        # Show title if user has one
        if hasattr(utente, 'title') and utente.title:
            msg += f"👑 **{escape_markdown(utente.title)}**\n"
        
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
        
        # Advanced Stats (always show)
        user_resistance = getattr(utente, 'resistance', 0) or 0
        user_crit = getattr(utente, 'crit_chance', 0) or 0
        user_speed = getattr(utente, 'speed', 0) or 0
        
        msg += f"🛡️ **Resistenza**: {user_resistance}% (MAX 75%)\n"
        msg += f"💥 **Critico**: {user_crit}%\n"
        msg += f"⚡ **Velocità**: {user_speed}\n"
        
        if utente.stat_points > 0:
            msg += f"\n📊 **Punti Stat**: {utente.stat_points} (usa /stats)\n"
            
        msg += "\n      aROMa\n"
        msg += "╚═══🕹═══╝\n"
            
        # Check resting status
        resting_status = user_service.get_resting_status(utente.id_telegram)
        if resting_status:
            msg += f"\n🛌 **Stai riposando** nella Locanda Pubblica\n"
            msg += f"⏱️ Tempo: {resting_status['minutes']} minuti\n"
            msg += f"💖 Recupero stimato: +{resting_status['hp']} HP, +{resting_status['mana']} Mana\n"
            
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
            markup.add(types.InlineKeyboardButton("📊 Alloca Statistiche", callback_data="stat_alloc"))
            markup.add(types.InlineKeyboardButton("🎒 Equipaggiamento", callback_data="view_equipment"))
            markup.add(types.InlineKeyboardButton("🏆 Scegli Titolo", callback_data="title_menu"))
            # markup.add(types.InlineKeyboardButton("🔄 Reset Stats (Gratis)", callback_data="stat_reset")) # Removed as per user request
        if character:
            # markup.add(types.InlineKeyboardButton("✨ Attacco Speciale", callback_data="special_attack_mob")) # Removed as per user request
            
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
            self.bot.reply_to(message, "Menu principale", reply_markup=get_main_menu())
            return
            
        platform = message.text
        msg = self.bot.reply_to(message, f"Hai selezionato {platform}.\nOra scrivi il tuo nome in game:", reply_markup=types.ReplyKeyboardRemove())
        self.bot.register_next_step_handler(msg, self.process_gamename_input, platform)

    def process_gamename_input(self, message, platform):
        gamename = message.text
        user_service.update_user(self.chatid, {'platform': platform, 'game_name': gamename})
        self.bot.reply_to(message, f"✅ Salvato! {platform}: {gamename}", reply_markup=get_main_menu())

    def process_item_target(self, message, item_name):
        """Handle target selection for items"""
        target_input = message.text.strip()
        
        # Check if target is a User
        target_user = user_service.get_user(target_input)
        target_mob = None
        
        if not target_user:
            # Check if target is a Mob (by name)
            # We need to find an active mob with this name
            from database import Database
            from models.pve import Mob
            db = Database()
            session = db.get_session()
            # Find active mob with matching name (case insensitive)
            target_mob = session.query(Mob).filter(Mob.name.ilike(target_input), Mob.is_dead == False).first()
            session.close()
            
            if not target_mob:
                # If item is TNT/Nitro, allow "Terra" or empty to place trap
                if item_name in ["TNT", "Nitro"] and (target_input.lower() in ["terra", "ground", "nessuno"] or target_input == ""):
                    target_user = None # Explicitly None to trigger trap logic
                else:
                    self.bot.reply_to(message, f"❌ Bersaglio '{target_input}' non trovato (né Utente né Mob). Operazione annullata.")
                    return
        
        # Use the item on the target
        if item_service.use_item(self.chatid, item_name):
            utente = user_service.get_user(self.chatid)
            msg, data = item_service.apply_effect(utente, item_name, target_user, target_mob)
            
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
            
            elif data and data.get('type') == 'mob_drop':
                # Mob drops Wumpa!
                percent = data['percent']
                mob_id = data['mob_id']
                
                # Execute drop logic in PvEService
                dropped_amount = pve_service.force_mob_drop(mob_id, percent)
                
                if dropped_amount > 0:
                    # Create buttons for stealing the dropped wumpa
                    markup = types.InlineKeyboardMarkup()
                    buttons = []
                    import uuid
                    # Cap visual buttons to 50 to avoid limits, but amount is real
                    visual_amount = min(dropped_amount, 50)
                    for i in range(visual_amount):
                        uid = str(uuid.uuid4())[:8]
                        buttons.append(types.InlineKeyboardButton("🍑", callback_data=f"steal|{uid}"))
                    
                    # Add rows of 5
                    for i in range(0, len(buttons), 5):
                        markup.row(*buttons[i:i+5])
                        
                    msg += f"\n\n💰 Il Mob ha perso {dropped_amount} Wumpa!"
                    
                    try:
                        self.bot.send_message(GRUPPO_AROMA, msg, reply_markup=markup)
                        self.bot.reply_to(message, "Oggetto usato! Controlla il gruppo.")
                    except:
                        self.bot.reply_to(message, msg, reply_markup=markup)
                else:
                    self.bot.reply_to(message, f"{msg}\n(Ma non ha droppato nulla!)")

            elif data and data.get('type') == 'trap':
                # Set trap in the chat
                drop_service.set_trap(message.chat.id, data['trap_type'], self.chatid)
                self.bot.reply_to(message, msg)
                
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

    def handle_classifica(self, ranking_type="global"):
        """Show ranking (global or seasonal)"""
        
        msg = ""
        markup = types.InlineKeyboardMarkup()
        
        if ranking_type == "global":
            users = user_service.get_users()
            # Sort logic: EXP (descending), treating None as 0
            users.sort(key=lambda x: x.exp if x.exp is not None else 0, reverse=True)
            
            msg = "🌍 **CLASSIFICA GLOBALE** 🌍\n\n"
            
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
                
                nome_display = u.game_name or u.username or u.nome or f"Eroe {u.id_telegram}"
                # Escape markdown in name
                if nome_display:
                    nome_display = nome_display.replace("_", "\\_").replace("*", "\\*").replace("[", "\\[")
                
                msg += f"{i+1}. **{nome_display}**\n"
                msg += f"   Lv. {u.livello or 1} - {char_name}\n"
                msg += f"   ✨ EXP: {u.exp or 0} | 🍑 {u.points or 0}\n\n"
            
            # Buttons
            markup.row(types.InlineKeyboardButton("🌟 Classifica Stagione", callback_data="ranking|season"))
                
        elif ranking_type == "season":
            from services.season_manager import SeasonManager
            manager = SeasonManager()
            ranking, season_name = manager.get_season_ranking(limit=15)
            
            if not ranking:
                msg = "⚠️ Nessuna stagione attiva o nessun partecipante al momento."
            else:
                msg = f"🏆 **CLASSIFICA STAGIONE** 🏆\n"
                msg += f"🌟 **{season_name}** 🌟\n\n"
                
                emojis = ["🥇", "🥈", "🥉"]
                
                for i, data in enumerate(ranking):
                    rank_emoji = emojis[i] if i < 3 else f"#{i+1}"
                    name = data['game_name'] or data['username'] or data['nome'] or "Eroe"
                    # Escape markdown
                    if name:
                        name = name.replace("_", "\\_").replace("*", "\\*").replace("[", "\\[")
                    
                    msg += f"{rank_emoji} **{name}**\n"
                    msg += f"   ├ 🏅 Grado: {data['level']}\n"
                    msg += f"   └ 📊 Lv. Eroe: {data['user_level']}\n\n"
            
            # Buttons
            markup.row(types.InlineKeyboardButton("🌍 Classifica Globale", callback_data="ranking|global"))
        
        # Add common buttons if any needed (e.g. Back)
        
        # Send or Edit
        # Check if we are in a callback context (self.message is the original message)
        # We need to determine if we edit or send new.
        # Usually handle_* methods in BotCommands check context or are called with context.
        # But here we pass ranking_type.
        # If we are called from callback handler, we should EDIT.
        # If called from command /classifica, we send NEW.
        
        # Simple heuristic: if we have a callback query ID in context (not available here directly unless passed)
        # OR we rely on caller to set self.is_callback or similar.
        # But BotCommands instance is created per request.
        
        # Let's try to edit if existing message looks like a ranking, otherwise send.
        # Or just use reply_to / edit_message_text based on whether it was a button click.
        # But we don't know here.
        
        # Actually, self.message is available.
        # We can try to edit self.message if it was sent by bot (which is true for callbacks).
        # But self.message in callback is the message FROM user? No, call.message is message with buttons.
        # BotCommands is init with call.message if callback.
        
        try:
            # Try to edit first (if it's a callback update)
            self.bot.edit_message_text(msg, self.message.chat.id, self.message.message_id, reply_markup=markup, parse_mode='markdown')
        except Exception as e:
            # If edit fails (e.g. content same, or not bot message), send new
            # print(f"Edit failed (expected for new command): {e}")
            self.bot.send_message(self.message.chat.id, msg, reply_markup=markup, parse_mode='markdown')

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

    def handle_stats(self, is_callback=False):
        """Show user stats and allocation menu"""
        utente = user_service.get_user(self.chatid)
        if not utente:
            return
            
        from services.stats_service import StatsService
        stats_service = StatsService()
        
        msg = stats_service.get_stat_allocation_summary(utente)
        
        markup = types.InlineKeyboardMarkup()
        
        # Allocation buttons
        points_info = stats_service.get_available_stat_points(utente)
        if points_info['available'] > 0:
            markup.row(
                types.InlineKeyboardButton("❤️ HP (+10)", callback_data="stat_up_health"),
                types.InlineKeyboardButton("💙 Mana (+5)", callback_data="stat_up_mana")
            )
            markup.row(
                types.InlineKeyboardButton("⚔️ Danno (+2)", callback_data="stat_up_damage"),
                types.InlineKeyboardButton("⚡ Vel (+1)", callback_data="stat_up_speed")
            )
            markup.row(
                types.InlineKeyboardButton("🛡️ Res (+1%)", callback_data="stat_up_resistance"),
                types.InlineKeyboardButton("🎯 Crit (+1%)", callback_data="stat_up_crit_rate")
            )
        
        # Reset button
        markup.add(types.InlineKeyboardButton("🔄 Reset Statistiche (Gratis)", callback_data="stat_reset"))
        # Changed to profile as main_menu might not be implemented
        markup.add(types.InlineKeyboardButton("🔙 Profilo", callback_data="profile"))
        
        if is_callback:
            # Edit existing message
            try:
                self.bot.edit_message_text(msg, self.message.chat.id, self.message.message_id, reply_markup=markup, parse_mode='markdown')
            except Exception:
                # If editing fails (e.g. it was a photo), send new message then delete old
                
                # Send new message FIRST
                try:
                    self.bot.send_message(self.message.chat.id, msg, reply_markup=markup, parse_mode='markdown')
                except Exception:
                    import traceback
                    traceback.print_exc()
                
                # Then try to delete old message
                try:
                    self.bot.delete_message(self.message.chat.id, self.message.message_id)
                except Exception:
                    pass
        else:
            # Send new message (don't reply as command might be deleted)
            # Use self.message.chat.id if available, otherwise self.chatid (fallback)
            target_chat = self.message.chat.id if hasattr(self, 'message') and self.message else self.chatid
            self.bot.send_message(target_chat, msg, reply_markup=markup, parse_mode='markdown')

    def handle_title_selection(self, is_callback=False, call_id=None):
        """Show menu to select a title from unlocked achievements"""
        utente = user_service.get_user(self.chatid)
        if not utente:
            return
            
        # Fetch unlocked achievements
        from services.achievement_tracker import AchievementTracker
        tracker = AchievementTracker()
        achievements = tracker.get_user_achievements(self.chatid)
        
        # Filter for unlocked ones (current_tier is not None)
        unlocked_titles = []
        tier_emojis = {
            'bronze': '🥉',
            'silver': '🥈',
            'gold': '🥇',
            'platinum': '💎',
            'diamond': '💎',
            'legendary': '👑'
        }
        
        for ach in achievements:
            if ach['current_tier']:
                emoji = tier_emojis.get(ach['current_tier'], '')
                title_display = f"{ach['name']} {emoji}"
                unlocked_titles.append(title_display)
            
        if not unlocked_titles:
            msg = "❌ Non hai ancora sbloccato nessun titolo!\n\nCompleta gli achievement per ottenerne uno."
            if is_callback and call_id:
                self.safe_answer_callback(call_id, "Nessun titolo disponibile", show_alert=True)
                return
            elif not is_callback:
                self.bot.send_message(self.chatid, msg)
                return
            else:
                return
        
        if is_callback and call_id:
            try:
                self.safe_answer_callback(call_id)
            except:
                pass
                
        msg = f"🏆 **SCEGLI IL TUO TITOLO**\n\n"
        msg += f"Titolo attuale: **{utente.title or 'Nessuno'}**\n\n"
        msg += "Seleziona un titolo da equipaggiare:"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("❌ Rimuovi Titolo", callback_data="set_title|NONE"))
        
        for ach in achievements:
            if ach['current_tier']:
                emoji = tier_emojis.get(ach['current_tier'], '')
                title_display = f"{ach['name']} {emoji}"
                
                # Check if current
                icon = "✅" if utente.title == title_display else "▪️"
                
                # Use key in callback to avoid string encoding issues
                markup.add(types.InlineKeyboardButton(f"{icon} {title_display}", callback_data=f"set_title|{ach['key']}"))
            
        markup.add(types.InlineKeyboardButton("🔙 Profilo", callback_data="profile"))
        
        if is_callback:
            try:
                self.bot.edit_message_text(msg, self.message.chat.id, self.message.message_id, reply_markup=markup, parse_mode='markdown')
            except:
                self.bot.send_message(self.message.chat.id, msg, reply_markup=markup, parse_mode='markdown')
        else:
            self.bot.send_message(self.chatid, msg, reply_markup=markup, parse_mode='markdown')

    def handle_stat_callback(self, call):
        """Handle stat allocation callbacks"""
        try:
            # FIX: When called from callback, self.chatid is the Bot ID (sender of the message).
            # We must use the ID of the user who clicked the button.
            user_id = call.from_user.id
            self.chatid = user_id
            
            utente = user_service.get_user(user_id)
            if not utente:
                self.safe_answer_callback(call.id, "Utente non trovato!", show_alert=True)
                return
            
            if call.data == "stat_reset":
                from services.stats_service import StatsService
                stats_service = StatsService()
                success, msg = stats_service.reset_stat_points(utente)
                self.safe_answer_callback(call.id, "Statistiche resettate!")
                
                # Refresh view
                self.message = call.message
                self.handle_stats(is_callback=True)
                return

            if call.data.startswith("stat_up_") or call.data.startswith("stat_alloc|"):
                if "stat_up_" in call.data:
                    stat_type = call.data.replace("stat_up_", "")
                else:
                    stat_type = call.data.replace("stat_alloc|", "")
                
                from services.stats_service import StatsService
                stats_service = StatsService()
                
                success, msg = stats_service.allocate_stat_point(utente, stat_type)
                
                if success:
                    self.safe_answer_callback(call.id, "Punto allocato!")
                    # Refresh view
                    self.message = call.message
                    self.handle_stats(is_callback=True)
                else:
                    self.safe_answer_callback(call.id, msg, show_alert=True)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.safe_answer_callback(call.id, f"Errore: {str(e)}", show_alert=True)

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
        
        # Show Owner if applicable
        owner_name = character_service.get_character_owner_name(char_id)
        if owner_name:
            if owner_name == (utente.nome if utente.username is None else utente.username):
                msg += "👤 **Proprietario**: TU\n"
            else:
                msg += f"👤 **Proprietario**: {owner_name}\n"
        
        
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
        can_go_fast_prev = False
        if level_idx >= 5:
            prev_5_val = levels[level_idx-5]
            if is_admin or prev_5_val <= utente.livello:
                can_go_fast_prev = True
        
        if can_go_fast_prev:
             nav_levels_row.append(types.InlineKeyboardButton("⏪ -5", callback_data=f"char_nav|{level_idx-5}|0"))
        
        # Prev Level
        can_go_prev = False
        if level_idx > 0:
            prev_level_val = levels[level_idx-1]
            if is_admin or prev_level_val <= utente.livello:
                can_go_prev = True
        
        if can_go_prev:
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
        
        # Row 4: Season Filter Button (Dragon Ball)
        season_row = []
        season_row.append(types.InlineKeyboardButton("🐉 Personaggi della Stagione", callback_data="saga_nav|Dragon Ball|0"))
        markup.row(*season_row)
        
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
            self.bot.reply_to(self.message, "Hai già acquistato tutti i personaggi disponibili!", reply_markup=get_main_menu())
        else:
            msg = self.bot.reply_to(self.message, f"Benvenuto nel Negozio Personaggi!\nHai {utente.points} {PointsName}.\nScegli chi acquistare:", reply_markup=markup)
            self.bot.register_next_step_handler(msg, self.process_buy_character)

    def process_buy_character(self, message):
        if message.text == "🔙 Indietro":
            self.bot.reply_to(message, "Menu principale", reply_markup=get_main_menu())
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
                self.bot.reply_to(message, f"🎉 {msg}", reply_markup=get_main_menu())
            else:
                self.bot.reply_to(message, f"❌ {msg}", reply_markup=get_main_menu())
        else:
            self.bot.reply_to(message, "Personaggio non trovato.", reply_markup=get_main_menu())
            self.handle_shop_characters()
            
    def handle_guide(self):
        """Show guide menu"""
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("⚔️ Sistema di Combattimento", callback_data="guide|fight_system"),
            types.InlineKeyboardButton("🏰 Dungeon", callback_data="guide|dungeons"),
            types.InlineKeyboardButton("📊 Allocazione Statistiche", callback_data="guide|stats_allocation"),
            types.InlineKeyboardButton("🍂 Sistema Stagionale", callback_data="guide|season_system"),
            types.InlineKeyboardButton("🏆 Achievements", callback_data="guide|achievements")
        )
        
        msg = "📚 **GUIDE DI GIOCO** 📚\n\n"
        msg += "Benvenuto nella sezione guide! Qui puoi imparare tutto su aROMa RPG.\n"
        msg += "Seleziona un argomento per leggere la guida completa:"
        
        self.bot.reply_to(self.message, msg, reply_markup=markup, parse_mode='markdown')

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
            mob = pve_service.get_current_mob_status(mob_id)
            if mob:
                markup = get_combat_markup("mob", mob_id, GRUPPO_AROMA)
                
                msg_text = f"⚠️ Un {mob['name']} selvatico è apparso!\n📊 Lv. {mob.get('level', 1)} | ⚡ Vel: {mob.get('speed', 30)} | 🛡️ Res: {mob.get('resistance', 0)}%\n❤️ Salute: {mob['health']}/{mob['max_health']} HP\n⚔️ Danno: {mob['attack']}\n\nSconfiggilo per ottenere ricompense!"
                
                # Send with image if available
                sent_msg = send_combat_message(GRUPPO_AROMA, msg_text, mob.get('image'), markup, mob_id)
                
                # Immediate attack
                attack_events = pve_service.mob_random_attack(specific_mob_id=mob_id)
                if attack_events:
                    for event in attack_events:
                        msg = event['message']
                        image_path = event['image']
                        old_msg_id = event['last_message_id']
                        
                        send_combat_message(GRUPPO_AROMA, msg, image_path, markup, mob_id, old_msg_id)
        else:
            self.bot.reply_to(self.message, f"❌ {msg}")

    def handle_enemies(self):
        """List active enemies in the chat"""
        mobs = pve_service.get_active_mobs(self.chatid)
        
        if not mobs:
            self.bot.reply_to(self.message, "🧟 Nessun nemico attivo al momento. Tutto tranquillo... per ora.")
            return
            
        msg = "🧟 **NEMICI ATTIVI** 🧟\n\n"
        
        for mob in mobs:
            # Status icons
            status = ""
            if mob.is_boss: status += "👑 **BOSS** "
            if mob.difficulty_tier >= 4: status += "💀 "
            
            # Health bar approximation
            hp_percent = (mob.health / mob.max_health) * 100
            hp_bar = "🟩" * int(hp_percent / 10) + "⬜" * (10 - int(hp_percent / 10))
            
            msg += f"{status}**{mob.name}** (Lv. {mob.mob_level if hasattr(mob, 'mob_level') else 1})\n"
            msg += f"❤️ {mob.health}/{mob.max_health} {hp_bar}\n"
            msg += f"⚔️ Danno: {mob.attack_damage} | 🛡️ Res: {mob.resistance}%\n"
            if mob.difficulty_tier:
                msg += f"🔥 Difficoltà: {mob.difficulty_tier}\n"
            msg += f"🆔 ID: `{mob.id}` (Usa per targettare)\n"
            msg += "-------------------\n"
            
        markup = types.InlineKeyboardMarkup()
        # Add a generic attack button that attacks the first mob? 
        # Or maybe just let users use the specific buttons on spawn message.
        # Let's add a refresh button.
        markup.add(types.InlineKeyboardButton("🔄 Aggiorna", callback_data="refresh_enemies"))
        
        self.bot.reply_to(self.message, msg, reply_markup=markup, parse_mode='markdown')

    def handle_taunt(self):
        """Taunt the enemy (Tank ability)"""
        utente = user_service.get_user(self.chatid)
        
        # Requirement: Allocated Resistance >= 10
        if utente.allocated_resistance < 10:
            self.bot.reply_to(self.message, "❌ Non sei abbastanza resistente per provocare il nemico!\nDevi avere almeno 10 punti in Resistenza.")
            return
            
        # Get active mobs
        mobs = pve_service.get_active_mobs(self.chatid)
        if not mobs:
            self.bot.reply_to(self.message, "Non ci sono nemici da provocare.")
            return
            
        # If multiple mobs, maybe ask which one? For now, taunt the first one (or boss)
        target_mob = mobs[0]
        # Prioritize boss
        for m in mobs:
            if m.is_boss:
                target_mob = m
                break
        
        success, msg = pve_service.taunt_mob(utente, target_mob.id)
        self.bot.reply_to(self.message, msg)


    def handle_shield(self):
        """Cast a shield (Tank ability)"""
        utente = user_service.get_user(self.chatid)
        
        # Requirement: Allocated Resistance >= 10
        if utente.allocated_resistance < 10:
            self.bot.reply_to(self.message, "❌ Non sei abbastanza resistente per usare lo scudo!\nDevi avere almeno 10 punti in Resistenza.")
            return
            
        # Cooldown check (30 minutes)
        now = datetime.datetime.now()
        if utente.last_shield_cast:
            diff = now - utente.last_shield_cast
            if diff.total_seconds() < 1800: # 30 mins
                remaining = int((1800 - diff.total_seconds()) / 60)
                self.bot.reply_to(self.message, f"⏳ Abilità in ricarica! Riprova tra {remaining} minuti.")
                return
                
        # Calculate Shield Amount (20% of Max HP)
        shield_amount = int(utente.max_health * 0.2)
        
        user_service.cast_shield(utente, shield_amount)
        
        self.bot.reply_to(self.message, f"🛡️ **Scudo Attivato!**\nHai guadagnato uno scudo di {shield_amount} HP per 10 minuti.\nLa tua resistenza è aumentata del 25%!")

    def handle_aoe(self, is_special=False):
        """Perform an Area of Effect attack"""
        utente = user_service.get_user(self.chatid)
        
        # Base damage calculation
        damage = utente.base_damage
        
        if is_special:
            success, msg, extra_data, attack_events = pve_service.use_special_attack(utente, is_aoe=True, chat_id=self.chat_id)
        else:
            success, msg, extra_data, attack_events = pve_service.attack_aoe(utente, damage, chat_id=self.chat_id)
        
        if success:
            sent_msg = self.bot.reply_to(self.message, msg, parse_mode='markdown')
            # Handle message deletion if mobs died
            if extra_data:
                if 'delete_message_ids' in extra_data:
                    for msg_id in extra_data['delete_message_ids']:
                        try:
                            self.bot.delete_message(self.chat_id, msg_id)
                        except:
                            pass
                
                # Re-display all surviving mobs
                if 'mob_ids' in extra_data:
                    # Get IDs of mobs that are counter-attacking to avoid double display
                    counter_attacking_ids = []
                    if attack_events:
                        counter_attacking_ids = [event.get('mob_id') for event in attack_events]
                        
                    for mob_id in extra_data['mob_ids']:
                        if mob_id not in counter_attacking_ids:
                            # Check if still alive
                            m = pve_service.get_mob_details(mob_id)
                            if m and m['health'] > 0:
                                display_mob_spawn(self.bot, self.chat_id, mob_id)
            
            # Handle counter-attacks
            if attack_events:
                for event in attack_events:
                    msg = event['message']
                    image_path = event['image']
                    mob_id = event['mob_id']
                    old_msg_id = event['last_message_id']
                    
                    markup = get_combat_markup("mob", mob_id, self.chat_id)
                    send_combat_message(self.chat_id, msg, image_path, markup, mob_id, old_msg_id)
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
        
        # Check for guide command explicitly if not in dict (or add to dict)
        if message.text.lower().startswith("/guida") or message.text.lower().startswith("/guide"):
            self.handle_guide()
            return

        # Check for enemies command
        if message.text.lower().startswith("/nemici") or message.text.lower().startswith("/enemies"):
            self.handle_enemies()
            return

        # Check for taunt command
        if message.text.lower().startswith("/taunt") or message.text.lower().startswith("/provoca"):
            self.handle_taunt()
            return

        # Check for shield command
        if message.text.lower().startswith("/scudo") or message.text.lower().startswith("/shield"):
            self.handle_shield()
            return

        # Check for aoe command
        if message.text.lower().startswith("/aoe") or message.text.lower().startswith("/area"):
            self.handle_aoe()
            return
            
        # Check for flee command
        if message.text.lower().startswith("/flee") or message.text.lower().startswith("/scappa"):
            self.handle_flee()
            return


            self.handle_aoe()
            return

@bot.message_handler(commands=['flee', 'scappa'])
def handle_flee_command(message):
    """Dedicated handler for flee command"""
    bot_cmds = BotCommands(message, bot)
    bot_cmds.handle_flee()

@bot.message_handler(func=lambda message: message.text and (message.text.startswith('+') or message.text.startswith('-')))
def handle_admin_points(message):
    """Handle admin point commands (+1000, -500)"""
    # Check admin
    # ADMIN_IDS is imported from settings
    try:
        if message.from_user.id not in ADMIN_IDS:
             return
    except NameError:
        # Fallback if ADMIN_IDS is not defined
        print("ADMIN_IDS not defined!")
        return

    try:
        parts = message.text.split()
        amount = int(parts[0])
        
        target_user = None
        if message.reply_to_message:
            target_user = user_service.get_user(message.reply_to_message.from_user.id)
        elif len(parts) > 1 and parts[1].startswith('@'):
            username = parts[1][1:]
            target_user = user_service.get_user_by_username(username)
        else:
            target_user = user_service.get_user(message.from_user.id)
            
        if target_user:
            user_service.add_points(target_user, amount)
            bot.reply_to(message, f"✅ Aggiunti {amount} Wumpa a {target_user.username or target_user.id_telegram}!")
        else:
            bot.reply_to(message, "❌ Utente non trovato.")
    except ValueError:
        pass

@bot.message_handler(commands=['missing_image_command'])
def handle_missing_image_command(message):
    """Find a character, mob, or boss without an image and ask for upload"""
    # Check if user is admin
    user_id = message.from_user.id
    utente = user_service.get_user(user_id)
    if not user_service.is_admin(utente):
        return

    # 1. Check Characters
    all_chars = character_service.get_all_characters()
    for char in all_chars:
        image_exists = False
        char_name_lower = char['nome'].lower().replace(" ", "_")
        for ext in ['.png', '.jpg', '.jpeg']:
            if os.path.exists(f"images/characters/{char_name_lower}{ext}"):
                image_exists = True
                break
        
        if not image_exists:
            # Check base name
            base_name = char['nome'].split('-')[0].strip().lower().replace(" ", "_")
            for ext in ['.png', '.jpg', '.jpeg']:
                if os.path.exists(f"images/characters/{base_name}{ext}"):
                    image_exists = True
                    break
        
        if not image_exists:
            admin_last_viewed_character[message.from_user.id] = {'type': 'character', 'id': char['id'], 'name': char['nome']}
            msg = "🔍 **Immagine Mancante Trovata!**\n\n"
            msg += f"Nome: **{char['nome']}**\n"
            msg += f"Tipo: Character\n\n"
            msg += "📸 Invia una foto ORA per caricarla!"
            bot.reply_to(message, msg, parse_mode='markdown')
            return

    # 2. Check Mobs
    if pve_service.mob_data:
        for mob in pve_service.mob_data:
            mob_name_lower = mob['nome'].lower().replace(" ", "_")
            image_exists = False
            for ext in ['.png', '.jpg', '.jpeg']:
                if os.path.exists(f"images/mobs/{mob_name_lower}{ext}"):
                    image_exists = True
                    break
            
            if not image_exists:
                admin_last_viewed_character[message.from_user.id] = {'type': 'mob', 'id': mob['nome'], 'name': mob['nome']} # Use name as ID for mobs
                msg = "🔍 **Immagine Mancante Trovata!**\n\n"
                msg += f"Nome: **{mob['nome']}**\n"
                msg += f"Tipo: Mob\n\n"
                msg += "📸 Invia una foto ORA per caricarla!"
                bot.reply_to(message, msg, parse_mode='markdown')
                return

    # 3. Check Bosses
    if pve_service.boss_data:
        for boss in pve_service.boss_data:
            boss_name_lower = boss['nome'].lower().replace(" ", "_")
            image_exists = False
            for ext in ['.png', '.jpg', '.jpeg']:
                if os.path.exists(f"images/bosses/{boss_name_lower}{ext}"):
                    image_exists = True
                    break
            
            if not image_exists:
                admin_last_viewed_character[message.from_user.id] = {'type': 'boss', 'id': boss['nome'], 'name': boss['nome']} # Use name as ID for bosses
                msg = "🔍 **Immagine Mancante Trovata!**\n\n"
                msg += f"Nome: **{boss['nome']}**\n"
                msg += f"Tipo: Boss\n\n"
                msg += "📸 Invia una foto ORA per caricarla!"
                bot.reply_to(message, msg, parse_mode='markdown')
                return

    bot.reply_to(message, "✅ Tutti i personaggi, mob e boss hanno un'immagine!")

@bot.message_handler(content_types=['document', 'animation', 'video'])
def handle_docs_and_media(message):
    """Handle media uploads (specifically for attack GIFs)"""
    chat_id = message.chat.id
    
    # Check if this is an attack GIF upload
    global pending_attack_upload
    if chat_id in pending_attack_upload:
        char_id = pending_attack_upload[chat_id]
        
        try:
            # Get file info
            file_info = None
            file_name = None
            
            if message.document:
                file_info = bot.get_file(message.document.file_id)
                file_name = message.document.file_name
            elif message.animation:
                file_info = bot.get_file(message.animation.file_id)
                file_name = message.animation.file_name or "animation.gif"
            elif message.video:
                file_info = bot.get_file(message.video.file_id)
                file_name = message.video.file_name or "video.mp4"
                
            if not file_info:
                bot.reply_to(message, "❌ Errore nel recupero del file.")
                return

            downloaded_file = bot.download_file(file_info.file_path)
            
            # Determine extension
            ext = os.path.splitext(file_name)[1].lower()
            if not ext:
                ext = os.path.splitext(file_info.file_path)[1].lower()
            
            if ext not in ['.gif', '.mp4', '.mov']:
                bot.reply_to(message, "❌ Formato non supportato. Usa GIF o MP4.")
                return

            # Get character info for naming
            from services.character_loader import get_character_loader
            char_loader = get_character_loader()
            char = char_loader.get_character_by_id(char_id)
            
            if not char:
                bot.reply_to(message, "❌ Errore: Personaggio non trovato.")
                del pending_attack_upload[chat_id]
                return
                
            # Sanitize filename: [char_name]_[attack_name].ext
            safe_char = char['nome'].lower().replace(' ', '_')
            safe_attack = char['special_attack_name'].lower().replace(' ', '_')
            # Remove non-alphanumeric except underscore
            import re
            safe_char = re.sub(r'[^a-z0-9_]', '', safe_char)
            safe_attack = re.sub(r'[^a-z0-9_]', '', safe_attack)
            
            new_filename = f"{safe_char}_{safe_attack}{ext}"
            save_path = f"images/attacks/{new_filename}"
            
            # Save file
            with open(save_path, 'wb') as new_file:
                new_file.write(downloaded_file)
                
            # Update CSV
            if char_loader.update_character_gif(char_id, new_filename):
                bot.reply_to(message, f"✅ GIF salvata per **{char['nome']}**!\nFile: `{new_filename}`")
            else:
                bot.reply_to(message, "⚠️ File salvato ma errore nell'aggiornamento del CSV.")
                
            # Clear pending and ask for next
            del pending_attack_upload[chat_id]
            
            # Prompt for next one
            # Prompt for next one
            handle_missing_attack(message)
            
        except Exception as e:
            print(f"Error handling upload: {e}")
            bot.reply_to(message, f"❌ Errore durante l'upload: {e}")
            if chat_id in pending_attack_upload:
                del pending_attack_upload[chat_id]
        return

    # Existing document handler logic (if any) or pass
    pass
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    """Handle photo uploads for characters, mobs, and bosses"""
    user_id = message.from_user.id
    
    # Check if admin is waiting to upload
    if user_id in admin_last_viewed_character:
        pending = admin_last_viewed_character[user_id]
        
        # Handle old format (just ID) for backward compatibility or if session persisted
        if not isinstance(pending, dict):
             pending = {'type': 'character', 'id': pending, 'name': 'Unknown'}
             # Try to fetch name if possible, or just fail gracefully
             char = character_service.get_character(pending['id'])
             if char: pending['name'] = char['nome']

        try:
            # Get the photo
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            name_lower = pending['name'].lower().replace(" ", "_")
            
            if pending['type'] == 'character':
                save_dir = "images/characters"
            elif pending['type'] == 'mob':
                save_dir = "images/mobs"
            elif pending['type'] == 'boss':
                save_dir = "images/bosses"
            else:
                bot.reply_to(message, "❌ Tipo sconosciuto.")
                return

            save_path = f"{save_dir}/{name_lower}.png"
            
            # Ensure directory exists
            os.makedirs(save_dir, exist_ok=True)
            
            # Save file
            with open(save_path, 'wb') as new_file:
                new_file.write(downloaded_file)
                
            bot.reply_to(message, f"✅ Immagine salvata per **{pending['name']}** ({pending['type']})!\nUsa /missing_image_command per cercarne un'altra.", parse_mode='markdown')
            
            # Clear pending state
            del admin_last_viewed_character[user_id]
            
        except Exception as e:
            bot.reply_to(message, f"❌ Errore nel salvataggio: {e}")
            # Don't clear pending state on error so they can retry

@bot.message_handler(content_types=['text'] + util.content_type_media)
def any(message):
    # Initialize services needed
    from services.pve_service import PvEService
    pve_service = PvEService()

    # Track activity IMMEDIATELY
    user_service.track_activity(message.from_user.id, message.chat.id)
    
    # Check if message is a forward
    if message.forward_from_chat or message.forward_from:
        # SCAN FEATURE: Check if user has Scouter equipped and message contains mob ID
        if message.chat.type == 'private' and message.text:
            # Try to extract mob ID from forwarded message
            # Mob messages typically contain "ID: XXX" or similar pattern
            import re
            mob_id_match = re.search(r'ID:\s*(\d+)', message.text)
            
            if mob_id_match:
                mob_id = int(mob_id_match.group(1))
                user_id = message.from_user.id
                
                # Check if user has Scouter equipped
                from sqlalchemy import text
                session = user_service.db.get_session()
                try:
                    has_scouter = session.execute(text("""
                        SELECT 1 FROM user_equipment ue
                        JOIN equipment e ON ue.equipment_id = e.id
                        WHERE ue.user_id = :uid AND ue.equipped = TRUE 
                        AND e.effect_type = 'scan'
                    """), {"uid": user_id}).fetchone()
                    
                    if has_scouter:
                        # Get mob details from PVE service
                        from services.pve_service import PVEService
                        pve_service = PVEService(user_service.db)
                        
                        # Get mob from active enemies
                        mob = pve_service.get_mob_by_id(mob_id)
                        
                        if mob:
                            # Build detailed stats message
                            msg = f"🔍 **SCOUTER SCAN - Analisi Completa**\n\n"
                            msg += f"📛 **Nome**: {mob.nome}\n"
                            msg += f"🆔 **ID**: {mob.id}\n"
                            msg += f"⚡ **Livello**: {mob.livello}\n\n"
                            msg += f"❤️ **HP**: {mob.current_hp}/{mob.max_health}\n"
                            msg += f"⚔️ **Attacco**: {mob.base_damage}\n"
                            msg += f"🛡️ **Difesa**: {mob.defense if hasattr(mob, 'defense') else 0}\n"
                            msg += f"💨 **Velocità**: {mob.speed if hasattr(mob, 'speed') else 'N/A'}\n\n"
                            
                            # Boss status
                            if mob.is_boss:
                                msg += f"👑 **BOSS** - Ricompense maggiorate!\n"
                            
                            # Elemental info
                            if hasattr(mob, 'element') and mob.element:
                                msg += f"🌟 **Elemento**: {mob.element}\n"
                            
                            # Resistances
                            if hasattr(mob, 'resistances') and mob.resistances:
                                msg += f"🛡️ **Resistenze**: {mob.resistances}\n"
                            
                            # Weaknesses
                            if hasattr(mob, 'weaknesses') and mob.weaknesses:
                                msg += f"💥 **Debolezze**: {mob.weaknesses}\n"
                            
                            # Special abilities
                            if hasattr(mob, 'special_ability') and mob.special_ability:
                                msg += f"✨ **Abilità**: {mob.special_ability}\n"
                            
                            msg += f"\n💡 *Scouter attivo - Scansione completa*"
                            
                            bot.reply_to(message, msg, parse_mode='markdown')
                            session.close()
                            return
                        else:
                            bot.reply_to(message, "❌ Mob non trovato o già sconfitto!")
                            session.close()
                            return
                    else:
                        bot.reply_to(message, "🔒 Hai bisogno di uno **Scouter** equipaggiato per analizzare i nemici!", parse_mode='markdown')
                        session.close()
                        return
                        
                except Exception as e:
                    print(f"Error in Scan feature: {e}")
                    import traceback
                    traceback.print_exc()
                finally:
                    if session:
                        session.close()
        
        # GAME PURCHASE: Only allow purchases in private chat
        if message.chat.type != 'private':
            return

        # RESTRICTION: Check if forward source is valid (bot must be member)
        # If forwarded from a user (no forward_from_chat), we block it
        if not message.forward_from_chat:
             return
             
    # Private Chat Catch-all: If we are here, the message was not handled by specific handlers
    if message.chat.type == 'private':
        # Try to handle it via BotCommands dispatcher (manual dispatch)
        cmd = BotCommands(message, bot)
        # Check if the text matches a private command key
        if message.text in cmd.comandi_privati:
            # Execute handler directly
            try:
                cmd.comandi_privati[message.text]()
                return
            except Exception as e:
                print(f"[ERROR] Error executing private command {message.text}: {e}")
                # Fallthrough to error message
        
        # If not handled:
        bot.send_message(message.chat.id, "❌ Comando non riconosciuto o menu scaduto.\nUsa il menu qui sotto per navigare:", reply_markup=get_main_menu())
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
    
    # Passive EXP gain: 1-10 EXP per message (silent, no notification)
    # ONLY IN OFFICIAL GROUP AND NOT WHILE RESTING
    if message.chat.id == GRUPPO_AROMA:
        resting_status = user_service.get_resting_status(message.from_user.id)
        if not resting_status:
            # Anti-spam check: 30 seconds cooldown for chat rewards
            can_receive_reward = True
            if utente.last_chat_drop_time:
                elapsed = (datetime.datetime.now() - utente.last_chat_drop_time).total_seconds()
                if elapsed < 30:
                    can_receive_reward = False
            
            if not can_receive_reward:
                return

            # Update last drop time
            user_service.update_user(message.from_user.id, {'last_chat_drop_time': datetime.datetime.now()})

            passive_exp = random.randint(1, 10)
            level_up_info = user_service.add_exp_by_id(message.from_user.id, passive_exp)
            
            if level_up_info['leveled_up']:
                username = escape_markdown(message.from_user.username if message.from_user.username else message.from_user.first_name)
                bot.send_message(message.chat.id, f"🎉 **LEVEL UP!** @{username} è salito al livello **{level_up_info['new_level']}**! 🚀", parse_mode='markdown')
            
            # Track chat EXP for achievements
            new_chat_exp_total = user_service.add_chat_exp(message.from_user.id, passive_exp)
            
            achievement_tracker = AchievementTracker()
            achievement_tracker.on_chat_exp(
                message.from_user.id,
                new_chat_exp_total,
                increment=passive_exp
            )
            # Process achievements immediately
            achievement_tracker.process_pending_events(limit=5)
    
    # Sunday bonus: 10 Wumpa when you write on Sunday
    if datetime.datetime.today().weekday() == 6:  # Sunday
        try:
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
                bot.send_message(message.chat.id, f"🎉 **Buona Domenica!**\nEcco il tuo regalo settimanale:\n\n{box_msg}", parse_mode='Markdown')
            session.close()
        except Exception as e:
            print(f"Error in Sunday bonus: {e}")
            try:
                session.close()
            except:
                pass
        
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
        
        # Random Mob Spawn
        spawn_chance = 0.08 # Increased from 0.05
        
        markup = None # Initialize markup to avoid UnboundLocalError
        
        if random.random() < spawn_chance:
            # 10% chance to spawn a boss instead of a mob
            if random.random() < 0.10:
                success, msg, mob_id = pve_service.spawn_boss(chat_id=message.chat.id, reference_level=utente.livello)
            else:
                success, msg, mob_id = pve_service.spawn_specific_mob(chat_id=message.chat.id, reference_level=utente.livello)
            
            if mob_id:
                mob = pve_service.get_current_mob_status(mob_id)
                if mob:
                    markup = get_combat_markup("mob", mob_id, message.chat.id)
                    
                    msg_text = f"⚠️ Un {mob['name']} selvatico è apparso!\n{format_mob_stats(mob, show_full=False)}\n\nSconfiggilo per ottenere ricompense!"
                    
                    # Send with image if available
                    sent_msg = None
                    if mob.get('image') and os.path.exists(mob['image']):
                        try:
                            with open(mob['image'], 'rb') as photo:
                                sent_msg = bot.send_photo(message.chat.id, photo, caption=msg_text, reply_markup=markup, parse_mode='markdown')
                        except:
                            sent_msg = bot.send_message(message.chat.id, msg_text, reply_markup=markup, parse_mode='markdown')
                    else:
                        sent_msg = bot.send_message(message.chat.id, msg_text, reply_markup=markup, parse_mode='markdown')
                    
                    # Update message ID for deletion later
                    if sent_msg:
                        pve_service.update_mob_message_id(mob_id, sent_msg.message_id)
        
        # Mobs attack! (subject to cooldowns)
        attack_events = pve_service.mob_random_attack(chat_id=message.chat.id)
        
        # Send immediate attack messages if any
        if attack_events:
            for event in attack_events:
                msg = event['message']
                image_path = event['image']
                # Fix: Generate markup for the specific attacking mob
                # The event should contain mob_id. If not, we can't generate specific buttons.
                # Assuming pve_service returns mob_id in event.
                attacker_id = event.get('mob_id')
                
                attack_markup = None
                if attacker_id:
                    attack_markup = get_combat_markup("mob", attacker_id, message.chat.id)
                
                try:
                    if image_path and os.path.exists(image_path):
                        with open(image_path, 'rb') as photo:
                            bot.send_photo(message.chat.id, photo, caption=msg, reply_markup=attack_markup, parse_mode='markdown')
                    else:
                        bot.send_message(message.chat.id, msg, reply_markup=attack_markup, parse_mode='markdown')
                except:
                    bot.send_message(message.chat.id, msg, reply_markup=markup, parse_mode='markdown')

    bothandler = BotCommands(message, bot)
    bothandler.handle_all_commands()


def display_mob_spawn(bot, chat_id, mob_id):
    """Helper to display a spawned mob with image and buttons"""
    print(f"[DEBUG] display_mob_spawn called for mob_id {mob_id} in chat {chat_id}")
    mob = pve_service.get_mob_details(mob_id)
    if not mob: 
        print(f"[DEBUG] display_mob_spawn: mob details not found for {mob_id}")
        return
    
    # Format ASCII Card
    hp_percent = int((mob['health'] / mob['max_health']) * 10)
    hp_bar = "█" * hp_percent + "░" * (10 - hp_percent)
    
    msg_text = f"⚠️ Un {mob['name']} è apparso!\n"
    msg_text += f"╔══════🕹 {mob['name'].upper()} ══════╗\n"
    msg_text += f" ❤️ Vita: {hp_bar} {int((mob['health']/mob['max_health'])*100)}%\n"
    msg_text += f" ⚡ Velocità: {mob.get('speed', 0)}\n"
    msg_text += f" 📊 Livello: {mob.get('level', 1)}\n"
    msg_text += f"          aROMa\n"
    msg_text += f"╚═══════════════════════╝\n"
    msg_text += "\nSconfiggilo per proseguire!"
    
    image_path = mob['image_path']
    print(f"[DEBUG] display_mob_spawn: image_path={image_path}")
    
    sent_msg = None
    try:
        # Define markup inside try block to be safe
        mob_type = "boss" if mob.get('is_boss') else "mob"
        markup = get_combat_markup(mob_type, mob_id, chat_id)
        
        if image_path and os.path.exists(image_path):
            with open(image_path, 'rb') as photo:
                sent_msg = bot.send_photo(chat_id, photo, caption=msg_text, reply_markup=markup, parse_mode='markdown')
        else:
            print(f"[DEBUG] display_mob_spawn: sending text only (image not found or None)")
            sent_msg = bot.send_message(chat_id, msg_text, reply_markup=markup, parse_mode='markdown')
            
        if sent_msg:
            pve_service.update_mob_message_id(mob_id, sent_msg.message_id)
            print(f"[DEBUG] display_mob_spawn: message sent successfully (id: {sent_msg.message_id})")
    except Exception as e:
        print(f"Error displaying mob: {e}")

def trigger_dungeon_mob_attack(bot, chat_id, mob_ids):
    """Helper to trigger immediate attack from spawned mobs"""
    print(f"[DEBUG] Triggering immediate attack for mobs: {mob_ids}")
    for mob_id in mob_ids:
        # Force attack
        attack_events = pve_service.mob_random_attack(specific_mob_id=mob_id, chat_id=chat_id)
        
        if attack_events:
            for event in attack_events:
                msg = event['message']
                image_path = event['image']
                mob_id = event['mob_id']
                old_msg_id = event['last_message_id']
                
                markup = get_combat_markup("mob", mob_id, chat_id)
                send_combat_message(chat_id, msg, image_path, markup, mob_id, old_msg_id)

def send_combat_message(chat_id, text, image_path, markup, mob_id, old_message_id=None, is_death=False):
    """Helper to send combat messages, deleting the previous one and showing the enemy image."""
    if old_message_id:
        try:
            bot.delete_message(chat_id, old_message_id)
        except Exception:
            pass
    
    # Parse text to extract HP if it's in the old format or raw text
    # But wait, the text passed here is usually constructed by the caller.
    # We should modify the CALLER to format the text correctly, OR reformat it here if it's a simple string.
    # However, pve_service.attack_mob returns a message that is already formatted.
    # The user wants the ASCII card format.
    # Let's check if the text is already an ASCII card.
    
    # Actually, the best place to format the message is in the caller (handle_combat_callback) 
    # or inside pve_service.attack_mob return value.
    # But pve_service returns a simple string.
    # Let's modify send_combat_message to WRAP the text in the card if it's not already.
    
    # Wait, pve_service.attack_mob returns "Hai inflitto X danni...".
    # We need to fetch the mob status again to build the card?
    # Yes, handle_combat_callback does fetching if needed, or we can do it here.
    
    # Let's look at handle_combat_callback again. It constructs `full_msg = f"@{username}\n{msg}"`.
    # This is just the attack result.
    # The user wants the MOB STATUS CARD to be updated.
    
    # So we need to rebuild the card with the new HP.
    # We need the mob object.
    
    mob = pve_service.get_mob_details(mob_id)
    if mob:
        hp_percent = int((mob['health'] / mob['max_health']) * 10)
        hp_bar = "█" * hp_percent + "░" * (10 - hp_percent)
        
        # ASCII Card with HIDDEN HP (100%)
        card = f"╔══════🕹 {mob['name'].upper()} ══════╗\n"
        card += f" ❤️ Vita: {hp_bar} {int((mob['health']/mob['max_health'])*100)}%\n"
        card += f" ⚡ Velocità: {mob.get('speed', 0)}\n"
        card += f" 📊 Livello: {mob.get('level', 1)}\n"
        card += f"          aROMa\n"
        card += f"╚═══════════════════════╝\n"
        
        # Append the attack result text below the card ONLY if not already there
        if "╔══════🕹" in text:
            final_text = text
        else:
            final_text = f"{text}\n\n{card}"
        
        # Update image path if not provided (use mob's image)
        if not image_path:
            image_path = mob.get('image_path')
    else:
        final_text = text
    
    sent_msg = None
    try:
        if image_path and os.path.exists(image_path):
            ext = os.path.splitext(image_path)[1].lower()
            if ext in ['.gif']:
                with open(image_path, 'rb') as animation:
                    sent_msg = bot.send_animation(chat_id, animation, caption=final_text, reply_markup=markup, parse_mode='markdown')
            elif ext in ['.mp4', '.mov']:
                with open(image_path, 'rb') as video:
                    sent_msg = bot.send_video(chat_id, video, caption=final_text, reply_markup=markup, parse_mode='markdown')
            else:
                with open(image_path, 'rb') as photo:
                    sent_msg = bot.send_photo(chat_id, photo, caption=final_text, reply_markup=markup, parse_mode='markdown')
        else:
            sent_msg = bot.send_message(chat_id, final_text, reply_markup=markup, parse_mode='markdown')
        
        if not is_death and sent_msg:
            pve_service.update_mob_message_id(mob_id, sent_msg.message_id)
    except Exception as e:
        print(f"[ERROR] send_combat_message failed: {e}")
        try:
            sent_msg = bot.send_message(chat_id, final_text, reply_markup=markup, parse_mode='markdown')
            if not is_death:
                pve_service.update_mob_message_id(mob_id, sent_msg.message_id)
        except:
            pass
    return sent_msg


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    
    # Track activity for mob targeting IMMEDIATELY
    user_service.track_activity(user_id, chat_id)

    # --- Crafting Callbacks (handle before other callbacks) ---
    if call.data == "craft_select_equipment":
        print(f"[DEBUG] Catch-all: detected craft_select_equipment")
        handle_craft_select_equipment(call)
        return
    elif call.data.startswith("craft_view_set|"):
        print(f"[DEBUG] Catch-all: detected craft_view_set")
        handle_craft_view_set(call)
        return
    elif call.data.startswith("craft_item|"):
        print(f"[DEBUG] Catch-all: detected craft_item| with data: {call.data}")
        handle_craft_item(call)
        return
    elif call.data == "craft_view_resources":
        print(f"[DEBUG] Catch-all: detected craft_view_resources")
        handle_craft_view_resources(call)
        return
    elif call.data == "craft_claim_all":
        print(f"[DEBUG] Catch-all: detected craft_claim_all")
        handle_craft_claim_all(call)
        return

    # --- Ranking Callbacks ---
    if call.data.startswith("ranking|"):
        cmd = BotCommands(call.message, bot, user_id=call.from_user.id)
        # Patch for callback user ID logic
        cmd.chatid = user_id
        cmd.user_id = user_id
        
        _, r_type = call.data.split("|", 1)
        cmd.handle_classifica(ranking_type=r_type)
        return
    
    # Guide Navigation
    if call.data.startswith("guide_"):
        safe_answer_callback(call.id)
        
        if call.data == "guide_main":
            # Back to main menu
            categories = guide_service.get_categories()
            markup = types.InlineKeyboardMarkup()
            for key, title in categories:
                markup.add(types.InlineKeyboardButton(title, callback_data=f"guide_cat|{key}"))
            bot.edit_message_text("📚 **Guida di aROMa**\n\nSeleziona un argomento per saperne di più:", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='markdown')
            
        elif call.data.startswith("guide_cat|"):
            cat_key = call.data.split("|")[1]
            category = guide_service.get_category(cat_key)
            if category:
                markup = types.InlineKeyboardMarkup()
                for key, item in category['items'].items():
                    markup.add(types.InlineKeyboardButton(item['title'], callback_data=f"guide_item|{cat_key}|{key}"))
                markup.add(types.InlineKeyboardButton("🔙 Indietro", callback_data="guide_main"))
                
                msg = f"**{category['title']}**\n\n{category['description']}"
                bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='markdown')
                
        elif call.data.startswith("guide_item|"):
            parts = call.data.split("|")
            cat_key = parts[1]
            item_key = parts[2]
            item = guide_service.get_item(cat_key, item_key)
            
            if item:
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("🔙 Indietro", callback_data=f"guide_cat|{cat_key}"))
                
                msg = f"**{item['title']}**\n\n{item['text']}"
                bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='markdown')
        return

    if call.data == "stat_alloc":
        try:
            safe_answer_callback(call.id)
        except:
            pass
            
        # Use BotCommands to handle stats
        bot_cmds = BotCommands(call.message, bot, user_id=call.from_user.id)
        bot_cmds.chatid = user_id 
        bot_cmds.message = call.message 
        bot_cmds.handle_stats(is_callback=True)
        return

    # Market callbacks delegation
    if call.data.startswith("market_") or call.data.startswith("buy_item") or call.data.startswith("cancel_listing") or call.data == "market_menu":
        bot_cmds = BotCommands(call.message, bot, user_id=call.from_user.id)
        bot_cmds.chatid = user_id
        bot_cmds.message = call.message
        # We need to manually handle this dispatch in BotCommands or exposing handle_market_callback
        bot_cmds.handle_market_callback(call)
        return

    if call.data == "view_equipment":
        safe_answer_callback(call.id)
        
        # Get user equipment from database
        user_id = call.from_user.id
        utente = user_service.get_user(user_id)
        
        if not utente:
            bot.answer_callback_query(call.id, "Utente non trovato!")
            return
        
        nome_utente = utente.nome if utente.username is None else utente.username
        
        # Get user's equipment from database
        from sqlalchemy import text
        session = user_service.db.get_session()
        
        try:
            # Get all user equipment with details
            items = session.execute(text("""
                SELECT ue.id, ue.equipped, ue.slot_equipped, e.name, e.slot, 
                       COALESCE(ue.rarity, e.rarity) as rarity, 
                       COALESCE(ue.stats_json, e.stats_json) as stats_json
                FROM user_equipment ue
                JOIN equipment e ON ue.equipment_id = e.id
                WHERE ue.user_id = :uid
                ORDER BY ue.equipped DESC, COALESCE(ue.rarity, e.rarity) DESC
            """), {"uid": user_id}).fetchall()
            
            # Organize by slot
            slots = {
                'head': None, 'shoulders': None, 'chest': None, 'wrists': None,
                'hands': None, 'waist': None, 'legs': None, 'feet': None,
                'main_hand': None, 'off_hand': None,
                'accessory1': None, 'accessory2': None
            }
            
            for item in items:
                item_id, equipped, slot_equipped, name, slot, rarity, stats = item
                if equipped and slot_equipped and slot_equipped in slots and not slots[slot_equipped]:
                    symbol = get_rarity_emoji(rarity)
                    slots[slot_equipped] = f"{symbol} {name}"
            
            # ASCII Equipment Display - simplified without right border alignment
            msg = f"```\n"
            msg += f"╔════════════════════════════════════\n"
            
            # Header with name, level
            msg += f"║ 🧙 {nome_utente} │ Lv {utente.livello}\n"
            
            msg += f"╠════════════════════════════════════\n"
            msg += f"║\n"
            
            # Center figure with emoji
            msg += f"║            👑\n"
            msg += f"║            O\n"
            msg += f"║       💪   /|\\   ⚔️\n"
            msg += f"║            |\n"
            msg += f"║            🔗\n"
            msg += f"║           / \\\n"
            msg += f"║          👖 👟\n"
            msg += f"║\n"
            
            # Slot list format - simplified
            def format_slot(emoji, label, item_text):
                return f"║ [{emoji} {label.ljust(12)}] {item_text}\n"
            
            msg += format_slot("👑", "TESTA", slots['head'] or "———")
            msg += format_slot("🎽", "SPALLINE", slots['shoulders'] or "———")
            msg += format_slot("⚔️", "ARMA", slots['main_hand'] or "———")
            msg += format_slot("👔", "TORSO", slots['chest'] or "———")
            msg += format_slot("🔗", "CINTURA", slots['waist'] or "———")
            msg += format_slot("👖", "GAMBE", slots['legs'] or "———")
            msg += format_slot("👟", "PIEDI", slots['feet'] or "———")
            msg += f"║\n"
            
            msg += f"╠═════════════ ACCESSORI ═════════════\n"
            acc1 = slots['accessory1'] or "⚫ Slot libero"
            acc2 = slots['accessory2'] or "⚫ Slot libero"
            msg += f"║ 1️⃣ {acc1}\n"
            msg += f"║ 2️⃣ {acc2}\n"
            
            msg += f"╠════════════════════════════════════\n"
            
            # Count inventory items
            inventory_count = len([i for i in items if not i[1]])  # not equipped
            equipped_count = len([i for i in items if i[1]])
            
            msg += f"║ 📦 Inv: {inventory_count} item   ⚔️ Equip: {equipped_count} / 12\n"
            msg += f"╚════════════════════════════════════\n"
            msg += f"```"
            
        except Exception as e:
            print(f"Error loading equipment: {e}")
            import traceback
            traceback.print_exc()
            msg = "❌ Errore nel caricamento dell'equipaggiamento!"
        finally:
            session.close()
        
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("📦 Inventario", callback_data="equip_inventory"),
            types.InlineKeyboardButton("🔙 Profilo", callback_data="back_to_profile")
        )
        
        try:
            bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, 
                                parse_mode='markdown', reply_markup=markup)
        except:
            bot.send_message(call.message.chat.id, msg, parse_mode='markdown', reply_markup=markup)
        return

    if call.data == "equip_inventory":
        safe_answer_callback(call.id)
        user_id = call.from_user.id
        
        # Get user's unequipped items
        from sqlalchemy import text
        session = user_service.db.get_session()
        
        try:
            items = session.execute(text("""
                SELECT ue.id, e.name, e.slot, e.rarity, e.min_level, e.description
                FROM user_equipment ue
                JOIN equipment e ON ue.equipment_id = e.id
                WHERE ue.user_id = :uid AND ue.equipped = FALSE
                ORDER BY e.rarity DESC, e.name
            """), {"uid": user_id}).fetchall()
            
            utente = user_service.get_user(user_id)
            rarity_symbols = {1: '●', 2: '◆', 3: '★', 4: '✦', 5: '✪'}
            rarity_names = {1: 'Comune', 2: 'Non Comune', 3: 'Rara', 4: 'Epica', 5: 'Leggendaria'}
            slot_emoji = {
                'head': '👑', 'shoulders': '🎽', 'chest': '👔', 'wrists': '💪',
                'hands': '🧤', 'waist': '🔗', 'legs': '👖', 'feet': '👟',
                'main_hand': '⚔️', 'off_hand': '🛡️', 'accessory1': '💍', 'accessory2': '💍'
            }
            
            if not items:
                msg = "📦 **Inventario Equipaggiamento**\n\n"
                msg += "Il tuo inventario è vuoto!\n"
                msg += "Tutti gli oggetti sono equipaggiati."
            else:
                msg = f"📦 **Inventario Equipaggiamento** ({len(items)} item)\n\n"
                
            markup = types.InlineKeyboardMarkup(row_width=1)
            
            for item in items:
                item_id, name, slot, rarity, min_level, desc = item
                symbol = rarity_symbols.get(rarity, '●')
                emoji = slot_emoji.get(slot, '📦')
                
                # Check level requirement
                can_equip = utente.livello >= min_level
                lock = "" if can_equip else "🔒 "
                
                btn_text = f"{lock}{symbol} {emoji} {name}"
                if not can_equip:
                    btn_text += f" (Lv{min_level})"
                
                callback = f"equip_item|{item_id}" if can_equip else "equip_locked"
                markup.add(types.InlineKeyboardButton(btn_text, callback_data=callback))
            
            markup.add(types.InlineKeyboardButton("🔙 Equipaggiamento", callback_data="view_equipment"))
            
            try:
                bot.edit_message_text(msg, call.message.chat.id, call.message.message_id,
                                    parse_mode='markdown', reply_markup=markup)
            except:
                bot.send_message(call.message.chat.id, msg, parse_mode='markdown', reply_markup=markup)
                
        except Exception as e:
            print(f"Error loading inventory: {e}")
            import traceback
            traceback.print_exc()
            safe_answer_callback(call.id, "Errore caricamento inventario!")
        finally:
            session.close()
        return

    if call.data.startswith("equip_item|"):
        item_id = int(call.data.split("|")[1])
        user_id = call.from_user.id
        
        from sqlalchemy import text
        session = user_service.db.get_session()
        
        try:
            # Get item details
            item = session.execute(text("""
                SELECT e.slot, e.name FROM user_equipment ue
                JOIN equipment e ON ue.equipment_id = e.id
                WHERE ue.id = :iid AND ue.user_id = :uid
            """), {"iid": item_id, "uid": user_id}).fetchone()
            
            if not item:
                safe_answer_callback(call.id, "Oggetto non trovato!")
                return
            
            slot, name = item
            
            # Unequip current item in that slot
            session.execute(text("""
                UPDATE user_equipment
                SET equipped = FALSE, slot_equipped = NULL
                WHERE user_id = :uid AND slot_equipped = :slot
            """), {"uid": user_id, "slot": slot})
            
            # Equip new item
            session.execute(text("""
                UPDATE user_equipment
                SET equipped = TRUE, slot_equipped = :slot
                WHERE id = :iid
            """), {"iid": item_id, "slot": slot})
            
            session.commit()
            session.close()
            
            safe_answer_callback(call.id, f"✅ {name} equipaggiato!")
            
            # Refresh to equipment view - just edit message to show updated equipment
            # Re-fetch updated data and rebuild view
            from sqlalchemy import text
            new_session = user_service.db.get_session()
            try:
                items = new_session.execute(text("""
                    SELECT ue.id, ue.equipped, ue.slot_equipped, e.name, e.slot, e.rarity, e.stats_json
                    FROM user_equipment ue
                    JOIN equipment e ON ue.equipment_id = e.id
                    WHERE ue.user_id = :uid
                    ORDER BY ue.equipped DESC, e.rarity DESC
                """), {"uid": user_id}).fetchall()
                
                slots_new = {
                    'head': None, 'shoulders': None, 'chest': None, 'wrists': None,
                    'hands': None, 'waist': None, 'legs': None, 'feet': None,
                    'main_hand': None, 'off_hand': None,
                    'accessory1': None, 'accessory2': None
                }
                
                rarity_symbols = {1: '●', 2: '◆', 3: '★', 4: '✦', 5: '✪'}
                
                for item in items:
                    item_id_i, equipped_i, slot_equipped_i, name_i, slot_i, rarity_i, stats_i = item
                    if equipped_i and slot_equipped_i and slot_equipped_i in slots_new and not slots_new[slot_equipped_i]:
                        symbol = rarity_symbols.get(rarity_i, '●')
                        slots_new[slot_equipped_i] = f"{symbol} {name_i}"
                
                # Rebuild message
                msg_refresh = f"```\n"
                msg_refresh += f"╔════════════════════════════════════\n"
                msg_refresh += f"║ 🧙 {nome_utente} │ Lv {utente.livello}\n"
                msg_refresh += f"╠════════════════════════════════════\n"
                msg_refresh += f"║\n"
                msg_refresh += f"║            👑\n"
                msg_refresh += f"║            O\n"
                msg_refresh += f"║       💪   /|\\   ⚔️\n"
                msg_refresh += f"║            |\n"
                msg_refresh += f"║            🔗\n"
                msg_refresh += f"║           / \\\n"
                msg_refresh += f"║          👖 👟\n"
                msg_refresh += f"║\n"
                
                def format_slot_refresh(emoji, label, item_text):
                    return f"║ [{emoji} {label.ljust(12)}] {item_text}\n"
                
                msg_refresh += format_slot_refresh("👑", "TESTA", slots_new['head'] or "———")
                msg_refresh += format_slot_refresh("🎽", "SPALLINE", slots_new['shoulders'] or "———")
                msg_refresh += format_slot_refresh("⚔️", "ARMA", slots_new['main_hand'] or "———")
                msg_refresh += format_slot_refresh("👔", "TORSO", slots_new['chest'] or "———")
                msg_refresh += format_slot_refresh("🔗", "CINTURA", slots_new['waist'] or "———")
                msg_refresh += format_slot_refresh("👖", "GAMBE", slots_new['legs'] or "———")
                msg_refresh += format_slot_refresh("👟", "PIEDI", slots_new['feet'] or "———")
                msg_refresh += f"║\n"
                
                msg_refresh += f"╠═════════════ ACCESSORI ═════════════\n"
                acc1_refresh = slots_new['accessory1'] or "⚫ Slot libero"
                acc2_refresh = slots_new['accessory2'] or "⚫ Slot libero"
                msg_refresh += f"║ 1️⃣ {acc1_refresh}\n"
                msg_refresh += f"║ 2️⃣ {acc2_refresh}\n"
                
                msg_refresh += f"╠════════════════════════════════════\n"
                inv_count = len([i for i in items if not i[1]])
                eq_count = len([i for i in items if i[1]])
                msg_refresh += f"║ 📦 Inv: {inv_count} item   ⚔️ Equip: {eq_count} / 12\n"
                msg_refresh += f"╚════════════════════════════════════\n"
                msg_refresh += f"```"
                
                markup_refresh = types.InlineKeyboardMarkup()
                markup_refresh.row(
                    types.InlineKeyboardButton("📦 Inventario", callback_data="equip_inventory"),
                    types.InlineKeyboardButton("🔙 Profilo", callback_data="back_to_profile")
                )
                
                bot.edit_message_text(msg_refresh, call.message.chat.id, call.message.message_id,
                                    parse_mode='markdown', reply_markup=markup_refresh)
            finally:
                new_session.close()
            return
            
        except Exception as e:
            print(f"Error equipping item: {e}")
            import traceback
            traceback.print_exc()
            safe_answer_callback(call.id, "Errore equipaggiamento!")
            session.rollback()
        finally:
            if session:
                session.close()
        return

    if call.data == "equip_locked":
        safe_answer_callback(call.id, "🔒 Livello troppo basso!", show_alert=True)
        return

    if call.data == "back_to_profile":
        safe_answer_callback(call.id)
        # Recreate profile display
        bot_cmds = BotCommands(call.message, bot, user_id=call.from_user.id)
        bot_cmds.chatid = call.from_user.id
        bot_cmds.message = call.message
        
        # Delete old message and send new profile
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        bot_cmds.handle_profile()
        return

    if call.data == "title_menu":
        # Don't answer here, let handle_title_selection do it (to show alert if needed)
        
        bot_cmds = BotCommands(call.message, bot, user_id=call.from_user.id)
        bot_cmds.chatid = user_id
        bot_cmds.message = call.message
        bot_cmds.handle_title_selection(is_callback=True, call_id=call.id)
        return
        
    if call.data.startswith("set_title|"):
        key = call.data.split("|")[1]
        
        if key == "NONE":
            user_service.update_user(user_id, {'title': None})
            msg = "Titolo rimosso!"
        else:
            # Verify user owns achievement (security check)
            from services.achievement_tracker import AchievementTracker
            tracker = AchievementTracker()
            achievements = tracker.get_user_achievements(user_id)
            
            tier_emojis = {
                'bronze': '🥉',
                'silver': '🥈',
                'gold': '🥇',
                'platinum': '💎',
                'diamond': '💎',
                'legendary': '👑'
            }
            
            selected_title = None
            for ach in achievements:
                if ach['key'] == key and ach['current_tier']:
                    emoji = tier_emojis.get(ach['current_tier'], '')
                    selected_title = f"{ach['name']} {emoji}"
                    break
            
            if selected_title:
                user_service.update_user(user_id, {'title': selected_title})
                msg = f"Titolo impostato: {selected_title}"
            else:
                msg = "Non possiedi questo titolo o achievement non trovato!"
        
        safe_answer_callback(call.id, msg)
        
        # Refresh menu
        bot_cmds = BotCommands(call.message, bot, user_id=call.from_user.id)
        bot_cmds.chatid = user_id
        bot_cmds.message = call.message
        bot_cmds.handle_title_selection(is_callback=True, call_id=call.id)
        return

    if call.data.startswith("guild_create_final|"):
        _, name, x, y = call.data.split("|")
        success, msg, guild_id = guild_service.create_guild(call.from_user.id, name, int(x), int(y))
        if success:
            safe_answer_callback(call.id, "Gilda creata con successo!")
            # Show the guild menu
            handle_guild_cmd(call.message)
        else:
            safe_answer_callback(call.id, msg, show_alert=True)
        return

    elif call.data == "guild_found_start":
        safe_answer_callback(call.id)
        # Fix: use call.from_user.id instead of call.message.from_user.id
        user_id = call.from_user.id
        utente = user_service.get_user(user_id)
        
        if not utente:
            bot.send_message(call.message.chat.id, "❌ Errore: utente non trovato. Usa /start per registrarti.")
            return
        
        if utente.livello < 10:
            safe_answer_callback(call.id, "❌ Devi essere almeno al livello 10 per fondare una gilda!", show_alert=True)
            return
            
        if utente.points < 1000:
            safe_answer_callback(call.id, "❌ Ti servono 1000 Wumpa per fondare una gilda!", show_alert=True)
            return
            
        msg = bot.send_message(call.message.chat.id, "🏰 **Fondazione Gilda**\n\nInserisci il nome della tua gilda (max 32 caratteri):")
        bot.register_next_step_handler(msg, process_guild_name)
        return

    elif call.data == "guild_deposit_start":
        safe_answer_callback(call.id)
        msg = bot.send_message(call.message.chat.id, "💰 **Deposito Gilda**\n\nInserisci la quantità di Wumpa da depositare:")
        bot.register_next_step_handler(msg, process_guild_deposit)
        return

    elif call.data == "inn_rest_start":
        # Check if user is in combat (attacked in last 2 minutes)
        utente = user_service.get_user(call.from_user.id)
        last_attack = getattr(utente, 'last_attack_time', None)
        in_combat = False
        if last_attack:
            elapsed = (datetime.datetime.now() - last_attack).total_seconds()
            if elapsed < 120: # 2 minutes
                in_combat = True
                remaining = int(120 - elapsed)
        
        if in_combat:
            safe_answer_callback(call.id, f"⚔️ Sei in combattimento! Devi aspettare {remaining}s prima di riposare.", show_alert=True)
            return

        success, msg = user_service.start_resting(call.from_user.id)
        safe_answer_callback(call.id, msg, show_alert=True)
        if success:
            handle_inn_cmd(call.message)

    elif call.data == "inn_rest_stop":
        # Public Inn (No bonus)
        success, msg = user_service.stop_resting(call.from_user.id, recovery_multiplier=1.0)
        safe_answer_callback(call.id, msg, show_alert=True)
        if success:
            handle_inn_cmd(call.message)

    elif call.data == "guild_rest":
        # Same check logic as inn_rest_start
        utente = user_service.get_user(call.from_user.id)
        last_attack = getattr(utente, 'last_attack_time', None)
        in_combat = False
        remaining = 0

        if last_attack:
            elapsed = (datetime.datetime.now() - last_attack).total_seconds()
            if elapsed < 120: # 2 minutes
                in_combat = True
                remaining = int(120 - elapsed)
        
        if in_combat:
            safe_answer_callback(call.id, f"⚔️ Sei in combattimento! Devi aspettare {remaining}s prima di riposare.", show_alert=True)
            return

        success, msg = user_service.start_resting(call.from_user.id)
        safe_answer_callback(call.id, msg, show_alert=True)
        if success:
            handle_guild_inn_view(call)

    elif call.data == "guild_wakeup":
        # Calculate bonus
        from services.guild_service import GuildService
        gs = GuildService() # Local instance
        guild = gs.get_user_guild(call.from_user.id)
        multiplier = 1.0
        if guild:
            multiplier = 1.0 + (guild['inn_level'] * 0.5)
            
        success, msg = user_service.stop_resting(call.from_user.id, recovery_multiplier=multiplier)
        safe_answer_callback(call.id, msg, show_alert=True)
        if success:
            handle_guild_inn_view(call)

    elif call.data == "guild_list_view":
        safe_answer_callback(call.id)
        handle_guilds_list_cmd(call.message)

    elif call.data.startswith("guild_members|"):
        _, guild_id = call.data.split("|")
        members = guild_service.get_guild_members(int(guild_id))
        msg = "👥 **Membri della Gilda**\n\n"
        for m in members:
            msg += f"🔹 {m['name']} ({m['role']}) - Lv. {m['level']}\n"
        
        markup = types.InlineKeyboardMarkup()
        # Add Leave button for members (Leader has manage menu)
        # We need to check if user is leader? No, get_guild_members returns list.
        # We are in guild_back_main or similar context.
        # Actually, this block is for "guild_back_main" or initial view?
        # Line 3840 is inside "guild_view_members" probably?
        # Let's check context. 
        # Wait, I need to find where the main guild menu is shown for MEMBERS.
        # It's usually in handle_guild_cmd or similar.
        # Let's look at handle_guild_cmd implementation first.
        markup.add(types.InlineKeyboardButton("🔙 Indietro", callback_data="guild_back_main"))
        bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='markdown')
        return

    elif call.data == "guild_manage_menu":
        safe_answer_callback(call.id)
        guild = guild_service.get_user_guild(call.from_user.id)
        if not guild or guild['role'] != "Leader":
            safe_answer_callback(call.id, "Solo il capogilda può accedere a questo menu!", show_alert=True)
            return
            
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(f"🏠 Locanda ({guild['inn_level'] * 500} W)", callback_data="guild_upgrade|inn"))
        markup.add(types.InlineKeyboardButton(f"⚔️ Armeria ({(guild['armory_level'] + 1) * 750} W)", callback_data="guild_upgrade|armory"))
        markup.add(types.InlineKeyboardButton(f"🏘️ Villaggio ({guild['village_level'] * 1000} W)", callback_data="guild_upgrade|village"))
        markup.add(types.InlineKeyboardButton(f"🔞 Bordello ({(guild['bordello_level'] + 1) * 1500} W)", callback_data="guild_upgrade|bordello"))
        
        # Visual button for Locanda
        markup.add(types.InlineKeyboardButton("🏨 Vai alla Locanda", callback_data="guild_inn_view"))
        
        markup.add(types.InlineKeyboardButton("✏️ Rinomina", callback_data="guild_rename_ask"),
                   types.InlineKeyboardButton("🗑️ Elimina", callback_data="guild_delete_ask"))
        markup.add(types.InlineKeyboardButton("🔙 Indietro", callback_data="guild_back_main"))
        
        bot.edit_message_text(f"⚙️ **Gestione Gilda: {guild['name']}**\n\nBanca: {guild['wumpa_bank']} Wumpa", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='markdown')
        return

    elif call.data == "guild_leave_ask":
        safe_answer_callback(call.id)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Sì, abbandona", callback_data="guild_leave_confirm"))
        markup.add(types.InlineKeyboardButton("❌ No, resta", callback_data="guild_back_main"))
        
        bot.edit_message_text("⚠️ **Sei sicuro di voler abbandonare la gilda?**\nPerderai l'accesso a tutti i benefici.", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='markdown')
        return

    elif call.data == "guild_leave_confirm":
        success, msg = guild_service.leave_guild(call.from_user.id)
        safe_answer_callback(call.id, msg, show_alert=True)
        if success:
            # Go back to main guild menu (which will show "Found" or "Join")
            handle_guild_cmd(call.message)
        return

        bot.edit_message_text(f"⚙️ **Gestione Gilda: {guild['name']}**\n\nBanca: {guild['wumpa_bank']} Wumpa", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='markdown')
        return

    elif call.data == "guild_warehouse":
        safe_answer_callback(call.id)
        guild = guild_service.get_user_guild(call.from_user.id)
        if not guild:
            safe_answer_callback(call.id, "Non sei in una gilda!", show_alert=True)
            return
            
        items = guild_service.get_guild_inventory(guild['id'])
        msg = f"📦 **Magazzino Gilda: {guild['name']}**\n\n"
        if not items:
            msg += "Il magazzino è vuoto."
        else:
            for item, qty in items:
                msg += f"• {item}: x{qty}\n"
                
        markup = types.InlineKeyboardMarkup()
        if items:
            for item, qty in items:
                markup.add(types.InlineKeyboardButton(f"Preleva {item}", callback_data=f"guild_withdraw|{item}"))
        
        markup.add(types.InlineKeyboardButton("📥 Deposita Oggetto", callback_data="guild_deposit_ask"))
        markup.add(types.InlineKeyboardButton("🔙 Indietro", callback_data="guild_back_main"))
        
        bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='markdown')
        return

    elif call.data == "guild_deposit_ask":
        safe_answer_callback(call.id)
        # Show user inventory to pick item
        inventory = item_service.get_inventory(call.from_user.id)
        if not inventory:
            safe_answer_callback(call.id, "Il tuo inventario è vuoto!", show_alert=True)
            return
            
        markup = types.InlineKeyboardMarkup()
        for item, qty in inventory:
            markup.add(types.InlineKeyboardButton(f"Deposita {item} (x1)", callback_data=f"guild_deposit|{item}"))
        markup.add(types.InlineKeyboardButton("🔙 Indietro", callback_data="guild_warehouse"))
        
        bot.edit_message_text("📥 **Scegli cosa depositare:**", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='markdown')
        return

    elif call.data.startswith("guild_deposit|"):
        _, item_name = call.data.split("|", 1)
        success, msg = guild_service.deposit_item(call.from_user.id, item_name, 1)
        safe_answer_callback(call.id, msg, show_alert=not success)
        if success:
            # Refresh warehouse view
            guild = guild_service.get_user_guild(call.from_user.id)
            items = guild_service.get_guild_inventory(guild['id'])
            msg_text = f"📦 **Magazzino Gilda: {guild['name']}**\n\n"
            if not items:
                msg_text += "Il magazzino è vuoto."
            else:
                for item, qty in items:
                    msg_text += f"• {item}: x{qty}\n"
            
            markup = types.InlineKeyboardMarkup()
            if items:
                for item, qty in items:
                    markup.add(types.InlineKeyboardButton(f"Preleva {item}", callback_data=f"guild_withdraw|{item}"))
            markup.add(types.InlineKeyboardButton("📥 Deposita Oggetto", callback_data="guild_deposit_ask"))
            markup.add(types.InlineKeyboardButton("🔙 Indietro", callback_data="guild_back_main"))
            
            bot.edit_message_text(msg_text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='markdown')
        return

    # --- Dungeon Callbacks ---
    elif call.data.startswith("dungeon_host|"):
        _, d_id_str = call.data.split("|", 1)
        try:
            d_id = int(d_id_str)
            d_real_id, msg = dungeon_service.create_dungeon(call.message.chat.id, d_id, call.from_user.id)
            if not d_real_id:
                safe_answer_callback(call.id, msg, show_alert=True)
            else:
                # Update message to Lobby
                dungeon = dungeon_service.get_active_dungeon(call.message.chat.id)
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("➕ Unisciti", callback_data=f"dungeon_join|{dungeon.id}"))
                markup.add(types.InlineKeyboardButton("▶️ Avvia (Admin)", callback_data=f"dungeon_start|{dungeon.id}"))
                
                msg_text = f"🏰 **DUNGEON ATTIVO: {dungeon.name}**\n"
                msg_text += f"Status: {dungeon.status}\n\n"
                
                participants = dungeon_service.get_dungeon_participants(dungeon.id)
                msg_text += f"👥 Partecipanti ({len(participants)}):\n"
                for p in participants:
                    u = user_service.get_user(p.user_id)
                    name = f"@{u.username}" if u and u.username else (u.nome if u else f"Utente {p.user_id}")
                    msg_text += f"- {name}\n"
                
                bot.edit_message_text(msg_text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='markdown')
        except ValueError:
            safe_answer_callback(call.id, "ID non valido.")
        return

    elif call.data.startswith("dungeon_join|"):
        _, d_id_str = call.data.split("|", 1)
        success, msg = dungeon_service.join_dungeon(call.message.chat.id, call.from_user.id)
        safe_answer_callback(call.id, msg, show_alert=not success)
        
        if success:
            # Update Lobby
            dungeon = dungeon_service.get_active_dungeon(call.message.chat.id)
            if dungeon:
                 markup = types.InlineKeyboardMarkup()
                 markup.add(types.InlineKeyboardButton("➕ Unisciti", callback_data=f"dungeon_join|{dungeon.id}"))
                 markup.add(types.InlineKeyboardButton("▶️ Avvia (Admin)", callback_data=f"dungeon_start|{dungeon.id}"))
                 
                 msg_text = f"🏰 **DUNGEON ATTIVO: {dungeon.name}**\n"
                 msg_text += f"Status: {dungeon.status}\n"
                 
                 participants = dungeon_service.get_dungeon_participants(dungeon.id)
                 msg_text += f"\n👥 Partecipanti ({len(participants)}):\n"
                 for p in participants:
                     u = user_service.get_user(p.user_id)
                     name = f"@{u.username}" if u and u.username else (u.nome if u else f"Utente {p.user_id}")
                     msg_text += f"- {name}\n"
                     
                 bot.edit_message_text(msg_text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='markdown')
        return

    elif call.data.startswith("dungeon_start|"):
        success, msg, events = dungeon_service.start_dungeon(call.message.chat.id)
        if success:
             bot.edit_message_text(f"🚀 **DUNGEON INIZIATO!**", call.message.chat.id, call.message.message_id, parse_mode='markdown')
             
             # Process events
             cmd = BotCommands(call.message, bot, user_id=call.from_user.id)
             cmd.process_dungeon_events(events, call.message.chat.id)
             
             # We need to trigger attack for spawned mobs. 
             # process_dungeon_events handles spawning messages but maybe not the immediate attack trigger?
             # Let's check process_dungeon_events implementation.
             # It doesn't trigger attack. We need to extract mob_ids from events to trigger attack.
             
             print(f"[DEBUG] Events received: {events}")
             all_mob_ids = []
             for event in events:
                 if event['type'] == 'spawn' and 'mob_ids' in event:
                     all_mob_ids.extend(event['mob_ids'])
             
             print(f"[DEBUG] All mob IDs to trigger: {all_mob_ids}")
             if all_mob_ids:
                 trigger_dungeon_mob_attack(bot, call.message.chat.id, all_mob_ids)
             else:
                 print("[DEBUG] No mob IDs found in events!")
        else:
             safe_answer_callback(call.id, msg, show_alert=True)
        return

    elif call.data.startswith("dungeon_show_mobs|"):
        _, d_id_str = call.data.split("|", 1)
        try:
            d_id = int(d_id_str)
            # Get active mobs for this dungeon
            mobs = pve_service.get_active_mobs(call.message.chat.id)
            print(f"[DEBUG] dungeon_show_mobs: Found {len(mobs)} active mobs for chat {call.message.chat.id}")
            if not mobs:
                safe_answer_callback(call.id, "Nessun nemico attivo trovato!", show_alert=True)
            else:
                safe_answer_callback(call.id, "Mostro i nemici...")
                for mob in mobs:
                    print(f"[DEBUG] Displaying mob {mob.id} ({mob.name})")
                    display_mob_spawn(bot, call.message.chat.id, mob.id)
        except Exception as e:
            print(f"[DEBUG] Error in dungeon_show_mobs: {e}")
            safe_answer_callback(call.id, f"Errore: {e}", show_alert=True)
        return

    elif call.data == "ignore":
        safe_answer_callback(call.id)
        return

    elif call.data == "flee":
        # Show confirmation
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Fuggire", callback_data="flee_confirm"),
            types.InlineKeyboardButton("❌ Annulla", callback_data="flee_cancel")
        )
        safe_answer_callback(call.id, "Sei sicuro?", show_alert=False)
        bot.edit_message_text("⚠️ **SEI SICURO DI VOLER FUGGIRE?**\n\nAbbandonando lo scontro, non riceverai le ricompense di fine battaglia.", 
                              call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='markdown')
        return

    elif call.data == "flee_confirm":
        success, msg = dungeon_service.leave_dungeon(call.message.chat.id, call.from_user.id)
        safe_answer_callback(call.id, "Fuga completata!", show_alert=False)
        bot.send_message(call.message.chat.id, f"🏃 @{call.from_user.username or call.from_user.first_name}: {msg}", parse_mode='markdown')
        # We can't edit the original message easily to 'restore' lobby for others if it was PM, 
        # but here it's likely a group chat. The user left, so valid.
        try:
             bot.delete_message(call.message.chat.id, call.message.message_id) 
        except:
             pass
        return

    elif call.data == "flee_cancel":
        # Restore Lobby UI
        session = user_service.db.get_session()
        active_dungeon = dungeon_service.get_active_dungeon(call.message.chat.id, session=session)
        
        if active_dungeon and active_dungeon.status in ["registration", "active"]:
             markup = types.InlineKeyboardMarkup()
             if active_dungeon.status == "registration":
                 markup.add(types.InlineKeyboardButton("➕ Unisciti", callback_data=f"dungeon_join|{active_dungeon.id}"))
                 markup.add(types.InlineKeyboardButton("▶️ Avvia (Admin)", callback_data=f"dungeon_start|{active_dungeon.id}"))
             elif active_dungeon.status == "active":
                 markup.add(types.InlineKeyboardButton("👁️ Mostra Nemici", callback_data=f"dungeon_show_mobs|{active_dungeon.id}"))
                 markup.add(types.InlineKeyboardButton("🏃 Fuggire", callback_data="flee"))
             
             msg = f"🏰 **DUNGEON ATTIVO: {active_dungeon.name}**\n"
             msg += f"Status: {active_dungeon.status}\n"
                 
             # Get participants
             participants = dungeon_service.get_dungeon_participants(active_dungeon.id, session=session)
             msg += f"\n👥 Partecipanti ({len(participants)}):\n"
             for p in participants:
                 u = user_service.get_user(p.user_id)
                 name = f"@{u.username}" if u and u.username else (u.nome if u else f"Utente {p.user_id}")
                 msg += f"- {name}\n"
             
             bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='markdown')
        else:
             bot.edit_message_text("Il dungeon non è più attivo.", call.message.chat.id, call.message.message_id)
        
        session.close()
        safe_answer_callback(call.id, "Fuga annullata")
        return
        
    elif call.data.startswith("guild_join|"):
        _, guild_id = call.data.split("|")
        success, msg = guild_service.join_guild(call.from_user.id, int(guild_id))
        safe_answer_callback(call.id, msg, show_alert=True)
        if success:
            # Refresh guild view
            handle_guild_cmd(call.message)
        return

    elif call.data.startswith("guild_withdraw|"):
        _, item_name = call.data.split("|", 1)
        success, msg = guild_service.withdraw_item(call.from_user.id, item_name, 1)
        safe_answer_callback(call.id, msg, show_alert=not success)
        if success:
            # Refresh warehouse view
            guild = guild_service.get_user_guild(call.from_user.id)
            items = guild_service.get_guild_inventory(guild['id'])
            msg_text = f"📦 **Magazzino Gilda: {guild['name']}**\n\n"
            if not items:
                msg_text += "Il magazzino è vuoto."
            else:
                for item, qty in items:
                    msg_text += f"• {item}: x{qty}\n"
            
            markup = types.InlineKeyboardMarkup()
            if items:
                for item, qty in items:
                    markup.add(types.InlineKeyboardButton(f"Preleva {item}", callback_data=f"guild_withdraw|{item}"))
            markup.add(types.InlineKeyboardButton("📥 Deposita Oggetto", callback_data="guild_deposit_ask"))
            markup.add(types.InlineKeyboardButton("🔙 Indietro", callback_data="guild_back_main"))
            
            bot.edit_message_text(msg_text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='markdown')
        return

    elif call.data.startswith("wish_summon|"):
        _, dragon_type = call.data.split("|", 1)
        cmd = BotCommands(call.message, bot, user_id=call.from_user.id)
        # Fix: BotCommands uses message.from_user which is the bot in callbacks.
        # We must explicitly set the user ID from the callback.
        cmd.chatid = call.from_user.id
        cmd.handle_wish() # handle_wish checks counts again, which is fine
        safe_answer_callback(call.id)
        return

    elif call.data.startswith("use_item|"):
        _, item_name = call.data.split("|", 1)
        
        # Dragon Ball Restriction (Double check)
        if "Sfera del Drago" in item_name:
             safe_answer_callback(call.id, "❌ Non puoi usare le sfere singolarmente!", show_alert=True)
             return

        user_id = call.from_user.id
        
        # Check if user has the item
        if item_service.get_item_by_user(user_id, item_name) <= 0:
            safe_answer_callback(call.id, "❌ Non hai questo oggetto!", show_alert=True)
            return
        
        # Use the item
        utente = user_service.get_user(user_id)
        success = item_service.use_item(user_id, item_name)
        
        if success:
            # Check for active dungeon to record item usage
            dungeon = dungeon_service.get_active_dungeon(call.message.chat.id)
            if dungeon:
                dungeon_service.record_item_use(dungeon.id)

            # Apply item effect
            effect_msg, extra_data = item_service.apply_effect(utente, item_name)
            safe_answer_callback(call.id, f"✅ {item_name} utilizzato!")
            
            # TNT Trap Logic
            if extra_data and extra_data.get('type') == 'tnt_trap':
                import uuid
                sticker = extra_data.get('sticker')
                if sticker:
                    bot.send_sticker(call.message.chat.id, sticker)
                
                # Drop Wumpa
                dropped_wumpa = extra_data.get('wumpa_drop', 0)
                if dropped_wumpa > 0:
                    markup_w = types.InlineKeyboardMarkup()
                    buttons = []
                    # Create buttons for picking up
                    for i in range(min(dropped_wumpa, 20)): # Cap buttons
                        uid = str(uuid.uuid4())[:8]
                        buttons.append(types.InlineKeyboardButton("🍑", callback_data=f"steal|{uid}"))
                    
                    # Row of 5
                    for i in range(0, len(buttons), 5):
                        markup_w.row(*buttons[i:i+5])
                        
                    bot.send_message(call.message.chat.id, f"💰 **{dropped_wumpa} Wumpa** sono caduti a terra!", reply_markup=markup_w, parse_mode='markdown')

                # Send Timer Message
                markup_t = types.InlineKeyboardMarkup()
                markup_t.add(types.InlineKeyboardButton("✂️ DISINNESCA", callback_data="defuse_tnt"))
                
                sent_msg = bot.send_message(call.message.chat.id, "💣 **TNT ATTIVATA!**\n⏳ **3 secondi all'esplosione!**", reply_markup=markup_t, parse_mode='markdown')
                
                # Arm Trap
                trap_service.arm_trap(call.message.chat.id, user_id, duration=3.0, on_timeout=tnt_timeout)
            
            elif extra_data and extra_data.get('type') == 'nitro_trap':
                sticker = extra_data.get('sticker')
                if sticker:
                    bot.send_sticker(call.message.chat.id, sticker)
                    
                bot.send_message(call.message.chat.id, "🟩 **NITRO PIAZZATA!**\n☠️ **Esplosione Imminente!**", parse_mode='markdown')
                
                # Arm Trap (Instant/Fast)
                trap_service.arm_trap(call.message.chat.id, user_id, duration=0.5, on_timeout=nitro_timeout, trap_type='NITRO')
            # Update inventory display
            inventory = item_service.get_inventory(user_id)
            if not inventory:
                msg = "🎒 Il tuo inventario è vuoto!"
                markup = None
            else:
                msg = "🎒 **Il tuo Inventario**\nClicca su un oggetto per usarlo.\n\n"
                for item, quantity in inventory:
                    meta = item_service.get_item_metadata(item)
                    emoji = meta.get('emoji', '🎒')
                    desc = meta.get('descrizione', '')
                    
                    if not desc:
                        from services.potion_service import PotionService
                        potion_service = PotionService()
                        potion = potion_service.get_potion_by_name(item)
                        if potion:
                            desc = potion.get('descrizione', '')
                            p_type = potion.get('tipo', '')
                            if p_type == 'health_potion':
                                emoji = '❤️'
                            elif p_type == 'mana_potion':
                                emoji = '💙'
                            elif p_type == 'full_restore':
                                emoji = '💖'
                            elif emoji == '🎒': 
                                emoji = '🧪'
                            
                    msg += f"{emoji} {item} - {desc} (x{quantity})\n"
                
                # Recreate buttons
                markup = types.InlineKeyboardMarkup()
                
                # Check Dragon Balls
                from services.wish_service import WishService
                wish_service = WishService()
                utente = user_service.get_user(user_id)
                shenron, porunga = wish_service.get_dragon_ball_counts(utente)
                
                if shenron >= 7:
                    markup.add(types.InlineKeyboardButton("🐉 Evoca Shenron", callback_data="wish_summon|Shenron"))
                if porunga >= 7:
                    markup.add(types.InlineKeyboardButton("🐲 Evoca Porunga", callback_data="wish_summon|Porunga"))
                    
                for item, quantity in inventory:
                    if "Sfera del Drago" in item:
                        continue
                        
                    # Get Emoji
                    meta = item_service.get_item_metadata(item)
                    emoji = meta.get('emoji', '🎒')
                    
                    # Check potion emoji
                    from services.potion_service import PotionService
                    potion_service = PotionService()
                    potion = potion_service.get_potion_by_name(item)
                    if potion:
                        p_type = potion.get('tipo', '')
                        if p_type == 'health_potion':
                            emoji = '❤️'
                        elif p_type == 'mana_potion':
                            emoji = '💙'
                        elif p_type == 'full_restore':
                            emoji = '💖'
                        elif emoji == '🎒': 
                            emoji = '🧪'
                            
                    markup.add(types.InlineKeyboardButton(f"{emoji} {item}", callback_data=f"use_item|{item}"))
            
            # Edit the message with updated inventory
            bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='markdown')
            
            # Send effect message
            if effect_msg:
                bot.send_message(call.message.chat.id, effect_msg)
                
            # Handle Traps
                active_traps[call.message.chat.id] = {
                    'type': extra_data.get('trap_type', 'TNT'),
                    'user_id': user_id,
                    'time': datetime.datetime.now()
                }
            
            # Handle Next Mob Effects
            if extra_data and extra_data.get('type') == 'next_mob_effect':
                chat_id = call.message.chat.id
                if chat_id not in pve_service.pending_mob_effects:
                    pve_service.pending_mob_effects[chat_id] = []
                pve_service.pending_mob_effects[chat_id].append(extra_data.get('effect'))
        else:
            safe_answer_callback(call.id, "❌ Errore nell'uso dell'oggetto!", show_alert=True)
        return

    elif call.data == "defuse_tnt":
        chat_id = call.message.chat.id
        success, code = trap_service.defuse_trap(chat_id, call.from_user.id)
        
        if success:
             user_name = call.from_user.username or call.from_user.first_name
             bot.edit_message_text(f"✂️ **{user_name}** ha disinnescato la TNT! Siamo salvi! 😌", chat_id, call.message.message_id, parse_mode='markdown')
             safe_answer_callback(call.id, "Disinnescata!")
        else:
             if code == "volatile":
                 safe_answer_callback(call.id, "È troppo tardi! È instabile!", show_alert=True)
                 try: bot.delete_message(chat_id, call.message.message_id)
                 except: pass
             else:
                 safe_answer_callback(call.id, "Già disinnescata o esplosa.", show_alert=True)
                 try: bot.delete_message(chat_id, call.message.message_id)
                 except: pass
        return

    elif call.data.startswith("use_item_mob|"):
        # use_item_mob|{item_name}|{mob_id}
        parts = call.data.split("|")
        if len(parts) != 3:
            safe_answer_callback(call.id, "❌ Formato non valido", show_alert=True)
            return
            
        item_name = parts[1]
        mob_id = int(parts[2])
        user_id = call.from_user.id
        
        # Check if user has the item
        if item_service.get_item_by_user(user_id, item_name) <= 0:
            safe_answer_callback(call.id, f"❌ Non hai {item_name}!", show_alert=True)
            return
            
        # Get mob details
        mob_data = pve_service.get_mob_details(mob_id)
        if not mob_data:
            safe_answer_callback(call.id, "❌ Nemico non trovato!", show_alert=True)
            return
            
        # Use the item
        utente = user_service.get_user(user_id)
        success = item_service.use_item(user_id, item_name)
        
        if success:
            # Create a dummy mob object for apply_effect (it expects an object with .id and .name)
            class DummyMob:
                def __init__(self, d):
                    self.id = d['id']
                    self.name = d['name']
            
            target_mob = DummyMob(mob_data)
            
            # Apply effect on mob
            effect_msg, data = item_service.apply_effect(utente, item_name, target_mob=target_mob)
            safe_answer_callback(call.id, f"✅ {item_name} utilizzato!")
            
            # Handle mob drop (Nitro/TNT effect)
            if data and data.get('type') == 'mob_drop':
                percent = data['percent']
                dropped_amount = pve_service.force_mob_drop(mob_id, percent)
                
                if dropped_amount > 0:
                    # Apply damage if present
                    damage = data.get('damage', 0)
                    if damage > 0:
                        mob = pve_service.db.get_session().query(Mob).filter_by(id=mob_id).first()
                        if mob:
                            mob.health -= damage
                            if mob.health < 0: mob.health = 0
                            pve_service.db.get_session().commit()
                            effect_msg += f"\n💥 Danni inflitti: **{damage}**!"

                    # Create buttons for stealing the dropped wumpa
                    markup = types.InlineKeyboardMarkup()
                    buttons = []
                    import uuid
                    visual_amount = min(dropped_amount, 50)
                    for i in range(visual_amount):
                        uid = str(uuid.uuid4())[:8]
                        buttons.append(types.InlineKeyboardButton("🍑", callback_data=f"steal|{uid}"))
                    
                    for i in range(0, len(buttons), 5):
                        markup.row(*buttons[i:i+5])
                        
                    username = escape_markdown(utente.username if utente.username else utente.nome)
                    full_msg = f"@{username}\n{effect_msg}\n\n💰 Il Mob ha perso {dropped_amount} Wumpa!"
                    
                    # Send as a new message to the group
                    bot.send_message(call.message.chat.id, full_msg, reply_markup=markup)
                else:
                    username = escape_markdown(utente.username if utente.username else utente.nome)
                    bot.send_message(call.message.chat.id, f"@{username}\n{effect_msg}")
            
            elif data and data.get('type') == 'next_mob_effect':
                chat_id = call.message.chat.id
                if chat_id not in pve_service.pending_mob_effects:
                    pve_service.pending_mob_effects[chat_id] = []
                pve_service.pending_mob_effects[chat_id].append(data.get('effect'))
                username = escape_markdown(utente.username if utente.username else utente.nome)
                bot.send_message(call.message.chat.id, f"@{username}\n{effect_msg}")
            else:
                username = escape_markdown(utente.username if utente.username else utente.nome)
                bot.send_message(call.message.chat.id, f"@{username}\n{effect_msg}")
        else:
            safe_answer_callback(call.id, "❌ Errore nell'uso dell'oggetto!", show_alert=True)
        return

    elif call.data == "guild_rename_ask":
        safe_answer_callback(call.id)
        msg = bot.send_message(call.message.chat.id, "✏️ **Rinomina Gilda**\n\nInserisci il nuovo nome per la gilda:", parse_mode='markdown')
        bot.register_next_step_handler(msg, process_guild_rename)
        return

    elif call.data == "guild_delete_ask":
        safe_answer_callback(call.id)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ SÌ, ELIMINA", callback_data="guild_delete_confirm"))
        markup.add(types.InlineKeyboardButton("❌ Annulla", callback_data="guild_manage_menu"))
        bot.edit_message_text("⚠️ **ELIMINAZIONE GILDA**\n\nSei sicuro di voler sciogliere la gilda? Questa azione è IRREVERSIBILE e tutti i progressi andranno persi!", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='markdown')
        return

    elif call.data == "guild_delete_confirm":
        success, msg = guild_service.delete_guild(call.from_user.id)
        safe_answer_callback(call.id, msg, show_alert=True)
        if success:
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.send_message(call.message.chat.id, msg)
        else:
            handle_guild_cmd(call.message)
        return

    elif call.data == "guild_back_main":
        safe_answer_callback(call.id)
        # Reload guild menu
        guild = guild_service.get_user_guild(call.from_user.id)
        if guild:
            msg = f"🏰 **Gilda: {guild['name']}**\n"
            leader = user_service.get_user(guild['leader_id'])
            leader_name = f"@{leader.username}" if leader and leader.username else (leader.nome if leader else f"{guild['leader_id']}")
            msg += f"👑 **Capo**: {leader_name}\n"
            msg += f"💰 **Banca**: {guild['wumpa_bank']} Wumpa\n"
            msg += f"👥 **Membri**: {guild['member_limit']} (max)\n\n"
            msg += f"🏠 **Locanda**: Lv. {guild['inn_level']}\n"
            msg += f"⚔️ **Armeria**: Lv. {guild['armory_level']}\n"
            msg += f"🏘️ **Villaggio**: Lv. {guild['village_level']}\n"
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("👥 Membri", callback_data=f"guild_members|{guild['id']}"))
            markup.add(types.InlineKeyboardButton("🏨 Locanda", callback_data="guild_inn_view"))
            markup.add(types.InlineKeyboardButton("🔨 Armeria", callback_data="guild_armory_view"))
            markup.add(types.InlineKeyboardButton("📦 Magazzino", callback_data="guild_warehouse"))
            markup.add(types.InlineKeyboardButton("💰 Deposita Wumpa", callback_data="guild_deposit_start"))
            if guild['role'] == "Leader":
                markup.add(types.InlineKeyboardButton("⚙️ Gestisci Gilda", callback_data="guild_manage_menu"))
            else:
                markup.add(types.InlineKeyboardButton("🚪 Abbandona Gilda", callback_data="guild_leave_ask"))
            
            bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='markdown')
        return

    elif call.data.startswith("guild_upgrade|"):
        _, upgrade_type = call.data.split("|")
        if upgrade_type == "inn":
            success, msg = guild_service.upgrade_inn(call.from_user.id)
        elif upgrade_type == "village":
            success, msg = guild_service.expand_village(call.from_user.id)
        elif upgrade_type == "armory":
            success, msg = guild_service.upgrade_armory(call.from_user.id)
        elif upgrade_type == "bordello":
            success, msg = guild_service.upgrade_bordello(call.from_user.id)
            
        if success:
            safe_answer_callback(call.id, "Upgrade completato!")
            # Refresh view
            handle_guild_view(call)
        else:
            safe_answer_callback(call.id, msg, show_alert=True)
            
    elif call.data.startswith("stat_"):
        bot_cmds = BotCommands(call.message, bot, user_id=call.from_user.id)
        bot_cmds.handle_stat_callback(call)
        return

    elif call.data == "guild_back_main":
        safe_answer_callback(call.id)
        handle_guild_cmd(call.message)
        return

    action = call.data
    user_id = call.from_user.id
    utente = user_service.get_user(user_id)
    
    # Track activity already done at the beginning
    
    # SEASON PAGINATION
    if action.startswith("season_page|"):
        page = int(action.split("|")[1])
        handle_season_cmd(call.message, page=page, user_id=user_id)
        safe_answer_callback(call.id)
        return

    # REFRESH ENEMIES LIST
    if action == "refresh_enemies":
        # Re-use the logic from handle_enemies but edit the message
        mobs = pve_service.get_active_mobs(call.message.chat.id)
        
    elif action == "profile":
        bot_cmds = BotCommands(call.message, bot, user_id=call.from_user.id)
        bot_cmds.chatid = call.from_user.id # Fix: Ensure chatid is the user's ID
        bot_cmds.handle_profile()
        return
        
        if not mobs:
            safe_answer_callback(call.id, "Nessun nemico attivo!")
            bot.edit_message_text("🧟 Nessun nemico attivo al momento. Tutto tranquillo... per ora.", call.message.chat.id, call.message.message_id)
            return
            
        msg = "🧟 **NEMICI ATTIVI** 🧟\n\n"
        
        for mob in mobs:
            # Status icons
            status = ""
            if mob.is_boss: status += "👑 **BOSS** "
            if mob.difficulty_tier >= 4: status += "💀 "
            
            # Health bar approximation
            hp_percent = (mob.health / mob.max_health) * 100
            hp_bar = "🟩" * int(hp_percent / 10) + "⬜" * (10 - int(hp_percent / 10))
            
            msg += f"{status}**{mob.name}** (Lv. {mob.mob_level if hasattr(mob, 'mob_level') else 1})\n"
            msg += f"❤️ {mob.health}/{mob.max_health} {hp_bar}\n"
            msg += f"⚔️ Danno: {mob.attack_damage} | 🛡️ Res: {mob.resistance}%\n"
            if mob.difficulty_tier:
                msg += f"🔥 Difficoltà: {mob.difficulty_tier}\n"
            msg += f"🆔 ID: `{mob.id}` (Usa per targettare)\n"
            msg += "-------------------\n"
            
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔄 Aggiorna", callback_data="refresh_enemies"))
        
        try:
            bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='markdown')
            safe_answer_callback(call.id, "Lista aggiornata!")
        except Exception as e:
            # If message content is same, Telegram API raises error
            safe_answer_callback(call.id, "Nessun cambiamento.")
        return

    # TITLE SELECTION
    if action.startswith("set_title|"):
        new_title = action.split("|")[1]
        

        try:
            user_service.update_user(user_id, {'title': new_title})
            safe_answer_callback(call.id, f"✅ Titolo impostato: {new_title}")
            bot.edit_message_text(f"✅ Titolo impostato con successo: **{new_title}**", user_id, call.message.message_id, parse_mode='markdown')
        except Exception as e:
            print(f"Error setting title in callback: {e}")
            safe_answer_callback(call.id, "❌ Errore nel salvataggio")
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
        
        # Use centralized formatter with user projection
        msg = f"{lock_icon}{saga_info}"
        msg += character_service.format_character_card(char, show_price=True, is_equipped=is_equipped, user=utente)
        
        # Append lock info
        if not is_unlocked:
            msg += "\n\n🔒 **PERSONAGGIO BLOCCATO**\n"
            if char_level > utente.livello:
                msg += f"Raggiungi livello {char_level} per sbloccarlo!\n"
            elif char_lv_premium == 1:
                msg += "Richiede abbonamento Premium!\n"
        
        msg += f"\n📄 Livello {level_idx + 1}/{len(levels)} - Personaggio {char_idx + 1}/{len(level_chars)}"
        
        markup = types.InlineKeyboardMarkup()
        
        nav_levels_row = []
        
        # -5 Levels
        can_go_fast_prev = False
        if level_idx >= 5:
            prev_5_val = levels[level_idx-5]
            if is_admin or prev_5_val <= utente.livello:
                can_go_fast_prev = True
        
        if can_go_fast_prev:
             nav_levels_row.append(types.InlineKeyboardButton("⏪ -5", callback_data=f"char_nav|{level_idx-5}|0"))
        
        # Prev Level
        can_go_prev = False
        if level_idx > 0:
            prev_level_val = levels[level_idx-1]
            if is_admin or prev_level_val <= utente.livello:
                can_go_prev = True
        
        if can_go_prev:
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
        
        # Row 4: Season Filter Button (Dragon Ball)
        season_row = []
        season_row.append(types.InlineKeyboardButton("🐉 Personaggi della Stagione", callback_data="saga_nav|Dragon Ball|0"))
        markup.row(*season_row)
        
        if is_unlocked:
            if not is_equipped:
                markup.add(types.InlineKeyboardButton("✅ Equipaggia", callback_data=f"char_select|{char_id}"))
            else:
                markup.add(types.InlineKeyboardButton("⭐ Già Equipaggiato", callback_data="char_already_equipped"))
        elif char_lv_premium == 2 and char_price > 0:
             # Re-calculate price for button
             price = char_price
             if utente.premium == 1:
                 price = int(price * 0.5)
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
                # Edit the existing message with new media instead of deleting and resending
                media = types.InputMediaPhoto(image_data, caption=msg, parse_mode='markdown')
                bot.edit_message_media(media, user_id, call.message.message_id, reply_markup=markup)
            except Exception as e:
                print(f"Error editing message media: {e}")
                # Fallback: delete and resend if edit fails
                try:
                    bot.delete_message(user_id, call.message.message_id)
                    bot.send_photo(user_id, image_data, caption=msg, reply_markup=markup, parse_mode='markdown')
                except Exception as e2:
                    print(f"Error in fallback send: {e2}")
        else:
            # No image, just edit the text
            try:
                bot.edit_message_text(msg, user_id, call.message.message_id, reply_markup=markup, parse_mode='markdown')
            except Exception as e:
                print(f"Error editing message text: {e}")

        safe_answer_callback(call.id)
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
            safe_answer_callback(call.id, f"Nessun personaggio nella saga {saga_name}!")
            return
        
        # Filter by user access (unless admin)
        if not is_admin:
            saga_chars = [c for c in saga_chars if c['livello'] <= utente.livello or c['lv_premium'] == 2]
        
        if not saga_chars:
            safe_answer_callback(call.id, f"Nessun personaggio sbloccato in {saga_name}!")
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
        
        # Use centralized formatter with user projection
        msg = f"{lock_icon}"
        msg += character_service.format_character_card(char, show_price=True, is_equipped=is_equipped, user=utente)
        
        # Append lock info
        if not is_unlocked:
            msg += "\n\n🔒 **PERSONAGGIO BLOCCATO**\n"
            if char['livello'] > utente.livello:
                msg += f"Raggiungi livello {char['livello']} per sbloccarlo!\n"
            elif char['lv_premium'] == 1:
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
             # Re-calculate price for button
             price = char_price
             if utente.premium == 1:
                 price = int(price * 0.5)
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
        
        safe_answer_callback(call.id)
        return
    
    elif action.startswith("char_filter|"):
        filter_value = action.split("|")[1]
        level_filter = None if filter_value == "all" else int(filter_value)
        
        # Show first page with filter
        page_chars, total_pages, current_page = character_service.get_all_characters_paginated(utente, page=0, level_filter=level_filter)
        
        if not page_chars:
            safe_answer_callback(call.id, f"Nessun personaggio di livello {filter_value}!")
            return
        
        char = page_chars[0]
        # Ensure char is treated as dict
        char_id = char['id']
        is_unlocked = character_service.is_character_unlocked(utente, char_id)
        is_equipped = (utente.livello_selezionato == char_id)
        
        # Format character card
        lock_icon = "" if is_unlocked else "🔒 "
        
        # Use centralized formatter with user projection
        msg = f"{lock_icon}"
        msg += character_service.format_character_card(char, show_price=True, is_equipped=is_equipped, user=utente)
        
        # Append lock info if needed (format_character_card doesn't handle locked reason text)
        if not is_unlocked:
            msg += "\n\n🔒 **PERSONAGGIO BLOCCATO**\n"
            if char['livello'] > utente.livello:
                msg += f"Raggiungi livello {char['livello']} per sbloccarlo!\n"
            elif char['lv_premium'] == 1:
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
        safe_answer_callback(call.id, f"Filtrando per {'tutti i livelli' if filter_value == 'all' else f'livello {filter_value}'}")
        return
    
    elif action.startswith("char_buy|"):
        char_id = int(action.split("|")[1])
        
        success, msg = character_service.purchase_character(utente, char_id)
        
        if success:
            safe_answer_callback(call.id, "✅ Personaggio acquistato!")
            # Send confirmation message
            bot.send_message(user_id, f"🎉 {msg}\n\nOra puoi equipaggiarlo dalla selezione personaggi!", reply_markup=get_main_menu())
            
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
            safe_answer_callback(call.id, f"❌ {msg}", show_alert=True)
        return
    
    elif action == "char_already_equipped":
        safe_answer_callback(call.id, "⭐ Questo personaggio è già equipaggiato!")
        return
    
    elif action == "char_page_info":
        safe_answer_callback(call.id, "Usa le frecce per navigare")
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
                safe_answer_callback(call.id)
                return
        
        success, msg = character_service.equip_character(utente, char_id)
        
        if success:
            safe_answer_callback(call.id, "✅ Personaggio equipaggiato!")
            bot.send_message(user_id, f"✅ {msg}", reply_markup=get_main_menu())
        else:
            safe_answer_callback(call.id, f"❌ {msg}")
        return
    
    elif action.startswith("transform_menu|"):
        base_char_id = int(action.split("|")[1])
        
        from services.character_loader import get_character_loader
        char_loader = get_character_loader()
        
        # Get available transformations
        transforms = char_loader.get_transformation_chain(base_char_id)
        base_char = char_loader.get_character_by_id(base_char_id)
        
        if not transforms:
            safe_answer_callback(call.id, "❌ Nessuna trasformazione disponibile!")
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
        safe_answer_callback(call.id)
        return
    
    elif action.startswith("activate_transform|"):
        trans_id = int(action.split("|")[1])
        
        from services.character_loader import get_character_loader
        char_loader = get_character_loader()
        
        trans_char = char_loader.get_character_by_id(trans_id)
        if not trans_char:
            safe_answer_callback(call.id, "❌ Trasformazione non trovata!")
            return
        
        mana_cost = trans_char.get('transformation_mana_cost', 50)
        duration_days = trans_char.get('transformation_duration_days', 0)
        
        # Check mana
        if utente.mana < mana_cost:
            safe_answer_callback(call.id, f"❌ Mana insufficiente! Serve: {mana_cost}, hai: {utente.mana}")
            return
        
        # Deduct mana and apply transformation
        session = user_service.db.get_session()
        
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
        
        bot.send_message(user_id, msg, reply_markup=get_main_menu(), parse_mode='markdown')
        safe_answer_callback(call.id, f"🔥 Trasformato in {trans_char['nome']}!")
        return
    
    elif action.startswith("buy_transform|"):
        trans_id = int(action.split("|")[1])
        
        # Use character_service to purchase
        success, msg = character_service.purchase_character(utente, trans_id)
        
        if success:
            safe_answer_callback(call.id, "✅ Trasformazione acquistata!")
            bot.send_message(user_id, f"✅ {msg}\n\nOra puoi trasformarti dal profilo!", reply_markup=get_main_menu())
        else:
            safe_answer_callback(call.id, f"❌ {msg}")
        return
    
    elif action == "no_mana":
        safe_answer_callback(call.id, "❌ Non hai abbastanza mana! Rigenera +10 ogni ora.")
        return
    
    elif action == "back_to_profile":
        # Redirect to profile
        safe_answer_callback(call.id)
        try:
            bot.delete_message(user_id, call.message.message_id)
        except:
            pass
        # The user should use the profile button again
        bot.send_message(user_id, "Usa il pulsante 👤 Profilo per vedere il tuo profilo.", reply_markup=get_main_menu())
        return
    
    elif action == "stats_menu":
        points_info = stats_service.get_available_stat_points(utente)
        
        msg = f"📊 **ALLOCAZIONE STATISTICHE**\n\n"
        # Old stat_alloc handler removed
        
    elif action.startswith("stat_alloc|"):
        stat_type = action.split("|")[1]
        
        success, msg = stats_service.allocate_stat_point(utente, stat_type)
        
        safe_answer_callback(call.id, msg if success else f"❌ {msg}")
        
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
            msg += f"Costo: Gratuito\n\n"
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
            safe_answer_callback(call.id)
        
        elif action == "reset_stats_yes":
            success, msg = stats_service.reset_stat_points(utente)
            safe_answer_callback(call.id, "✅ Reset completato!" if success else f"❌ Errore")
            bot.send_message(user_id, msg)
        
        elif action == "reset_stats_no":
            safe_answer_callback(call.id, "Reset annullato")
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
        
        safe_answer_callback(call.id)
        return
    
    elif action == "transform_locked":
        safe_answer_callback(call.id, "🔒 Non puoi attivare questa trasformazione!")
        return
    
    elif action.startswith("transform|"):
        trans_id = int(action.split("|")[1])
        
        success, msg = transformation_service.activate_transformation(utente, trans_id)
        
        safe_answer_callback(call.id, "✨ Trasformazione attivata!" if success else f"❌ Errore")
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
            safe_answer_callback(call.id, "✅ Pozione usata!")
            bot.send_message(user_id, msg)
        else:
            safe_answer_callback(call.id, f"❌ {msg}", show_alert=True)
        return
    
    elif action.startswith("buy_potion|"):
        parts = action.split("|")
        potion_name = parts[1]
        
        utente = user_service.get_user(user_id)
        
        from services.potion_service import PotionService
        potion_service = PotionService()
        
        success, msg = potion_service.buy_potion(utente, potion_name)
        
        if success:
            safe_answer_callback(call.id, "✅ Acquisto effettuato!")
            bot.send_message(user_id, f"🛍️ {msg}\n\nPuoi usare la pozione dal tuo 📦 Inventario.")
        else:
            safe_answer_callback(call.id, f"❌ {msg}", show_alert=True)
        return


    elif action.startswith("attack_enemy|"):
        # New unified attack system: attack_enemy|{type}|{id}
        # Type can be 'mob' or 'raid'
        parts = action.split("|")
        if len(parts) != 3:
            safe_answer_callback(call.id, "❌ Formato callback non valido", show_alert=True)
            return
            
        # Check if user is resting in inn
        resting_status = user_service.get_resting_status(user_id)
        if resting_status:
            safe_answer_callback(call.id, "❌ Non puoi attaccare mentre stai riposando nella locanda! Usa /inn per smettere di riposare.", show_alert=True)
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
                safe_answer_callback(call.id, "❌ Nemico non trovato!", show_alert=True)
                return
            enemy_dead = mob.is_dead
        else:
            session.close()
            safe_answer_callback(call.id, "❌ Tipo nemico non valido", show_alert=True)
            return
        session.close()
        
        if enemy_dead:
            safe_answer_callback(call.id, "💀 Questo nemico è già morto!", show_alert=True)
            return
        
        # Attack the specific target (all are mobs now, bosses are just mobs with is_boss=True)
        try:
            success, msg, extra_data = pve_service.attack_mob(utente, damage, mob_id=enemy_id)
            
            # Handle Dungeon Events (Dialogues, Delays, Spawns)
            # Handle Dungeon Events (Dialogues, Delays, Spawns)
            if extra_data and 'dungeon_events' in extra_data:
                cmd = BotCommands(call.message, bot, user_id=call.from_user.id)
                cmd.process_dungeon_events(extra_data['dungeon_events'], call.message.chat.id)
        except Exception as e:
            import traceback
            traceback.print_exc()
            safe_answer_callback(call.id, f"❌ Errore critico: {e}", show_alert=True)
            return
        
        # Send response
        if success:
            try:
                safe_answer_callback(call.id, "⚔️ Attacco effettuato!")
            except Exception:
                pass
            
            enemy_died = extra_data.get('is_dead', False)
            image_path = extra_data.get('image_path')
            old_msg_id = extra_data.get('delete_message_id')
            
            username = escape_markdown(utente.username if utente.username else utente.nome)
            full_msg = f"@{username}\n{msg}"
            
            if enemy_died:
                send_combat_message(call.message.chat.id, full_msg, image_path, None, enemy_id, old_msg_id, is_death=True)
            else:
                markup = get_combat_markup(enemy_type, enemy_id, call.message.chat.id)
                send_combat_message(call.message.chat.id, full_msg, image_path, markup, enemy_id, old_msg_id)
                
            # Check for new mobs (Dungeon progression)
            if extra_data and 'new_mob_ids' in extra_data:
                for new_mob_id in extra_data['new_mob_ids']:
                    display_mob_spawn(bot, call.message.chat.id, new_mob_id)
                
                # Immediate Attack!
                trigger_dungeon_mob_attack(bot, call.message.chat.id, extra_data['new_mob_ids'])
        else:
            try:
                safe_answer_callback(call.id, msg, show_alert=True)
            except Exception:
                pass
        return

    elif action.startswith("special_attack_enemy|"):
        # Special attack on specific enemy: special_attack_enemy|{type}|{id}
        parts = action.split("|")
        if len(parts) != 3:
            safe_answer_callback(call.id, "❌ Formato non valido", show_alert=True)
            return
            
        # Check if user is resting in inn
        resting_status = user_service.get_resting_status(user_id)
        if resting_status:
            safe_answer_callback(call.id, "❌ Non puoi attaccare mentre stai riposando nella locanda! Usa /inn per smettere di riposare.", show_alert=True)
            return
        
        enemy_type = parts[1]
        enemy_id = int(parts[2])
        utente = user_service.get_user(user_id)
        
        # Get character
        from services.character_loader import get_character_loader
        char_loader = get_character_loader()
        character = char_loader.get_character_by_id(utente.livello_selezionato)
        
        if not character:
            safe_answer_callback(call.id, "❌ Personaggio non selezionato!", show_alert=True)
            return
        
        # Check mana
        mana_cost = character.get('special_attack_mana_cost', 0)
        if utente.mana < mana_cost:
            safe_answer_callback(call.id, f"❌ Mana insufficiente! Serve: {mana_cost}", show_alert=True)
            return
        
        # Deduct mana and calculate damage
        # user_service.update_user(user_id, {'mana': utente.mana - mana_cost}) # MOVED TO PVE_SERVICE
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
                safe_answer_callback(call.id, "❌ Nemico non trovato!", show_alert=True)
                return
            enemy_dead = mob.is_dead
        else:
            session.close()
            safe_answer_callback(call.id, "❌ Tipo non valido", show_alert=True)
            return
        session.close()
        
        if enemy_dead:
            safe_answer_callback(call.id, "💀 Questo nemico è già morto!", show_alert=True)
            return
        
        # Attack (all are mobs now, bosses are just mobs with is_boss=True)
        success, msg, extra_data = pve_service.attack_mob(utente, damage, use_special=True, mob_id=enemy_id, mana_cost=mana_cost)
        
        # Handle Dungeon Events (Dialogues, Delays, Spawns)
        # Handle Dungeon Events (Dialogues, Delays, Spawns)
        if extra_data and 'dungeon_events' in extra_data:
            cmd = BotCommands(call.message, bot, user_id=call.from_user.id)
            cmd.process_dungeon_events(extra_data['dungeon_events'], call.message.chat.id)
        
        if success:
            try:
                safe_answer_callback(call.id, "✨ Attacco Speciale!")
            except:
                pass
            
            enemy_died = extra_data.get('is_dead', False)
            image_path = extra_data.get('image_path')
            old_msg_id = extra_data.get('delete_message_id')
            
            special_name = character.get('special_attack_name', 'Attacco Speciale')
            msg = f"✨ **{special_name}!** ✨\n{msg}"
            
            username = escape_markdown(utente.username if utente.username else utente.nome)
            full_msg = f"@{username}\n{msg}"
            
            if enemy_died:
                send_combat_message(call.message.chat.id, full_msg, image_path, None, enemy_id, old_msg_id, is_death=True)
            else:
                markup = get_combat_markup(enemy_type, enemy_id, call.message.chat.id)
                send_combat_message(call.message.chat.id, full_msg, image_path, markup, enemy_id, old_msg_id)
                
            # Check for new mobs (Dungeon progression)
            if extra_data and 'new_mob_ids' in extra_data:
                for new_mob_id in extra_data['new_mob_ids']:
                    display_mob_spawn(bot, call.message.chat.id, new_mob_id)

    elif call.data.startswith("flee_enemy|"):
        # flee_enemy|{type}|{id}
        parts = call.data.split("|")
        if len(parts) < 3:
            safe_answer_callback(call.id, "Dati non validi.")
            return
            
        enemy_type = parts[1]
        enemy_id = int(parts[2])
        
        # Check if it's a dungeon mob
        mob_details = pve_service.get_mob_details(enemy_id)
        if mob_details and mob_details.get('dungeon_id'):
            # Use existing dungeon flee logic
            success, msg = dungeon_service.leave_dungeon(call.message.chat.id, call.from_user.id)
            safe_answer_callback(call.id, "Tentativo di fuga dal dungeon...", show_alert=False)
            bot.send_message(call.message.chat.id, f"🏃 @{call.from_user.username or call.from_user.first_name}: {msg}", parse_mode='markdown')
            
            # If successful and mob is now dead (dungeon failed), delete message
            if success:
                # Re-check mob status
                updated_mob = pve_service.get_mob_details(enemy_id)
                if updated_mob and updated_mob.get('health', 1) <= 0:
                    try:
                        bot.delete_message(call.message.chat.id, call.message.message_id)
                    except:
                        pass
        else:
            # Regular mob flee
            utente = user_service.get_user(call.from_user.id)
            success, msg = pve_service.flee_mob(utente, enemy_id)
            safe_answer_callback(call.id, msg, show_alert=True)
            if success:
                try:
                    bot.delete_message(call.message.chat.id, call.message.message_id)
                except:
                    pass

    elif action.startswith("aoe_attack_enemy|") or action.startswith("special_aoe_attack_enemy|"):
        # AoE attack on all enemies: aoe_attack_enemy|{type}|{id} or special_aoe_attack_enemy|{type}|{id}
        is_special = action.startswith("special_aoe_attack_enemy|")
        parts = action.split("|")
        if len(parts) != 3:
            safe_answer_callback(call.id, "❌ Formato non valido", show_alert=True)
            return
            
        # Check if user is resting in inn
        resting_status = user_service.get_resting_status(user_id)
        if resting_status:
            safe_answer_callback(call.id, "❌ Non puoi attaccare mentre stai riposando nella locanda! Usa /inn per smettere di riposare.", show_alert=True)
            return
        
        enemy_id = int(parts[2])
        utente = user_service.get_user(user_id)
        
        # Perform AoE attack
        if is_special:
            success, msg, extra_data, attack_events = pve_service.use_special_attack(utente, is_aoe=True, chat_id=call.message.chat.id)
        else:
            damage = utente.base_damage
            success, msg, extra_data, attack_events = pve_service.attack_aoe(utente, damage, chat_id=call.message.chat.id, target_mob_id=enemy_id)
            
        # Handle Dungeon Events (Dialogues, Delays, Spawns)
        # Handle Dungeon Events (Dialogues, Delays, Spawns)
        if extra_data and 'dungeon_events' in extra_data:
            cmd = BotCommands(call.message, bot, user_id=call.from_user.id)
            cmd.process_dungeon_events(extra_data['dungeon_events'], call.message.chat.id)
        
        if success:
            try:
                alert_text = "🌟 Speciale AoE!" if is_special else "💥 Attacco ad Area!"
                safe_answer_callback(call.id, alert_text)
            except:
                pass
            
            # Handle message deletion for all hit mobs
            if extra_data and 'delete_message_ids' in extra_data:
                for msg_id in extra_data['delete_message_ids']:
                    try:
                        bot.delete_message(call.message.chat.id, msg_id)
                    except:
                        pass
            
            username = escape_markdown(utente.username if utente.username else utente.nome)
            full_msg = f"@{username}\n{msg}"
            
            # Send the summary message
            # We don't use send_combat_message here because it's a multi-target summary
            sent_msg = bot.send_message(call.message.chat.id, full_msg, parse_mode='markdown')
            
            # Re-display all surviving mobs
            if extra_data and 'mob_ids' in extra_data:
                # Get IDs of mobs that are counter-attacking to avoid double display
                counter_attacking_ids = []
                if attack_events:
                    counter_attacking_ids = [event.get('mob_id') for event in attack_events]
                    
                for mob_id in extra_data['mob_ids']:
                    if mob_id not in counter_attacking_ids:
                        # Check if still alive
                        m = pve_service.get_mob_details(mob_id)
                        if m and m['health'] > 0:
                            display_mob_spawn(bot, call.message.chat.id, mob_id)
            
            # Handle counter-attacks
            if attack_events:
                for event in attack_events:
                    msg = event['message']
                    image_path = event['image']
                    attacker_id = event.get('mob_id')
                    
                    attack_markup = None
                    if attacker_id:
                        attack_markup = get_combat_markup("mob", attacker_id, call.message.chat.id)
                    
                    try:
                        if image_path and os.path.exists(image_path):
                            with open(image_path, 'rb') as photo:
                                bot.send_photo(call.message.chat.id, photo, caption=msg, reply_markup=attack_markup, parse_mode='markdown')
                        else:
                            bot.send_message(call.message.chat.id, msg, reply_markup=attack_markup, parse_mode='markdown')
                    except Exception as e:
                        print(f"Error sending counter-attack message: {e}")
        else:
            try:
                safe_answer_callback(call.id, msg, show_alert=True)
            except:
                pass
        return

    elif action.startswith("flee_enemy|"):
        # flee_enemy|{type}|{id}
        parts = action.split("|")
        enemy_type = parts[1]
        enemy_id = int(parts[2])
        
        utente = user_service.get_user(user_id)
        
        success, msg = pve_service.flee_mob(utente, enemy_id)
        
        if success:
            try:
                safe_answer_callback(call.id, "🏃 Fuga riuscita!")
            except:
                pass
            
            username = escape_markdown(utente.username if utente.username else utente.nome)
            full_msg = f"@{username}\n{msg}"
            
            # Check if mob is now dead (group flee)
            session = db.get_session()
            from models.pve import Mob
            mob = session.query(Mob).filter_by(id=enemy_id).first()
            is_dead = mob.is_dead if mob else True
            session.close()
            
            try:
                if is_dead:
                    # Remove buttons for everyone
                    if call.message.photo:
                        bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id, caption=full_msg, reply_markup=None, parse_mode='markdown')
                    else:
                        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=full_msg, reply_markup=None, parse_mode='markdown')
                else:
                    # Update message but keep buttons
                    if call.message.photo:
                        bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id, caption=full_msg, reply_markup=get_combat_markup(enemy_type, enemy_id, call.message.chat.id), parse_mode='markdown')
                    else:
                        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=full_msg, reply_markup=get_combat_markup(enemy_type, enemy_id, call.message.chat.id), parse_mode='markdown')
            except Exception as e:
                print(f"Error updating message after flee: {e}")
                bot.send_message(call.message.chat.id, full_msg, parse_mode='markdown')
        else:
            try:
                safe_answer_callback(call.id, msg, show_alert=True)
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
        success, msg, _ = pve_service.attack_mob(utente, damage)
        
        if success:
            try:
                safe_answer_callback(call.id, "⚔️ Attacco effettuato!")
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
                    markup.add(types.InlineKeyboardButton("🛡️ Difesa", callback_data="defend_mob"))
            else:
                markup = None

            # Always show the full message with damage
            username = escape_markdown(utente.username if utente.username else utente.nome)
            bot.send_message(call.message.chat.id, f"@{username}\n{msg}", reply_markup=markup, parse_mode='markdown')
        else:
            try:
                safe_answer_callback(call.id, msg, show_alert=True)
            except Exception:
                pass
        return

    elif action == "special_attack_mob":
        utente = user_service.get_user(user_id)
        
        # Try special attack on any active mob
        success, msg, extra_data, attack_events = pve_service.use_special_attack(utente, chat_id=call.message.chat.id)
        
        if success:
            try:
                safe_answer_callback(call.id, "✨ Attacco Speciale effettuato!")
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
                    markup.add(types.InlineKeyboardButton("🛡️ Difesa", callback_data="defend_mob"))
            else:
                markup = None
                       
            username = escape_markdown(utente.username if utente.username else utente.nome)
            bot.send_message(call.message.chat.id, f"@{username}\n{msg}", reply_markup=markup, parse_mode='markdown')
            
            # Handle counter-attacks
            if attack_events:
                for event in attack_events:
                    e_msg = event['message']
                    image_path = event['image']
                    e_mob_id = event['mob_id']
                    old_msg_id = event['last_message_id']
                    
                    # We need to define get_combat_markup or use inline logic
                    # Assuming get_combat_markup is not available in this scope or needs import?
                    # Let's check if get_combat_markup is defined in main.py
                    # It seems it was used in the garbage code, so it might exist.
                    # If not, we'll use a simple markup generation.
                    
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton("⚔️ Attacca", callback_data=f"attack_enemy|mob|{e_mob_id}"), 
                               types.InlineKeyboardButton("✨ Attacco Speciale", callback_data=f"special_attack_enemy|mob|{e_mob_id}"))
                    markup.add(types.InlineKeyboardButton("🛡️ Difesa", callback_data="defend_mob"))
                    
                    # send_combat_message might also be a helper or need to be replaced by bot.send_message
                    # The garbage code used send_combat_message. Let's assume it exists or use bot.send_message.
                    # To be safe, I'll use bot.send_photo or bot.send_message directly.
                    
                    if image_path and os.path.exists(image_path):
                        with open(image_path, 'rb') as photo:
                            bot.send_photo(call.message.chat.id, photo, caption=e_msg, reply_markup=markup, parse_mode='markdown')
                    else:
                        bot.send_message(call.message.chat.id, e_msg, reply_markup=markup, parse_mode='markdown')
        return

    elif action == "defend_mob":
        utente = user_service.get_user(user_id)
        success, msg = pve_service.defend(utente, chat_id=call.message.chat.id)
        
        if success:
            try:
                safe_answer_callback(call.id, "🛡️ Posizione difensiva assunta!")
            except Exception:
                pass
            
            username = escape_markdown(utente.username if utente.username else utente.nome)
            bot.send_message(call.message.chat.id, f"@{username}\n{msg}", parse_mode='markdown')
        else:
            safe_answer_callback(call.id, msg, show_alert=True)
    
    
    # EXISTING HANDLERS BELOW
    if action.startswith("use|"):
        item_name = action.split("|")[1]
        
        # Check if item requires a target
        targeted_items = ["Colpisci un giocatore", "Mira un giocatore"]
        
        if item_name in targeted_items:
            safe_answer_callback(call.id)
            msg = bot.send_message(user_id, f"🎯 Hai scelto di usare **{item_name}**.\n\nScrivi il @username del giocatore che vuoi colpire:", parse_mode='markdown')
            
            # Instantiate BotCommands to use its method
            cmd_handler = BotCommands(call.message, bot, user_id=call.from_user.id)
            cmd_handler.chatid = user_id
            bot.register_next_step_handler(msg, cmd_handler.process_item_target, item_name)
            return
            
        # Use item logic (immediate effect)
        if item_service.use_item(user_id, item_name):
            msg, data = item_service.apply_effect(utente, item_name)
            
            if data and data.get('type') == 'trap':
                # Set trap in the chat
                drop_service.set_trap(call.message.chat.id, data['trap_type'], user_id)
                
            bot.send_message(user_id, msg)
            safe_answer_callback(call.id, "✅ Oggetto usato!")
        else:
            bot.send_message(user_id, "Non hai questo oggetto o è già stato usato.")
            safe_answer_callback(call.id, "❌ Errore")

    elif action.startswith("steal|"):
        # Give 1 wumpa
        user_service.add_points(utente, 1)
        safe_answer_callback(call.id, "Hai rubato 1 Wumpa!")
        
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
        from services.wish_service import WishService
        wish_service = WishService()
        has_shenron, has_porunga = wish_service.check_dragon_balls(utente)
        
        if dragon == "shenron" and has_shenron:
            wish_service.log_summon(user_id, "Shenron")
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(f"💰 {PointsName} (300-500)", callback_data="wish|Shenron|wumpa"))
            markup.add(types.InlineKeyboardButton("⭐ EXP (300-500)", callback_data="wish|Shenron|exp"))
            bot.send_message(user_id, "🐉 Shenron è stato evocato!\n\nEsprimi il tuo desiderio!", reply_markup=markup)
        elif dragon == "porunga" and has_porunga:
            wish_service.log_summon(user_id, "Porunga")
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(f"💰 {PointsName} (50-100)", callback_data="pwish|1|wumpa"))
            markup.add(types.InlineKeyboardButton("🎁 Oggetto Raro", callback_data="pwish|1|item"))
            bot.send_message(user_id, "🐲 Porunga è stato evocato!\n\nEsprimi 3 desideri!\n\n[Desiderio 1/3]", reply_markup=markup)
        else:
            bot.send_message(user_id, "❌ Non hai le sfere necessarie!")

    elif action.startswith("wish|"):
        # Shenron wish
        safe_answer_callback(call.id)
        parts = action.split("|")
        dragon = parts[1]
        wish = parts[2]
        
        from services.wish_service import WishService
        wish_service = WishService()
        
        try:
            msg = wish_service.grant_wish(utente, wish, dragon)
            bot.send_message(call.message.chat.id, msg)
        except Exception as e:
            print(f"[ERROR] wish handler failed: {e}")
            bot.send_message(call.message.chat.id, f"❌ Errore durante l'esaudimento del desiderio: {e}")
        return

    elif action.startswith("pwish|"):
        # Porunga wish (multi-step)
        safe_answer_callback(call.id)
        parts = action.split("|")
        wish_number = int(parts[1])
        wish_choice = parts[2]
        
        from services.wish_service import WishService
        wish_service = WishService()
        
        try:
            # Grant this wish
            msg = wish_service.grant_porunga_wish(utente, wish_choice, wish_number)
            
            # Check if there are more wishes
            if wish_number < 3:
                # Show next wish options
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton(f"💰 {PointsName} (50-100)", callback_data=f"pwish|{wish_number+1}|wumpa"))
                markup.add(types.InlineKeyboardButton("🎁 Oggetto Raro", callback_data=f"pwish|{wish_number+1}|item"))
                bot.send_message(call.message.chat.id, f"{msg}\n\n[Desiderio {wish_number+1}/3]", reply_markup=markup)
            else:
                # Final wish
                # Consume spheres now (in a single transaction)
                session = wish_service.db.get_session()
                try:
                    for i in range(1, 8):
                        item_service.use_item(user_id, f"La Sfera del Drago Porunga {i}", session=session)
                    session.commit()
                except Exception as e:
                    session.rollback()
                    print(f"[ERROR] Failed to consume Porunga spheres: {e}")
                finally:
                    session.close()
                    
                bot.send_message(call.message.chat.id, f"{msg}\n\n🐲 PORUNGA HA ESAUDITO I TUOI 3 DESIDERI!")
        except Exception as e:
            print(f"[ERROR] pwish handler failed: {e}")
            bot.send_message(call.message.chat.id, f"❌ Errore durante il desiderio {wish_number}: {e}")
        return

    elif action.startswith("guide|"):
        # Show specific guide
        guide_name = action.split("|")[1]
        
        try:
            file_path = os.path.join("guides", f"{guide_name}.md")
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Split content if too long (Telegram limit 4096)
                if len(content) > 4000:
                    parts = [content[i:i+4000] for i in range(0, len(content), 4000)]
                    for part in parts:
                        bot.send_message(user_id, part, parse_mode='markdown')
                else:
                    bot.send_message(user_id, content, parse_mode='markdown')
                    
                safe_answer_callback(call.id, "📖 Guida aperta!")
            else:
                safe_answer_callback(call.id, "❌ Guida non trovata!", show_alert=True)
        except Exception as e:
            print(f"Error showing guide: {e}")
            safe_answer_callback(call.id, "❌ Errore nell'apertura della guida", show_alert=True)
        return

    # ACHIEVEMENT PAGINATION
    elif action.startswith("ach_page|"):
        parts = action.split("|")
        if len(parts) == 3:
            category = parts[1]
            page = int(parts[2])
            handle_achievements_cmd(call.message, page=page, user_id=user_id, category=category)
        else:
            page = int(parts[1])
            handle_achievements_cmd(call.message, page=page, user_id=user_id)
        safe_answer_callback(call.id)
        return

    # ACHIEVEMENT CATEGORY
    elif action.startswith("ach_cat|"):
        category = action.split("|")[1]
        handle_achievements_cmd(call.message, category=category, user_id=user_id)
        safe_answer_callback(call.id)
        return

    # SEASON PAGINATION
    elif action.startswith("season_page|"):
        page = int(action.split("|")[1])
        handle_season_cmd(call.message, page=page)
        safe_answer_callback(call.id)
        return

    # SEASON PASS PURCHASE
    elif action == "buy_season_pass":
        from services.season_manager import SeasonManager
        manager = SeasonManager()
        success, msg = manager.purchase_season_pass(user_id)
        
        if success:
            safe_answer_callback(call.id, "✅ Acquisto completato!")
            # Update the season message to show the new status
            handle_season_cmd(call.message)
        else:
            safe_answer_callback(call.id, "❌ Errore")
            bot.send_message(user_id, msg, parse_mode='markdown')
        return

def bot_polling_thread():
    bot.infinity_polling()

def regenerate_mana_job():
    """Hourly job to regenerate mana for all users (+10 capped at max_mana)"""
    try:
        session = user_service.db.get_session()
        
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
    # Random check to spawn between 8 and 22
    now = datetime.datetime.now()
    if 8 <= now.hour <= 22:
        # 20% chance every check
        if random.random() < 0.2: 
            success, msg, mob_id = pve_service.spawn_specific_mob(chat_id=GRUPPO_AROMA)
            if mob_id:
                # Apply pending effects
                applied = pve_service.apply_pending_effects(mob_id, GRUPPO_AROMA)
                for app in applied:
                    bot.send_message(GRUPPO_AROMA, f"💥 **{app['effect']}** esplode sul nuovo arrivato! Danni: {app['damage']}")
                
                mob = pve_service.get_current_mob_status(mob_id)
                if mob:
                    # Get the actual mob ID from spawn_daily_mob return value
                    markup = get_combat_markup("mob", mob_id, GRUPPO_AROMA)
                    
                    msg_text = f"⚠️ Un {mob['name']} selvatico è apparso!\n{format_mob_stats(mob, show_full=False)}\n\nSconfiggilo per ottenere ricompense!"
                    
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
    success, msg, boss_id = pve_service.spawn_boss(chat_id=GRUPPO_AROMA)
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
    try:
        active_enemies = session.query(Mob).filter_by(is_dead=False).all()
        session.close()
        
        if active_enemies:
            print(f"[DEBUG] Found {len(active_enemies)} active enemies. Processing attacks...")
            for enemy in active_enemies:
                try:
                    # Pass the chat_id where the enemy is located
                    chat_id = enemy.chat_id if enemy.chat_id else GRUPPO_AROMA
                    attack_events = pve_service.mob_random_attack(specific_mob_id=enemy.id, chat_id=chat_id)
                    if attack_events:
                        markup = get_combat_markup("mob", enemy.id, chat_id)
                        
                        for event in attack_events:
                            msg = event['message']
                            image_path = event['image']
                            mob_id = event['mob_id']
                            old_msg_id = event['last_message_id']
                            
                            sent = send_combat_message(chat_id, msg, image_path, markup, mob_id, old_msg_id)
                            if not sent:
                                # If message failed to send, check if it's a "chat not found" error
                                # This is handled inside send_combat_message but we can double check here
                                pass
                except Exception as e:
                    err_msg = str(e).lower()
                    if "chat not found" in err_msg or "chat_id_invalid" in err_msg:
                        print(f"[WARNING] Chat {enemy.chat_id} not found. Marking mob {enemy.id} as dead.")
                        # We need a new session to mark as dead since we are in a loop
                        temp_session = db.get_session()
                        try:
                            m = temp_session.query(Mob).filter_by(id=enemy.id).first()
                            if m:
                                m.is_dead = True
                                temp_session.commit()
                        finally:
                            temp_session.close()
                    else:
                        print(f"Error processing attack for enemy {enemy.id}: {e}")
    except Exception as e:
        print(f"Error in mob_attack_job: {e}")
        try:
            session.close()
        except:
            pass

def process_achievements_job():
    """Job to process pending achievements"""
    try:
        tracker = AchievementTracker()
        tracker.process_pending_events(limit=50) # Process in batches of 50, but it loops now
    except Exception as e:
        print(f"[ACHIEVEMENT JOB ERROR] {e}")




# Global state for uploads
pending_attack_upload = {}

@bot.message_handler(commands=['missing_attack'])
def handle_missing_attack(message):
    """Admin command to upload missing attack GIFs"""
    # Need to use message.chat.id since it's a message handler
    chat_id = message.chat.id
    utente = user_service.get_user(chat_id)
    if not user_service.is_admin(utente):
        return
        
    from services.character_loader import get_character_loader
    char_loader = get_character_loader()
    all_chars = char_loader.get_all_characters()
    
    # Find characters with special attack but no GIF
    missing = []
    for char in all_chars:
        has_attack = char.get('special_attack_name') and char['special_attack_name'].strip()
        has_gif = char.get('special_attack_gif') and char['special_attack_gif'].strip()
        if has_attack and not has_gif:
            missing.append(char)
            
    if not missing:
        bot.reply_to(message, "✅ Tutti i personaggi con attacchi speciali hanno una GIF!")
        return
        
    # Pick the first one
    target = missing[0]
    
    # Set pending state
    global pending_attack_upload
    pending_attack_upload[chat_id] = target['id']
    
    msg = f"🎥 **Upload GIF Attacco**\n\n"
    msg += f"Personaggio: **{target['nome']}**\n"
    msg += f"Attacco: **{target['special_attack_name']}**\n\n"
    msg += "Invia ora la GIF o il Video (MP4) per questo attacco.\n"
    msg += f"Rimanenti: {len(missing)}"
    
    bot.reply_to(message, msg, parse_mode='markdown')

# --- Equipment System Commands ---

@bot.message_handler(commands=['inventory', 'inv'])
def command_inventory(message):
    user_id = message.from_user.id
    items = equipment_service.get_user_inventory(user_id)
    if not items:
        bot.reply_to(message, "Il tuo inventario è vuoto.")
        return
        
    msg = "�� **Inventario**\n\n"
    for u_item, item in items:
        status = "✅" if u_item.is_equipped else ""
        rarity_icon = "⚪️"
        if item.rarity == "Uncommon": rarity_icon = "🟢"
        elif item.rarity == "Rare": rarity_icon = "🔵"
        elif item.rarity == "Epic": rarity_icon = "🟣"
        elif item.rarity == "Legendary": rarity_icon = "🟠"
        elif item.rarity == "Mythic": rarity_icon = "🔴"
        
        msg += f"{rarity_icon} 🆔 `{u_item.id}` - **{item.name}** ({item.slot}) {status}\n"
        
    msg += "\nUsa `/equip <id>` per equipaggiare."
    bot.reply_to(message, msg, parse_mode="Markdown")

@bot.message_handler(commands=['equip'])
def command_equip(message):
    try:
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, "Uso: `/equip <id_oggetto>`")
            return
            
        item_id = int(args[1])
        success, result = user_service.equip_item(message.from_user.id, item_id)
        bot.reply_to(message, result)
    except ValueError:
        bot.reply_to(message, "ID non valido.")

@bot.message_handler(commands=['unequip'])
def command_unequip(message):
    try:
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, "Uso: `/unequip <id_oggetto>`")
            return
            
        item_id = int(args[1])
        success, result = user_service.unequip_item(message.from_user.id, item_id)
        bot.reply_to(message, result)
    except ValueError:
        bot.reply_to(message, "ID non valido.")

@bot.message_handler(commands=['stats', 'me', 'profilo'])
def command_stats(message):
    # Pass Utente object or User object from message?
    # info_user expects the message.from_user object (which has id, first_name etc)
    # Wait, info_user signature: def info_user(self, utente_sorgente):
    # utente_sorgente should be the telegram user object.
    # But inside info_user it accesses id_telegram.
    # message.from_user has id.
    # However, Utente model has id_telegram.
    # Let's check info_user implementation again.
    # "utente = self.get_user(utente_sorgente.id_telegram)" -> No, message.from_user.id is the ID.
    # message.from_user does NOT have id_telegram attribute. It has id.
    # So I need to wrap it or pass an object with id_telegram.
    # Actually, in main.py usually we pass message.from_user and UserService handles it?
    # Let's check how other commands call info_user.
    # I can't see other calls.
    # But UserService.info_user (Line 404 in user_service.py):
    # "utente = self.get_user(utente_sorgente.id_telegram)"
    # So it expects an object with id_telegram.
    # message.from_user has 'id'.
    # So I need to adapt it.
    
    class UserWrapper:
        def __init__(self, user):
            self.id_telegram = user.id
            self.first_name = user.first_name
            self.username = user.username
            # Add other fields if needed
            self.scadenza_premium = "N/A" # Hack
            
    wrapper = UserWrapper(message.from_user)
    info = user_service.info_user(wrapper)
    bot.reply_to(message, info, parse_mode="Markdown")


@bot.message_handler(commands=['fusion'])
def command_fusion(message):
    user_id = message.from_user.id
    
    # Check Potara
    equipped = equipment_service.get_equipped_items(user_id)
    potara_count = 0
    for ui, item in equipped:
        if item.special_effect_id == 'potara_fusion':
            potara_count += 1
            
    if potara_count < 2:
        bot.reply_to(message, "Devi indossare entrambi gli orecchini Potara per la fusione!")
        return
        
    trans_id = transformation_service.get_transformation_id_by_name("Potara Fusion")
    if not trans_id:
        bot.reply_to(message, "Errore: Trasformazione non trovata.")
        return
        
    class UserWrapper:
        def __init__(self, user):
            self.id_telegram = user.id
            
    wrapper = UserWrapper(message.from_user)
    success, msg = transformation_service.activate_temporary_transformation(wrapper, trans_id, duration_minutes=5)
    bot.reply_to(message, msg)


@bot.message_handler(commands=['spawn'])
def handle_spawn_cmd(message):
    """Admin command to spawn mobs"""
    # Check Admin
    try:
        if message.from_user.id not in ADMIN_IDS:
            return
    except NameError:
        # Fallback if ADMIN_IDS not defined
        if message.from_user.id != 62716473: # Hardcoded fallback
            return

    args = message.text.split()
    # Syntax:
    # /spawn -> random mob
    # /spawn [name] -> specific mob
    # /spawn boss -> random boss
    # /spawn boss [name] -> specific boss
    
    mob_name = None
    is_boss = False
    
    if len(args) > 1:
        if args[1].lower() == 'boss':
            is_boss = True
            if len(args) > 2:
                mob_name = " ".join(args[2:])
        else:
            mob_name = " ".join(args[1:])
            
    chat_id = message.chat.id
    
    try:
        if is_boss:
            success, msg, mob_id = pve_service.spawn_boss(boss_name=mob_name, chat_id=chat_id, ignore_limit=True)
        else:
            success, msg, mob_id = pve_service.spawn_specific_mob(mob_name=mob_name, chat_id=chat_id, ignore_limit=True)
            
        bot.reply_to(message, msg)
        
        if success and mob_id:
            # Trigger immediate attack
            pve_service.mob_random_attack(specific_mob_id=mob_id, chat_id=chat_id)
            
    except Exception as e:
        bot.reply_to(message, f"❌ Errore durante lo spawn: {e}")

# --- Global Helpers ---
def process_dungeon_events(events, chat_id):
    """Global function to process dungeon events"""
    import time
    
    for event in events:
        if event['type'] == 'message':
            bot.send_message(chat_id, event['content'], parse_mode='markdown')
        elif event['type'] == 'delay':
            seconds = event.get('seconds', 3)
            try:
                bot.send_chat_action(chat_id, 'typing')
            except: pass
            time.sleep(seconds)
        elif event['type'] == 'spawn':
            # Display spawned mobs
            mob_ids = event.get('mob_ids', [])
            for mob_id in mob_ids:
                # Use global pve_service
                mob_data = pve_service.get_mob_details(mob_id)
                if mob_data:
                    # Construct message
                    msg = f"⚠️ **{mob_data['name']}** è apparso!"
                    if mob_data['is_boss']:
                        msg = f"☠️ **BOSS: {mob_data['name']}** è sceso in campo!"
                    
                    # Get markup (need global helper)
                    # Assuming get_combat_markup and send_combat_message are global
                    markup = get_combat_markup("mob", mob_id, chat_id)
                    send_combat_message(chat_id, msg, mob_data['image_path'], markup, mob_id)

# --- Scheduler Logic ---
def job_dungeon_check():
    """Periodic check for dungeon events"""
    try:
        # Check triggers
        # We handle result which might be event string or dict
        result = dungeon_service.check_daily_dungeon_trigger(GRUPPO_AROMA)
        
        if result:
            if result == "DUNGEON_PREANNOUNCED":
                bot.send_message(GRUPPO_AROMA, "🌑 **L'aria nel gruppo si fa pesante...**\nUn'energia instabile attraversa il canale.\nQualcosa sta per emergere...\n\n⚠️ **Preparatevi!**", parse_mode='markdown')
            
            elif isinstance(result, dict) and result.get("type") == "DUNGEON_STARTED":
                # Dungeon Started!
                name = result['dungeon_name']
                count = result['participant_count']
                events = result['events']
                
                msg = f"💥 **IL DUNGEON È EMERSO: {name}** 💥\n\nTutti i presenti ({count} eroi) sono stati trascinati all'interno!\n\n"
                bot.send_message(GRUPPO_AROMA, msg, parse_mode='markdown')
                
                # Send spawn messages
                process_dungeon_events(events, GRUPPO_AROMA)
                
    except Exception as e:
        print(f"[ERROR] job_dungeon_check: {e}")

def job_weekly_ranking():
    """Weekly Season Ranking Announcement"""
    print("[SCHEDULER] Running weekly ranking job...")
    try:
        from services.season_manager import SeasonManager
        manager = SeasonManager()
        
        ranking, season_name = manager.get_season_ranking(limit=10)
        
        if not ranking:
            return
            
        msg = f"🏆 **CLASSIFICA SETTIMANALE STAGIONE** 🏆\n"
        msg += f"🌟 **{season_name}** 🌟\n\n"
        
        emojis = ["🥇", "🥈", "🥉"]
        
        for i, data in enumerate(ranking):
            rank_emoji = emojis[i] if i < 3 else f"#{i+1}"
            name = data['game_name'] or data['username'] or data['nome'] or "Eroe"
            # Escape markdown
            if name:
                name = name.replace("_", "\\_").replace("*", "\\*")
            
            msg += f"{rank_emoji} **{name}**\n"
            msg += f"   ├ 🏅 Grado Stagione: {data['level']}\n"
            msg += f"   └ 📊 Livello Eroe: {data['user_level']}\n\n"
            
        msg += "🔥 Continuate a combattere per scalare la vetta!\n"
        msg += "Usa `/season` per vedere i tuoi progressi dettagliati."
        
        bot.send_message(GRUPPO_AROMA, msg, parse_mode='markdown')
    except Exception as e:
        print(f"[ERROR] Failed to send weekly ranking: {e}")

def process_crafting_queue_job():
    """Background job to check and complete finished crafting projects"""
    from datetime import datetime
    print(f"[CRAFTING JOB] Running at {datetime.now().strftime('%H:%M:%S')}")
    try:
        from services.crafting_service import CraftingService
        crafting_service = CraftingService()
        results = crafting_service.process_queue()
        print(f"[CRAFTING JOB] Processed {len(results)} jobs")
        
        for res in results:
            if res.get('success'):
                user_id = res['user_id']
                item_name = res['item_name']
                rarity = res['base_rarity']
                final_rarity = res['final_rarity']
                
                print(f"[CRAFTING JOB] Notifying user {user_id} about {item_name}")
                # Notify user
                try:
                    rarity_emoji = get_rarity_emoji(final_rarity)
                    rarity_names = {1: 'Comune', 2: 'Non Comune', 3: 'Raro', 4: 'Epico', 5: 'Leggendario'}
                    r_name = rarity_names.get(final_rarity, 'Comune')
                    
                    msg = f"🔨 **CRAFTING COMPLETATO!**\n\n"
                    msg += f"Il tuo oggetto **{rarity_emoji} {item_name}** è pronto ed è stato aggiunto al tuo inventario!\n"
                    
                    if final_rarity > rarity:
                        msg += f"✨ **GRANDE SUCCESSO!** L'oggetto è stato migliorato a **{r_name}** {rarity_emoji}!\n"
                    else:
                        msg += f"Rarità: **{r_name}** {rarity_emoji}\n"
                    
                    # Show stats if available
                    if 'stats' in res:
                        msg += "\n📊 **Statistiche Ottenute:**\n"
                        for stat, val in res['stats'].items():
                           msg += f"- {stat.capitalize()}: +{val}\n"
                    
                    bot.send_message(user_id, msg, parse_mode='markdown')
                except Exception as e:
                    print(f"[CRAFTING JOB] Could not notify user {user_id}: {e}")
                    
    except Exception as e:
        print(f"[CRAFTING JOB] Error: {e}")
        import traceback
        traceback.print_exc()

# Schedule the check every minute
# Schedule Jobs
schedule.every().hour.do(spawn_daily_mob_job)
schedule.every().hour.do(regenerate_mana_job)
schedule.every(10).seconds.do(mob_attack_job)
schedule.every(30).seconds.do(process_achievements_job)
schedule.every(1).minutes.do(process_crafting_queue_job)
schedule.every(1).minutes.do(job_dungeon_check)
schedule.every().sunday.at("20:00").do(job_weekly_ranking)
schedule.every().day.at("04:00").do(lambda: BackupService().create_backup())  # Daily Backup at 4 AM

@bot.message_handler(content_types=['text'], func=lambda message: message.reply_to_message is not None)
def scan_mob_reply(message):
    """Handle replies (e.g. Scanning a mob via Scouter)"""
    if "⚠️ Un" in message.reply_to_message.caption or "⚠️ Un" in message.reply_to_message.text:
        # Check for Scouter
        try:
            from services.equipment_service import EquipmentService
            from sqlalchemy import text
            eq_service = EquipmentService()
            session = eq_service.db.get_session()
            
            chat_id_user = message.from_user.id
            
            has_scouter = session.execute(text("""
                SELECT 1 FROM user_equipment ue
                JOIN equipment e ON ue.equipment_id = e.id
                WHERE ue.user_id = :uid AND ue.equipped = TRUE AND e.effect_type = 'scouter'
            """), {"uid": chat_id_user}).scalar()
            
            session.close()
            
            if not has_scouter:
                bot.reply_to(message, "🚫 Non hai uno **Scouter** o un **Visore** equipaggiato!")
                return
            
            # Parse Mob Name
            original_text = message.reply_to_message.caption or message.reply_to_message.text
            import re
            match = re.search(r"⚠️ Un (.+?) selvatico è apparso!", original_text)
            if match:
                mob_name = match.group(1)
                
                from services.pve_service import PVEService
                pve_service = PVEService()
                
                # Find recent active mob
                session = eq_service.db.get_session()
                mob_data = session.execute(text("""
                    SELECT id FROM mob 
                    WHERE name = :name AND current_hp > 0
                    ORDER BY id DESC LIMIT 1
                """), {"name": mob_name}).first()
                session.close()
                
                if mob_data:
                    mob = pve_service.get_mob_status_by_id(mob_data[0])
                    if mob:
                        txt = f"🔍 **Scansione Completata!**\n\n{format_mob_stats(mob, show_full=True)}"
                        bot.reply_to(message, txt, parse_mode='markdown')
                        return
                        
            bot.reply_to(message, "Non riesco a scansionare questo bersaglio.")
            
        except Exception as e:
            print(f"Error scanning mob: {e}")
            bot.reply_to(message, "Errore durante la scansione.")

            bot.reply_to(message, "Errore durante la scansione.")
            
@bot.message_handler(func=lambda message: True)
def handle_general_chat(message):
    """Handle all other chat messages for resource drops + spam protection"""
    # 5% chance to drop a resource
    try:
        # Check if message is long enough to be considered active chat (anti-spam)
        if not message.text or len(message.text) < 4:
            return
            
        user_id = message.from_user.id
        
        # Initialize service if not global (it should be)
        from services.crafting_service import CraftingService
        crafting_service = CraftingService()
        
        # Roll drop
        resource_id, image_path = crafting_service.roll_chat_drop(chance=3) # 3% chance
        
        if resource_id:
             # Add to inventory
            from sqlalchemy import text
            session = crafting_service.db.get_session()
            try:
                resource_name = session.execute(text("SELECT name FROM resources WHERE id = :id"), {"id": resource_id}).scalar()
                
                # Add drop
                success = crafting_service.add_resource_drop(user_id, resource_id, quantity=1, source="chat")
                
                if success and resource_name:
                     msg = f"✨ Hai trovato **{resource_name}**!"
                     
                     # Check if image exists and send it
                     import os
                     if image_path and os.path.exists(image_path):
                         try:
                             with open(image_path, 'rb') as photo:
                                 bot.send_photo(message.chat.id, photo, caption=msg, parse_mode='markdown', reply_to_message_id=message.message_id)
                         except Exception as img_err:
                             print(f"[IMAGE ERROR] {img_err}")
                             bot.reply_to(message, msg, parse_mode='markdown')
                     else:
                         bot.reply_to(message, msg, parse_mode='markdown')
            finally:
                session.close()
                
    except Exception as e:
        print(f"[CHAT DROP ERROR] {e}")

def schedule_checker():
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    print("Starting aROMa Bot...")
    
    # Initialize DB (if needed)
    db = Database()
    db.create_all_tables()
    
    # Reload achievements from CSV
    achievement_tracker.load_from_csv()
    
    # NEW: Validate user stats on startup
    user_service.validate_and_fix_user_stats()
    
    # Schedule jobs
    schedule.every().day.at("04:00").do(BackupService().create_backup)
    threading.Thread(target=schedule_checker, daemon=True).start()
    
    # Start Bot Polling (Main Thread)
    # Using the defined wrapper if exists, or direct.
    # bot_polling_thread() calls infinity_polling.
    try:
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except Exception as e:
        print(f"Bot polling crash: {e}")

