import telebot
from telebot import types
import datetime
import json
import os
from services.user_service import UserService
from services.item_service import ItemService
from services.equipment_service import EquipmentService
from services.stats_service import StatsService
from services.stat_build_service import get_stat_editor_ui
from services.achievement_tracker import AchievementTracker
from services.season_manager import SeasonManager
from services.shop_service import ShopService
from services.potion_service import PotionService
from services.character_loader import get_character_loader
from services.skin_service import SkinService
from services.wish_service import WishService
from services.character_service import CharacterService
from services.guild_service import GuildService
from settings import PointsName, PremiumCurrencyName, PremiumCurrencyIcon
from services.skill_service import SkillService
from services.transformation_service import TransformationService
from services.crafting_service import CraftingService
from utils.markup_utils import safe_answer_callback, safe_edit_message, get_mention_markdown, escape_markdown

# Initialize services
user_service = UserService()
item_service = ItemService()
equipment_service = EquipmentService()
stats_service = StatsService()
achievement_tracker = AchievementTracker()
season_manager = SeasonManager()
shop_service = ShopService()
potion_service = PotionService()
skin_service = SkinService()
wish_service = WishService()
character_service = CharacterService()
guild_service = GuildService()
skill_service = SkillService()
transformation_service = TransformationService()
crafting_service = CraftingService()

# Global state for admin features (volatile)
admin_last_viewed_character = {}

def safe_answer_callback(bot, call_id, text=None, show_alert=False):
    """Safely answer a callback query"""
    try:
        bot.answer_callback_query(call_id, text=text, show_alert=show_alert)
    except Exception as e:
        # print(f"Error answering callback: {e}")
        pass

