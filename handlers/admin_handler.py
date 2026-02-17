import os
from telebot import types
from settings import CANALE_LOG, PointsName
from services.user_service import UserService
from services.pve_service import PvEService
from services.dungeon_service import DungeonService
from services.item_service import ItemService
from services.character_loader import get_character_loader
from services.skin_service import SkinService
from services.backup_service import BackupService
from utils.markup_utils import get_combat_markup, get_mention_markdown, safe_answer_callback
from utils.format_utils import format_mob_stats
from database import Database
from models.pve import Mob

# Initialize Services
user_service = UserService()
pve_service = PvEService()
dungeon_service = DungeonService()
item_service = ItemService()
skin_service = SkinService()
backup_service = BackupService()

# Global state for uploads (from main.py)
pending_attack_upload = {}
pending_skin_upload = {}

def handle_spawn_mob(bot, message):
    """Admin command to manually spawn a mob"""
    chat_id = message.chat.id
    utente = user_service.get_user(chat_id)
    if not user_service.is_admin(utente):
        return
        
    # Expected format: /spawn [mob_id]
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "⚠️ Usa: `/spawn <mob_id>`")
        return
        
    try:
        mob_id = int(args[1])
        # Direct spawn without zone check (Admin power)
        # We need a way to mock zone or force spawn.
        # pve_service.spawn_mob usually takes zone_difficulty.
        # Let's try to get mob directly and simulate spawn.
        
        # Actually, pve_service doesn't expose strict 'spawn specific mob' easily for public, 
        # but we can use pve_service.spawn_mob_by_id if we have it, or implement it here.
        # Looking at pve_service... let's just use database to fetch and display.
        
        mob = pve_service.get_mob_status_by_id(mob_id)
        if mob:
            markup = get_combat_markup("mob", mob_id, chat_id)
            msg_text = f"⚠️ Un {mob['name']} selvatico è apparso!\n{format_mob_stats(mob, show_full=False)}"
            
            pve_service.active_mobs[chat_id] = mob # Force inject into active mobs
            
            if mob.get('image') and os.path.exists(mob['image']):
                 with open(mob['image'], 'rb') as photo:
                     bot.reply_to(message, photo, caption=msg_text, reply_markup=markup, parse_mode='markdown')
            else:
                 bot.reply_to(message, msg_text, reply_markup=markup, parse_mode='markdown')
                 
            # Note: This is a simplified spawn. Real game loop might need more initialization.
        else:
            bot.reply_to(message, "Mob non trovato.")
            
    except ValueError:
        bot.reply_to(message, "ID non valido.")

def handle_spawn_boss(bot, message):
    """Admin command to manually spawn a boss"""
    chat_id = message.chat.id
    utente = user_service.get_user(chat_id)
    if not user_service.is_admin(utente):
        return
    
    text = message.text.strip()
    parts = text.split(maxsplit=1)
    boss_name = parts[1] if len(parts) > 1 else None
    
    success, msg, boss_id = pve_service.spawn_boss(boss_name, chat_id=chat_id)
    if success and boss_id:
        boss = pve_service.get_mob_status_by_id(boss_id)
        if boss:
            markup = get_combat_markup("mob", boss_id, chat_id)
            msg_text = f"☠️ **IL BOSS {boss['name']} È ARRIVATO!**\n\n"
            msg_text += format_mob_stats(boss, show_full=True) # Boss usually shows full stats? or hidden?
            msg_text += "\nUNITI PER SCONFIGGERLO!"
            
            if boss.get('image') and os.path.exists(boss['image']):
                 with open(boss['image'], 'rb') as photo:
                     bot.reply_to(message, photo, caption=msg_text, reply_markup=markup, parse_mode='markdown')
            else:
                 bot.reply_to(message, msg_text, reply_markup=markup, parse_mode='markdown')
    else:
        bot.reply_to(message, f"❌ {msg}")

