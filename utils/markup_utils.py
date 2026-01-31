from telebot import types
from services.pve_service import PvEService
import os

pve_service = PvEService()

def get_combat_markup(enemy_type, enemy_id, chat_id, can_use_items=None):
    """Generate combat markup with all required buttons"""
    if can_use_items is None:
        # Auto-detect if it's a "next mob" (ID > 237)
        mob = pve_service.get_mob_details(enemy_id)
        can_use_items = mob and mob['id'] > 237
        
    markup = types.InlineKeyboardMarkup()
    # Standard attack buttons
    markup.add(
        types.InlineKeyboardButton("⚔️ Attacca", callback_data=f"attack_enemy|{enemy_type}|{enemy_id}"),
        types.InlineKeyboardButton("✨ Speciale", callback_data=f"special_attack_enemy|{enemy_type}|{enemy_id}")
    )
    # Defend button
    markup.add(types.InlineKeyboardButton("🛡️ Difesa", callback_data="defend_mob"))
    
    # AoE buttons (only if >= 2 mobs)
    mob_count = pve_service.get_active_mobs_count(chat_id)
    if mob_count >= 2:
        markup.add(
            types.InlineKeyboardButton("💥 AoE", callback_data=f"aoe_attack_enemy|{enemy_type}|{enemy_id}"),
            types.InlineKeyboardButton("🌟 Speciale AoE", callback_data=f"special_aoe_attack_enemy|{enemy_type}|{enemy_id}")
        )
    
    # Nitro and TNT buttons (only for "next mobs")
    if can_use_items:
        markup.add(
            types.InlineKeyboardButton("🧨 Nitro", callback_data=f"use_item_mob|Nitro|{enemy_id}"),
            types.InlineKeyboardButton("💣 TNT", callback_data=f"use_item_mob|TNT|{enemy_id}")
        )
    
    # Always show Flee button (requested by user)
    markup.add(types.InlineKeyboardButton("🏃 Fuggi", callback_data=f"flee_enemy|{enemy_type}|{enemy_id}"))
        
    return markup