def handle_profile_view(bot, message, target_user=None, is_callback=False, call_id=None):
    """Show comprehensive user profile with stats and transformations (Legacy Layout)"""
    try:
        user_id = message.from_user.id
        
        if target_user:
            target = target_user
        else:
            # Self-healing: Ensure level is correct before showing profile
            try:
                user_service.check_level_up(user_id)
            except Exception as e:
                print(f"[ERROR] Failed to check level up for {user_id}: {e}")
                
            target = user_service.get_user(user_id)
        
        if not target:
            bot.reply_to(message, "❌ Utente non trovato.")
            return

        # Handle callback answer if needed
        if is_callback and call_id:
            safe_answer_callback(bot, call_id)

        # Get character info
        # Note: In user_handler, we have char_loader available via get_character_loader()
        # but better to use user_service or character_service if possible, 
        # but old code used char_loader directly.
        char_loader = get_character_loader()
        character = None
        if target.livello_selezionato:
            character = char_loader.get_character_by_id(target.livello_selezionato)
        
        # Build new premium profile format
        full_name = target.game_name or target.username or target.nome or "Eroe"
        
        # Header with level and status
        status_line = ""
        if target.premium == 1:
            status_line = " 🎖 **PREMIUM**"
        
        msg = f"👤 **{escape_markdown(full_name)}** | Lv. {target.livello}{status_line}\n"
        
        char_name = character['nome'] if character else 'N/A'
        saga = f" ({character['character_group']})" if character and character.get('character_group') else ""
        msg += f"🎭 **{char_name}**{saga}\n"
        
        if hasattr(target, 'title') and target.title:
            msg += f"👑 *{escape_markdown(target.title)}*\n"
            
        msg += "\n╔═══🕹═══╗\n"
        
        # RPG Stats with visual bars/emojis
        current_hp = target.current_hp if hasattr(target, 'current_hp') and target.current_hp is not None else target.health
        hp_percent = int((current_hp / target.max_health) * 10)
        hp_bar = "❤️" + "▰" * hp_percent + "▱" * (10 - hp_percent)
        msg += f"{hp_bar} `{current_hp}/{target.max_health}`\n"
        
        mana_percent = int((target.mana / target.max_mana) * 10) if target.max_mana > 0 else 0
        mana_bar = "💙" + "▰" * mana_percent + "▱" * (10 - mana_percent)
        msg += f"{mana_bar} `{target.mana}/{target.max_mana}`\n"
        
        # Core Stats
        # Using base_damage as per old layout. If user_handler used attack_power, we might want to consolidate,
        # but 'grafica precedente' implies looking like before.
        # Ensure base_damage exists (it should as per grep).
        msg += f"\n⚔️ **Danno**: `{target.base_damage}`\n"
        
        # Advanced Stats
        res = getattr(target, 'resistance', 0) or 0
        crit = getattr(target, 'crit_chance', 0) or 0
        speed = getattr(target, 'speed', 0) or 0
        
        msg += f"🛡️ **Res**: `{res}%` | 💥 **Crit**: `{crit}%` | ⚡ **Vel**: `{speed}`\n"
        
        # Progression
        next_lv_num = target.livello + 1
        next_lv_row = char_loader.get_characters_by_level(next_lv_num)
        next_lv_row = next_lv_row[0] if next_lv_row else None
        
        if next_lv_row:
            exp_req = next_lv_row.get('exp_required', 100)
        else:
            exp_req = 100 * (next_lv_num ** 2)
            
        exp_percent = int((target.exp / exp_req) * 10) if exp_req > 0 else 0
        exp_bar = "▰" * exp_percent + "▱" * (10 - exp_percent)
        msg += f"\n📈 **Exp**: `{target.exp}/{exp_req}`\n`[{exp_bar}]`\n"
        
        # Profession Level
        prof_info = crafting_service.get_profession_info(target.id_telegram)
        prof_level = prof_info['level']
        prof_xp = prof_info['xp']
        prof_xp_needed = 100 * (prof_level * (prof_level + 1) // 2)
        prof_percent = int((prof_xp / prof_xp_needed) * 10) if prof_xp_needed > 0 else 0
        prof_bar = "▰" * prof_percent + "▱" * (10 - prof_percent)
        msg += f"🔨 **Armaiolo**: Lv. `{prof_level}/50` | `{prof_xp}/{prof_xp_needed}` XP\n`[{prof_bar}]`\n"
        
        msg += f"\n🍑 **{PointsName}**: `{target.points}`"
        if target.stat_points > 0:
            msg += f" | 📊 **Punti**: `{target.stat_points}`"
        msg += "\n"
        
        # Premium Currency
        cristalli = getattr(target, 'cristalli_aroma', 0) or 0
        if cristalli > 0:
            msg += f"{PremiumCurrencyIcon} **{PremiumCurrencyName}**: `{cristalli}`\n"

        # Special Attack / Abilities
        if character:
            abilities = skill_service.get_character_abilities(character['id'])
            
            if abilities:
                msg += f"\n✨ **Abilità:**\n"
                for ability in abilities:
                    msg += f"🔮 {ability['name']}: `{ability['damage']}` DMG | `{ability['mana_cost']}` MP\n"
            elif character.get('special_attack_name'):
                msg += f"\n✨ **Attacco Speciale**: {character['special_attack_name']}\n"
                msg += f"⚔️ Danno: `{character['special_attack_damage']}` | 💙 Mana: `{character['special_attack_mana_cost']}`\n"

        msg += "      aROMa\n"
        msg += "╚═══🕹═══╝\n"

        # Active Status (Resting/Fatigue)
        status_extras = []
        resting_status = user_service.get_resting_status(target.id_telegram)
        if resting_status:
            status_extras.append(f"🛌 **Riposo**: +{resting_status['hp']} HP/+{resting_status['mana']} MP")
        if user_service.check_fatigue(target):
            status_extras.append("⚠️ **AFFATICATO**")
            
        active_trans = transformation_service.get_active_transformation(target)
        if active_trans:
            time_left = active_trans['expires_at'] - datetime.now()
            if time_left.total_seconds() > 0:
                hours_left = int(time_left.total_seconds() / 3600)
                status_extras.append(f"🔥 **{active_trans['name']}** ({hours_left}h)")
        
        if status_extras:
            msg += "─" * 20 + "\n" + "\n".join(status_extras) + "\n"

        # Buttons (Reusing the existing button logic structure but adapting to new layout if needed)
        markup = types.InlineKeyboardMarkup()
        
        # Self-profile actions
        if target.id_telegram == user_id: # user_id is requestor
            markup.row(
                types.InlineKeyboardButton("🎒 Inventario", callback_data="inventory_view"),
                types.InlineKeyboardButton("🛡️ Equipaggiamento", callback_data="equipment_view")
            )
            markup.row(
                types.InlineKeyboardButton("📊 Statistiche", callback_data="stats_view"),
                types.InlineKeyboardButton("👤 Cambia Eroe", callback_data="char_select_menu")
            )
            markup.row(
                types.InlineKeyboardButton("🎭 Skin", callback_data=f"skin_menu|{target.livello_selezionato}"),
                types.InlineKeyboardButton("🏆 Titoli", callback_data="titles_menu")
            )
            
            # Rest button
            if not target.resting_since:
                markup.add(types.InlineKeyboardButton("🛌 Riposa (Locanda)", callback_data="profile_rest_start"))
            else:
                 markup.add(types.InlineKeyboardButton("🏃 Sveglia (Stop Riposo)", callback_data="profile_rest_stop"))
            
            # Potion Shortcut
            markup.add(types.InlineKeyboardButton("🧪 Pozioni Rapide", callback_data="profile_potions"))
        
        # Send
        if is_callback:
            try:
                bot.edit_message_text(msg, message.chat.id, message.message_id, reply_markup=markup, parse_mode='markdown')
            except:
                bot.send_message(message.chat.id, msg, reply_markup=markup, parse_mode='markdown')
        else:
            bot.send_message(message.chat.id, msg, reply_markup=markup, parse_mode='markdown')

    except Exception as e:
        print(f"Error in handle_profile_view: {e}")
        bot.reply_to(message, "❌ Errore nel caricamento del profilo.")

def handle_inventory_view(bot, message, user_id=None, page=0):
    """Show user inventory with interactive buttons"""
    if user_id is None:
        user_id = message.from_user.id
        
    inventory = item_service.get_inventory(user_id)
    
    if not inventory:
        txt = "🎒 Il tuo inventario è vuoto!"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Menu Principale", callback_data="main_menu"))
        
        if hasattr(message, 'message_id') and not hasattr(message, 'text'):
             bot.edit_message_text(txt, message.chat.id, message.message_id, reply_markup=markup)
        else:
             bot.reply_to(message, txt, reply_markup=markup)
        return
    
    msg = "🎒 **Il tuo Inventario**\nClicca su un oggetto per usarlo.\n\n"
    
    # Simple list first
    for item, quantity in inventory:
        meta = item_service.get_item_metadata(item)
        emoji = meta.get('emoji', '🎒')
        msg += f"{emoji} **{item}** (x{quantity})\n"
    
    markup = types.InlineKeyboardMarkup()
    
    # Usable items buttons
    for item, quantity in inventory:
        # Skip Dragon Balls, Key items etc if needed
        if "Sfera del Drago" in item: continue
        
        meta = item_service.get_item_metadata(item)
        emoji = meta.get('emoji', '🔹')
        
        markup.add(types.InlineKeyboardButton(f"{emoji} Usa {item}", callback_data=f"use_item|{item}"))
        
    markup.add(types.InlineKeyboardButton("🔙 Indietro", callback_data="back_to_profile"))
    
    if hasattr(message, 'message_id') and not hasattr(message, 'text'):
        bot.edit_message_text(msg, message.chat.id, message.message_id, reply_markup=markup, parse_mode='markdown')
    else:
        bot.reply_to(message, msg, reply_markup=markup, parse_mode='markdown')

def handle_stats_view(bot, message, is_callback=False):
    """Show stats editor"""
    user_id = message.from_user.id
    stats = stats_service.start_editing(user_id)
    
    if not stats:
        bot.reply_to(message, "❌ Errore statistiche.")
        return
        
    text, markup = get_stat_editor_ui(stats)
    
    if is_callback:
        bot.edit_message_text(text, message.chat.id, message.message_id, reply_markup=markup, parse_mode='markdown')
    else:
        bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='markdown')

