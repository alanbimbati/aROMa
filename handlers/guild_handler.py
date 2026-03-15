import telebot
from telebot import types
import datetime
import os
from settings import BASE_DIR
from services.user_service import UserService
from services.guild_service import GuildService
from services.guild_activity_service import GuildActivityService
from services.mount_service import MountService
from utils.markup_utils import get_mention_markdown, escape_markdown

# Initialize services
user_service = UserService()
guild_service = GuildService()
guild_activity_service = GuildActivityService()
mount_service = MountService()

PIL_AVAILABLE = False
try:
    from PIL import Image
    import io
    PIL_AVAILABLE = True
except ImportError:
    pass

def safe_answer_callback(bot, call_id, text=None, show_alert=False):
    try:
        bot.answer_callback_query(call_id, text=text, show_alert=show_alert)
    except Exception:
        pass

def handle_guilds_list_cmd(bot, message):
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

def handle_guild_cmd(bot, message):
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
        leader_name = get_mention_markdown(leader.id_telegram, leader.username if leader.username else leader.nome) if leader else f"{guild['leader_id']}"
        msg += f"👑 **Capo**: {leader_name}\n"
        msg += f"💰 **Banca**: {guild['wumpa_bank']} Wumpa\n"
        msg += f"👥 **Membri**: {guild['member_limit']} (max)\n\n"
        msg += f"🏠 **Locanda**: Lv. {guild['inn_level']}\n"
        msg += f"⚔️ **Armeria**: Lv. {guild['armory_level']}\n"
        msg += f"🏘️ **Villaggio**: Lv. {guild['village_level']}\n"
        msg += f"🧪 **Laboratorio**: Lv. {guild.get('laboratory_level', 0) or 0}\n"
        msg += f"🌻 **Giardino**: Lv. {guild.get('garden_level', 0) or 0}\n\n"
        
        markup = types.InlineKeyboardMarkup()
        # Main Entry Point: Visit Village (starts the tour)
        markup.add(types.InlineKeyboardButton("🏰 Visita Villaggio", callback_data="guild_tour|0"))
        
        # Using main_image for the guild overview
        image = guild.get('main_image') or "https://i.imgur.com/placeholder_village.png"
        
        # Try to use the newly generated image if artifact exists (legacy check, can be removed or kept)
        if not guild.get('main_image') and os.path.exists("/home/alan/.gemini/antigravity/brain/9a4a9ae3-f560-4ab4-9a81-ef73f8b4bc22/guild_village_square_v2_1771249621834.png"):
             image = "/home/alan/.gemini/antigravity/brain/9a4a9ae3-f560-4ab4-9a81-ef73f8b4bc22/guild_village_square_v2_1771249621834.png"

        try:
            if isinstance(image, str) and image.startswith("http"):
                 bot.send_photo(message.chat.id, image, caption=msg, reply_markup=markup, parse_mode='markdown')
            elif isinstance(image, str) and os.path.exists(image):
                 with open(image, 'rb') as photo:
                     bot.send_photo(message.chat.id, photo, caption=msg, reply_markup=markup, parse_mode='markdown')
            else:
                 bot.send_message(message.chat.id, msg, reply_markup=markup, parse_mode='markdown')
        except Exception:
            bot.send_message(message.chat.id, msg, reply_markup=markup, parse_mode='markdown')

def handle_found_cmd(bot, message):
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
    # Note: registering next step handler needs 'bot' which is passed.
    # But functions should be self-contained if possible. 
    # For next step, we might need to define process_guild_name here or importing it?
    # Simpler: define it here.
    bot.register_next_step_handler(msg, process_guild_name)

def process_guild_name(message):
    from main import bot
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
    map_path = "assets/aroma_land_map.png"
    try:
        if os.path.exists(map_path):
            with open(map_path, 'rb') as photo:
                bot.send_photo(message.chat.id, photo, caption=f"🗺️ **Scegli la posizione per {name}**\n\nSeleziona una coordinata sulla mappa:", reply_markup=markup, parse_mode='markdown')
        else:
             bot.send_message(message.chat.id, f"🗺️ **Scegli la posizione per {name}**\n\nSeleziona una coordinata sulla mappa:", reply_markup=markup, parse_mode='markdown')
    except Exception:
        bot.send_message(message.chat.id, f"🗺️ **Scegli la posizione per {name}**\n\nSeleziona una coordinata sulla mappa:", reply_markup=markup, parse_mode='markdown')




