import telebot
from telebot import types
import time
import datetime
import random
import os

from services.user_service import UserService
from services.pve_service import PvEService
from services.item_service import ItemService
from services.drop_service import DropService
from utils.markup_utils import get_combat_markup, get_mention_markdown

# Global lock for mob display to prevent race conditions
from threading import Lock
_mob_display_locks = {}
_global_lock = Lock()

def get_mob_display_lock(mob_id):
    with _global_lock:
        if mob_id not in _mob_display_locks:
            _mob_display_locks[mob_id] = Lock()
        return _mob_display_locks[mob_id]

class CombatHandler:
    def __init__(self, bot):
        self.bot = bot
        self.user_service = UserService()
        self.pve_service = PvEService()
        self.item_service = ItemService()
        self.drop_service = DropService()

    def send_combat_message(self, chat_id, text, image_path, markup, mob_id, old_message_id=None, is_death=False):
        """Send or update a combat message with locking to prevent visual glitches"""
        # Acquire lock for this mob to prevent race conditions (duplicate messages)
        lock = get_mob_display_lock(mob_id)
        with lock:
            # ANTI-SPAM: Automatically fetch old message ID from DB if not provided
            # Always re-fetch inside lock to get the latest state from other threads
            mob = self.pve_service.get_mob_details(mob_id)
            
            # If we didn't have an old_message_id, or we want to be sure satisfy race condition:
            # It's safer to rely on DB state inside the lock (unless we passed an explicit ID we know is valid)
            current_db_msg_id = mob.get('last_message_id') if mob else None
            
            # Determine which ID to delete: explicit arg or DB value
            id_to_delete = old_message_id if old_message_id else current_db_msg_id
            
            # If DB has a DIFFERENT ID than what was passed, prefer DB authority
            if current_db_msg_id:
                id_to_delete = current_db_msg_id

            if is_death:
                # Check if someone else already sent the death message for this mob
                if current_db_msg_id == -999:
                    print(f"[DEBUG] Skipping duplicate death message for mob {mob_id}")
                    return None
                
                # Immediately mark as "death in progress/processed" to block other threads
                self.pve_service.update_mob_message_id(mob_id, -999)

            sent_msg = None
            
            # Try to DELETE old message first (cleaner than editing sometimes, especially if image changes)
            if id_to_delete and id_to_delete > 0:
                try:
                    self.bot.delete_message(chat_id, id_to_delete)
                except Exception as e:
                    # Message might not exist or be too old
                    print(f"[DEBUG] verify_combat_message: failed to delete {id_to_delete}: {e}")

            # SEND new message
            try:
                if image_path and os.path.exists(image_path):
                    with open(image_path, 'rb') as photo:
                        sent_msg = self.bot.send_photo(chat_id, photo, caption=text, reply_markup=markup, parse_mode='markdown')
                else:
                    sent_msg = self.bot.send_message(chat_id, text, reply_markup=markup, parse_mode='markdown')
                
                # Update DB with new message ID (unless dead)
                if sent_msg and not is_death:
                    self.pve_service.update_mob_message_id(mob_id, sent_msg.message_id)
                    
            except Exception as e:
                print(f"[ERROR] send_combat_message failed: {e}")
                # Fallback: try sending text only if photo failed
                try:
                    sent_msg = self.bot.send_message(chat_id, text, reply_markup=markup, parse_mode='markdown')
                except:
                    pass

            return sent_msg

    def handle_spawn_command(self, message):
        """Handle /spawn [mob_name]"""
        utente = self.user_service.get_user(message.from_user.id)
        if not self.user_service.is_admin(utente):
            return

        parts = message.text.split(' ', 1)
        mob_name = parts[1] if len(parts) > 1 else None
        
        success, msg, mob_id = self.pve_service.spawn_specific_mob(mob_name, chat_id=message.chat.id)
        
        if success:
            mob = self.pve_service.get_current_mob_status(mob_id)
            if mob:
                markup = get_combat_markup("mob", mob_id, message.chat.id)
                
                msg_text = f"⚠️ Un {mob['name']} selvatico è apparso!\n📊 Lv. {mob.get('level', 1)} | ⚡ Vel: {mob.get('speed', 30)} | 🛡️ Res: {mob.get('resistance', 0)}%\n❤️ Salute: {mob['health']}/{mob['max_health']} HP\n⚔️ Danno: {mob['attack']}\n\nSconfiggilo per ottenere ricompense!"
                
                # Send with image if available
                sent_msg = self.send_combat_message(message.chat.id, msg_text, mob.get('image'), markup, mob_id)
                
                # Immediate attack
                attack_events = self.pve_service.mob_random_attack(specific_mob_id=mob_id, chat_id=message.chat.id)
                if attack_events:
                    for event in attack_events:
                        msg = event['message']
                        image_path = event['image']
                        old_msg_id = sent_msg.message_id if sent_msg else event.get('last_message_id')
                        
                        self.send_combat_message(message.chat.id, msg, image_path, markup, mob_id, old_msg_id)
        else:
            self.bot.reply_to(message, f"❌ {msg}")

    def handle_enemies_command(self, message):
        """Handle /enemies"""
        mobs = self.pve_service.get_active_mobs(message.chat.id)
        
        if not mobs:
            self.bot.reply_to(message, "🧟 Nessun nemico attivo al momento. Tutto tranquillo... per ora.")
            return
            
        msg = "🧟 **NEMICI ATTIVI** 🧟\n\n"
        
        for mob in mobs:
            status = "👑 **BOSS** " if mob.is_boss else ""
            if mob.difficulty_tier and mob.difficulty_tier >= 4: status += "💀 "
            
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
        
        self.bot.reply_to(message, msg, reply_markup=markup, parse_mode='markdown')

    def handle_taunt_command(self, message):
        """Handle /taunt"""
        utente = self.user_service.get_user(message.from_user.id)
        
        if utente.allocated_resistance < 10:
            self.bot.reply_to(message, "❌ Non sei abbastanza resistente per provocare il nemico!\nDevi avere almeno 10 punti in Resistenza.")
            return
            
        mobs = self.pve_service.get_active_mobs(message.chat.id)
        if not mobs:
            self.bot.reply_to(message, "Non ci sono nemici da provocare.")
            return
            
        target_mob = mobs[0]
        for m in mobs:
            if m.is_boss:
                target_mob = m
                break
        
        self.bot.reply_to(message, msg)

    def handle_shield_command(self, message):
        """Cast a shield (Tank ability)"""
        utente = self.user_service.get_user(message.from_user.id)
        
        # Requirement: Allocated Resistance >= 10
        if utente.allocated_resistance < 10:
            self.bot.reply_to(message, "❌ Non sei abbastanza resistente per usare lo scudo!\nDevi avere almeno 10 punti in Resistenza.")
            return
            
        # Cooldown check (30 minutes)
        now = datetime.datetime.now()
        if utente.last_shield_cast:
            diff = now - utente.last_shield_cast
            if diff.total_seconds() < 1800: # 30 mins
                remaining = int((1800 - diff.total_seconds()) / 60)
                self.bot.reply_to(message, f"⏳ Abilità in ricarica! Riprova tra {remaining} minuti.")
                return
                
        # Calculate Shield Amount (20% of Max HP)
        shield_amount = int(utente.max_health * 0.2)
        
        self.user_service.cast_shield(utente, shield_amount)
        
        self.bot.reply_to(message, f"🛡️ **Scudo Attivato!**\nHai guadagnato uno scudo di {shield_amount} HP per 10 minuti.\nLa tua resistenza è aumentata del 25%!")

    def handle_aoe_command(self, message, is_special=False):
        """Perform an Area of Effect attack"""
        utente = self.user_service.get_user(message.from_user.id)
        
        # Cooldown check (e.g. 5 minutes for AOE)
        now = datetime.datetime.now()
        # Note: 'last_aoe_attack' might need to be added to User model if not present,
        # or managed via pve_service. For now assuming it's on user or we check via service.
        # But looking at main.py logic (if it was there), let's replicate or improve.
        # Use pve_service to handle logic + cooldowns.
        
        damage = utente.attack_power # Base damage
        if is_special:
            damage *= 2 # Placeholder for special AoE
            
        success, msg, extra_data, attack_events = self.pve_service.attack_aoe(utente, damage, chat_id=message.chat.id)
        
        self.bot.reply_to(message, msg)
        
        if attack_events:
            for event in attack_events:
                 # Process counter-attacks
                 msg = event['message']
                 image_path = event['image']
                 mob_id = event['mob_id']
                 old_msg_id = event.get('last_message_id')
                 
                 self.send_combat_message(message.chat.id, msg, image_path, markup, mob_id, old_msg_id)

    def handle_combat_callback(self, call):
        """Dispatcher for all combat callbacks"""
        action = call.data
        user_id = call.from_user.id
        chat_id = call.message.chat.id
        bot = self.bot
        
        # --- ATTACK HANDLERS ---
        if action == "attack_mob" or action.startswith("attack_enemy"):
            # Format: attack_enemy|type|id OR attack_mob (legacy)
            target_id = None
            if "|" in action:
                try:
                    target_id = int(action.split("|")[2])
                except (IndexError, ValueError):
                    pass
            
            utente = self.user_service.get_user(user_id)
            damage = random.randint(10, 30) + utente.base_damage
            
            # Luck boost
            if utente.luck_boost > 0:
                 damage *= 2
                 self.user_service.update_user(user_id, {'luck_boost': 0})
            
            # Attack specific mob or any
            if target_id:
                success, msg, extra_data = self.pve_service.attack_mob(utente, damage, mob_id=target_id, chat_id=chat_id)
            else:
                success, msg, extra_data = self.pve_service.attack_mob(utente, damage, chat_id=chat_id)
            
            # Extract mob_id from extra_data
            mob_id = extra_data.get('mob_id') if extra_data else None
            
            if success:
                try:
                    self.bot.answer_callback_query(call.id, "⚔️ Attacco effettuato!")
                except:
                    pass
                
                # Get updated mob status
                mob_data = self.pve_service.get_mob_details(mob_id)
                
                # Rebuild message
                markup = None
                if mob_data and mob_data['health'] > 0:
                    markup = get_combat_markup("mob", mob_id, chat_id)
                
                mention = get_mention_markdown(utente.id_telegram, utente.username if utente.username else utente.nome)
                full_msg = f"{mention}\n{msg}"
                
                # Update combat message
                self.send_combat_message(chat_id, full_msg, None, markup, mob_id, mob_data.get('last_message_id') if mob_data else None)
                
                # Handle death manually if PVE service didn't return is_dead in a way we caught?
                # PVE service returns success=True if hit.
                # If mob died, pve_service handles drops and returns "Hai sconfitto..."
                
            else:
                self.bot.answer_callback_query(call.id, msg, show_alert=True)
            return True

        # --- SPECIAL ATTACK ---
        elif action == "special_attack_mob" or action.startswith("special_attack_enemy"):
            target_id = None
            if "|" in action:
                try:
                    target_id = int(action.split("|")[2])
                except:
                    pass
            
            utente = self.user_service.get_user(user_id)
            
            # Use separate method for specific target if needed, or pass ID to use_special_attack
            # pve_service.use_special_attack currently takes chat_id. Does it take mob_id?
            # Let's assume it attacks 'current' or 'any'. We should update PVE service later if needed.
            # For now, replicate main.py logic which calls use_special_attack(utente, chat_id=...)
            
            # TODO: Update pve_service to support target_id in special attack
            success, msg, extra_data, attack_events = self.pve_service.use_special_attack(utente, chat_id=chat_id)
            
            if success:
                self.bot.answer_callback_query(call.id, "✨ Attacco Speciale!")
                
                # Logic to update message similar to attack...
                # Requires knowing WHICH mob was hit.
                # extra_data might contain 'mob_id'
                mob_id = extra_data.get('mob_id') if extra_data else None
                
                if mob_id:
                     mob_data = self.pve_service.get_mob_details(mob_id)
                     markup = get_combat_markup("mob", mob_id, chat_id) if mob_data and mob_data['health'] > 0 else None
                     
                     mention = get_mention_markdown(utente.id_telegram, utente.username if utente.username else utente.nome)
                     full_msg = f"{mention}\n{msg}"
                     
                     self.send_combat_message(chat_id, full_msg, None, markup, mob_id, mob_data.get('last_message_id') if mob_data else None)
                else:
                     self.bot.send_message(chat_id, msg)
                
                # Handle counter-attacks
                if attack_events:
                    self._process_attack_events(chat_id, attack_events)
            else:
                self.bot.answer_callback_query(call.id, msg, show_alert=True)
            return True

        # --- DEFEND ---
        elif action.startswith("defend_mob"):
            utente = self.user_service.get_user(user_id)
            success, msg, mob_info = self.pve_service.defend(utente, chat_id=chat_id)
            
            if success:
                self.bot.answer_callback_query(call.id, "🛡️ Difesa!")
                
                mention = get_mention_markdown(utente.id_telegram, utente.username if utente.username else utente.nome)
                full_msg = f"{mention}\n{msg}"
                
                mob_id = mob_info.get('mob_id')
                old_msg_id = mob_info.get('last_message_id')
                
                if mob_id:
                    markup = get_combat_markup("mob", mob_id, chat_id)
                    self.send_combat_message(chat_id, full_msg, None, markup, mob_id, old_msg_id)
                else:
                    self.bot.send_message(chat_id, full_msg)
            else:
                self.bot.answer_callback_query(call.id, msg, show_alert=True)
            return True

        # --- FLEE ---
        elif action.startswith("flee_enemy"):
             # Format: flee_enemy|type|id
             parts = action.split("|")
             if len(parts) < 3:
                 self.bot.answer_callback_query(call.id, "Dati non validi.", show_alert=True)
                 return True

             enemy_id = int(parts[2])
             utente = self.user_service.get_user(user_id)
             
             if utente.resting_since:
                 self.bot.answer_callback_query(call.id, "❌ Non puoi fuggire mentre riposi!", show_alert=True)
                 return True

             success, msg = self.pve_service.flee_mob(utente, enemy_id)
             
             if success:
                 self.bot.answer_callback_query(call.id, "🏃 Fuga riuscita!")
                 
                 mention = get_mention_markdown(utente.id_telegram, utente.username if utente.username else utente.nome)
                 full_msg = f"{mention}\n{msg}"
                 
                 # Check if mob is dead/despawned
                 mob = self.pve_service.get_mob_details(enemy_id)
                 is_dead = True
                 if mob and mob['health'] > 0:
                     is_dead = False
                 
                 if is_dead:
                     # Mob gone
                     if call.message.content_type == 'photo':
                         self.bot.edit_message_caption(chat_id=chat_id, message_id=call.message.message_id, caption=full_msg, reply_markup=None, parse_mode='markdown')
                     else:
                         self.bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=full_msg, reply_markup=None, parse_mode='markdown')
                 else:
                     # Mob still there (just user fled)
                     self.bot.send_message(chat_id, full_msg, parse_mode='markdown')
             else:
                 self.bot.answer_callback_query(call.id, msg, show_alert=True)
                 # self.bot.send_message(chat_id, f"Running refused: {msg}", parse_mode='markdown') # Optional spam
             return True

        # --- SCAN ---
        elif action.startswith("scan_mob"):
             # Format: scan_mob|id
             parts = action.split("|")
             mob_id = int(parts[1]) if len(parts) > 1 else None
             
             if mob_id:
                 # Get mob data using status method (returns dict with CD)
                 mob = self.pve_service.get_mob_status_by_id(mob_id)
                 if mob:
                     # Get user for player CD calculation
                     user = self.user_service.get_user(user_id)
                     
                     # Basic stats
                     msg = f"🔍 Analisi {mob['name']}\n"
                     msg += f"❤️ HP: {mob['health']}/{mob['max_health']}\n"
                     msg += f"⚔️ Atk: {mob['attack']}\n"
                     msg += f"🛡️ Res: {mob.get('resistance', 0)}%\n"
                     msg += f"⚡ Spd: {mob['speed']}\n"
                     msg += f"🔥 Tier: {mob.get('level', 1)}\n"
                     
                     # Player CD (calculate from user's last_attack_time)
                     if user:
                         user_speed = getattr(user, 'speed', 0) or 0
                         player_cd_total = 60 / (1 + user_speed * 0.05)
                         
                         last_attack = getattr(user, 'last_attack_time', None)
                         if last_attack:
                             from datetime import datetime
                             elapsed = (datetime.now() - last_attack).total_seconds()
                             player_cd_remaining = max(0, player_cd_total - elapsed)
                             if player_cd_remaining > 0:
                                 msg += f"\n⏰ Tu: {player_cd_remaining:.1f}s"
                             else:
                                 msg += f"\n⏰ Tu: Pronto!"
                         else:
                             msg += f"\n⏰ Tu: Pronto!"
                     
                     # Mob CD (from get_mob_status_by_id)
                     mob_cd_remaining = mob.get('next_attack_in', 0)
                     if mob_cd_remaining > 0:
                         msg += f"\n🔴 Mob: {mob_cd_remaining:.1f}s"
                     else:
                         msg += f"\n🟢 Mob: Pronto!"
                     
                     # Calculate potential EXP reward
                     mob_level = mob.get('level', 1)
                     difficulty = mob_level  # Using level as difficulty approximation
                     is_boss = mob.get('is_boss', False)
                     
                     if is_boss:
                         # Boss reward (fixed)
                         est_exp = 10000
                         est_wumpa = 1000
                     else:
                         # Regular mob reward (formula from reward_service.py line 71-72)
                         difficulty_multiplier = difficulty ** 1.8
                         est_exp = int((mob_level * 5) * difficulty_multiplier)
                         # Wumpa formula from line 88 (approximated for 100% contribution)
                         est_wumpa = int(100 * 0.05 * difficulty)
                     
                     msg += f"\n\n💎 Ricompense (100%)"
                     msg += f"\n✨ EXP: ~{est_exp}"
                     msg += f"\n🍎 Wumpa: ~{est_wumpa}"
                     
                     self.bot.answer_callback_query(call.id, msg, show_alert=True)
                 else:
                     self.bot.answer_callback_query(call.id, "❌ Mob non più attivo.", show_alert=True)
             return True

        # --- AOE CALLBACKS ---
        elif action.startswith("aoe_attack_enemy") or action.startswith("special_aoe_attack_enemy"):
             # Format: aoe_attack_enemy|type|id
             # We ignore type/id since AoE hits all.
             is_special = "special" in action
             
             utente = self.user_service.get_user(user_id)
             damage = utente.attack_power
             if is_special:
                 damage *= 2
                 
             # Check cooldowns logic if needed (handled in service returns?)
             success, msg, extra_data, attack_events = self.pve_service.attack_aoe(utente, damage, chat_id=chat_id)
             
             if success:
                 self.bot.answer_callback_query(call.id, "💥 AoE effettuato!")
                 self.bot.send_message(chat_id, msg)
                 
                 if attack_events:
                     self._process_attack_events(chat_id, attack_events)
                     
                 # Refresh surviving mobs
                 if extra_data and 'mob_ids' in extra_data:
                     # We should re-display them or update messages.
                     # For now, let's just leave them. The attack events handle counter attacks.
                     pass
             else:
                 self.bot.answer_callback_query(call.id, msg, show_alert=True)
             return True

        return False

    def _process_attack_events(self, chat_id, attack_events):
        """Helper to process counter-attacks"""
        for event in attack_events:
            msg = event['message']
            image_path = event['image']
            mob_id = event['mob_id']
            old_msg_id = event.get('last_message_id')
            
            markup = get_combat_markup("mob", mob_id, chat_id)
            self.send_combat_message(chat_id, msg, image_path, markup, mob_id, old_msg_id)