def handle_titles_view(bot, message, is_callback=False, call_id=None):
    """Show title selection menu"""
    user_id = message.from_user.id
    utente = user_service.get_user(user_id)
    
    # Fetch achievements
    achievements = achievement_tracker.get_user_achievements(user_id)
    
    unlocked_titles = []
    tier_emojis = {'bronze': '🥉', 'silver': '🥈', 'gold': '🥇', 'platinum': '💎', 'diamond': '💎', 'legendary': '👑'}
    
    for ach in achievements:
        if ach['current_tier']:
            emoji = tier_emojis.get(ach['current_tier'], '')
            title = ach.get('title') or ach['name']
            unlocked_titles.append((ach['key'], f"{title} {emoji}"))
            
    if not unlocked_titles:
        msg = "❌ Non hai ancora sbloccato nessun titolo!"
        if is_callback and call_id:
            safe_answer_callback(bot, call_id, msg, show_alert=True)
            return
        bot.send_message(message.chat.id, msg)
        return

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("❌ Rimuovi Titolo", callback_data="set_title|NONE"))
    
    for key, title_display in unlocked_titles:
        icon = "✅" if utente.title == title_display else "▪️"
        markup.add(types.InlineKeyboardButton(f"{icon} {title_display}", callback_data=f"set_title|{key}"))
        
    markup.add(types.InlineKeyboardButton("🔙 Indietro", callback_data="back_to_profile"))
    
    msg = f"🏆 **GESTIONE TITOLI**\nTitolo attuale: **{utente.title or 'Nessuno'}**"
    
    if is_callback:
        bot.edit_message_text(msg, message.chat.id, message.message_id, reply_markup=markup, parse_mode='markdown')
    else:
        bot.send_message(message.chat.id, msg, reply_markup=markup, parse_mode='markdown')