def process_guild_rename(message):
    new_name = message.text
    if not new_name or len(new_name) > 32:
        # We need bot here. I'll import it from main or pass it. 
        # Actually, the convention in this project seems to be passing bot or using it globally.
        # Since I can't easily import bot from main (circular), I'll use a trick or pass it.
        # Let's check how other handlers do it.
        from main import bot
        bot.reply_to(message, "❌ Nome non valido (max 32 caratteri).")
        return
        
    user_id = message.from_user.id
    success, msg = guild_service.rename_guild(user_id, new_name)
    from main import bot
    bot.reply_to(message, msg)

def process_guild_deposit(message):
    try:
        amount = int(message.text)
        print(f"[DEBUG][GUILD] User {message.from_user.id} depositing {amount} Wumpa")
        success, msg = guild_service.deposit_wumpa(message.from_user.id, amount)
        from main import bot
        bot.reply_to(message, msg)
    except ValueError:
        from main import bot
        bot.reply_to(message, "❌ Inserisci un numero valido.")

def handle_guild_view(bot, call):
    """Refresh the guild management view"""
    guild = guild_service.get_user_guild(call.from_user.id)
    if not guild or guild['role'] != "Leader":
        safe_answer_callback(bot, call.id, "Solo il capogilda può accedere a questo menu!", show_alert=True)
        return

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(f"🏠 Locanda ({guild['inn_level'] * 500} W)", callback_data="guild_upgrade|inn"))
    markup.add(types.InlineKeyboardButton(f"⚔️ Armeria (Lv. {guild['armory_level']})", callback_data="guild_armory_view"))
    markup.add(types.InlineKeyboardButton(f"🏘️ Villaggio ({guild['village_level'] * 1000} W)", callback_data="guild_upgrade|village"))
    markup.add(types.InlineKeyboardButton(f"🔞 Bordello ({(guild['bordello_level'] + 1) * 1500} W)", callback_data="guild_upgrade|bordello"))
    
    # Alchemy & Garden Upgrades
    lab_lvl = guild.get('laboratory_level', 0) or 0
    gar_lvl = guild.get('garden_level', 0) or 0
    markup.add(
        types.InlineKeyboardButton(f"🧪 Lab. Alchimia (Lv. {lab_lvl})", callback_data="guild_lab_info"),
        types.InlineKeyboardButton(f"🌻 Giardino (Lv. {gar_lvl})", callback_data="guild_upgrade_garden_info")
    )
    
    # New Upgrades: Dragon Stables, Ancient Temple, Magic Library
    drag_lvl = guild.get('dragon_stables_level', 0) or 0
    temple_lvl = guild.get('ancient_temple_level', 0) or 0
    lib_lvl = guild.get('magic_library_level', 0) or 0
    
    markup.add(
        types.InlineKeyboardButton(f"🐉 Scuderie (Lv. {drag_lvl})", callback_data="guild_upgrade|dragon_stables"),
        types.InlineKeyboardButton(f"⛩️ Tempio (Lv. {temple_lvl})", callback_data="guild_upgrade|ancient_temple")
    )
    markup.add(
        types.InlineKeyboardButton(f"📚 Biblioteca (Lv. {lib_lvl})", callback_data="guild_upgrade|magic_library")
    )

    # Customization Menu
    markup.add(types.InlineKeyboardButton("✨ Personalizza Menu (5000 W)", callback_data="guild_personalize_menu"))
    
    # Visual button for Locanda
    markup.add(types.InlineKeyboardButton("🏨 Vai alla Locanda", callback_data="guild_inn_view"))
    
    markup.add(types.InlineKeyboardButton("✏️ Rinomina", callback_data="guild_rename_ask"),
               types.InlineKeyboardButton("🗑️ Elimina", callback_data="guild_delete_ask"))
    markup.add(types.InlineKeyboardButton("🔙 Indietro", callback_data="guild_tour|3"))
    
    bot.edit_message_text(f"⚙️ **Gestione Gilda: {guild['name']}**\n\nBanca: {guild['wumpa_bank']} Wumpa", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='markdown')