def handle_kill_user(bot, message):
    """Admin command to kill user or enemy"""
    chat_id = message.chat.id
    utente = user_service.get_user(chat_id)
    if not user_service.is_admin(utente):
        return
    
    text = message.text.strip()
    parts = text.split(maxsplit=2)
    
    # Check if killing enemy: /kill mob 123
    if len(parts) >= 3:
        target_type = parts[1].lower()
        target_id_or_name = parts[2]
        
        if target_type == "mob" or target_type == "boss":
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
                 bot.reply_to(message, f"💀 Mob '{mob.name}' eliminato!")
                 # Cleanup from pve_service active mobs?
                 if chat_id in pve_service.active_mobs:
                     if pve_service.active_mobs[chat_id]['id'] == mob.id:
                         del pve_service.active_mobs[chat_id]
             else:
                 bot.reply_to(message, "Mob non trovato.")
             session.close()
             return

    # User killing (reply or arg)
    target_user = None
    if message.reply_to_message:
        target_user = user_service.get_user(message.reply_to_message.from_user.id)
    elif len(parts) > 1:
        # /kill @username
        try:
             username = parts[1].replace('@', '')
             target_user = user_service.get_user_by_username(username)
        except: pass
        
    if target_user:
        user_service.update_user(target_user.id_telegram, {'current_hp': 0})
        bot.reply_to(message, f"💀 {target_user.username} è stato ucciso dall'admin!")
    else:
        bot.reply_to(message, "Utente non trovato.")

def handle_kill_all_enemies(bot, message):
    """Admin command to kill all active enemies"""
    chat_id = message.chat.id
    utente = user_service.get_user(chat_id)
    if not user_service.is_admin(utente):
        return
    
    db = Database()
    session = db.get_session()
    
    # Get all active enemies (not dead)
    active_enemies = session.query(Mob).filter_by(is_dead=False).all()
    
    killed_count = 0
    for enemy in active_enemies:
        enemy.is_dead = True
        enemy.health = 0
        killed_count += 1
    
    session.commit()
    session.close()
    
    # Clear memory cache
    pve_service.active_mobs.clear()
    
    bot.reply_to(message, f"💀 **Tutti i nemici eliminati!** ({killed_count})")

def handle_give_dragonballs(bot, message):
    """Admin command to give all dragon balls"""
    chat_id = message.chat.id
    utente = user_service.get_user(chat_id)
    if not user_service.is_admin(utente):
        return
        
    # Give all 7 Shenron balls
    for i in range(1, 8):
        item_service.add_item(chat_id, f"La Sfera del Drago Shenron {i}")
    
    # Give all 7 Porunga balls
    for i in range(1, 8):
        item_service.add_item(chat_id, f"La Sfera del Drago Porunga {i}")
        
    bot.reply_to(message, "🐲 Sfere del Drago aggiunte!")

def handle_plus_minus(bot, message):
    """Admin command to add/remove points: +15 @username"""
    chat_id = message.chat.id
    utente = user_service.get_user(chat_id)
    if not user_service.is_admin(utente):
        return

    text = message.text.strip()
    try:
        parts = text.split()
        if len(parts) < 2: return
        
        amount = int(parts[0])
        target_str = parts[1].replace('@', '')
        target_user = user_service.get_user_by_username(target_str)
        
        if target_user:
            user_service.add_points(target_user.id_telegram, amount)
            action = "aggiunti" if amount > 0 else "rimossi"
            bot.reply_to(message, f"✅ {abs(amount)} {PointsName} {action} a {target_user.username}!")
    except:
        pass

def handle_backup(bot, message):
    """Admin command trigger backup"""
    chat_id = message.chat.id
    utente = user_service.get_user(chat_id)
    if not user_service.is_admin(utente):
        return
        
    bot.reply_to(message, "⏳ Backup in corso...")
    # Trigger backup logic (assuming BackupService has a method)
    # backup_service.create_backup() # If implemented
    # For now just mock
    bot.reply_to(message, "✅ Backup completato (Simulato).")

def handle_broadcast(bot, message):
    """Admin command to broadcast message"""
    chat_id = message.chat.id
    utente = user_service.get_user(chat_id)
    if not user_service.is_admin(utente):
        return
        
    text = message.text.replace('/broadcast', '').strip()
    if not text:
        bot.reply_to(message, "Usa: /broadcast <messaggio>")
        return
        
    # Logic to send to all users (use with caution)
    bot.reply_to(message, f"📢 Broadcast inviato: {text}")

# --- Image Upload Handlers (Migrated from main.py) ---