def handle_character_choice_menu(bot, message, level_idx=None, char_idx=0, only_owned=0, is_callback=False):
    """Character selection with improved navigation"""
    user_id = message.from_user.id
    utente = user_service.get_user(user_id)
    if not utente: return

    is_admin = user_service.is_admin(utente)
    
    # Get all levels
    levels = character_service.get_character_levels()
    if not levels:
        bot.reply_to(message, "Nessun personaggio trovato!")
        return

    # Determine level_idx if not provided
    if level_idx is None:
        start_level = character_service.get_closest_level(utente.livello)
        try:
            level_idx = levels.index(start_level)
        except ValueError:
            level_idx = 0
    
    # Validation
    if level_idx < 0: level_idx = 0
    if level_idx >= len(levels): level_idx = len(levels) - 1

    current_level = levels[level_idx]

    # Handle "Only Owned/Unlocked" flat list mode
    if only_owned == 1:
        # FLAT LIST MODE: unlocked chars
        all_chars = character_service.get_available_characters(utente)
        level_chars = [c for c in all_chars if character_service.is_character_unlocked(utente, c['id'])]
        level_chars.sort(key=lambda x: (x['livello'], x['nome']))
        current_level = "TUTTI"
        # Mock levels for display
        # levels remains as is for reference, but navigation might be weird if we mix modes.
        # But here we are in a mode where level_idx doesn't matter for fetching, only for back navigation?
        # Actually char_nav uses level_idx to toggle back to standard mode.
    else:
        # STANDARD MODE: Per Level
        # Check visibility
        if not is_admin and current_level > utente.livello:
            # Revert to max allowed
            valid_levels = [l for l in levels if l <= utente.livello]
            if valid_levels:
                current_level = valid_levels[-1]
                level_idx = levels.index(current_level)
            else:
                level_idx = 0
                current_level = levels[0]
        
        level_chars = character_service.get_characters_by_level(current_level)

    if not level_chars:
         msg = f"🔒 **Livello {current_level}**\n\nNessun personaggio sbloccato in questo livello."
         markup = types.InlineKeyboardMarkup()
         nav_row = []
         if level_idx > 0:
             nav_row.append(types.InlineKeyboardButton("◀️ Livello", callback_data=f"char_nav|{level_idx - 1}|0|{only_owned}"))
         nav_row.append(types.InlineKeyboardButton(f"Liv {current_level}", callback_data="ignore"))
         if level_idx < len(levels) - 1:
             nav_row.append(types.InlineKeyboardButton("▶️ Livello", callback_data=f"char_nav|{level_idx + 1}|0|{only_owned}"))
         markup.row(*nav_row)
         markup.add(types.InlineKeyboardButton("🔙 Profilo", callback_data="back_to_profile"))
         
         toggle_text = "🔓 Mostra Tutti" if only_owned == 1 else "🔐 Solo Sbloccati"
         new_owned = 0 if only_owned == 1 else 1
         markup.add(types.InlineKeyboardButton(toggle_text, callback_data=f"char_nav|{level_idx}|0|{new_owned}"))

         if is_callback:
             try:
                 bot.edit_message_text(msg, message.chat.id, message.message_id, reply_markup=markup, parse_mode='markdown')
             except:
                 bot.send_message(message.chat.id, msg, reply_markup=markup, parse_mode='markdown')
         else:
             bot.send_message(message.chat.id, msg, reply_markup=markup, parse_mode='markdown')
         return

    # Validate char_idx
    if char_idx < 0: char_idx = 0
    if char_idx >= len(level_chars): char_idx = len(level_chars) - 1

    char = level_chars[char_idx]
    
    char_id = char['id']
    char_name = char['nome']
    char_group = char.get('character_group', '')
    char_element = char.get('elemental_type', '')
    char_level = char['livello']
    char_lv_premium = char.get('lv_premium', 0)
    char_price = char.get('price', 0)

    is_owned = character_service.is_character_owned(utente, char_id)
    is_equipped = (utente.livello_selezionato == char_id)
    is_unlocked = character_service.is_character_unlocked(utente, char_id)

    # Format Card
    lock_icon = "" if is_unlocked else "🔒 "
    msg = f"{lock_icon}"
    msg += character_service.format_character_card(char, show_price=True, is_equipped=is_equipped, user=utente)

    if not is_unlocked:
        msg += "\n\n🔒 **PERSONAGGIO BLOCCATO**\n"
        if char['livello'] > utente.livello:
             msg += f"Raggiungi livello {char['livello']} per sbloccarlo!\n"
        elif char['lv_premium'] == 1:
             msg += "Richiede abbonamento Premium!\n"

    filter_status = " (Sbloccati)" if only_owned == 1 else ""
    msg += f"\n📄 Livello {level_idx + 1}/{len(levels)} - Personaggio {char_idx + 1}/{len(level_chars)}{filter_status}"

    markup = types.InlineKeyboardMarkup()
    
    # Row 1: Level Nav (Only in Standard Mode)
    if only_owned == 0:
        level_row = []
        if level_idx > 0:
            level_row.append(types.InlineKeyboardButton("◀️ Lv", callback_data=f"char_nav|{level_idx - 1}|0|{only_owned}"))
        level_row.append(types.InlineKeyboardButton(f"Liv {current_level}", callback_data="ignore"))
        if level_idx < len(levels) - 1:
            level_row.append(types.InlineKeyboardButton("▶️ Lv", callback_data=f"char_nav|{level_idx + 1}|0|{only_owned}"))
        markup.row(*level_row)
    else:
        markup.row(types.InlineKeyboardButton(f"🔓 Lista Completa ({len(level_chars)})", callback_data="ignore"))

    # Row 2: Char Nav
    nav_char_row = []
    if char_idx > 0:
        nav_char_row.append(types.InlineKeyboardButton("◀️", callback_data=f"char_nav|{level_idx}|{char_idx-1}|{only_owned}"))
    else:
        nav_char_row.append(types.InlineKeyboardButton("⏺️", callback_data="ignore"))
    
    nav_char_row.append(types.InlineKeyboardButton(f"{char_idx + 1}/{len(level_chars)}", callback_data="ignore"))

    if char_idx < len(level_chars) - 1:
        nav_char_row.append(types.InlineKeyboardButton("▶️", callback_data=f"char_nav|{level_idx}|{char_idx+1}|{only_owned}"))
    else:
        nav_char_row.append(types.InlineKeyboardButton("⏺️", callback_data="ignore"))
    markup.row(*nav_char_row)

    # Row 2.5: Filter Toggle
    toggle_text = "🔓 Mostra Tutti" if only_owned == 1 else "🔐 Solo Sbloccati"
    new_owned = 0 if only_owned == 1 else 1
    markup.add(types.InlineKeyboardButton(toggle_text, callback_data=f"char_nav|{level_idx}|{char_idx}|{new_owned}"))

    # Row 3: Saga Nav
    if char_group:
         markup.add(types.InlineKeyboardButton(f"📚 {char_group}", callback_data=f"saga_nav|{char_group}|0"))
    
    # Row 4: Season Filter
    markup.add(types.InlineKeyboardButton("🐉 Personaggi della Stagione", callback_data="saga_nav|Dragon Ball|0"))

    # Action Buttons
    if is_owned:
        if not is_equipped:
            markup.add(types.InlineKeyboardButton("✅ Equipaggia", callback_data=f"char_select|{char_id}"))
        else:
            markup.add(types.InlineKeyboardButton("⭐ Già Equipaggiato", callback_data="char_already_equipped"))
    elif char_lv_premium == 2 and char_price > 0:
        price = char_price
        if utente.premium == 1: price = int(price * 0.5)
        markup.add(types.InlineKeyboardButton(f"🛒 Compra ({price} 🍑)", callback_data=f"char_buy|{char_id}"))
    
    markup.add(types.InlineKeyboardButton("🔙 Profilo", callback_data="back_to_profile"))

    # Admin Tracking
    if is_admin:
        admin_last_viewed_character[user_id] = {
            'character_id': char_id,
            'character_name': char_name,
            'timestamp': datetime.datetime.now()
        }

    # Send/Edit logic
    from services.character_loader import get_character_image
    image_data = get_character_image(char, is_locked=not is_unlocked)
    
    if is_callback:
        try:
             # Delete and resend if switching media type logic (simplified here to always delete/send for safety or edit caption if possible)
             # But for character browser, image changes often.
             # We try to send new photo.
             try:
                 bot.delete_message(message.chat.id, message.message_id)
             except: pass
             
             if image_data:
                 bot.send_photo(message.chat.id, image_data, caption=msg, reply_markup=markup, parse_mode='markdown')
             else:
                 bot.send_message(message.chat.id, msg, reply_markup=markup, parse_mode='markdown')
        except Exception as e:
            print(f"Error updating char menu: {e}")
    else:
        if image_data:
             bot.send_photo(message.chat.id, image_data, caption=msg, reply_markup=markup, parse_mode='markdown')
        else:
             bot.send_message(message.chat.id, msg, reply_markup=markup, parse_mode='markdown')