def handle_inn_cmd(bot, message):
    """Access the Locanda (Private Chat Only)"""
    user_id = message.from_user.id
    
    # Deadlock Fix: Check if user is resting BEFORE combat check
    user = user_service.get_user(user_id)
    if user and user.resting_since:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🛑 Smetti di Riposare", callback_data="profile_rest_stop"))
        bot.send_message(message.chat.id, "🛌 Stai riposando in Locanda.\nVuoi smettere e tornare all'avventura?", reply_markup=markup)
        return

    # Check if user is in combat (only if trying to ENTER)
    if user_service.is_true_in_combat(user_id):
        utente = user_service.get_user(user_id)
        last_attack = getattr(utente, 'last_attack_time', None)
        remaining = 600
        if last_attack:
            import datetime
            elapsed = (datetime.datetime.now() - last_attack).total_seconds()
            remaining = int(600 - elapsed)
        
        bot.send_message(message.chat.id, f"⚔️ Sei ancora in combattimento! Devi terminare la battaglia o aspettare {remaining//60}m {remaining%60}s.")
        return
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🍺 Entra in Locanda", callback_data="guild_inn_view"))
    bot.send_message(message.chat.id, "Benvenuto viandante! Clicca per entrare:", reply_markup=markup)

def handle_guild_inn_view(bot, call):
    """Show Inn interior"""
    user_id = call.from_user.id
    
    # Check if user is in combat
    if user_service.is_true_in_combat(user_id):
        utente = user_service.get_user(user_id)
        last_attack = getattr(utente, 'last_attack_time', None)
        remaining = 600
        if last_attack:
            import datetime
            elapsed = (datetime.datetime.now() - last_attack).total_seconds()
            remaining = int(600 - elapsed)
            
        safe_answer_callback(bot, call.id, f"⚔️ Sei in combattimento! Termina la battaglia o aspetta {remaining//60}m {remaining%60}s.", show_alert=True)
        return
    
    safe_answer_callback(bot, call.id)
    # We call handle_facility_view alias or impl
    handle_facility_view(bot, call, "inn")

def handle_facility_view(bot, call, facility_type):
    """View specialized guild facilities"""
    user_id = call.from_user.id
    guild = guild_service.get_user_guild(user_id)
    if not guild:
        safe_answer_callback(bot, call.id, "Non sei in una gilda!")
        return
        
    facility_data = {
        'inn': {'name': '🏨 Locanda', 'level': guild['inn_level'], 'img_attr': 'inn_image'},
        'brewery': {'name': '🍻 Birrificio', 'level': guild['brewery_level'], 'img_attr': 'brewery_image'},
        'bordello': {'name': '💃 Bordello delle Elfe', 'level': guild['bordello_level'], 'img_attr': 'bordello_image'},
        'armory': {'name': '⚔️ Armeria', 'level': guild['armory_level'], 'img_attr': 'armory_image'}
    }
    
    data = facility_data.get(facility_type)
    if not data: return

    level = data['level']
    img_url = guild.get(data['img_attr'])
    
    msg = f"{data['name']} (Lv. {level})\n\n"
    if facility_type == 'inn':
        msg += "Benvenuto alla Locanda della Gilda! Qui puoi riposare per recuperare HP e Mana velocemente.\n\n"
    elif facility_type == 'brewery':
        msg += "Il Birrificio produce birre artigianali che potenziano l'efficacia delle tue pozioni!\n\n"
    elif facility_type == 'bordello':
        msg += "Il Bordello delle Elfe offre relax e Vigore ai membri della gilda.\n\n"
        if level == 0:
            msg += "🚨 *Questa struttura deve ancora essere costruita dal capogilda.*"
    elif facility_type == 'armory':
        msg += "L'Armeria ti permette di potenziare il tuo equipaggiamento e depositare risorse utili per l'intera Gilda.\n\n"
        if level == 0:
            msg += "🚨 *L'Armeria deve ancora essere costruita dal capogilda.*"

    markup = types.InlineKeyboardMarkup()
    if level > 0:
        if facility_type == 'inn':
             markup.add(types.InlineKeyboardButton("🛌 Riposa", callback_data="inn_rest_start"))
             markup.add(types.InlineKeyboardButton("🍻 Birrificio", callback_data="guild_inn_brewery")) # Link to brewery
             markup.add(types.InlineKeyboardButton("💃 Bordello", callback_data="visita_bordello")) # Link to bordello
        elif facility_type == 'brewery':
             markup.add(types.InlineKeyboardButton("🍺 Bevi Birra", callback_data="buy_guild_beer"))
        elif facility_type == 'bordello':
             markup.add(types.InlineKeyboardButton("🔞 Visita", callback_data="visita_bordello_action")) # Action to visit
        elif facility_type == 'armory':
             markup.add(
                 types.InlineKeyboardButton("⚒️ Inizia Crafting", callback_data="craft_select_equipment"),
                 types.InlineKeyboardButton("💎 Raffineria", callback_data="guild_refinery_view")
             )
             markup.add(types.InlineKeyboardButton("📦 Risorse", callback_data="craft_view_resources"))
             
    if guild['role'] in ["Leader", "Officer"]:
        if level == 0:
             markup.add(types.InlineKeyboardButton("💰 Costruisci", callback_data=f"guild_buy|{facility_type}"))
        else:
             markup.add(types.InlineKeyboardButton("🆙 Upgrade", callback_data=f"guild_upgrade|{facility_type}"))
        markup.add(types.InlineKeyboardButton("🖼️ Cambia Immagine", callback_data=f"guild_img|{facility_type}"))
        
    markup.add(types.InlineKeyboardButton("🔙 Indietro", callback_data="guild_tour|0")) # Back to village
    
    image = img_url if img_url else "https://i.imgur.com/generic_facility.png"
    
    try:
        bot.edit_message_media(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            media=types.InputMediaPhoto(image, caption=msg, parse_mode='markdown'),
            reply_markup=markup
        )
    except Exception:
        bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id, caption=msg, reply_markup=markup, parse_mode='markdown')
    
    safe_answer_callback(bot, call.id)

