import telebot
from telebot import types
import os
from services.pve_service import PvEService

pve_service = PvEService()

def get_combat_markup(enemy_type, enemy_id, chat_id, can_use_items=None):
    """Generate combat markup with all required buttons"""
    if can_use_items is None:
        # Auto-detect if it's a "next mob" (ID > 237)
        mob = pve_service.get_mob_details(enemy_id)
        can_use_items = mob and mob.id > 237
        
    markup = types.InlineKeyboardMarkup()
    # Standard attack buttons
    markup.add(
        types.InlineKeyboardButton("⚔️ Attacca", callback_data=f"attack_enemy|{enemy_type}|{enemy_id}"),
        types.InlineKeyboardButton("✨ Speciale", callback_data=f"special_attack_enemy|{enemy_type}|{enemy_id}")
    )
    # Defend button
    markup.add(types.InlineKeyboardButton("🛡️ Difesa", callback_data=f"defend_mob|{enemy_type}|{enemy_id}"))
    
    # AoE buttons (only if >= 2 mobs)
    mob_count = pve_service.get_active_mobs_count(chat_id)
    if mob_count >= 2:
        markup.add(
            types.InlineKeyboardButton("💥 AoE", callback_data=f"aoe_attack_enemy|{enemy_type}|{enemy_id}"),
            types.InlineKeyboardButton("🌟 Speciale AoE", callback_data=f"special_aoe_attack_enemy|{enemy_type}|{enemy_id}")
        )
    
    # Always show Flee and Scan buttons
    markup.add(
        types.InlineKeyboardButton("🏃 Fuggi", callback_data=f"flee_enemy|{enemy_type}|{enemy_id}"),
        types.InlineKeyboardButton("🔍 Scan", callback_data=f"scan_mob|{enemy_id}")
    )
        
    return markup

def escape_markdown(text):
    """Escape Markdown V1 special characters"""
    if not text: return ""
    return text.replace("_", "\\_").replace("*", "\\*").replace("[", "\\[").replace("`", "\\`")

def get_mention_markdown(user_id, name):
    """Generate a markdown mention link for a user"""
    return f"[{escape_markdown(name)}](tg://user?id={user_id})"


def safe_answer_callback(bot, call_id, text=None, show_alert=False):
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


def safe_edit_message(bot, text, chat_id, message_id, reply_markup=None, parse_mode='markdown', message_obj=None):
    """Safely edit a message, handling both text and media (caption)"""
    try:
        # Try to detect if it's a media message
        is_media = False
        if message_obj:
            if hasattr(message_obj, 'content_type'):
                 is_media = message_obj.content_type in ['photo', 'animation', 'video', 'document']
            else:
                 is_media = any([getattr(message_obj, x, None) for x in ['photo', 'animation', 'video', 'document']])
        

        if is_media:
            bot.edit_message_caption(chat_id=chat_id, message_id=message_id, caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
        else:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=reply_markup, parse_mode=parse_mode)
            

    except telebot.apihelper.ApiTelegramException as e:
        err_msg = str(e).lower()
        if "there is no text in the message to edit" in err_msg:
            # Re-try as caption if text edit failed with this error
            try:
                bot.edit_message_caption(chat_id=chat_id, message_id=message_id, caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
            except Exception as e2:
                print(f"[ERROR] safe_edit_message fallback failed: {e2}")
        elif "message to edit not found" in err_msg:
            pass # Message deleted
        elif "message is not modified" in err_msg:
            pass # Ignore
        else:
            print(f"[ERROR] safe_edit_message failed: {e}")
    except Exception as e:
        print(f"[ERROR] safe_edit_message general failure: {e}")