def handle_saga_view(bot, message, saga_name, char_idx=0, is_callback=False):
    """Show characters by saga"""
    user_id = message.from_user.id
    utente = user_service.get_user(user_id)
    is_admin = user_service.is_admin(utente)

    char_loader = get_character_loader()
    all_sagas = char_loader.get_all_sagas()
    
    if saga_name not in all_sagas:
        # Check if valid or default?
        pass
        
    saga_idx = all_sagas.index(saga_name) if saga_name in all_sagas else 0
    saga_chars = char_loader.get_characters_by_saga(saga_name)

    # Filter
    if not is_admin:
        saga_chars = [c for c in saga_chars if c['livello'] <= utente.livello or c['lv_premium'] == 2]

    if not saga_chars:
        if is_callback: safe_answer_callback(bot, message.id if hasattr(message, 'id') else None, "Nessun personaggio trovato.") # callback id is in call
        return

    if char_idx < 0: char_idx = 0
    if char_idx >= len(saga_chars): char_idx = len(saga_chars) - 1

    char = saga_chars[char_idx]
    char_id = char['id']
    is_owned = character_service.is_character_owned(utente, char_id)
    is_equipped = (utente.livello_selezionato == char_id)
    is_unlocked = character_service.is_character_unlocked(utente, char_id)

    # Format Card
    lock_icon = "" if is_unlocked else "🔒 "
    msg = f"{lock_icon}"
    msg += character_service.format_character_card(char, show_price=True, is_equipped=is_equipped, user=utente)

    if not is_unlocked:
         msg += "\n\n🔒 **PERSONAGGIO BLOCCATO**\n"
         if char['livello'] > utente.livello:
             msg += f"Raggiungi livello {char['livello']} per sbloccarlo!\n"

    msg += f"\n📚 **{saga_name}** - {char_idx + 1}/{len(saga_chars)}"

    markup = types.InlineKeyboardMarkup()

    # Row 1: Saga Nav
    saga_nav_row = []
    if saga_idx > 0:
        saga_nav_row.append(types.InlineKeyboardButton("⏮️", callback_data=f"saga_nav|{all_sagas[saga_idx-1]}|0"))
    if saga_idx < len(all_sagas) - 1:
        saga_nav_row.append(types.InlineKeyboardButton("⏭️", callback_data=f"saga_nav|{all_sagas[saga_idx+1]}|0"))
    if saga_nav_row: markup.row(*saga_nav_row)

    # Row 2: Char Nav
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

    markup.add(types.InlineKeyboardButton("🔙 Torna a Livelli", callback_data="char_nav|0|0|0"))

    # Actions
    if is_owned:
        if not is_equipped:
            markup.add(types.InlineKeyboardButton("✅ Equipaggia", callback_data=f"char_select|{char_id}"))
        else:
            markup.add(types.InlineKeyboardButton("⭐ Già Equipaggiato", callback_data="char_already_equipped"))
    elif char.get('lv_premium', 0) == 2 and char.get('price', 0) > 0:
        price = char['price']
        if utente.premium == 1: price = int(price * 0.5)
        markup.add(types.InlineKeyboardButton(f"🛒 Compra ({price} 🍑)", callback_data=f"char_buy|{char_id}"))

    # Send/Edit (Same logic as above)
    from services.character_loader import get_character_image
    image_data = get_character_image(char, is_locked=not is_unlocked)
    
    if is_callback:
        try:
             try: bot.delete_message(message.chat.id, message.message_id)
             except: pass
             if image_data:
                 bot.send_photo(message.chat.id, image_data, caption=msg, reply_markup=markup, parse_mode='markdown')
             else:
                 bot.send_message(message.chat.id, msg, reply_markup=markup, parse_mode='markdown')
        except Exception as e:
            print(f"Error in saga_nav: {e}")
    else:
        if image_data:
             bot.send_photo(message.chat.id, image_data, caption=msg, reply_markup=markup, parse_mode='markdown')
        else:
             bot.send_message(message.chat.id, msg, reply_markup=markup, parse_mode='markdown')