def handle_buy_beer(bot, call):
    user_id = call.from_user.id
    success, msg = guild_service.buy_guild_drink(user_id, drink_type='beer')
    safe_answer_callback(bot, call.id, msg, show_alert=not success)
    if success:
        handle_facility_view(bot, call, "brewery")

def handle_guild_structure_action(bot, call, structure_key, action_type):
    """Handle buying or upgrading guild structures"""
    user_id = call.from_user.id
    
    # Check if user is leader
    is_leader = guild_service.is_guild_leader(user_id)
    if not is_leader:
        safe_answer_callback(bot, call.id, "❌ Solo il Capogilda può gestire gli upgrade!", show_alert=True)
        return
        
    # Map structure keys to service methods
    methods = {
        'inn': guild_service.upgrade_inn,
        'armory': guild_service.upgrade_armory,
        'brewery': guild_service.upgrade_brewery,
        'bordello': guild_service.upgrade_bordello,
        'laboratory': guild_service.upgrade_laboratory,
        'garden': guild_service.upgrade_garden,
        'stables': guild_service.upgrade_dragon_stables,
        'temple': guild_service.upgrade_ancient_temple,
        'library': guild_service.upgrade_magic_library,
        'village': guild_service.expand_village
    }
    
    if structure_key not in methods:
        safe_answer_callback(bot, call.id, f"❌ Struttura '{structure_key}' non valida.")
        return

    success, msg = methods[structure_key](user_id)
    safe_answer_callback(bot, call.id, msg, show_alert=True)
    
    # Refresh view
    if structure_key in ['inn', 'brewery', 'bordello']:
        handle_facility_view(bot, call, structure_key)
    else:
        handle_guild_view(bot, call)