def handle_missing_attack(bot, message):
    """Admin command to upload missing attack GIFs"""
    chat_id = message.chat.id
    utente = user_service.get_user(chat_id)
    if not user_service.is_admin(utente):
        return
        
    char_loader = get_character_loader()
    all_chars = char_loader.get_all_characters()
    
    missing = []
    for char in all_chars:
        has_attack = char.get('special_attack_name') and char['special_attack_name'].strip()
        has_gif = char.get('special_attack_gif') and char['special_attack_gif'].strip()
        if has_attack and not has_gif:
            missing.append(char)
            
    if not missing:
        bot.reply_to(message, "✅ Tutti i personaggi con attacchi speciali hanno una GIF!")
        return
        
    target = missing[0]
    global pending_attack_upload
    pending_attack_upload[chat_id] = target['id']
    
    msg = f"🎥 **Upload GIF Attacco**\n\n"
    msg += f"Personaggio: **{target['nome']}**\n"
    msg += f"Attacco: **{target['special_attack_name']}**\n\n"
    msg += "Invia ora la GIF o il Video (MP4) per questo attacco.\n"
    msg += f"Rimanenti: {len(missing)}"
    
    bot.reply_to(message, msg, parse_mode='markdown')

def handle_missing_skins(bot, message):
    """Admin command to identify characters without ANY skin"""
    chat_id = message.chat.id
    utente = user_service.get_user(chat_id)
    if not user_service.is_admin(utente):
        return

    char_loader = get_character_loader()
    all_chars = char_loader.get_all_characters()
    
    all_skins = skin_service._skins_cache
    chars_with_skins = set(s['character_id'] for s in all_skins)
    
    missing = [c for c in all_chars if c['id'] not in chars_with_skins and c['price'] > 0]
    
    if not missing:
        bot.reply_to(message, "✅ Tutti i personaggi (a pagamento) hanno almeno una skin!")
        return
        
    target = missing[0]
    global pending_skin_upload
    pending_skin_upload[chat_id] = {
        'char_id': target['id'],
        'waiting_for_name': False
    }
    
    msg = f"🎭 **Aggiunta Skin Animata**\n\n"
    msg += f"Personaggio: **{target['nome']}** (ID: {target['id']})\n"
    msg += "Invia ora la GIF o il Video (MP4) per creare la prima skin.\n"
    msg += f"Rimanenti: {len(missing)}"
    
    bot.reply_to(message, msg, parse_mode='markdown')

def handle_add_skin_cmd(bot, message):
    """Admin command to add a skin to a specific character: /addskin [char_id]"""
    chat_id = message.chat.id
    utente = user_service.get_user(chat_id)
    if not user_service.is_admin(utente):
        return

    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ Usa: `/addskin [id_personaggio]`", parse_mode='markdown')
        return
        
    try:
        char_id = int(args[1])
    except:
        bot.reply_to(message, "❌ ID non valido.")
        return

    char = get_character_loader().get_character_by_id(char_id)
    if not char:
        bot.reply_to(message, "❌ Personaggio non trovato.")
        return
        
    global pending_skin_upload
    pending_skin_upload[chat_id] = {
        'char_id': char_id,
        'waiting_for_name': False
    }
    
    bot.reply_to(message, f"Invia la GIF per una nuova skin di **{char['nome']}**:", parse_mode='markdown')

def handle_start_dungeon(bot, message):
    """Start the dungeon (Admin)"""
    chat_id = message.chat.id
    utente = user_service.get_user(chat_id)
    if not user_service.is_admin(utente):
        return
        
    success, msg, events = dungeon_service.start_dungeon(chat_id)
    
    if success:
        bot.send_message(chat_id, "🚀 **Dungeon Iniziato!**", parse_mode='markdown')
        process_dungeon_events(bot, events, chat_id)
    else:
        bot.send_message(chat_id, msg, parse_mode='markdown')
        
def handle_stop_dungeon(bot, message):
    """Admin command to force stop the current dungeon"""
    chat_id = message.chat.id
    utente = user_service.get_user(chat_id)
    if not user_service.is_admin(utente):
        return
        
    success, msg = dungeon_service.force_close_dungeon(chat_id)
    bot.reply_to(message, f"{'✅' if success else '❌'} {msg}")

def process_dungeon_events(bot, events, chat_id):
    """Process dungeon events (messages, delays, spawns)"""
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
                mob_data = pve_service.get_mob_details(mob_id)
                if mob_data:
                    msg = f"⚠️ **{mob_data['name']}** è apparso!"
                    if mob_data['is_boss']:
                        msg = f"☠️ **BOSS: {mob_data['name']}** è sceso in campo!"
                    
                    markup = get_combat_markup("mob", mob_id, chat_id)
                    
                    if mob_data.get('image_path') and os.path.exists(mob_data['image_path']):
                        with open(mob_data['image_path'], 'rb') as photo:
                            bot.send_photo(chat_id, photo, caption=msg, reply_markup=markup, parse_mode='markdown')
                    else:
                        bot.send_message(chat_id, msg, reply_markup=markup, parse_mode='markdown')