def handle_user_callbacks(bot, call):
    """Dispatcher for user-related callbacks"""
    data = call.data
    user_id = call.from_user.id
    message = call.message
    
    if data == "back_to_profile" or data == "profile_view":
        handle_profile_view(bot, message, is_callback=True, call_id=call.id)
        return True
        
    elif data == "inventory_view":
        handle_inventory_view(bot, message, user_id)
        return True
        
    elif data == "stats_view":
        handle_stats_view(bot, message, is_callback=True)
        return True
        
    elif data == "titles_menu":
        handle_titles_view(bot, message, is_callback=True, call_id=call.id)
        return True
        
    elif data == "char_select_menu":
        handle_character_choice_menu(bot, message, is_callback=True)
        return True
        
    elif data.startswith("char_nav|"):
        parts = data.split("|")
        # char_nav|level_idx|char_idx|only_owned
        l_idx = int(parts[1])
        c_idx = int(parts[2])
        o_own = int(parts[3]) if len(parts) > 3 else 0
        handle_character_choice_menu(bot, message, level_idx=l_idx, char_idx=c_idx, only_owned=o_own, is_callback=True)
        safe_answer_callback(bot, call.id)
        return True
        
    elif data.startswith("saga_nav|"):
        parts = data.split("|")
        s_name = parts[1]
        c_idx = int(parts[2])
        handle_saga_view(bot, message, s_name, char_idx=c_idx, is_callback=True)
        if is_callback: safe_answer_callback(bot, call.id)
        return True
        
    elif data.startswith("set_title|"):
        key = data.split("|")[1]
        
        if key == "NONE":
            user_service.update_user(user_id, {'title': None})
            safe_answer_callback(bot, call.id, "Titolo rimosso!")
        else:
             # Find title text
             achievements = achievement_tracker.get_user_achievements(user_id)
             title_text = None
             tier_emojis = {'bronze': '🥉', 'silver': '🥈', 'gold': '🥇', 'platinum': '💎', 'diamond': '💎', 'legendary': '👑'}
             
             for ach in achievements:
                 if ach['key'] == key and ach['current_tier']:
                     emoji = tier_emojis.get(ach['current_tier'], '')
                     t = ach.get('title') or ach['name']
                     title_text = f"{t} {emoji}"
                     break
            
             if title_text:
                 user_service.update_user(user_id, {'title': title_text})
                 safe_answer_callback(bot, call.id, f"Titolo impostato: {title_text}")
             else:
                 safe_answer_callback(bot, call.id, "Errore: Titolo non trovato.")
                 
        handle_titles_view(bot, message, is_callback=True, call_id=call.id)
        return True
        
    elif data == "profile_potions":
        handle_profile_potions(bot, message, is_callback=True)
        return True
        
    elif data.startswith("potion_use|"):
        potion_name = data.split("|")[1]
        success, msg = potion_service.use_potion(user_service.get_user(user_id), potion_name)
        safe_answer_callback(bot, call.id, msg, show_alert=not success)
        if success:
            handle_profile_potions(bot, message, is_callback=True)
        return True

    elif data.startswith("potion_buy|"):
        potion_name = data.split("|")[1]
        success, msg = potion_service.buy_potion(user_service.get_user(user_id), potion_name)
        safe_answer_callback(bot, call.id, msg, show_alert=not success)
        if success:
            handle_profile_potions(bot, message, is_callback=True)
        return True
        
    elif data.startswith("skin_menu|"):
        try:
            char_id = int(data.split("|")[1])
        except:
            # If no char_id or "none", get from user
            u = user_service.get_user(user_id)
            char_id = u.livello_selezionato
            
        handle_skin_menu(bot, message, char_id, is_callback=True)
        return True
        
    elif data.startswith("skin_buy|"):
        skin_id = int(data.split("|")[1])
        success, msg = skin_service.purchase_skin(user_id, skin_id)
        safe_answer_callback(bot, call.id, msg, show_alert=not success)
        if success:
            skin = skin_service.get_skin_by_id(skin_id)
            handle_skin_menu(bot, message, skin['character_id'], is_callback=True)
        return True
        
    elif data == "skin_unequip":
        success, msg = skin_service.equip_skin(user_id, None)
        safe_answer_callback(bot, call.id, msg)
        handle_skin_menu(bot, message, user_service.get_user(user_id).livello_selezionato, is_callback=True)
        return True
        
    elif data.startswith("skin_equip|"):
        skin_id = int(data.split("|")[1])
        success, msg = skin_service.equip_skin(user_id, skin_id)
        safe_answer_callback(bot, call.id, msg)
        if success:
            skin = skin_service.get_skin_by_id(skin_id)
            handle_skin_menu(bot, message, skin['character_id'], is_callback=True)
        return True

    elif data.startswith("char_select|"):
        char_id = int(data.split("|")[1])
        user_service.update_user(user_id, {'livello_selezionato': char_id})
        safe_answer_callback(bot, call.id, "Personaggio selezionato!")
        
        # Admin check for tracking
        u = user_service.get_user(user_id)
        if u and user_service.is_admin(u):
            # We don't have access to the global admin_last_viewed_character dict directly here efficiently
            # We can skip it or reimplement it if crucial.
            # For now, simplistic approach: just confirm.
            pass
            
        handle_profile_view(bot, message, is_callback=True)
        return True
        
    elif data == "ach_menu" or data.startswith("ach_cat|"):
        category = "menu"
        if data.startswith("ach_cat|"):
             category = data.split("|")[1]
        handle_achievements_view(bot, message, category, is_callback=True)
        return True
        
    elif data == "profile_rest_start":
        user_service.start_resting(user_id)
        safe_answer_callback(bot, call.id, "Ti sei messo a riposare!")
        handle_profile_view(bot, message, is_callback=True)
        return True
        
    elif data == "profile_rest_stop":
        multiplier = 1.0
        guild = guild_service.get_user_guild(user_id)
        if guild:
            multiplier = 1.0 + (guild.get('inn_level', 1) * 0.5)
        success, msg = user_service.stop_resting(user_id, recovery_multiplier=multiplier)
        safe_answer_callback(bot, call.id, msg)
        handle_profile_view(bot, message, is_callback=True)
        return True
        
    elif data.startswith("season_page|"):
        page = int(data.split("|")[1])
        handle_season_view(bot, message, page, is_callback=True)
        return True
        
    elif data == "buy_season_pass":
        # Simplified buy logic
        u = user_service.get_user(user_id)
        if u.points >= 1000:
            user_service.add_points(u, -1000)
            season = season_manager.get_active_season()
            if season:
                 season_manager.activate_premium_pass(user_id, season.id)
                 safe_answer_callback(bot, call.id, "Season Pass acquistato!", show_alert=True)
                 handle_season_view(bot, message, is_callback=True)
            else:
                 safe_answer_callback(bot, call.id, "Nessuna stagione attiva.", show_alert=True)
        else:
            safe_answer_callback(bot, call.id, "Non hai abbastanza Wumpa!", show_alert=True)
        return True
        
    elif data.startswith("ranking|"):
        rtype = data.split("|")[1]
        handle_ranking_view(bot, message, rtype, is_callback=True)
        return True
        
    elif data.startswith("use_item|"):
        # We handle item usage in main dispatch usually, but can do it here if simple
        # For now return False to let main handle it or we implement handle_item_use
        return False # Let main.py or specialized item handler deal with it? 
                     # Actually main.py has callbacks for use_item. 
                     # We should migrate it later.
    
    return False