def handle_mount_list(bot, call):
    """Show list of mounts"""
    user_id = call.from_user.id
    all_mounts = mount_service.get_all_mounts()
    user_mounts = mount_service.get_user_mounts(user_id)
    owned_ids = [m.id for m in user_mounts]
    
    utente = user_service.get_user(user_id)
    
    msg = "🏇 **SCUDERIE DEI DRAGHI** 🏇\n\n"
    msg += "Qui puoi acquistare creature per viaggiare più velocemente!\n"
    msg += "*Nota: Sulla mount non puoi usare Attacchi Speciali o Difesa.*\n\n"
    
    markup = types.InlineKeyboardMarkup()
    
    for m in all_mounts:
        rarity_stars = "⭐" * m.rarity
        owned_tag = "✅ " if m.id in owned_ids else ""
        equipped_tag = "👉 " if utente.current_mount_id == m.id else ""
        
        line = f"{owned_tag}{equipped_tag}{m.name} (+{m.speed_bonus} Vel) {rarity_stars}\n"
        msg += line
        
        if m.id in owned_ids:
            if utente.current_mount_id == m.id:
                markup.add(types.InlineKeyboardButton(f"🚶 Scendi da {m.name}", callback_data="equip_mount|None"))
            else:
                markup.add(types.InlineKeyboardButton(f"🏇 Sali su {m.name}", callback_data=f"equip_mount|{m.id}"))
        else:
            markup.add(types.InlineKeyboardButton(f"💰 Compra {m.name} ({m.price} 🍑)", callback_data=f"buy_mount|{m.id}"))
            
    markup.add(types.InlineKeyboardButton("🔙 Indietro", callback_data="guild_tour|5")) # Scuderie is index 5
    
    # Image logic for mount
    image_path = os.path.join(BASE_DIR, "assets", "guild", "stables.png")
    
    try:
        bot.edit_message_media(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            media=types.InputMediaPhoto(image_path, caption=msg, parse_mode='markdown'),
            reply_markup=markup
        )
    except Exception:
        bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id, caption=msg, reply_markup=markup, parse_mode='markdown')

def handle_buy_mount(bot, call, mount_id):
    success, msg = mount_service.buy_mount(call.from_user.id, mount_id)
    safe_answer_callback(bot, call.id, msg, show_alert=True)
    if success:
        handle_mount_list(bot, call)

def handle_equip_mount(bot, call, mount_id):
    success, msg = mount_service.equip_mount(call.from_user.id, mount_id)
    safe_answer_callback(bot, call.id, msg)
    handle_mount_list(bot, call)

def handle_guild_rank_cmd(bot, message):
    args = message.text.split()
    dungeon_id = None
    if len(args) > 1 and args[1].isdigit():
        dungeon_id = int(args[1])
        
    ranking = guild_service.get_dungeon_ranking(dungeon_id=dungeon_id, limit=5)
    
    if not ranking:
         bot.reply_to(message, "🏰 Nessuna attività di gilda registrata nei dungeon.")
         return
         
    title = "🏰 **Classifica Gilde (Danni Dungeon)** 🏰"
    if dungeon_id:
        title += f"\n(Dungeon ID: {dungeon_id})"
        
    msg = f"{title}\n\n"
    emojis = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    
    for i, row in enumerate(ranking):
        rank_icon = emojis[i] if i < len(emojis) else f"#{i+1}"
        msg += f"{rank_icon} **{row['name']}**\n"
        msg += f"   💥 Danni: {row['total_damage']}\n\n"
        
    bot.reply_to(message, msg, parse_mode='markdown')

# Dispatcher update - we re-define it to include new functions
def handle_guild_callbacks(bot, call):
    action = call.data
    print(f"[DEBUG][GUILD_HANDLER] Callback received: {action} from user: {call.from_user.id}")
    
    if action == "guild_list_view":
        handle_guilds_list_cmd(bot, call.message)
        return True
        
    elif action == "guild_found_start":
        bot.answer_callback_query(call.id, "Digita /found per iniziare!")
        return True

    elif action == "guild_deposit_start":
        msg = bot.send_message(call.message.chat.id, "💰 Quanti Wumpa vuoi depositare?")
        bot.register_next_step_handler(msg, lambda m: process_guild_deposit(bot, m))
        return True
    
    elif action == "guild_inn_view":
        handle_guild_inn_view(bot, call)
        return True
        
    elif action.startswith("guild_upgrade|") or action.startswith("guild_buy|"):
        # Format: guild_upgrade|type
        parts = action.split("|")
        struct_type = parts[1]
        handle_guild_structure_action(bot, call, struct_type, "upgrade")
        return True
        
    elif action == "buy_guild_beer":
        handle_buy_beer(bot, call)
        return True
        
    elif action == "visita_bordello":
        handle_facility_view(bot, call, "bordello")
        return True
        
    elif action == "guild_inn_brewery":
        handle_facility_view(bot, call, "brewery")
        return True

    elif action.startswith("buy_mount|"):
        mount_id = int(action.split("|")[1])
        handle_buy_mount(bot, call, mount_id)
        return True
        
    elif action.startswith("equip_mount|"):
        mount_id_str = action.split("|")[1]
        mount_id = int(mount_id_str) if mount_id_str != "None" else None
        handle_equip_mount(bot, call, mount_id)
        return True
        
    # More callbacks to follow (tour, etc)
    return False


