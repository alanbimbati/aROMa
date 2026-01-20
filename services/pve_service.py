from database import Database
from sqlalchemy import desc
from models.pve import Mob
from models.combat import CombatParticipation
from models.system import Livello
from models.user import Utente
from services.user_service import UserService
from services.item_service import ItemService
from services.event_dispatcher import EventDispatcher
from services.damage_calculator import DamageCalculator
from services.status_effects import StatusEffect
import datetime
import random
import csv
import os
import json
from settings import PointsName, GRUPPO_AROMA

class PvEService:
    def __init__(self):
        self.db = Database()
        self.user_service = UserService()
        self.item_service = ItemService()
        from services.battle_service import BattleService
        self.battle_service = BattleService()
        
        # NEW: Enhanced combat services
        self.event_dispatcher = EventDispatcher()
        self.damage_calculator = DamageCalculator()
        
        # NEW: Achievement tracker
        from services.achievement_tracker import AchievementTracker
        from services.mob_ai import MobAI
        from services.boss_phase_manager import BossPhaseManager
        from services.season_manager import SeasonManager
        from services.season_manager import SeasonManager
        from services.guild_service import GuildService
        self.achievement_tracker = AchievementTracker()
        self.mob_ai = MobAI()
        self.boss_phase_manager = BossPhaseManager()
        self.season_manager = SeasonManager()
        self.guild_service = GuildService()
        
        self.mob_data = self.load_mob_data()
        self.boss_data = self.load_boss_data()
        self.recent_mobs = [] # Track last 10 spawned mobs to avoid repetition

    def load_mob_data(self):
        """Load mob data from CSV"""
        mobs = []
        try:
            with open('data/mobs.csv', 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    mobs.append(row)
        except Exception as e:
            print(f"Error loading mobs: {e}")
        return mobs
    
    def load_boss_data(self):
        """Load boss data from CSV"""
        bosses = []
        try:
            with open('data/bosses.csv', 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    bosses.append(row)
        except Exception as e:
            print(f"Error loading bosses: {e}")
        return bosses

    def use_special_attack(self, user):
        """
        Execute special attack for the user.
        Checks mana, calculates damage, and calls attack_mob.
        """
        # Get character
        from services.character_loader import get_character_loader
        char_loader = get_character_loader()
        character = char_loader.get_character_by_id(user.livello_selezionato)
        
        if not character:
            return False, "Personaggio non trovato."
            
        # Check mana
        mana_cost = character.get('special_attack_mana_cost', 50)
        multiplier = self.guild_service.get_mana_cost_multiplier(user.id_telegram)
        mana_cost = int(mana_cost * multiplier)
        
        if user.mana < mana_cost:
            return False, f"Mana insufficiente! Serve: {mana_cost}, hai: {user.mana}"
            
        # Deduct mana
        self.user_service.update_user(user.id_telegram, {'mana': user.mana - mana_cost})
        
        # Calculate damage (base + special bonus)
        # We let attack_mob handle the base damage + stats
        # But we need to pass the special damage bonus
        special_damage = character.get('special_attack_damage', 0)
        
        # Call attack_mob with use_special=True
        # Note: attack_mob will calculate total damage using BattleService
        # We might need to pass the ability or just let BattleService handle it if we pass use_special=True
        # Looking at attack_mob signature: attack_mob(self, user, base_damage=0, use_special=False, ability=None, mob_id=None)
        
        # We'll pass the special damage as base_damage addition or handle it inside
        # Actually, let's pass it as base_damage for now, or rely on BattleService if it knows about special attacks.
        # The current attack_mob implementation takes base_damage.
        
        success, msg = self.attack_mob(user, base_damage=special_damage, use_special=True)
        
        if not success:
            # Refund mana if attack failed (e.g. no mob)
            self.user_service.update_user(user.id_telegram, {'mana': user.mana + mana_cost})
            
        return success, msg




    def spawn_daily_mob(self, chat_id=None):
        """Spawn a random daily mob and immediately attack"""
        # Check if we can spawn (limit check is in spawn_specific_mob)
        success, msg, mob_id = self.spawn_specific_mob(chat_id=chat_id)
        if success and mob_id:
            # Immediate attack
            attack_events = self.mob_random_attack(specific_mob_id=mob_id, chat_id=chat_id)
            return mob_id, attack_events
        # Return None if spawn failed (e.g., too many mobs)
        return None, None

    def _allocate_mob_stats(self, level, difficulty, is_boss=False):
        """
        Allocate stats based on level and difficulty using a point-based system.
        Each level gives 1 point to allocate.
        """
        # Base stats
        base_speed = 20 if is_boss else 10
        base_resistance = 0
        base_hp_bonus = 0
        base_dmg_bonus = 0
        
        # Points to allocate
        points = level
        
        # Stats to distribute points into
        stats = ['hp', 'dmg', 'speed', 'res']
        allocation = {s: 0 for s in stats}
        
        for _ in range(points):
            stat = random.choice(stats)
            allocation[stat] += 1
            
        # Scaling per point
        # HP: +20 per point
        # DMG: +5 per point
        # Speed: +5 per point
        # Res: +5% per point (capped at 50%)
        
        hp_bonus = allocation['hp'] * 20
        dmg_bonus = allocation['dmg'] * 5
        speed = base_speed + (allocation['speed'] * 5)
        resistance = min(50, base_resistance + (allocation['res'] * 5))
            
        return speed, resistance, hp_bonus, dmg_bonus

    def spawn_specific_mob(self, mob_name=None, chat_id=None):
        """Spawn a specific mob by name or a random one if None. Returns (success, msg, mob_id)"""
        session = self.db.get_session()
        
        # Limit: max 10 active mobs total (to prevent spam)
        active_mobs_count = session.query(Mob).filter(Mob.is_dead == False, Mob.is_boss == False, Mob.dungeon_id == None).count()
        if active_mobs_count >= 10:
            session.close()
            return False, f"Ci sono troppi mob attivi! Sconfiggili prima di spawnarne altri.", None
            
        # RESTRICTION: Only spawn in official group
        if chat_id and chat_id != GRUPPO_AROMA:
             session.close()
             return False, "I mob possono apparire solo nel gruppo ufficiale!", None
            
        # Get current season theme
        from models.seasons import Season
        current_season = session.query(Season).filter_by(is_active=True).first()
        theme = current_season.theme.strip().lower() if current_season and current_season.theme else None
        
        mob_data = None
        if mob_name:
            # Find specific mob
            mob_data = next((m for m in self.mob_data if m['nome'].lower() == mob_name.lower()), None)
            if not mob_data:
                session.close()
                return False, f"Mob '{mob_name}' non trovato.", None
        else:
            # Random mob, 70% chance for themed mob if available
            if not self.mob_data:
                session.close()
                return False, "Nessun dato mob caricato.", None
            
            # Filter by theme if available (robust matching)
            themed_mobs = [m for m in self.mob_data if theme and theme in m.get('saga', '').strip().lower()]
            
            # Repetition avoidance: filter out recent mobs if possible
            def get_random_non_recent(pool):
                if not pool: return None
                available = [m for m in pool if m['nome'] not in self.recent_mobs]
                if not available or len(available) < 2: # If too few non-recent, just pick any to ensure randomness
                    return random.choice(pool)
                return random.choice(available)

            if themed_mobs and random.random() < 0.8:
                mob_data = get_random_non_recent(themed_mobs)
            else:
                # Fallback to any mob (30% chance or if no themed mobs)
                mob_data = get_random_non_recent(self.mob_data)
            
        # Update recent mobs list
        if mob_data:
            self.recent_mobs.append(mob_data['nome'])
            if len(self.recent_mobs) > 10:
                self.recent_mobs.pop(0)
            
        # Create Mob
        # Ensure HP is correct
        # Determine level based on difficulty: difficulty * random(1, 5)
        difficulty = int(mob_data.get('difficulty', 1))
        level = difficulty * random.randint(1, 5)
        
        # Allocate dynamic stats
        speed, resistance, hp_bonus, dmg_bonus = self._allocate_mob_stats(level, difficulty, is_boss=False)
        
        # Adjust HP and Damage based on level proportionally
        # HP: base + (level * 15) + hp_bonus
        # Damage: base + (level * 3) + dmg_bonus
        hp = int(mob_data['hp']) + (level * 15) + hp_bonus
        damage = int(mob_data['attack_damage']) + (level * 3) + dmg_bonus
        
        new_mob = Mob(
            name=mob_data['nome'],
            health=hp,
            max_health=hp,
            attack_damage=damage,
            attack_type=mob_data['attack_type'],
            difficulty_tier=int(mob_data.get('difficulty', 1)),
            speed=speed,
            resistance=resistance,
            is_boss=False,  # Normal mobs are not bosses
            chat_id=chat_id,
            last_attack_time=datetime.datetime.now() - datetime.timedelta(hours=1), # Allow immediate attack
            last_message_id=None # Will be updated by main.py
        )
        
        if hasattr(new_mob, 'mob_level'):
            new_mob.mob_level = level
        
        session.add(new_mob)
        session.commit()
        
        # Get ID
        mob_id = new_mob.id
        mob_name = new_mob.name
        
        session.close()
        return True, f"Un {mob_name} (Lv. {level}) è apparso! (Vel: {speed}, Res: {resistance}%)", mob_id

    def spawn_boss(self, boss_name=None, chat_id=None):
        """Spawn a boss (Mob with is_boss=True). Returns (success, msg, mob_id)"""
        session = self.db.get_session()
        
        # Limit: max 3 active bosses total
        active_boss_count = session.query(Mob).filter_by(is_boss=True, is_dead=False).count()
        if active_boss_count >= 3:
            session.close()
            return False, f"Troppi boss attivi ({active_boss_count}/3)!", None
        
        # Get current season theme
        from models.seasons import Season
        current_season = session.query(Season).filter_by(is_active=True).first()
        theme = current_season.theme if current_season else None
        
        boss_data = None
        if boss_name:
            # Find specific boss
            boss_data = next((b for b in self.boss_data if b['nome'].lower() == boss_name.lower()), None)
            if not boss_data:
                session.close()
                return False, f"Boss '{boss_name}' non trovato.", None
        else:
            # Random boss, 70% chance for themed boss if available
            if not self.boss_data:
                session.close()
                return False, "Nessun dato boss caricato.", None
            
            # Filter by theme if available
            themed_bosses = [b for b in self.boss_data if theme and theme in b.get('saga', '').strip().lower()]
            
            if themed_bosses and random.random() < 0.8:
                boss_data = random.choice(themed_bosses)
            else:
                # Fallback to any boss (30% chance or if no themed bosses)
                boss_data = random.choice(self.boss_data)
        
        # Create Mob with is_boss=True
        hp_base = int(boss_data['hp'])
        difficulty = int(boss_data.get('difficulty', 5))
        
        # Boss level: difficulty * random(5, 10) for extra challenge
        level = difficulty * random.randint(5, 10)
        
        # Allocate dynamic stats
        speed, resistance, hp_bonus, dmg_bonus = self._allocate_mob_stats(level, difficulty, is_boss=True)
        
        # Scale HP and Damage
        # HP: base + (level * 50) + hp_bonus
        # Damage: base + (level * 10) + dmg_bonus
        hp = hp_base + (level * 50) + hp_bonus
        damage = int(boss_data['attack_damage']) + (level * 10) + dmg_bonus
        
        new_boss = Mob(
            name=boss_data['nome'],
            health=hp,
            max_health=hp,
            attack_damage=damage,
            attack_type=boss_data['attack_type'],
            difficulty_tier=int(boss_data.get('difficulty', 5)),  # Bosses are high difficulty
            speed=speed,  # Bosses are faster
            resistance=resistance,
            description=boss_data.get('description', ''),
            is_boss=True,
            chat_id=chat_id,
            last_attack_time=datetime.datetime.now() - datetime.timedelta(hours=1), # Allow immediate attack
            # NEW: Advanced mechanics from CSV
            active_abilities=boss_data.get('abilities', '[]'),
            ai_behavior=boss_data.get('ai_behavior', 'aggressive'),
            phase_thresholds=boss_data.get('phase_config', '{}')
        )
        
        if hasattr(new_boss, 'mob_level'):
            new_boss.mob_level = level
        
        session.add(new_boss)
        session.commit()
        boss_id = new_boss.id
        boss_name = new_boss.name
        
        session.close()
        return True, f"Un boss {boss_name} (Lv. {level}) è apparso! (Vel: {speed}, Res: {resistance}%)", boss_id

    def taunt_mob(self, user, mob_id):
        """Taunt a mob to attack the user"""
        session = self.db.get_session()
        try:
            mob = session.query(Mob).filter_by(id=mob_id).first()
            if not mob:
                return False, "Mostro non trovato."
            if mob.is_dead:
                return False, "Il mostro è già morto."
                
            # Set aggro
            mob.aggro_target_id = user.id_telegram
            # Lasts for 5 minutes or until overwritten
            mob.aggro_end_time = datetime.datetime.now() + datetime.timedelta(minutes=5)
            session.commit()
            return True, f"🛡️ **{user.nome}** sta provocando {mob.name}! Il nemico ora attaccherà solo lui!"
        except Exception as e:
            return False, f"Errore durante la provocazione: {e}"
        finally:
            session.close()

    def get_active_mobs(self, chat_id):
        """Get list of active mobs in the chat"""
        session = self.db.get_session()
        try:
            mobs = session.query(Mob).filter_by(chat_id=chat_id, is_dead=False).all()
            # Detach objects from session so they can be used after session closes
            session.expunge_all()
            return mobs
        finally:
            session.close()

    def attack_mob(self, user, base_damage=0, use_special=False, ability=None, mob_id=None, mana_cost=0):
        """Attack current mob using BattleService"""
        session = self.db.get_session()
        
        if mob_id:
            # Attack specific mob by ID
            mob = session.query(Mob).filter_by(id=mob_id).first()
            if not mob:
                session.close()
                return False, "Mostro non trovato.", None
            if mob.is_dead:
                session.close()
                return False, "Questo mostro è già morto!", None
        else:
            # Attack first alive mob
            mob = session.query(Mob).filter_by(is_dead=False).first()
            if not mob:
                session.close()
                return False, "Nessun mostro nei paraggi.", None
        
        # Check fatigue
        if self.user_service.check_fatigue(user):
            session.close()
            return False, "Sei troppo affaticato per combattere! Riposa.", None
            
        # Check Cooldown based on Speed
        user_speed = getattr(user, 'allocated_speed', 0)
        cooldown_seconds = 60 / (1 + user_speed * 0.05)
        
        last_attack = getattr(user, 'last_attack_time', None)
        if last_attack:
            elapsed = (datetime.datetime.now() - last_attack).total_seconds()
            if elapsed < cooldown_seconds:
                remaining = int(cooldown_seconds - elapsed)
                minutes = remaining // 60
                seconds = remaining % 60
                session.close()
                return False, f"⏳ Sei stanco! (CD: {int(cooldown_seconds)}s)\nDevi riposare ancora per {minutes}m {seconds}s.", None
        
        # Deduct Mana (if applicable) - NOW AFTER COOLDOWN CHECK
        if mana_cost > 0:
            if user.mana < mana_cost:
                session.close()
                return False, f"❌ Mana insufficiente! Serve: {mana_cost}", None
            self.user_service.update_user(user.id_telegram, {'mana': user.mana - mana_cost})
        
        # Update last attack time
        self.user_service.update_user(user.id_telegram, {'last_attack_time': datetime.datetime.now()})
        
        # Get user character for stats/type
        from services.character_loader import get_character_loader
        char_loader = get_character_loader()
        character = char_loader.get_character_by_id(user.livello_selezionato)
        
        # Prepare attacker object wrapper for BattleService
        class AttackerWrapper:
            def __init__(self, user, char, base_dmg):
                self.damage_total = base_dmg
                self.elemental_type = char.get('elemental_type', "Normal") if char else "Normal"
                
                # Base crit from char + allocated crit rate
                # Base crit from char + allocated crit rate
                char_crit = char.get('crit_chance', 5) if char else 5
                # Use total crit_chance from user if available, otherwise calculate
                # But wait, we updated stats_service to update user.crit_chance.
                # So user.crit_chance SHOULD contain base + allocated?
                # Actually, user.crit_chance in DB default is 0.
                # If we rely on user.crit_chance, we should make sure it's initialized.
                # Let's use the allocated amount to be safe and additive, 
                # OR trust the total column.
                # Plan said: "Use user.crit_chance (Total) + character.crit_chance"
                
                user_crit = getattr(user, 'crit_chance', 0) or 0
                # If user.crit_chance is just the allocated part (which it seems to be based on stats_service update: current + 1),
                # then we add char_crit.
                # However, if user.crit_chance was intended to be THE total, we should be careful.
                # In stats_service: 'crit_chance': current_crit + 1.
                # So it accumulates.
                
                self.crit_chance = char_crit + user_crit
                
                self.crit_multiplier = char.get('crit_multiplier', 1.5) if char else 1.5
        
        attacker = AttackerWrapper(user, character, base_damage)
        
        # Prepare defender wrapper (Mob)
        class DefenderWrapper:
            def __init__(self, mob):
                self.defense_total = 0 
                self.elemental_type = mob.attack_type 
        
        defender = DefenderWrapper(mob)
        
        # Calculate damage
        combat_result = self.battle_service.calculate_damage(attacker, defender, ability)
        damage = combat_result['damage']
        
        # Apply Mob Resistance
        if hasattr(mob, 'resistance') and mob.resistance > 0:
            reduction = mob.resistance / 100.0
            damage = int(damage * (1 - reduction))
            combat_result['resistance_applied'] = mob.resistance
        
        # Apply damage to mob (no counterattack)
        actual_damage_dealt = max(0, min(damage, mob.health))
        mob.health -= damage
        
        # NEW: Update combat participation with capped damage
        self.update_participation(mob.id, user.id_telegram, actual_damage_dealt, combat_result['is_crit'])
        
        # NEW: Log damage event
        # NEW: Log damage event
        self.event_dispatcher.log_event(
            event_type='damage_dealt', 
            user_id=user.id_telegram, 
            value=damage,
            context={
                'is_crit': combat_result['is_crit'],
                'mob_id': mob.id,
                'mob_name': mob.name,
                'mob_level': getattr(mob, 'mob_level', 1),
                'effectiveness': combat_result.get('effectiveness', 1.0)
            }
        )
        
        # Build message
        msg = ""
        if combat_result['is_crit']:
            msg += "🔥 **Critico!** "
        
        eff = combat_result['effectiveness']
        if eff > 1:
            msg += "⚡ **Super Efficace!** "
        elif eff < 1 and eff > 0:
            msg += "🛡️ **Non molto efficace...** "
        elif eff == 0:
            msg += "🚫 **Nessun effetto!** "
            
        msg += f"⚔️ Hai inflitto {damage} danni ({combat_result['type']}) a {mob.name}!"
        
        if 'resistance_applied' in combat_result:
            msg += f" (Resistenza {combat_result['resistance_applied']}%)"
        
        # Capture data for extra_data before potential session close
        final_mob_id = mob.id
        final_mob_name = mob.name
        final_is_dead = mob.health <= 0
        final_last_msg_id = mob.last_message_id
        final_image_path = self.get_enemy_image_path(mob)

        if mob.health <= 0:
            mob.health = 0
            mob.is_dead = True
            mob.killer_id = user.id_telegram
            msg += f"\n💀 **{mob.name} è stato sconfitto!**\n🎁 Il nemico ha lasciato un bottino da distribuire a tutti i partecipanti!"
            
            # Return delete_message_id instruction
            combat_result['delete_message_id'] = mob.last_message_id
            
            # Capture data for rewards before closing session
            mob_id = mob.id
            mob_name = mob.name
            mob_max_health = mob.max_health
            is_boss = mob.is_boss
            dungeon_id = mob.dungeon_id
            difficulty = mob.difficulty_tier if mob.difficulty_tier else 1
            level = mob.mob_level if hasattr(mob, 'mob_level') and mob.mob_level else 1
            user_id = user.id_telegram
            user_level = user.livello
            
            # NEW: Log mob kill event
            participants = self.get_combat_participants(mob_id)
            solo_kill = len(participants) == 1
            participation = next((p for p in participants if p.user_id == user_id), None)
            
            self.event_dispatcher.log_event(
                event_type='mob_kill', 
                user_id=user_id, 
                value=1,
                context={
                    'mob_name': mob_name,
                    'is_boss': is_boss,
                    'solo_kill': solo_kill,
                    'damage_dealt': participation.damage_dealt if participation else 0
                }
            )
            
            # COMMIT AND CLOSE SESSION BEFORE REWARDS
            session.commit()
            session.close()
            
            # Rewards based on difficulty and level (already captured)
            reward_details = []
            
            # Bosses give much better rewards
            if is_boss:
                reward_details, total_wumpa, total_xp = self.distribute_boss_rewards(mob_id, user, damage)
                msg += f"\n\n🏆 **Ricompense Boss Distribuite!** ({total_wumpa} {PointsName} totali)\n"
            else:
                # Normal mob rewards distributed among participants
                participants = self.get_combat_participants(mob_id)
                total_damage = sum(p.damage_dealt for p in participants)
                
                actual_total_wumpa = 0
                actual_total_xp = 0
                
                rewards_to_distribute = []
                temp_session = self.db.get_session()
                try:
                    for p in participants:
                        share = p.damage_dealt / total_damage if total_damage > 0 else 1/len(participants)
                        wumpa_per_damage = 0.05 * difficulty
                        base_wumpa = int(p.damage_dealt * wumpa_per_damage)
                        if base_wumpa < 1 and p.damage_dealt > 0:
                            base_wumpa = 1
                            
                        mob_hp = mob_max_health if mob_max_health else 30
                        if difficulty >= 4: # Hard
                            base_exp_pool = random.randint(100, 300) * difficulty
                        elif difficulty == 3: # Medium
                            base_exp_pool = random.randint(100, 300) * difficulty
                        elif difficulty <= 2 and mob_hp >= 50: # Easy
                            base_exp_pool = random.randint(100, 300) * difficulty
                        else: # Trash
                            base_exp_pool = random.randint(100, 300) * difficulty
                            
                        base_exp = int(base_exp_pool * share)
                        mob_level = level if level else (difficulty * 5)
                        u_part = temp_session.query(Utente).filter_by(id_telegram=p.user_id).first()
                        user_level = u_part.livello if u_part else 1
                        
                        penalty_factor_xp = 1.0
                        penalty_factor_wumpa = 1.0
                        if user_level > mob_level + 10:
                            penalty_factor_xp = 0.5
                            penalty_factor_wumpa = 0.25
                        
                        p_xp = int(base_exp * penalty_factor_xp)
                        p_wumpa = int(base_wumpa * penalty_factor_wumpa)
                        p_user_check = temp_session.query(Utente).filter_by(id_telegram=p.user_id).first()
                        
                        is_stunned = False
                        has_turbo = False
                        if p_user_check:
                            if p_user_check.active_status_effects:
                                try:
                                    effects = json.loads(p_user_check.active_status_effects)
                                    for effect in effects:
                                        if effect.get('id') == 'stunned': is_stunned = True
                                        elif effect.get('id') == 'turbo': has_turbo = True
                                except: pass
                            if (p_user_check.daily_wumpa_earned or 0) >= 300:
                                p_wumpa = int(p_wumpa * 0.9)
                        
                        if is_stunned:
                            p_xp = 0
                            p_wumpa = 0
                        
                        # Check if user is dead (0 HP)
                        is_dead = False
                        current_hp = p_user_check.current_hp if hasattr(p_user_check, 'current_hp') and p_user_check.current_hp is not None else p_user_check.health
                        if current_hp <= 0:
                            is_dead = True
                            p_xp = 0
                            p_wumpa = 0

                        if has_turbo:
                            p_xp = int(p_xp * 1.2)
                        if p_xp < 1 and not is_stunned and not is_dead: p_xp = 1
                        
                        p_name = f"User {p.user_id}"
                        if p_user_check:
                            p_name = p_user_check.game_name if p_user_check.game_name else (p_user_check.nome if p_user_check.nome else (p_user_check.username if p_user_check.username else f"User {p.user_id}"))
                        
                        rewards_to_distribute.append({
                            'user_id': p.user_id,
                            'p_xp': p_xp,
                            'p_wumpa': p_wumpa,
                            'p_name': p_name,
                            'damage_dealt': p.damage_dealt,
                            'is_dead': is_dead,
                            'is_stunned': is_stunned
                        })
                        actual_total_wumpa += p_wumpa
                        actual_total_xp += p_xp
                finally:
                    temp_session.close()
                
                for reward in rewards_to_distribute:
                    user_id = reward['user_id']
                    p_xp = reward['p_xp']
                    p_wumpa = reward['p_wumpa']
                    p_name = reward['p_name']
                    damage_dealt = reward['damage_dealt']
                    
                    level_up_info = self.user_service.add_exp_by_id(user_id, p_xp)
                    self.user_service.add_points_by_id(user_id, p_wumpa, is_drop=True)
                    self.season_manager.add_seasonal_exp(user_id, p_xp)
                    
                    display_damage = min(damage_dealt, mob_max_health)
                    reward_line = f"👤 **{p_name}**: {display_damage}/{mob_max_health} dmg -> {p_xp} Exp, {p_wumpa} {PointsName}"
                    
                    if p_xp == 0 and p_wumpa == 0 and not is_stunned:
                         # Check if it was due to death (we don't have is_dead here easily without re-checking or passing it)
                         # But we know 0 xp/wumpa usually means stun or death or penalty.
                         # Let's re-check quickly or just assume if 0 and not stunned it might be death.
                         # Actually, let's pass is_dead in the reward dict.
                         pass
                    
                    if reward.get('is_dead'):
                        reward_line += " 💀 (Morto)"
                    elif reward.get('is_stunned'):
                        reward_line += " 💫 (Stordito)"
                    if level_up_info['leveled_up']:
                        reward_line += f"\n   🎉 **LEVEL UP!** Ora sei livello {level_up_info['new_level']}!"
                        if level_up_info['next_level_exp']:
                            reward_line += f" (Prossimo livello: {level_up_info['next_level_exp']} Exp)"
                        reward_line += f" (+2 punti statistica)"
                    reward_details.append(reward_line)
                
                msg += f"\n\n💰 **Ricompense Distribuite!** ({actual_total_wumpa} {PointsName} totali)\n"
            
            msg += "\n".join(reward_details)
            
            # Item reward
            item_chance = 0.10 if is_boss else 0.02
            if random.random() < item_chance:
                items_data = self.item_service.load_items_from_csv()
                if items_data:
                    weights = [1/float(item['rarita']) for item in items_data]
                    reward_item = random.choices(items_data, weights=weights, k=1)[0]
                    self.item_service.add_item(user_id, reward_item['nome'])
                    msg += f"\n\n✨ **Oggetto Raro Trovato!**\nHai ottenuto: **{reward_item['nome']}**"
            
            # Dungeon advancement
            if dungeon_id:
                from services.dungeon_service import DungeonService
                ds = DungeonService()
                dungeon_msg = ds.advance_dungeon(dungeon_id)
                if dungeon_msg:
                    msg += f"\n\n{dungeon_msg}"
        else:
            # Add status card only if alive
            card = self.get_status_card(mob)
            msg += f"\n\n{card}"
            msg += f"\n⏳ Cooldown: {int(cooldown_seconds)}s"

        # Capture data before closing session
        extra_data = {
            'mob_id': final_mob_id,
            'image_path': final_image_path,
            'mob_name': final_mob_name,
            'is_dead': final_is_dead,
            'delete_message_id': final_last_msg_id
        }
        
        if session.is_active:
            session.commit()
            session.close()
        
        # NEW: Process achievements
        self.achievement_tracker.process_pending_events(limit=10)
            
        return True, msg, extra_data

    def attack_aoe(self, user, base_damage=0, chat_id=None, target_mob_id=None):
        """Attack up to 5 active mobs. 70% damage to target, 50% to others. 2x cooldown."""
        if not chat_id:
            return False, "Chat ID non specificato.", None
            
        session = self.db.get_session()
        mobs = session.query(Mob).filter_by(chat_id=chat_id, is_dead=False).all()
        
        if not mobs:
            session.close()
            return False, "Nessun mostro nei paraggi.", None
            
            
        # Check fatigue
        if self.user_service.check_fatigue(user):
            session.close()
            return False, "Sei troppo affaticato per combattere! Riposa.", None
            
        # Check Cooldown (2x normal)
        user_speed = getattr(user, 'allocated_speed', 0)
        cooldown_seconds = (60 / (1 + user_speed * 0.05)) * 2
        
        last_attack = getattr(user, 'last_attack_time', None)
        if last_attack:
            elapsed = (datetime.datetime.now() - last_attack).total_seconds()
            if elapsed < cooldown_seconds:
                remaining = int(cooldown_seconds - elapsed)
                minutes = remaining // 60
                seconds = remaining % 60
                session.close()
                return False, f"⏳ Sei stanco! (CD AoE: {int(cooldown_seconds)}s)\nDevi riposare ancora per {minutes}m {seconds}s.", None
        
        # Update last attack time
        self.user_service.update_user(user.id_telegram, {
            'last_attack_time': datetime.datetime.now()
        })
        
        # Get user character for stats/type
        from services.character_loader import get_character_loader
        char_loader = get_character_loader()
        character = char_loader.get_character_by_id(user.livello_selezionato)
        
        # Prepare attacker object wrapper
        class AttackerWrapper:
            def __init__(self, user, char, base_dmg, multiplier=0.7):
                self.damage_total = int(base_dmg * multiplier)
                self.elemental_type = char.get('elemental_type', "Normal") if char else "Normal"
                char_crit = char.get('crit_chance', 5) if char else 5
                user_crit = getattr(user, 'crit_chance', 0) or 0
                self.crit_chance = char_crit + user_crit
                self.crit_multiplier = char.get('crit_multiplier', 1.5) if char else 1.5
        
        # Limit to 5 mobs
        mobs = mobs[:5]
        
        summary_msg = f"💥 **ATTACCO AD AREA!** (Max 5 bersagli)\n"
        extra_data = {
            'delete_message_ids': [],
            'mob_ids': [m.id for m in mobs]
        }
        
        for mob in mobs:
            # 70% to target, 50% to others
            multiplier = 0.7 if mob.id == target_mob_id else 0.5
            attacker = AttackerWrapper(user, character, base_damage, multiplier)
            
            # Prepare defender wrapper
            class DefenderWrapper:
                def __init__(self, mob):
                    self.defense_total = 0 
                    self.elemental_type = mob.attack_type 
            
            defender = DefenderWrapper(mob)
            
            # Calculate damage
            combat_result = self.battle_service.calculate_damage(attacker, defender)
            damage = combat_result['damage']
            
            # Apply Mob Resistance
            if hasattr(mob, 'resistance') and mob.resistance > 0:
                reduction = mob.resistance / 100.0
                damage = int(damage * (1 - reduction))
            
            # Apply damage
            actual_damage_dealt = max(0, min(damage, mob.health))
            mob.health -= damage
            
            # Update participation
            self.update_participation(mob.id, user.id_telegram, actual_damage_dealt, combat_result['is_crit'])
            
            # Log event
            self.event_dispatcher.log_event(
                event_type='damage_dealt', 
                user_id=user.id_telegram, 
                value=damage,
                context={'is_crit': combat_result['is_crit'], 'mob_id': mob.id, 'mob_name': mob.name, 'is_aoe': True}
            )
            
            # Compact status for AoE to avoid massive cards
            summary_msg += f"\n⚔️ **{mob.name}**: {mob.health}/{mob.max_health} HP (-{damage})"
            
            if mob.last_message_id:
                extra_data['delete_message_ids'].append(mob.last_message_id)
            
            if mob.health <= 0:
                mob.health = 0
                mob.is_dead = True
                mob.killer_id = user.id_telegram
                summary_msg += " 💀"
        
        session.commit()
        
        # Handle rewards for dead mobs (simplified for AoE to avoid massive spam)
        # We'll just distribute basic rewards without the full detailed breakdown for each if many die
        dead_mobs = [m for m in mobs if m.is_dead]
        if dead_mobs:
            summary_msg += "\n\n💰 **Ricompense ottenute!**"
            total_wumpa = 0
            total_xp = 0
            
            for mob in dead_mobs:
                difficulty = mob.difficulty_tier if mob.difficulty_tier else 1
                participants = self.get_combat_participants(mob.id)
                total_damage = sum(p.damage_dealt for p in participants)
                
                if total_damage <= 0: continue
                
                for p in participants:
                    share = p.damage_dealt / total_damage
                    
                    # Proportional Wumpa
                    wumpa = int(p.damage_dealt * 0.05 * difficulty)
                    if wumpa < 1: wumpa = 1
                    
                    # Flat XP based on difficulty and share
                    base_xp_pool = random.randint(100, 300) * difficulty
                    xp = int(base_xp_pool * share)
                    if xp < 1: xp = 1
                    
                    # Apply rewards
                    level_up_info = self.user_service.add_exp_by_id(p.user_id, xp)
                    self.user_service.add_points_by_id(p.user_id, wumpa, is_drop=True)
                    self.season_manager.add_seasonal_exp(p.user_id, xp)
                    
                    if level_up_info['leveled_up']:
                        p_name = self.user_service.get_user(p.user_id).game_name or f"User {p.user_id}"
                        summary_msg += f"\n🎉 **{p_name}** è salito al livello **{level_up_info['new_level']}**!"
                    
                    if p.user_id == user.id_telegram:
                        total_wumpa += wumpa
                        total_xp += xp
            
            summary_msg += f"\n✨ Hai ricevuto: +{total_xp} Exp, +{total_wumpa} {PointsName}"
            summary_msg += f"\n👥 Ricompense distribuite a tutti i partecipanti!"
            
        session.close()
        return True, summary_msg, extra_data

    def get_active_mobs_count(self, chat_id):
        """Get the number of active mobs in a chat"""
        session = self.db.get_session()
        count = session.query(Mob).filter_by(chat_id=chat_id, is_dead=False).count()
        session.close()
        return count

    def update_mob_message_id(self, mob_id, message_id):
        """Update the message ID for a mob spawn"""
        session = self.db.get_session()
        try:
            mob = session.query(Mob).filter_by(id=mob_id).first()
            if mob:
                mob.last_message_id = message_id
                session.commit()
        except Exception as e:
            print(f"Error updating mob message ID: {e}")
        finally:
            session.close()

    def mob_random_attack(self, specific_mob_id=None, chat_id=None):
        """Mobs attack random users. If specific_mob_id is provided, only that mob attacks."""
        session = self.db.get_session()
        
        if specific_mob_id:
            mobs = session.query(Mob).filter_by(id=specific_mob_id).all()
        else:
            mobs = session.query(Mob).filter_by(is_dead=False).all()
            
        session.close() # Close read session immediately
        
        if not mobs:
            return None
            
        attack_events = []
        print(f"[DEBUG] mob_random_attack called for {len(mobs)} mobs. Chat ID: {chat_id}")
        
        for mob in mobs:
            # Check mob cooldown based on speed
            # Formula: 60 / (1 + speed * 0.05)
            # Speed 1 -> ~57s
            # Speed 20 -> 30s
            # Speed 50 -> ~17s
            mob_speed = mob.speed if mob.speed else 30
            cooldown_seconds = 60 / (1 + mob_speed * 0.05)
            
            last_attack = mob.last_attack_time
            if last_attack:
                elapsed = (datetime.datetime.now() - last_attack).total_seconds()
                if elapsed < cooldown_seconds:
                    continue # This mob is on cooldown
            
            # AoE Logic: Bosses have 85% chance, normal mobs have 20% if difficulty >= 3
            is_aoe = False
            difficulty = mob.difficulty_tier if mob.difficulty_tier else 1
            if mob.is_boss:
                # Bosses have high AoE chance
                if random.random() < 0.85:
                    is_aoe = True
            elif difficulty >= 3 and random.random() < 0.20:
                is_aoe = True
            
            # Get targets
            # RESTRICTION: Only attack users in the current chat
            recent_users = self.user_service.get_recent_users(chat_id=chat_id)
            
            # Filter: Only alive users AND NOT RESTING
            alive_users = []
            for uid in recent_users:
                u = self.user_service.get_user(uid)
                if u and not self.user_service.check_fatigue(u):
                    # Check if resting
                    if not self.user_service.get_resting_status(u.id_telegram):
                        alive_users.append(uid)
            
            # Filter: If dungeon mob, only attack participants
            if mob.dungeon_id:
                from services.dungeon_service import DungeonService
                ds = DungeonService()
                participants = ds.get_participants(mob.dungeon_id)
                # Intersection of alive users and participants
                targets_pool = [uid for uid in alive_users if uid in participants]
            else:
                targets_pool = alive_users

            targets = []
            
            if not targets_pool:
                print(f"[DEBUG] No valid targets found for mob {mob.id} (chat {chat_id})")
                continue
            print(f"[DEBUG] Found {len(targets_pool)} valid targets for mob {mob.id}")

            if is_aoe:
                # Attack 1-5 targets
                max_targets = min(5, len(targets_pool))
                target_count = random.randint(1, max_targets)
                
                target_ids = random.sample(targets_pool, target_count)
                primary_target_id = target_ids[0]
                for tid in target_ids:
                    t = self.user_service.get_user(tid)
                    if t: targets.append(t)
            else:
                # Single target
                target = None
                
                # Check for Aggro
                if mob.aggro_target_id and mob.aggro_end_time and mob.aggro_end_time > datetime.datetime.now():
                    # Check if aggro target is in the pool (i.e. active in chat)
                    if mob.aggro_target_id in targets_pool:
                        target_id = mob.aggro_target_id
                    else:
                        # Aggro target not available, clear aggro
                        session = self.db.get_session()
                        m = session.query(Mob).filter_by(id=mob.id).first()
                        if m:
                            m.aggro_target_id = None
                            m.aggro_end_time = None
                            session.commit()
                        session.close()
                        # Fallback to random
                        target_id = random.choice(targets_pool)
                else:
                    # Avoid last target if possible
                    available_users = [uid for uid in targets_pool if uid != mob.last_target_id]
                    if not available_users:
                        available_users = targets_pool # Fallback if only one user active
                    
                    # Prioritize most recent users among available
                    # If we have at least 2 users, prioritize the last 3 (most recent)
                    if len(available_users) >= 2:
                        recent_pool = available_users[-3:]
                        # 80% chance to pick from the most recent pool, 20% from the rest
                        if random.random() < 0.8:
                            target_id = random.choice(recent_pool)
                        else:
                            target_id = random.choice(available_users)
                    else:
                        target_id = random.choice(available_users)
                
                target = self.user_service.get_user(target_id)
                
                if target:
                    targets.append(target)
                    # Update last target ID in DB
                    session = self.db.get_session()
                    mob_db = session.query(Mob).filter_by(id=mob.id).first()
                    if mob_db:
                        mob_db.last_target_id = target.id_telegram
                        session.commit()
                    session.close()
            
            if not targets:
                continue
                
            base_damage = mob.attack_damage if mob.attack_damage else 10
            
            # Collect damage info for each target
            damage_results = []
            death_messages = []
            for target in targets:
                # AoE logic: 70% to primary target, 50% to others. Single target: 100%
                multiplier = 1.0
                if is_aoe:
                    multiplier = 0.7 if target.id_telegram == primary_target_id else 0.5
                
                # Scale damage based on player level to prevent one-shotting high-level players
                # Reduce damage by 50% and add level-based scaling
                level_factor = 1 + (target.livello * 0.02)  # 2% per level
                adjusted_damage = int((base_damage * 0.5 * multiplier) / level_factor)
                
                # Add damage variance (±20%)
                damage = int(adjusted_damage * random.uniform(0.8, 1.2))
                
                # Apply Target Resistance
                user_res = getattr(target, 'allocated_resistance', 0)
                if user_res > 0:
                    reduction_factor = 100 / (100 + user_res)
                    damage = int(damage * reduction_factor)
                
                new_hp, died = self.user_service.damage_health(target, damage)
                
                # NEW: Log damage received event
                self.event_dispatcher.log_event(
                    event_type='damage_received',
                    user_id=target.id_telegram,
                    value=damage,
                    context={
                        'mob_name': mob.name,
                        'mob_id': mob.id,
                        'is_boss': mob.is_boss,
                        'new_hp': new_hp,
                        'died': died
                    }
                )
                
                # Fix double @ issue
                username = target.username.lstrip('@') if target.username else None
                tag = f"@{username}" if username else target.nome
                
                damage_results.append({'tag': tag, 'damage': damage})
                
                if died:
                    death_messages.append(f"💀 **{tag}** è caduto in battaglia!")
            
            # Create consolidated message
            if mob.is_boss:
                # Boss messages
                boss_name_escaped = mob.name.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)')
                if is_aoe:
                    tags = ", ".join([r['tag'] for r in damage_results])
                    avg_damage = sum([r['damage'] for r in damage_results]) // len(damage_results)
                    msg = f"☠️ **Attacco del Boss!**\n**{boss_name_escaped}** ha scatenato un attacco ad area!\n🎯 Colpiti: {tags}\n💥 Danni inflitti: **{avg_damage}** (media)"
                else:
                    tag = damage_results[0]['tag']
                    damage = damage_results[0]['damage']
                    msg = f"☠️ **Attacco del Boss!**\n**{boss_name_escaped}** ha attaccato {tag}\n💥 Danni inflitti: **{damage}**"
            else:
                # Normal mob messages
                if is_aoe:
                    tags = ", ".join([r['tag'] for r in damage_results])
                    avg_damage = sum([r['damage'] for r in damage_results]) // len(damage_results)
                    msg = f"🔥 **Attacco ad Area!**\n**{mob.name}** ha colpito: {tags}\n💥 Danni inflitti: **{avg_damage}** (media)"
                else:
                    tag = damage_results[0]['tag']
                    damage = damage_results[0]['damage']
                    msg = f"⚠️ **{mob.name}** ha attaccato {tag}\n💥 Danni inflitti: **{damage}**"
                
                # Add status card
                card = self.get_status_card(mob)
                msg += f"\n\n{card}"
            
            # Add death messages if any
            if death_messages:
                msg += "\n\n" + "\n".join(death_messages)
            
            # Find mob/boss image
            image_path = None
            safe_name = mob.name.lower().replace(" ", "_")
            if mob.is_boss:
                # Boss images in images/bosses/
                for ext in ['.png', '.jpg', '.jpeg']:
                    path = f"images/bosses/{safe_name}{ext}"
                    if os.path.exists(path):
                        image_path = path
                        break
                # Fallback to default boss image if specific not found
                if not image_path and os.path.exists("images/bosses/default.png"):
                    image_path = "images/bosses/default.png"
            else:
                # Normal mob images in images/mobs/
                mob_info = next((m for m in self.mob_data if m['nome'] == mob.name), None)
                if mob_info:
                    for ext in ['.png', '.jpg', '.jpeg']:
                        path = f"images/mobs/{safe_name}{ext}"
                        if os.path.exists(path):
                            image_path = path
                            break
                # Fallback to default mob image if specific not found
                if not image_path and os.path.exists("images/mobs/default.png"):
                    image_path = "images/mobs/default.png"
            
            # Update mob last attack
            session = self.db.get_session()
            mob_to_update = session.query(Mob).filter_by(id=mob.id).first()
            if mob_to_update:
                mob_to_update.last_attack_time = datetime.datetime.now()
                # Capture ID and message ID before commit/close
                mob_id = mob_to_update.id
                last_msg_id = mob_to_update.last_message_id
                session.commit()
            session.close()

            # Single event per mob (not per target)
            attack_events.append({
                'message': msg,
                'image': image_path,
                'mob_name': mob.name,
                'mob_id': mob_id,
                'last_message_id': last_msg_id
            })
            
        return attack_events

    def distribute_boss_rewards(self, mob_id, killer_user, final_damage):
        """Distribute rewards to all participants who attacked this boss"""
        session = self.db.get_session()
        boss = session.query(Mob).filter_by(id=mob_id).first()
        
        if not boss or not boss.is_boss:
            session.close()
            return []
        
        # Get boss loot from data
        boss_info = next((b for b in self.boss_data if b['nome'] == boss.name), None)
        if boss_info:
            TOTAL_POOL_WUMPA = int(boss_info.get('loot_wumpa', 5000))
            TOTAL_POOL_XP = int(boss_info.get('loot_exp', 10000))  # 10x boost
        else:
            # Default boss rewards
            difficulty = boss.difficulty_tier if boss.difficulty_tier else 5
            level = boss.mob_level if hasattr(boss, 'mob_level') and boss.mob_level else 1
            TOTAL_POOL_WUMPA = random.randint(300, 1000)
            TOTAL_POOL_XP = random.randint(15000, 25000) # Updated to ~1 level up for lvl 10
        
        # Distribute rewards based on damage dealt
        participants = self.get_combat_participants(mob_id)
        total_damage = sum(p.damage_dealt for p in participants)
        
        reward_details = []
        actual_total_wumpa = 0
        actual_total_xp = 0
        
        # Track redirected rewards from stunned users
        redirected_rewards = {} # {target_id: {'xp': 0, 'wumpa': 0}}
            
        for p in participants:
            share = p.damage_dealt / total_damage if total_damage > 0 else 1/len(participants)
            # --- NEW REWARD LOGIC (BOSS) ---
            # Bosses have fixed pools but we apply penalties
            
            # 1. Level Penalty
            mob_level = boss.mob_level if hasattr(boss, 'mob_level') and boss.mob_level else 50
            user_level = p.user_level or 1
            
            penalty_factor_xp = 1.0
            penalty_factor_wumpa = 1.0
            
            if user_level > mob_level + 10:
                penalty_factor_xp = 0.5
                penalty_factor_wumpa = 0.25
            
            p_xp = int(TOTAL_POOL_XP * share * penalty_factor_xp)
            p_wumpa = int(TOTAL_POOL_WUMPA * share * penalty_factor_wumpa)
            
            # 2. Daily Limit: "Fatigue" (Affaticamento)
            # After 300 Wumpa, rewards are 10% harder to obtain (10% reduction)
            p_user_check = session.query(Utente).filter_by(id_telegram=p.user_id).first()
            
            # Check Status Effects
            is_stunned = False
            stun_attacker_id = None
            has_turbo = False
            
            if p_user_check:
                # Parse active effects
                if p_user_check.active_status_effects:
                    try:
                        effects = json.loads(p_user_check.active_status_effects)
                        for effect in effects:
                            if effect.get('id') == 'stunned':
                                is_stunned = True
                                stun_attacker_id = effect.get('source_id')
                            elif effect.get('id') == 'turbo':
                                has_turbo = True
                    except:
                        pass
                
                self.user_service.check_daily_reset(p_user_check)
                if (p_user_check.daily_wumpa_earned or 0) >= 300:
                    # Fatigue: 10% reduction (90% efficiency)
                    p_wumpa = int(p_wumpa * 0.9)
            
            # Apply Item Effects
            if is_stunned:
                # Redirect rewards
                if stun_attacker_id:
                    if stun_attacker_id not in redirected_rewards:
                        redirected_rewards[stun_attacker_id] = {'xp': 0, 'wumpa': 0}
                    redirected_rewards[stun_attacker_id]['xp'] += p_xp
                    redirected_rewards[stun_attacker_id]['wumpa'] += p_wumpa
                
                p_xp = 0
                p_wumpa = 0
            
            if has_turbo:
                p_xp = int(p_xp * 1.2)
            
            actual_total_wumpa += p_wumpa
            actual_total_xp += p_xp
            
            # Add redirected rewards if this user was a stunner
            if p.user_id in redirected_rewards:
                p_xp += redirected_rewards[p.user_id]['xp']
                p_wumpa += redirected_rewards[p.user_id]['wumpa']
                # Note: We don't add to actual_total_wumpa/xp again because it was already counted (just redirected)
            
            # Add rewards and check for level-up
            level_up_info = self.user_service.add_exp_by_id(p.user_id, p_xp)
            self.user_service.add_points_by_id(p.user_id, p_wumpa, is_drop=True)
            self.season_manager.add_seasonal_exp(p.user_id, p_xp)
            
            # Get username for the message
            p_user = session.query(Utente).filter_by(id_telegram=p.user_id).first()
            if p_user:
                p_name = p_user.game_name if p_user.game_name else (p_user.nome if p_user.nome else (p_user.username if p_user.username else f"User {p.user_id}"))
            else:
                p_name = f"User {p.user_id}"
            
            # Format: User: [Damage]/[Max HP] dmg -> [Rewards]
            # Cap displayed damage at mob's max HP to avoid confusion
            display_damage = min(p.damage_dealt, boss.max_health)
            reward_line = f"👤 **{p_name}**: {display_damage}/{boss.max_health} dmg -> {p_xp} Exp, {p_wumpa} {PointsName}"
            
            # Add level-up notification if applicable
            if level_up_info['leveled_up']:
                reward_line += f"\n   🎉 **LEVEL UP!** Ora sei livello {level_up_info['new_level']}!"
                if level_up_info['next_level_exp']:
                    reward_line += f" (Prossimo livello: {level_up_info['next_level_exp']} Exp)"
                reward_line += f" (+2 punti statistica)"
            
            reward_details.append(reward_line)
        
        session.close()
        return reward_details, actual_total_wumpa, actual_total_xp

    def get_mob_status_by_id(self, mob_id):
        """Get specific mob info for display by ID"""
        session = self.db.get_session()
        mob = session.query(Mob).filter_by(id=mob_id).first()
        session.close()
        
        if not mob:
            return None
        
        return {
            'name': mob.name,
            'health': mob.health,
            'max_health': mob.max_health,
            'attack': mob.attack_damage,
            'type': mob.attack_type,
            'level': mob.mob_level if hasattr(mob, 'mob_level') and mob.mob_level else 1,
            'speed': mob.speed if hasattr(mob, 'speed') else 30,
            'resistance': mob.resistance if hasattr(mob, 'resistance') else 0,
            'image': self.get_enemy_image_path(mob),
            'is_boss': mob.is_boss
        }

    def get_current_mob_status(self, mob_id=None):
        """Get current mob info for display"""
        session = self.db.get_session()
        if mob_id:
            mob = session.query(Mob).filter_by(id=mob_id).first()
        else:
            # Get the most recently spawned active mob
            mob = session.query(Mob).filter_by(is_dead=False).order_by(desc(Mob.spawn_time)).first()
        session.close()
        
        if not mob:
            return None
        
        return {
            'name': mob.name,
            'health': mob.health,
            'max_health': mob.max_health,
            'attack': mob.attack_damage,
            'type': mob.attack_type,
            'level': mob.mob_level if hasattr(mob, 'mob_level') and mob.mob_level else 1,
            'speed': mob.speed if hasattr(mob, 'speed') else 30,
            'resistance': mob.resistance if hasattr(mob, 'resistance') else 0,
            'image': self.get_enemy_image_path(mob)
        }
    
    def get_current_boss_status(self):
        """Get current boss (Mob with is_boss=True) info for display"""
        session = self.db.get_session()
        boss = session.query(Mob).filter_by(is_boss=True, is_dead=False).first()
        
        if not boss:
            session.close()
            return None
        
        image_path = self.get_enemy_image_path(boss)
        result = {
            'name': boss.name,
            'health': boss.health,
            'max_health': boss.max_health,
            'attack': boss.attack_damage,
            'description': boss.description if boss.description else '',
            'image': image_path,
            'level': boss.mob_level if hasattr(boss, 'mob_level') and boss.mob_level else 5,
            'speed': boss.speed if hasattr(boss, 'speed') else 70,
            'resistance': boss.resistance if hasattr(boss, 'resistance') else 0
        }
        session.close()
        return result
    
    def get_all_active_enemies(self):
        """Get all active mobs (both normal and bosses) for target selection"""
        session = self.db.get_session()
        
        # Get all alive mobs (both normal and bosses)
        mobs = session.query(Mob).filter_by(is_dead=False).all()
        
        session.close()
        
        enemies = []
        
        # Add all mobs (normal and bosses)
        for mob in mobs:
            enemies.append({
                'type': 'mob',  # All are mobs now
                'id': mob.id,
                'name': mob.name,
                'health': mob.health,
                'max_health': mob.max_health,
                'attack': mob.attack_damage,
                'is_boss': mob.is_boss
            })
        
        return enemies

    def get_enemy_image_path(self, mob):
        """Helper to get image path for mob/boss"""
        image_path = None
        safe_name = mob.name.lower().replace(" ", "_")
        if mob.is_boss:
            # Boss images in images/bosses/
            for ext in ['.png', '.jpg', '.jpeg']:
                path = f"images/bosses/{safe_name}{ext}"
                if os.path.exists(path):
                    image_path = path
                    break
            # Fallback to default boss image if specific not found
            if not image_path and os.path.exists("images/bosses/default.png"):
                image_path = "images/bosses/default.png"
        else:
            # Normal mob images in images/mobs/
            mob_info = next((m for m in self.mob_data if m['nome'] == mob.name), None)
            if mob_info:
                for ext in ['.png', '.jpg', '.jpeg']:
                    path = f"images/mobs/{safe_name}{ext}"
                    if os.path.exists(path):
                        image_path = path
                        break
            # Fallback to default mob image if specific not found
            if not image_path and os.path.exists("images/mobs/default.png"):
                image_path = "images/mobs/default.png"
        return image_path

    def get_status_card(self, entity, is_user=False):
        """Generate a premium status card for a mob or user"""
        if is_user:
            name = entity.nome if entity.username is None else entity.username
            hp = entity.current_hp if hasattr(entity, 'current_hp') and entity.current_hp is not None else entity.health
            max_hp = entity.max_health
            speed = getattr(entity, 'allocated_speed', 0) or 0
            mana = entity.mana
            max_mana = entity.max_mana
            level = entity.livello
        else:
            name = entity.name
            hp = entity.health
            max_hp = entity.max_health
            speed = entity.speed
            mana = None # Mobs don't have mana yet
            max_mana = None
            level = getattr(entity, 'mob_level', 1)

        card = f"╔══════🕹 **{name.upper()}** ══════╗\n"
        card += f" ❤️ **Vita**: {hp}/{max_hp}\n"
        card += f" ⚡ **Velocità**: {speed}\n"
        if mana is not None:
            card += f" 🌀 **Mana**: {mana}/{max_mana}\n"
        if not is_user:
            card += f" 📊 **Livello**: {level}\n"
        card += "          *aROMa*\n"
        card += "╚═══════════════════════╝"
        return card

    # NEW: Combat Participation Tracking
    def get_or_create_participation(self, mob_id, user_id):
        """Get or create combat participation record"""
        session = self.db.get_session()
        try:
            participation = session.query(CombatParticipation).filter_by(
                mob_id=mob_id,
                user_id=user_id
            ).first()
            
            if not participation:
                participation = CombatParticipation(
                    mob_id=mob_id,
                    user_id=user_id,
                    damage_dealt=0,
                    hits_landed=0,
                    critical_hits=0,
                    first_hit_time=datetime.datetime.now()
                )
                session.add(participation)
                session.commit()
            
            return participation
        finally:
            session.close()
    
    def update_participation(self, mob_id, user_id, damage, is_crit=False):
        """Update combat participation with damage dealt (creates if missing)"""
        session = self.db.get_session()
        try:
            participation = session.query(CombatParticipation).filter_by(
                mob_id=mob_id,
                user_id=user_id
            ).first()
            
            if not participation:
                participation = CombatParticipation(
                    mob_id=mob_id,
                    user_id=user_id,
                    damage_dealt=0,
                    hits_landed=0,
                    critical_hits=0,
                    first_hit_time=datetime.datetime.now()
                )
                session.add(participation)
            
            participation.damage_dealt += damage
            participation.hits_landed += 1
            if is_crit:
                participation.critical_hits += 1
            participation.last_hit_time = datetime.datetime.now()
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error updating participation: {e}")
        finally:
            session.close()

    def force_mob_drop(self, mob_id, percent):
        """Force a mob to drop a percentage of its potential Wumpa loot"""
        session = self.db.get_session()
        mob = session.query(Mob).filter_by(id=mob_id).first()
        
        if not mob:
            session.close()
            return 0
            
        # Calculate potential loot based on difficulty
        difficulty = mob.difficulty_tier if mob.difficulty_tier else 1
        
        # Use the max of the range as the "pool" reference
        if difficulty >= 4: # Hard
            pool = 300
        elif difficulty == 3: # Medium
            pool = 200
        elif difficulty <= 2: # Easy
            pool = 50
        else: # Trash
            pool = 10
            
        if mob.is_boss:
             pool = 1000
             
        drop_amount = int(pool * percent)
        if drop_amount < 1: drop_amount = 1
        
        session.close()
        return drop_amount
    
    def get_combat_participants(self, mob_id):
        """Get all participants for a mob fight"""
        session = self.db.get_session()
        try:
            participants = session.query(CombatParticipation).filter_by(
                mob_id=mob_id
            ).all()
            return participants
        finally:
            session.close()