def handle_profile_potions(bot, message, is_callback=False):
    """Show dedicated potion management view"""
    # Just reuse profile view with is_potions=True flag (we need to support it in handle_profile_view logic)
    # The original main.py mixed profile and potions. 
    # Here we can implement a specialized view or call profile with extra arg.
    # In this file, handle_profile_view doesn't have is_potions arg yet.
    # We should add it or create a separate function. 
    # Let's create a separate function logic to keep things clean.
    
    user_id = message.from_user.id
    utente = user_service.get_user(user_id)
    
    all_potions = potion_service.get_all_potions()
    inventory = item_service.get_inventory(user_id)
    inventory_dict = {name: count for name, count in inventory}
    
    hp_pots = sorted([p for p in all_potions if p['tipo'] == 'health_potion'], key=lambda x: x['effetto_valore'])
    mana_pots = sorted([p for p in all_potions if p['tipo'] == 'mana_potion'], key=lambda x: x['effetto_valore'])
    
    markup = types.InlineKeyboardMarkup()
    
    # Ultra-short codes
    code_map = {"Piccola": "PP", "Media": "PM", "Grande": "PG", "Completa": "PC"}
    def get_code(name):
        return next((code for key, code in code_map.items() if key in name), "??")
        
    max_len = max(len(hp_pots), len(mana_pots))
    for i in range(max_len):
        row_btns = []
        if i < len(hp_pots):
            p = hp_pots[i]
            count = inventory_dict.get(p['nome'], 0)
            row_btns.append(types.InlineKeyboardButton(f"❤️{get_code(p['nome'])} ({count})", callback_data=f"potion_use|{p['nome']}"))
            row_btns.append(types.InlineKeyboardButton("🛒", callback_data=f"potion_buy|{p['nome']}"))
        else:
             row_btns.extend([types.InlineKeyboardButton(" ", callback_data="none")]*2)

        if i < len(mana_pots):
            p = mana_pots[i]
            count = inventory_dict.get(p['nome'], 0)
            row_btns.append(types.InlineKeyboardButton(f"💙{get_code(p['nome'])} ({count})", callback_data=f"potion_use|{p['nome']}"))
            row_btns.append(types.InlineKeyboardButton("🛒", callback_data=f"potion_buy|{p['nome']}"))
        else:
             row_btns.extend([types.InlineKeyboardButton(" ", callback_data="none")]*2)
             
        markup.row(*row_btns)
        
    # Elisir
    elisirs = [p for p in all_potions if p['tipo'] == 'full_restore']
    if elisirs:
        e = elisirs[0]
        c = inventory_dict.get(e['nome'], 0)
        markup.row(
            types.InlineKeyboardButton(f"✨ Elisir ({c})", callback_data=f"potion_use|{e['nome']}"),
            types.InlineKeyboardButton("🛒", callback_data=f"potion_buy|{e['nome']}")
        )
        
    markup.add(types.InlineKeyboardButton("🔄 Aggiorna", callback_data="profile_potions"),
               types.InlineKeyboardButton("🔙 Profilo", callback_data="profile_view"))
               
    msg = "🧪 **GESTIONE POZIONI**\n\n"
    msg += f"❤️ **PV**: {utente.current_hp}/{utente.max_health}\n"
    msg += f"💙 **Mana**: {utente.mana}/{utente.max_mana}\n"
    msg += f"💰 **Wumpa**: {utente.points}\n"
    
    if is_callback:
        bot.edit_message_text(msg, message.chat.id, message.message_id, reply_markup=markup, parse_mode='markdown')
    else:
        bot.send_message(message.chat.id, msg, reply_markup=markup, parse_mode='markdown')

def handle_skin_menu(bot, message, char_id, is_callback=False):
    """Show skin menu"""
    user_id = message.from_user.id
    
    # Get character details
    char = get_character_loader().get_character_by_id(char_id)
    if not char:
        bot.reply_to(message, "❌ Personaggio non trovato.")
        return

    owned_skins = skin_service.get_user_skins(user_id, char_id)
    available_skins = skin_service.get_available_skins(char_id)
    
    msg = f"🎭 **Skin Animate: {char['nome']}**\n\n"
    msg += "Qui puoi acquistare ed equipaggiare versioni animate.\n\n"
    
    markup = types.InlineKeyboardMarkup()
    
    if owned_skins:
        msg += "✅ **Le tue Skin:**\n"
        for us in owned_skins:
            status = " (Equipaggiata)" if us.is_equipped else ""
            msg += f"• {us.skin_name}{status}\n"
            if not us.is_equipped:
                markup.add(types.InlineKeyboardButton(f"👕 Equipaggia {us.skin_name}", callback_data=f"skin_equip|{us.skin_id}"))
        msg += "\n"
        markup.add(types.InlineKeyboardButton("🚫 Rimuovi Skin (Statica)", callback_data="skin_unequip"))
        
    owned_ids = [us.skin_id for us in owned_skins]
    to_buy = [s for s in available_skins if s['id'] not in owned_ids]
    
    if to_buy:
        msg += "💰 **Disponibili:**\n"
        for s in to_buy:
            msg += f"• **{s['name']}** - {s['price']} Wumpa\n"
            markup.add(types.InlineKeyboardButton(f"🛒 Compra {s['name']} ({s['price']} W)", callback_data=f"skin_buy|{s['id']}"))
    elif not owned_skins:
        msg += "😞 Nessuna skin disponibile."
        
    markup.add(types.InlineKeyboardButton("🔙 Profilo", callback_data="profile_view"))
    
    if is_callback:
        bot.edit_message_text(msg, message.chat.id, message.message_id, reply_markup=markup, parse_mode='markdown')
    else:
        bot.send_message(message.chat.id, msg, reply_markup=markup, parse_mode='markdown')

def handle_achievements_view(bot, message, category="menu", is_callback=False):
    """Show achievements"""
    user_id = message.from_user.id
    
    if category == "menu":
         markup = types.InlineKeyboardMarkup()
         markup.row(types.InlineKeyboardButton("🐉 Dragon Ball", callback_data="ach_cat|dragon_ball"),
                    types.InlineKeyboardButton("🏆 Classici", callback_data="ach_cat|classici"))
         msg = "🏆 **I TUOI ACHIEVEMENT**\nSeleziona categoria:"
         
         if is_callback:
             bot.edit_message_text(msg, message.chat.id, message.message_id, reply_markup=markup, parse_mode='markdown')
         else:
             bot.send_message(message.chat.id, msg, reply_markup=markup, parse_mode='markdown')
         return

    all_ach = achievement_tracker.get_all_achievements_with_progress(user_id, category=category)
    if not all_ach:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Indietro", callback_data="ach_menu"))
        msg = "Nessun achievement qui."
        if is_callback:
             bot.edit_message_text(msg, message.chat.id, message.message_id, reply_markup=markup)
        return

    # Sort
    tier_map = {'bronze': 1, 'silver': 2, 'gold': 3, 'platinum': 4, 'diamond': 5, 'legendary': 6}
    all_ach.sort(key=lambda x: (not x['is_completed'], -tier_map.get(x['achievement'].tier, 0)))
    
    # Pagination? (Simplified to show all or first 10 for now)
    msg = f"🏆 **Achievements: {category.capitalize()}**\n\n"
    for item in all_ach[:15]:
        status = "✅" if item['is_completed'] else "🔒"
        ach = item['achievement']
        msg += f"{status} **{ach.name}**\n_{ach.description}_\n"
        if not item['is_completed']:
             msg += f"   Progress: {item['progress']}/{ach.max_progress}\n"
        msg += "\n"
        
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Indietro", callback_data="ach_menu"))
    
    if is_callback:
        bot.edit_message_text(msg, message.chat.id, message.message_id, reply_markup=markup, parse_mode='markdown')
    else:
        bot.send_message(message.chat.id, msg, reply_markup=markup, parse_mode='markdown')

def handle_season_view(bot, message, page=0, is_callback=False):
    """Show season info"""
    user_id = message.from_user.id
    
    season_status = season_manager.get_season_status(user_id)
    if not season_status:
        bot.reply_to(message, "Nessuna stagione attiva.")
        return
        
    season = season_manager.get_active_season()
    all_rewards = season_manager.get_all_season_rewards(season.id)
    
    ITEMS_PER_PAGE = 5
    total_pages = (len(all_rewards) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    if page >= total_pages: page = total_pages - 1
    if page < 0: page = 0
    
    start = page * ITEMS_PER_PAGE
    page_rewards = all_rewards[start:start+ITEMS_PER_PAGE]
    
    progress = season_status['progress']
    msg = f"🏆 **{season.name}**\n"
    msg += f"⭐ Grado **{progress['level']}** | EXP: {progress['exp']}/{season_status['exp_per_level']}\n"
    if progress['has_premium']:
        msg += "👑 **Pass Premium Attivo**\n"
    else:
        msg += "🆓 **Pass Gratuito**\n"
        
    msg += f"\n🎁 **Ricompense (Pagina {page+1}/{total_pages})**:\n"
    for r in page_rewards:
        unlocked = progress['level'] >= r.level_required
        icon = "✅" if unlocked else "🔒"
        prem = "👑" if r.is_premium else "🆓"
        msg += f"{icon} Lv.{r.level_required} {prem}: {r.reward_name}\n"
        
    markup = types.InlineKeyboardMarkup()
    nav = []
    if page > 0: nav.append(types.InlineKeyboardButton("⬅️", callback_data=f"season_page|{page-1}"))
    if page < total_pages - 1: nav.append(types.InlineKeyboardButton("➡️", callback_data=f"season_page|{page+1}"))
    if nav: markup.row(*nav)
    
    if not progress['has_premium']:
        markup.add(types.InlineKeyboardButton("🛒 Acquista Pass (1000 W)", callback_data="buy_season_pass"))
        
    if is_callback:
        bot.edit_message_text(msg, message.chat.id, message.message_id, reply_markup=markup, parse_mode='markdown')
    else:
        bot.send_message(message.chat.id, msg, reply_markup=markup, parse_mode='markdown')

def handle_ranking_view(bot, message, ranking_type="global", is_callback=False):
    """Show ranking"""
    msg = ""
    markup = types.InlineKeyboardMarkup()
    
    if ranking_type == "global":
        users = user_service.get_users()
        users.sort(key=lambda x: x.exp if x.exp else 0, reverse=True)
        
        msg = "🌍 **CLASSIFICA GLOBALE** 🌍\n\n"
        char_loader = get_character_loader()
        
        for i, u in enumerate(users[:15]):
            char_name = "N/A"
            if u.livello_selezionato:
                c = char_loader.get_character_by_id(u.livello_selezionato)
                if c: char_name = c['nome']
            
            name = u.game_name or u.username or u.nome or "Eroe"
            msg += f"{i+1}. **{name}** (Lv. {u.livello}) - {char_name}\n"
            msg += f"   ✨ EXP: {u.exp}\n"
            
        markup.add(types.InlineKeyboardButton("🌟 Classifica Stagione", callback_data="ranking|season"))
        
    elif ranking_type == "season":
        ranking, sname = season_manager.get_season_ranking(limit=15)
        if not ranking:
            msg = "⚠️ Nessuna classifica stagionale."
        else:
            msg = f"🏆 **CLASSIFICA STAGIONE: {sname}**\n\n"
            for i, d in enumerate(ranking):
                msg += f"#{i+1} **{d['game_name'] or 'Eroe'}**\n"
                msg += f"   🏅 Grado {d['level']} (Lv. {d['user_level']})\n"
                
        markup.add(types.InlineKeyboardButton("🌍 Classifica Globale", callback_data="ranking|global"))
        
    if is_callback:
        bot.edit_message_text(msg, message.chat.id, message.message_id, reply_markup=markup, parse_mode='markdown')
    else:
        bot.send_message(message.chat.id, msg, reply_markup=markup, parse_mode='markdown')
