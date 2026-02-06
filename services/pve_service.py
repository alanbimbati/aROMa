from database import Database
from sqlalchemy import desc
from models.pve import Mob
from models.combat import CombatParticipation
from models.system import Livello
from models.user import Utente
from models.dungeon import Dungeon
from services.user_service import UserService
from services.item_service import ItemService
from services.event_dispatcher import EventDispatcher
from services.damage_calculator import DamageCalculator
from services.status_effects import StatusEffect
from services.targeting_service import TargetingService
import datetime
import random
import csv
import os
import json
from settings import PointsName, GRUPPO_AROMA
from services.equipment_service import EquipmentService

class PvEService:
    def __init__(self):
        self.db = Database()
        self.user_service = UserService()
        self.item_service = ItemService()
        from services.combat_service import CombatService
        self.combat_service = CombatService()
        from services.reward_service import RewardService
        
        # NEW: Enhanced combat services
        self.event_dispatcher = EventDispatcher()
        self.damage_calculator = DamageCalculator()
        self.targeting_service = TargetingService()
        
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
        self.equipment_service = EquipmentService()
        self.reward_service = RewardService(self.db, self.user_service, self.item_service, self.season_manager)
        
        self.mob_data = self.load_mob_data()
        self.boss_data = self.load_boss_data()
        self.recent_mobs = [] # Track last 10 spawned mobs to avoid repetition
        self.pending_mob_effects = {} # {chat_id: [effect1, effect2, ...]}

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

    def use_special_attack(self, user, is_aoe=False, chat_id=None, session=None):
        """
        Execute special attack for the user.
        Checks mana, calculates damage, and calls attack_mob or attack_aoe.
        """
        # Get character
        from services.character_loader import get_character_loader
        char_loader = get_character_loader()
        character = char_loader.get_character_by_id(user.livello_selezionato)
        
        if not character:
            return False, "Personaggio non trovato.", None, []
            
        # Check mana
        mana_cost = character.get('special_attack_mana_cost', 50)
        multiplier = self.guild_service.get_mana_cost_multiplier(user.id_telegram)
        mana_cost = int(mana_cost * multiplier)
        
        if user.mana < mana_cost:
            return False, f"Mana insufficiente! Serve: {mana_cost}, hai: {user.mana}", None, []
            
        # Calculate damage (base + special bonus)
        special_damage = character.get('special_attack_damage', 0)
        
        if is_aoe:
            # Special AoE Attack
            return self.attack_aoe(user, base_damage=special_damage, chat_id=chat_id, use_special=True, session=session)
        else:
            # Single Target Special Attack
            # Deduct mana here for single target (attack_aoe handles it for AoE)
            local_session = False
            if not session:
                session = self.db.get_session()
                local_session = True
                
            try:
                self.user_service.update_user(user.id_telegram, {'mana': user.mana - mana_cost}, session=session)
                success, msg, extra_data = self.attack_mob(user, base_damage=special_damage, use_special=True, chat_id=chat_id, session=session)
                
                if not success:
                    # Refund mana if attack failed (e.g. no mob)
                    self.user_service.update_user(user.id_telegram, {'mana': user.mana + mana_cost}, session=session)
                    if local_session:
                        session.commit()
                    return False, msg, None, []
                
                if local_session:
                    session.commit()
                return success, msg, extra_data, []
            except Exception as e:
                if local_session:
                    session.rollback()
                return False, f"Errore durante l'attacco speciale: {e}", None, []
            finally:
                if local_session:
                    session.close()


    def defend(self, user, chat_id=None):
        """
        Enter defensive stance.
        - Increases resistance by 5% (capped at 75%) for next attack.
        - Heals 2-3% HP.
        - Shares cooldown with attack.
        """
        session = self.db.get_session()
        try:
            # Re-fetch user in this session to ensure updates persist
            # (The passed user object might be detached or from another session)
            db_user = session.merge(user)
            
            # Check if Resting (Inn)
            if db_user.resting_since:
                session.close()
                return False, "💤 Sei alla Locanda! Non puoi combattere mentre riposi. Usa /locanda per uscire."

            # Check if dead (Robust check)
            current_hp = db_user.current_hp if hasattr(db_user, 'current_hp') and db_user.current_hp is not None else (db_user.health or 0)
            
            if current_hp <= 0:
                session.close()
                return False, "💀 Sei morto! Non puoi difenderti. Devi curarti alla Locanda."

            # Check if there are active mobs in chat (if chat_id provided)
            if chat_id:
                mobs_count = session.query(Mob).filter_by(chat_id=chat_id, is_dead=False).count()
                if mobs_count == 0:
                    session.close()
                    return False, "Non c'è nessuno da cui difendersi! I nemici sono stati sconfitti."

            # Check Cooldown (Shared with attack)
            user_speed = getattr(db_user, 'speed', 0) or 0
            cooldown_seconds = 60 / (1 + user_speed * 0.01)
            
            last_attack = getattr(db_user, 'last_attack_time', None)
            if last_attack:
                elapsed = (datetime.datetime.now() - last_attack).total_seconds()
                if elapsed < cooldown_seconds:
                    remaining = int(cooldown_seconds - elapsed)
                    session.close()
                    return False, f"⏳ Sei stanco! (CD: {int(cooldown_seconds)}s)\nDevi riposare ancora per {remaining}s."
            
            # Apply Defense Up Effect
            StatusEffect.apply_status(db_user, 'defense_up', duration=1)
            
            # Heal 2-3% HP
            heal_percent = random.uniform(0.02, 0.03)
            heal_amount = int(db_user.max_health * heal_percent)
            
            old_hp = db_user.health or 0
            new_hp = min(old_hp + heal_amount, db_user.max_health)
            db_user.health = new_hp
            db_user.current_hp = new_hp
            
            real_healed = new_hp - old_hp
            
            # Update last action time
            self.user_service.update_user(db_user.id_telegram, {'last_attack_time': datetime.datetime.now()}, session=session)
            
            session.commit()
            return True, f"🛡️ **{db_user.nome}** usa **Difesa**!\nResistenza aumentata del 5% e recuperati {real_healed} HP."
            
        except Exception as e:
            session.rollback()
            return False, f"Errore durante la difesa: {e}"
        finally:
            session.close()

    def flee_mob(self, user, mob_id, session=None):
        """
        Allow a user to flee from a mob with a chance based on level ratio.
        If threshold reached, mob is removed for everyone.
        """
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
            
        try:
            mob = session.query(Mob).filter_by(id=mob_id).first()
            if not mob:
                if local_session: session.close()
                return False, "Mostro non trovato."
            if mob.is_dead:
                if local_session: session.close()
                return False, "Il mostro è già fuggito o è stato sconfitto."
            
            # Check if user already fled
            participation = session.query(CombatParticipation).filter_by(mob_id=mob_id, user_id=user.id_telegram).first()
            if participation and participation.has_fled:
                if local_session: session.close()
                return False, "Sei già fuggito da questo mostro!"
            
            # Check if mob belongs to a dungeon
            if mob.dungeon_id:
                # Fleeing from a dungeon mob means leaving the dungeon
                from services.dungeon_service import DungeonService
                ds = DungeonService()
                
                # Check if user is actually in this dungeon
                active_dungeon = ds.get_user_active_dungeon(user.id_telegram, session=session)
                if active_dungeon and active_dungeon.id == mob.dungeon_id:
                    success, msg = ds.leave_dungeon(mob.chat_id, user.id_telegram, session=session)
                    if success:
                        if local_session: session.commit()
                        return True, f"🏃 **{user.nome}** è fuggito dal dungeon!\n\n{msg}"
                    elif "Non sei un partecipante" in msg:
                        # Ghost participant case: User is targeted but not actually in dungeon (DB mismatch)
                        # Allow standard flee to break the loop
                        pass 
                    else:
                        if local_session: session.close()
                        return False, f"Non sei riuscito a fuggire dal dungeon: {msg}"
            
            # Calculate flee chance: 0.5 * (mob_level / user_level)
            # Increases if enemy is stronger.
            user_level = user.livello if user.livello else 1
            mob_level = mob.mob_level if mob.mob_level else 1
            
            flee_chance = 0.5 * (mob_level / user_level)
            flee_chance = min(0.9, max(0.1, flee_chance)) # Cap between 10% and 90%
            
            if random.random() < flee_chance:
                # Success!
                # Update participation
                if not participation:
                    participation = CombatParticipation(mob_id=mob_id, user_id=user.id_telegram)
                    session.add(participation)
                
                participation.has_fled = True
                
                # Check group threshold
                fled_count = session.query(CombatParticipation).filter_by(mob_id=mob_id, has_fled=True).count()
                threshold = 5 if mob.is_boss else 3
                
                group_flee = False
                if fled_count >= threshold:
                    mob.is_dead = True
                    mob.has_fled = True
                    group_flee = True
                
                session.commit()
                
                msg = f"🏃 **{user.nome}** è fuggito con successo da {mob.name}! (Probabilità: {int(flee_chance*100)}%)"
                if group_flee:
                    msg += f"\n\n💨 **FUGA DI GRUPPO!** {fled_count} eroi sono fuggiti, {mob.name} ha perso interesse e se n'è andato!"
                
                return True, msg
            else:
                # Failure
                return False, f"🏃 **{user.nome}** ha provato a fuggire da {mob.name} ma è rimasto bloccato! (Probabilità: {int(flee_chance*100)}%)"
                
        except Exception as e:
            return False, f"Errore durante la fuga: {e}"
        finally:
            session.close()





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
        # HP: +10 per point (was 20)
        # DMG: +2 per point (was 5)
        # Speed: +1 per point (was 5)
        # Res: +1% per point (was 5%)
        
        hp_bonus = allocation['hp'] * 10
        dmg_bonus = allocation['dmg'] * 2
        speed = base_speed + (allocation['speed'] * 1)
        resistance = min(50, base_resistance + (allocation['res'] * 1))
            
        return speed, resistance, hp_bonus, dmg_bonus

    def spawn_specific_mob(self, mob_name=None, chat_id=None, reference_level=None, ignore_limit=False, session=None):
        """Spawn a specific mob by name or a random one if None. Returns (success, msg, mob_id)"""
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
        
        # Limit: max 10 active mobs total (to prevent spam), unless ignore_limit is True (e.g. dungeons)
        if not ignore_limit:
            active_mobs_count = session.query(Mob).filter(Mob.is_dead == False, Mob.is_boss == False, Mob.dungeon_id == None).count()
            if active_mobs_count >= 10:
                if local_session:
                    session.close()
                return False, f"C'è già un mob attivo! Sconfiggilo prima di spawnarne altri.", None
            
        # RESTRICTION: Only spawn in official group IF NOT DUNGEON (handled by caller context usually, but here we relax it for dungeons)
        # We trust the caller (DungeonService) to provide a valid chat_id
        # if chat_id and chat_id != GRUPPO_AROMA:
        #      session.close()
        #      return False, "I mob possono apparire solo nel gruppo ufficiale!", None
            
        # Get current season theme
        from models.seasons import Season
        current_season = session.query(Season).filter_by(is_active=True).first()
        theme = current_season.theme.strip().lower() if current_season and current_season.theme else None
        
        mob_data = None
        if mob_name:
            # Find specific mob
            mob_data = next((m for m in self.mob_data if m['nome'].lower() == mob_name.lower()), None)
            if not mob_data:
                if local_session:
                    session.close()
                return False, f"Mostro '{mob_name}' non trovato.", None
            
            if reference_level is not None:
                # Level range: -10 to +10 from reference, min 1
                level = max(1, reference_level + random.randint(-10, 10))
            else:
                difficulty = int(mob_data.get('difficulty', 1))
                # New Logic: Diff X -> Level range ((X-1)*10 + 1) to (X*10)
                min_lvl = (difficulty - 1) * 10 + 1
                max_lvl = difficulty * 10
                level = random.randint(min_lvl, max_lvl)
        else:
            # Random mob based on level and difficulty
            if not self.mob_data:
                session.close()
                return False, "No mob data loaded.", None
            
            if reference_level is not None:
                # Level range: -10 to +10 from reference, min 1
                level = max(1, reference_level + random.randint(-10, 10))
                target_difficulty = (level - 1) // 10 + 1
                
                # Filter by difficulty
                pool = [m for m in self.mob_data if int(m.get('difficulty', 1)) == target_difficulty]
                
                # Fallback: Try adjacent difficulties if pool is empty
                if not pool:
                    for offset in [1, -1, 2, -2]:
                        adj_diff = target_difficulty + offset
                        pool = [m for m in self.mob_data if int(m.get('difficulty', 1)) == adj_diff]
                        if pool: break
                
                # Final fallback to closest difficulty if pool is still empty
                if not pool:
                    all_diffs = sorted(list(set(int(m.get('difficulty', 1)) for m in self.mob_data)))
                    if all_diffs:
                        closest_diff = min(all_diffs, key=lambda x: abs(x - target_difficulty))
                        pool = [m for m in self.mob_data if int(m.get('difficulty', 1)) == closest_diff]
            else:
                # Fallback for job-based spawn
                pool = self.mob_data
                level = random.randint(1, 10) # Default
            
            if not pool:
                if local_session:
                    session.close()
                return False, "No suitable mob found.", None

            # Filter by theme if available
            themed_mobs = [m for m in pool if theme and theme in m.get('saga', '').strip().lower()]
            
            # If no themed mobs in current pool, try to find ANY themed mob within +/- 1 difficulty
            if not themed_mobs and theme:
                for offset in [1, -1, 2, -2]:
                    adj_diff = target_difficulty + offset
                    adj_pool = [m for m in self.mob_data if int(m.get('difficulty', 1)) == adj_diff]
                    themed_mobs = [m for m in adj_pool if theme in m.get('saga', '').strip().lower()]
                    if themed_mobs: break

            def get_random_non_recent(p):
                if not p: return None
                available = [m for m in p if m['nome'] not in self.recent_mobs]
                if not available or len(available) < 2:
                    return random.choice(p)
                return random.choice(available)

            # High chance (95%) to spawn themed mob if available
            if themed_mobs and random.random() < 0.95:
                mob_data = get_random_non_recent(themed_mobs)
            else:
                mob_data = get_random_non_recent(pool)
            
        # Update recent mobs list
        if mob_data:
            self.recent_mobs.append(mob_data['nome'])
            if len(self.recent_mobs) > 10:
                self.recent_mobs.pop(0)
            
        difficulty = int(mob_data.get('difficulty', 1))
        # level is already determined above
        
        # Allocate dynamic stats
        speed, resistance, hp_bonus, dmg_bonus = self._allocate_mob_stats(level, difficulty, is_boss=False)
        
        # Adjust HP and Damage based on level proportionally
        # HP: base + (level * 10) + hp_bonus (was 15)
        # Damage: base + (level * 1) + dmg_bonus (was 3)
        hp = int(mob_data['hp']) + (level * 10) + hp_bonus
        damage = int(mob_data['attack_damage']) + (level * 1) + dmg_bonus
        
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
        if local_session:
            session.commit()
        else:
            session.flush()
        
        # Get ID
        mob_id = new_mob.id
        mob_name = new_mob.name
        
        if local_session:
            session.close()
        return True, f"Un {mob_name} (Lv. {level}) è apparso! (Vel: {speed}, Res: {resistance}%)", mob_id

    def spawn_boss(self, boss_name=None, chat_id=None, reference_level=None, ignore_limit=False, session=None):
        """Spawn a boss (Mob with is_boss=True). Returns (success, msg, mob_id)"""
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
        
        # Limit: max 1 active world boss total (dungeon bosses excluded), unless ignore_limit is True
        if not ignore_limit:
            active_boss_count = session.query(Mob).filter(Mob.is_boss == True, Mob.is_dead == False, Mob.dungeon_id == None).count()
            # Check if boss already exists in this chat
            existing = session.query(Mob).filter_by(chat_id=chat_id, is_boss=True, is_dead=False).first()
            if existing:
                if local_session:
                    session.close()
                return False, f"C'è già un boss attivo: {existing.name}!", None
        
        # Get current season theme (if not provided)
        theme = None
        from models.seasons import Season
        current_season = session.query(Season).filter_by(is_active=True).first()
        theme = current_season.theme if current_season else None
        
        boss_data = None
        if boss_name:
            # Find specific boss
            boss_data = next((b for b in self.boss_data if b['nome'].lower() == boss_name.lower()), None)
            if not boss_data:
                if local_session:
                    session.close()
                return False, f"Boss '{boss_name}' not found.", None
            
            if reference_level is not None:
                level = reference_level + random.randint(5, 12)
            else:
                difficulty = int(boss_data.get('difficulty', 5))
                # New Logic: Bosses usage same tier logic but usually higher difficulty tiers
                min_lvl = (difficulty - 1) * 10 + 1
                max_lvl = difficulty * 10
                level = random.randint(min_lvl, max_lvl)
        else:
            # Random boss based on level and difficulty
            if not self.boss_data:
                if local_session:
                    session.close()
                return False, "No boss data loaded.", None
            
            if reference_level is not None:
                level = reference_level + random.randint(5, 12)
                target_difficulty = (level - 1) // 10 + 1
                
                # Filter by difficulty
                pool = [b for b in self.boss_data if int(b.get('difficulty', 5)) == target_difficulty]
                
                # Fallback to closest difficulty
                if not pool:
                    all_diffs = sorted(list(set(int(b.get('difficulty', 5)) for b in self.boss_data)))
                    if all_diffs:
                        closest_diff = min(all_diffs, key=lambda x: abs(x - target_difficulty))
                        pool = [b for b in self.boss_data if int(b.get('difficulty', 5)) == closest_diff]
            else:
                pool = self.boss_data
                level = random.randint(20, 50) # Default
            
            if not pool:
                if local_session:
                    session.close()
                return False, "No suitable boss found.", None

            # Filter by theme if available
            themed_bosses = [b for b in pool if theme and theme in b.get('saga', '').strip().lower()]
            
            # If no themed bosses in current pool, try to find ANY themed boss within +/- 1 difficulty
            if not themed_bosses and theme:
                for offset in [1, -1, 2, -2]:
                    adj_diff = target_difficulty + offset
                    adj_pool = [b for b in self.boss_data if int(b.get('difficulty', 5)) == adj_diff]
                    themed_bosses = [b for b in adj_pool if theme in b.get('saga', '').strip().lower()]
                    if themed_bosses: break

            if themed_bosses and random.random() < 0.95:
                boss_data = random.choice(themed_bosses)
            else:
                boss_data = random.choice(pool)
        
        # Create Mob with is_boss=True
        hp_base = int(boss_data['hp'])
        difficulty = int(boss_data.get('difficulty', 5))
        # level is already determined above
        
        # Allocate dynamic stats
        # User requested only HP scales like a boss, rest like a mob.
        # So we pass is_boss=False to get standard speed/stats allocation.
        speed, resistance, hp_bonus, dmg_bonus = self._allocate_mob_stats(level, difficulty, is_boss=False)
        
        # Scale HP and Damage
        # HP: base + (level * 200) + hp_bonus (Boss HP scaling)
        # Damage: base + (level * 1) + dmg_bonus (Standard Mob scaling)
        hp = hp_base + (level * 200) + hp_bonus
        damage = int(boss_data['attack_damage']) + (level * 1) + dmg_bonus
        
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
        if local_session:
            session.commit()
        else:
            session.flush()
        
        boss_id = new_boss.id
        boss_name = new_boss.name
        
        if local_session:
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

    def get_mob_details(self, mob_id):
        """Get mob details for display"""
        session = self.db.get_session()
        mob = session.query(Mob).filter_by(id=mob_id).first()
        if not mob:
            session.close()
            return None
            
        data = {
            'id': mob.id,
            'name': mob.name,
            'level': getattr(mob, 'mob_level', 1),
            'health': mob.health,
            'max_health': mob.max_health,
            'attack': getattr(mob, 'attack_damage', 10),
            'defense': 0,
            'speed': getattr(mob, 'speed', 0),
            'resistance': getattr(mob, 'resistance', 0),
            'image_path': self.get_enemy_image_path(mob),
            'dungeon_id': mob.dungeon_id,
            'is_boss': mob.is_boss,
            'spawn_time': mob.spawn_time
        }
        session.close()
        return data

    def attack_mob(self, user, base_damage=0, use_special=False, ability=None, mob_id=None, chat_id=None, mana_cost=0, session=None):
        """Attack current mob using CombatService"""
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
        extra_data = {}
        rewards_to_distribute = []
        
        # 0. STRICT DEATH CHECK (User)
        # Handle detached instances by merging or querying fresh if needed, but 'user' here acts as our object.
        # Ideally we use the session to check fresh state if we suspect desync.
        # But 'user' passed to this function usually comes from user_service.get_user which is fresh.
        current_hp = user.current_hp if hasattr(user, 'current_hp') and user.current_hp is not None else (user.health or 0)
        if current_hp <= 0:
            if local_session:
                session.close()
            return False, "💀 Sei morto! Non puoi attaccare. Devi curarti alla Locanda.", None

        if mob_id:
            # Attack specific mob by ID
            mob = session.query(Mob).filter_by(id=mob_id).first()
            if not mob:
                if local_session:
                    session.close()
                return False, "Mostro non trovato.", None
            if mob.is_dead:
                if local_session:
                    session.close()
                return False, "Questo mostro è già morto!", None
            
            # Check if user has fled
            participation = session.query(CombatParticipation).filter_by(mob_id=mob_id, user_id=user.id_telegram).first()
            if participation and participation.has_fled:
                if local_session:
                    session.close()
                return False, "Sei fuggito da questo mostro! Non puoi più attaccarlo.", None
        else:
            # Attack first alive mob (preferring this chat if provided)
            query = session.query(Mob).filter_by(is_dead=False)
            if chat_id:
                query = query.filter_by(chat_id=chat_id)
            mob = query.first()
            
            if not mob:
                if local_session:
                    session.close()
                return False, "Nessun mostro nei paraggi.", None
        
        # Dungeon Restriction
        from services.dungeon_service import DungeonService
        ds = DungeonService()
        
        if mob.dungeon_id:
            ds.register_participant_if_needed(user.id_telegram, mob.dungeon_id, session=session)
            # participants check removed to allow dynamic join
        else:
            # World mob: NO restriction (users can attack world mobs even if in dungeon)
            pass
        
        # Check fatigue (HP < 5%)
        if self.user_service.check_fatigue(user):
            if local_session:
                session.close()
            return False, "😫 **Sei troppo stanco!** (HP < 5%)\nSei affaticato e non riesci ad attaccare. **Difenditi** per recuperare forze!", None
            
        # Check Cooldown based on Speed
        # Speed is the raw value (e.g. 15). 1 point = 5 speed.
        # We want 1 point to give ~5% cooldown reduction.
        # So 5 speed * 0.01 = 0.05 (5%).
        user_speed = getattr(user, 'speed', 0) or 0
        cooldown_seconds = 60 / (1 + user_speed * 0.01)
        
        last_attack = getattr(user, 'last_attack_time', None)
        if last_attack:
            elapsed = (datetime.datetime.now() - last_attack).total_seconds()
            if elapsed < cooldown_seconds:
                remaining = int(cooldown_seconds - elapsed)
                minutes = remaining // 60
                seconds = remaining % 60
                if local_session:
                    session.close()
                return False, f"⏳ Sei stanco! (CD: {int(cooldown_seconds)}s)\nDevi riposare ancora per {minutes}m {seconds}s.", None
        
        # Deduct Mana (if applicable) - NOW AFTER COOLDOWN CHECK
        if mana_cost > 0:
            if user.mana < mana_cost:
                if local_session:
                    session.close()
                return False, f"❌ Mana insufficiente! Serve: {mana_cost}", None
            self.user_service.update_user(user.id_telegram, {'mana': user.mana - mana_cost}, session=session)
        
        # Update last attack time
        self.user_service.update_user(user.id_telegram, {
            'last_attack_time': datetime.datetime.now()
        }, session=session)
        
        # Track activity for targeting system
        self.user_service.track_activity(user.id_telegram, chat_id)

        
        # Get user character for stats/type
        from services.character_loader import get_character_loader
        char_loader = get_character_loader()
        character = char_loader.get_character_by_id(user.livello_selezionato)
        
        # Prepare attacker object wrapper for CombatService
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
        combat_result = self.combat_service.calculate_damage(attacker, defender, ability)
        damage = combat_result['damage']
        
        # Apply Mob Resistance
        if hasattr(mob, 'resistance') and mob.resistance > 0:
            reduction = mob.resistance / 100.0
            damage = int(damage * (1 - reduction))
            combat_result['resistance_applied'] = mob.resistance
        
        # Detect One Shot
        is_one_shot = (mob.health == mob.max_health) and (damage >= mob.health)
        
        # Apply damage to mob (no counterattack)
        actual_damage_dealt = max(0, min(damage, mob.health))
        mob.health -= damage
        
        # NEW: Update combat participation with capped damage
        self.update_participation(mob.id, user.id_telegram, actual_damage_dealt, combat_result['is_crit'], session=session)
        
        # NEW: Log damage event
        self.event_dispatcher.log_event(
            event_type='damage_dealt', 
            user_id=user.id_telegram, 
            value=damage,
            context={
                'is_crit': combat_result['is_crit'],
                'is_one_shot': is_one_shot,
                'mob_id': mob.id,
                'mob_name': mob.name,
                'mob_level': getattr(mob, 'mob_level', 1),
                'effectiveness': combat_result.get('effectiveness', 1.0)
            },
            session=session
        )
        
        # NEW: Guild Dungeon Damage Tracking
        if mob.dungeon_id:
             # Check if user is in a guild
             from models.guild import GuildMember
             from models.guild_dungeon_stats import GuildDungeonStats
             
             guild_member = session.query(GuildMember).filter_by(user_id=user.id_telegram).first()
             if guild_member:
                 # Update or Create Stats
                 stat = session.query(GuildDungeonStats).filter_by(
                     guild_id=guild_member.guild_id,
                     dungeon_id=mob.dungeon_id
                 ).first()
                 
                 if not stat:
                     stat = GuildDungeonStats(
                         guild_id=guild_member.guild_id,
                         dungeon_id=mob.dungeon_id,
                         total_damage=0
                     )
                     session.add(stat)
                 
                 stat.total_damage += actual_damage_dealt

        
        # NEW: Guild Dungeon Damage Tracking
        if mob.dungeon_id:
             # Check if user is in a guild
             from models.guild import GuildMember
             from models.guild_dungeon_stats import GuildDungeonStats
             
             guild_member = session.query(GuildMember).filter_by(user_id=user.id_telegram).first()
             if guild_member:
                 # Update or Create Stats
                 stat = session.query(GuildDungeonStats).filter_by(
                     guild_id=guild_member.guild_id,
                     dungeon_id=mob.dungeon_id
                 ).first()
                 
                 if not stat:
                     stat = GuildDungeonStats(
                         guild_id=guild_member.guild_id,
                         dungeon_id=mob.dungeon_id,
                         total_damage=0
                     )
                     session.add(stat)
                 
                 stat.total_damage += actual_damage_dealt
        
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
        # Determine image path (GIF priority for special attacks)
        final_image_path = self.get_enemy_image_path(mob)
        
        if use_special and character and character.get('special_attack_gif'):
            gif_filename = character['special_attack_gif']
            # Check images/attacks/ first (new standard)
            gif_path = f"images/attacks/{gif_filename}"
            if not os.path.exists(gif_path):
                # Fallback to root images/
                gif_path = f"images/{gif_filename}"
            
            if os.path.exists(gif_path):
                final_image_path = gif_path

        if mob.health <= 0:
            mob.health = 0
            mob.is_dead = True
            mob.killer_id = user.id_telegram
            
            # Regenerate 2-3% HP and Mana on kill
            import random
            regen_percent = random.uniform(0.02, 0.03)
            hp_regen = int(user.max_health * regen_percent)
            mana_regen = int(user.max_mana * regen_percent)
            
            # Apply regeneration
            user.health = min((user.health or 0) + hp_regen, user.max_health)
            user.current_hp = user.health # Sync
            user.mana = min((user.mana or 0) + mana_regen, user.max_mana)
            
            msg += f"\n💀 **{mob.name} è stato sconfitto!**\n"
            msg += f"💚 Rigenerato: +{hp_regen} HP, +{mana_regen} Mana\n"
            msg += f"🎁 Il nemico ha lasciato un bottino da distribuire a tutti i partecipanti!"
            
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
            participants = self.get_combat_participants(mob_id, session=session)
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
                },
                session=session
            )
            
            # COMMIT transaction but keep session open for rewards
            session.commit()
            
            # Rewards based on difficulty and level (already captured)
            reward_details = []
            total_wumpa = 0
            total_xp = 0
            
            # Rewards (Unified via RewardService)
            # Ensure participants are fetched
            participants = self.get_combat_participants(mob.id, session=session)
            
            # Calculate and Distribute
            try:
                rewards_data = self.reward_service.calculate_rewards(mob, participants)
                reward_msg = self.reward_service.distribute_rewards(rewards_data, mob, session)
                msg += f"\n\n{reward_msg}"
            except Exception as e:
                print(f"[ERROR] Reward distribution failed: {e}")
                rewards_data = []
            
            # Dungeon advancement
            if dungeon_id:
                try:
                    from services.dungeon_service import DungeonService
                    ds = DungeonService()
                    
                    # Record deaths for stats
                    if rewards_data:
                        for reward in rewards_data:
                            if reward.get('is_dead'):
                                ds.record_death(dungeon_id, session=session)

                    dungeon_events, new_mob_ids = ds.check_step_completion(dungeon_id, session=session)
                    
                    if dungeon_events:
                        if isinstance(dungeon_events, list):
                            extra_data['dungeon_events'] = dungeon_events
                        else:
                            msg += f"\n\n{dungeon_events}"
                    
                    if new_mob_ids:
                        extra_data['new_mob_ids'] = new_mob_ids
                except Exception as e:
                    print(f"[ERROR] Dungeon advancement error: {e}")
        else:
            # Add status card only if alive
            card = self.get_status_card(mob)
            msg += f"\n\n{card}"
            msg += f"\n⏳ Cooldown: {int(cooldown_seconds)}s"

        # Capture data before closing session
        final_extra_data = {
            'mob_id': final_mob_id,
            'image_path': final_image_path,
            'mob_name': final_mob_name,
            'is_dead': final_is_dead,
            'delete_message_id': final_last_msg_id,
            'new_mob_ids': extra_data.get('new_mob_ids', [])
        }
        
        if local_session:
            session.commit()
            session.close() # Close session BEFORE checking achievements to prevent transaction coupling
            
            # ACHIEVEMENT FIX: Process events using a NEW session after the main transaction is secure.
            # This prevents specific errors in achievement logic from rolling back the damage/kill.
            try:
                # We need a new session for this since we closed the local one
                self.achievement_tracker.process_pending_events(limit=10) 
            except Exception as e:
                print(f"[ERROR] Achievement processing failed (non-critical): {e}")

        else:
            # If session was passed in, we can't close it, but we should flush at least.
            # Ideally the caller handles commit. We can still try to process safe events.
            # But process_pending_events uses its own session management if none passed? 
            # No, it takes optional session.
            # To be safe and avoid recursion, we might want to defer this?
            # For now, let's just NOT process here if session is external, 
            # relying on the caller or a background job. 
            # OR we process using the passed session but wrap in try/except.
            try:
                self.achievement_tracker.process_pending_events(limit=10, session=session)
            except Exception as e:
                print(f"[ERROR] External session achievement processing failed: {e}")
        
        return True, msg, final_extra_data

    def attack_aoe(self, user, base_damage=0, chat_id=None, target_mob_id=None, use_special=False, session=None):
        """Attack up to 5 active mobs. 70% damage to target, 50% to others. 2x cooldown."""
        if not chat_id:
            return False, "Chat ID non specificato.", None, []
            
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
        all_mobs = session.query(Mob).filter_by(chat_id=chat_id, is_dead=False).all()
        
        if not all_mobs:
            if local_session:
                session.close()
            return False, "Nessun mostro nei paraggi.", None, []
            
        # Dungeon Isolation for AoE
        from services.dungeon_service import DungeonService
        ds = DungeonService()
        active_dungeon = ds.get_user_active_dungeon(user.id_telegram, session=session)
        
        if active_dungeon:
            # User is in a dungeon: prioritize mobs from THAT dungeon, then world mobs
            # Mobs from OTHER dungeons should probably be ignored or low priority (usually invisible in chat anyway)
            
            # Sort mobs: Active Dungeon > World > Other Dungeons
            def get_priority(m):
                if m.dungeon_id == active_dungeon.id: return 0
                if m.dungeon_id is None: return 1
                return 2
                
            mobs = sorted(all_mobs, key=get_priority)
        else:
            # User is NOT in a dungeon: ignore mobs from dungeons (they are "inside" instances)
            # User said: "AoE attacca più nemici attivi, che siano nel dungoen o meno." -> "AoE attacks active enemies, whether in dungeon or not".
            # This implies if I am outside, I might hit a dungeon mob if it's "mescolato" (mixed)?
            # But usually dungeon mobs are logically "in" the dungeon. 
            # However, if they are spawned in the chat, they are visible.
            # Let's target ALL mobs in chat, but prioritize World.
            
            def get_priority(m):
                if m.dungeon_id is None: return 0
                return 1
            
            mobs = sorted(all_mobs, key=get_priority)

        # Dynamic Join for AoE
        for m in all_mobs:
            if m.dungeon_id:
                ds.register_participant_if_needed(user.id_telegram, m.dungeon_id, session=session)

        # Filter out mobs that are strictly "private" or "invalid"? 
        # For now, just rely on chat_id visibility.
            
        if not mobs:
            if local_session:
                session.close()
            msg = "Non ci sono mostri da colpire!"
            return False, msg, None, []
            
        # Filter out mobs the user has fled from
        fled_mob_ids = [p.mob_id for p in session.query(CombatParticipation).filter_by(user_id=user.id_telegram, has_fled=True).all()]
        mobs = [m for m in mobs if m.id not in fled_mob_ids]
        
        if not mobs:
            if local_session:
                session.close()
            return False, "Non ci sono mostri validi da colpire (forse sei fuggito da tutti?)", None, []
            
            
        # Check fatigue
        if self.user_service.check_fatigue(user):
            if local_session:
                session.close()
            return False, "Sei troppo affaticato per combattere! Riposa.", None, []
            
        # Check Cooldown (2x normal)
        user_speed = getattr(user, 'allocated_speed', 0) or 0
        cooldown_seconds = (60 / (1 + user_speed * 0.05)) * 2
        
        last_attack = getattr(user, 'last_attack_time', None)
        if last_attack:
            elapsed = (datetime.datetime.now() - last_attack).total_seconds()
            if elapsed < cooldown_seconds:
                remaining = int(cooldown_seconds - elapsed)
                minutes = remaining // 60
                seconds = remaining % 60
                if local_session:
                    session.close()
                return False, f"⏳ Sei stanco! (CD AoE: {int(cooldown_seconds)}s)\nDevi riposare ancora per {minutes}m {seconds}s.", None, []
        
        # Update last attack time
        self.user_service.update_user(user.id_telegram, {
            'last_attack_time': datetime.datetime.now()
        }, session=session)
        
        # Track activity for targeting system
        self.user_service.track_activity(user.id_telegram, chat_id)

        
        # Get user character for stats/type
        from services.character_loader import get_character_loader
        char_loader = get_character_loader()
        character = char_loader.get_character_by_id(user.livello_selezionato)
        
        # Handle Mana for Special AoE
        if use_special and character:
            mana_cost = character.get('special_attack_mana_cost', 50)
            multiplier = self.guild_service.get_mana_cost_multiplier(user.id_telegram)
            mana_cost = int(mana_cost * multiplier)
            
            if user.mana < mana_cost:
                if local_session:
                    session.close()
                return False, f"Mana insufficiente! Serve: {mana_cost}, hai: {user.mana}", None, []
            self.user_service.update_user(user.id_telegram, {'mana': user.mana - mana_cost}, session=session)
        
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
        mob_count = len(mobs)
        
        title = "🌟 **ATTACCO SPECIALE AD AREA!**" if use_special else "💥 **ATTACCO AD AREA!**"
        summary_msg = f"{title} (Max 5 bersagli)\n"
        extra_data = {
            'delete_message_ids': [],
            'mob_ids': [m.id for m in mobs]
        }
        
        for mob in mobs:
            # 70% to target, 50% to others
            if target_mob_id and mob.id == target_mob_id:
                multiplier = 0.7
            else:
                multiplier = 0.5
            
            attacker = AttackerWrapper(user, character, base_damage, multiplier)
            
            # Prepare defender wrapper
            class DefenderWrapper:
                def __init__(self, mob):
                    self.defense_total = 0 
                    self.elemental_type = mob.attack_type 
            
            defender = DefenderWrapper(mob)
            
            # Calculate damage
            combat_result = self.combat_service.calculate_damage(attacker, defender)
            damage = combat_result['damage']
            
            # Apply Mob Resistance
            if hasattr(mob, 'resistance') and mob.resistance > 0:
                reduction = mob.resistance / 100.0
                damage = int(damage * (1 - reduction))
            
            # Detect One Shot
            is_one_shot = (mob.health == mob.max_health) and (damage >= mob.health)
            
            # Apply damage
            actual_damage_dealt = max(0, min(damage, mob.health))
            mob.health -= damage
            
            # NEW: Guild Dungeon Damage Tracking for AoE
            if mob.dungeon_id:
                from models.guild import GuildMember
                from models.guild_dungeon_stats import GuildDungeonStats
                
                guild_member = session.query(GuildMember).filter_by(user_id=user.id_telegram).first()
                if guild_member:
                    stat = session.query(GuildDungeonStats).filter_by(
                        guild_id=guild_member.guild_id,
                        dungeon_id=mob.dungeon_id
                    ).first()
                    
                    if not stat:
                        stat = GuildDungeonStats(
                            guild_id=guild_member.guild_id,
                            dungeon_id=mob.dungeon_id,
                            total_damage=0
                        )
                        session.add(stat)
                    
                    stat.total_damage += actual_damage_dealt

            # Update participation
            self.update_participation(mob.id, user.id_telegram, actual_damage_dealt, combat_result['is_crit'], session=session)
            
            # Log event
            self.event_dispatcher.log_event(
                event_type='damage_dealt', 
                user_id=user.id_telegram, 
                value=damage,
                context={
                    'is_crit': combat_result['is_crit'], 
                    'is_one_shot': is_one_shot,
                    'mob_id': mob.id, 
                    'mob_name': mob.name, 
                    'is_aoe': True
                },
                session=session
            )
            
            # Compact status for AoE to avoid massive cards
            hp_percent = int((mob.health / mob.max_health) * 100)
            summary_msg += f"\n⚔️ **{mob.name}**: {hp_percent}% HP (-{damage})"
            
            if mob.last_message_id:
                extra_data['delete_message_ids'].append(mob.last_message_id)
            
            if mob.health <= 0:
                mob.health = 0
                mob.is_dead = True
                mob.killer_id = user.id_telegram
                summary_msg += " 💀"
        
        if local_session:
            session.commit()
        
        # Handle rewards for dead mobs (Aggregated via RewardService)
        dead_mobs = [m for m in mobs if m.is_dead]
        if dead_mobs:
            mobs_rewards_map = {}
            for mob in dead_mobs:
                participants = self.get_combat_participants(mob.id, session=session)
                rewards_data = self.reward_service.calculate_rewards(mob, participants)
                if rewards_data:
                    mobs_rewards_map[mob] = rewards_data
            
            if mobs_rewards_map:
                reward_msg = self.reward_service.distribute_aggregated_rewards(mobs_rewards_map, session)
                summary_msg += f"\n\n{reward_msg}"
            
        # Dungeon advancement check
        dungeon_id = None
        for m in mobs:
            if m.dungeon_id:
                dungeon_id = m.dungeon_id
        if local_session:
            session.commit()
        
        if dungeon_id and dead_mobs:
            from services.dungeon_service import DungeonService
            ds = DungeonService()
            
            # Record deaths for stats
            for m in dead_mobs:
                ds.record_death(dungeon_id, session=session)
                
            dungeon_events, new_mob_ids = ds.check_step_completion(dungeon_id, session=session)
            if dungeon_events:
                if isinstance(dungeon_events, list):
                    extra_data['dungeon_events'] = dungeon_events
                else:
                    summary_msg += f"\n\n{dungeon_events}"
                
                if new_mob_ids:
                    extra_data['new_mob_ids'] = new_mob_ids
        
        # Trigger Counter-Attack (Enemy Turn)
        # Call mob_random_attack for the whole chat to simulate enemy turn
        # This allows all eligible mobs to attack back
        attack_events = self.mob_random_attack(chat_id=chat_id, session=session)
        
        # Append Cooldown to message
        summary_msg += f"\n⏳ Cooldown: {int(cooldown_seconds)}s"

        if local_session:

            session.commit()
            session.close()
            
        return True, summary_msg, extra_data, attack_events

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

    def mob_random_attack(self, specific_mob_id=None, chat_id=None, session=None):
        """Mobs attack random users. If specific_mob_id is provided, only that mob attacks."""
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
        
        from services.dungeon_service import DungeonService
        ds = DungeonService()
        
        try:
            mobs_to_process = []
            if specific_mob_id:
                mob = session.query(Mob).filter_by(id=specific_mob_id).first()
                if mob and not mob.is_dead:
                    mobs_to_process.append(mob)
            elif chat_id:
                mobs_to_process = session.query(Mob).filter_by(chat_id=chat_id, is_dead=False).all()
            else:
                mobs_to_process = session.query(Mob).filter_by(is_dead=False).all()
                
            if not mobs_to_process:
                if local_session:
                    session.close()
                return []
                
            attack_events = []
            print(f"[DEBUG] mob_random_attack called for {len(mobs_to_process)} mobs. Chat ID: {chat_id}")
            
            for mob in mobs_to_process:
                try:
                    # Dungeon Check: If mob belongs to a dungeon, check if it's still active
                    if mob.dungeon_id:
                        dungeon = session.query(Dungeon).filter_by(id=mob.dungeon_id).first()
                        if not dungeon or dungeon.status != "active":
                            print(f"[DEBUG] Mob {mob.id} belongs to inactive dungeon {mob.dungeon_id}. Marking as dead.")
                            mob.is_dead = True
                            # Removed individual commit to reduce locking
                            continue
                        
                        # Chat Consistency: Dungeon mobs only attack in their dungeon chat
                        if chat_id and chat_id != dungeon.chat_id:
                            print(f"[DEBUG] Mob {mob.id} (Dungeon {mob.dungeon_id}) skipped: chat {chat_id} != dungeon chat {dungeon.chat_id}")
                            continue

                    # Check mob cooldown based on speed
                    mob_speed = mob.speed if mob.speed else 30
                    cooldown_seconds = 60 / (1 + mob_speed * 0.05)
                    
                    last_attack = mob.last_attack_time
                    if last_attack:
                        elapsed = (datetime.datetime.now() - last_attack).total_seconds()
                        if elapsed < cooldown_seconds:
                            continue # This mob is on cooldown
                    
                    # AoE Logic
                    is_aoe = False
                    difficulty = mob.difficulty_tier if mob.difficulty_tier else 1
                    if mob.is_boss:
                        if random.random() < 0.85:
                            is_aoe = True
                    elif difficulty >= 3 and random.random() < 0.20:
                        is_aoe = True
                    
                    # Get targets using TargetingService
                    recent_users = self.user_service.get_recent_users(chat_id=chat_id, minutes=1440)
                    targets_pool = self.targeting_service.get_valid_targets(
                        mob=mob,
                        chat_id=chat_id,
                        recent_users=recent_users,
                        session=session
                    )
                    
                    print(f"[DEBUG] {'Dungeon' if mob.dungeon_id else 'World'} Mob {mob.id}: targets_pool={targets_pool}")

                    if not targets_pool:
                        print(f"[DEBUG] No valid targets found for mob {mob.id} (chat {chat_id})")
                        continue
                    
                    targets = []
                    primary_target_id = None
                    
                    # --- AGGRO SYSTEM IMPLEMENTATION ---
                    # 1. Fetch Aggro Data (Damage Dealt)
                    try:
                        # Get damage dealt by valid targets
                        participations = session.query(CombatParticipation).filter(
                            CombatParticipation.mob_id == mob.id,
                            CombatParticipation.user_id.in_(targets_pool)
                        ).all()
                        
                        damage_map = {p.user_id: p.damage_dealt for p in participations}
                    except Exception as e:
                        print(f"Error fetching aggro data: {e}")
                        damage_map = {}
                        
                    # 2. Calculate Weights
                    candidates = []
                    weights = []
                    
                    for uid in targets_pool:
                        # Damage Aggro - Primary factor
                        dmg = damage_map.get(uid, 0)
                        # If user has dealt damage, use damage as weight
                        # If no damage, give minimal weight (1) so they can still be randomly targeted
                        weight = max(dmg, 1.0) if dmg > 0 else 1.0
                        
                        # Defense Aggro (Taunt Status)
                        # We need to check if user has 'defense_up'
                        # We can't easily check status effect inside this loop efficiently without pre-loading
                        # But targeting_service already filters valid targets.
                        # Let's trust user_service.get_user to be cached or fast enough?
                        # Or query active_status_effects?
                        try:
                            t_user = session.query(Utente).filter_by(id_telegram=uid).first()
                            if t_user:
                                effects = StatusEffect.get_active_effects(t_user)
                                # Check for Defense Up (Shield)
                                if any(e.get('effect') == 'defense_up' for e in effects):
                                    weight *= 5.0 # 5x Aggro (Massive increase to ensure Tank role works)
                        except:
                            pass
                            
                        candidates.append(uid)
                        weights.append(weight)
                        print(f"[DEBUG AGGRO] User {uid}: damage={dmg}, weight={weight}")
                        
                    # 3. Select Target
                    target_id = None
                    
                    if is_aoe:
                        max_targets = min(5, len(candidates))
                        # Weighted selection for multiple targets is tricky with replacement
                        # Use random.sample for unique if weights are uniform, but here they aren't.
                        # Simple approach: Pick primary weighted, then neighbors or randoms.
                        # For now, let's just pick random weighted samples (allowing duplicates? No)
                        
                        # Workaround: Pick primary target weighted, rest random
                        if candidates:
                             primary_target_id = random.choices(candidates, weights=weights, k=1)[0]
                             targets_set = {primary_target_id}
                             
                             # Fill absolute randoms for the rest (Splash damage)
                             remaining = [c for c in candidates if c != primary_target_id]
                             if remaining:
                                 needed = max_targets - 1
                                 active_count = len(remaining)
                                 fillers = random.sample(remaining, min(needed, active_count))
                                 targets_set.update(fillers)
                                 
                             target_ids = list(targets_set)
                        else:
                            target_ids = []
                            
                        for tid in target_ids:
                            t = session.query(Utente).filter_by(id_telegram=tid).first()
                            if t: targets.append(t)
                    else:
                        # Single Target Logic
                        
                        # 15% Chance to attack RANDOM target (ignoring aggro/taunt)
                        random_roll = random.random()
                        if random_roll < 0.15 and len(candidates) > 1:
                            # Pure random choice from valid candidates in chat
                            target_id = random.choice(candidates)
                            print(f"[DEBUG AGGRO] 15% Random triggered (roll={random_roll:.3f}), selected {target_id}")
                        else:
                            # Standard Aggro Logic (85%)
                            # Check for Taunt first
                            taunt_target = None
                            if mob.aggro_target_id and mob.aggro_end_time and mob.aggro_end_time > datetime.datetime.now():
                                if mob.aggro_target_id in candidates:
                                    taunt_target = mob.aggro_target_id
                            
                            if taunt_target:
                                target_id = taunt_target
                                print(f"[DEBUG AGGRO] 85% Logic: Taunt active on {target_id}")
                            else:
                                # Weighted choice based on damage/defense
                                target_id = random.choices(candidates, weights=weights, k=1)[0]
                                total_weight = sum(weights)
                                selected_weight = weights[candidates.index(target_id)]
                                print(f"[DEBUG AGGRO] 85% Logic: Weighted choice {target_id} ({selected_weight}/{total_weight})")
                                
                        if target_id:
                            t = session.query(Utente).filter_by(id_telegram=target_id).first()
                            if t: targets.append(t)
                            mob.last_target_id = target_id
                    
                    if not targets:
                        continue
                        
                    base_damage = mob.attack_damage if mob.attack_damage else 10
                    damage_results = []
                    death_messages = []
                    
                    for target in targets:
                        is_aoe_target = is_aoe
                        damage = self.combat_service.calculate_mob_damage_to_user(mob, target, is_aoe=is_aoe_target, is_boss=mob.is_boss)
                        
                        new_hp, died = self.user_service.damage_health(target, damage, session=session)
                        
                        self.event_dispatcher.log_event(
                            event_type='damage_taken',
                            user_id=target.id_telegram,
                            value=damage,
                            context={'mob_name': mob.name, 'mob_id': mob.id, 'is_boss': mob.is_boss, 'new_hp': new_hp, 'died': died},
                            session=session
                        )
                        
                        username = target.username.lstrip('@') if target.username else None
                        tag = f"@{username}" if username else target.nome
                        
                        # Add HP info to tag
                        current_hp = target.current_hp if hasattr(target, 'current_hp') and target.current_hp is not None else target.health
                        tag += f" ({current_hp}/{target.max_health} HP)"
                        
                        if damage == 0 and self.user_service.is_invincible(target):
                            tag += " (INVINCIBILE! 🎭)"
                        damage_results.append({'tag': tag, 'damage': damage})
                        if died:
                            death_messages.append(f"💀 **{tag}** è caduto in battaglia!")
                            
                            # Check if dungeon failed (all players dead)
                            if mob.dungeon_id:
                                is_failed, fail_msg = ds.check_dungeon_failure(mob.dungeon_id, session=session)
                                if is_failed and fail_msg:
                                    death_messages.append(fail_msg)
                    
                    if mob.is_boss:
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
                        if is_aoe:
                            tags = ", ".join([r['tag'] for r in damage_results])
                            avg_damage = sum([r['damage'] for r in damage_results]) // len(damage_results)
                            msg = f"🔥 **Attacco ad Area!**\n**{mob.name}** ha colpito: {tags}\n💥 Danni inflitti: **{avg_damage}** (media)"
                        else:
                            tag = damage_results[0]['tag']
                            damage = damage_results[0]['damage']
                            msg = f"⚠️ **{mob.name}** ha attaccato {tag}\n💥 Danni inflitti: **{damage}**"
                        
                        # Pass the first target's ID to check for Scouter
                        target_id_for_scouter = targets[0].id_telegram if targets else None
                        card = self.get_status_card(mob, user_id=target_id_for_scouter, session=session)
                        msg += f"\n\n{card}\n⏳ Cooldown: {int(cooldown_seconds)}s"
                    
                    if death_messages:
                        msg += "\n\n" + "\n".join(death_messages)
                    
                    image_path = None
                    safe_name = mob.name.lower().replace(" ", "_")
                    
                    # Unified check for all mobs/bosses in images/
                    for ext in ['.png', '.jpg', '.jpeg']:
                        path = f"images/{safe_name}{ext}"
                        if os.path.exists(path):
                            image_path = path
                            break
                    
                    if not image_path and os.path.exists("images/default.png"):
                        image_path = "images/default.png"
                    
                    mob.last_attack_time = datetime.datetime.now()
                    mob_id = mob.id
                    last_msg_id = mob.last_message_id
                    
                    attack_events.append({
                        'message': msg,
                        'image': image_path,
                        'mob_name': mob.name,
                        'mob_id': mob_id,
                        'last_message_id': last_msg_id
                    })
                    
                    # Removed individual commit to reduce locking
                    
                except Exception as e:
                    print(f"Error in mob_random_attack loop for mob {mob.id}: {e}")
                    session.rollback()
            
            if local_session:
                session.commit()
                session.close()
            return attack_events
        except Exception as e:
            print(f"Error in mob_random_attack: {e}")
            if local_session:
                session.rollback()
                session.close()
            return []

    def distribute_boss_rewards(self, mob_id, killer_user, final_damage, session=None):
        """Distribute rewards to all participants who attacked this boss"""
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
            
        boss = session.query(Mob).filter_by(id=mob_id).first()
        
        if not boss or not boss.is_boss:
            if local_session:
                session.close()
            return [], 0, 0
        
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
            
            # Fetch user to get level and check limits
            p_user_check = session.query(Utente).filter_by(id_telegram=p.user_id).first()
            user_level = p_user_check.livello if p_user_check and p_user_check.livello else 1
            
            # 1. Level Penalty
            mob_level = boss.mob_level if hasattr(boss, 'mob_level') and boss.mob_level else 50
            
            penalty_factor_xp = 1.0
            penalty_factor_wumpa = 1.0
            
            if user_level > mob_level + 10:
                penalty_factor_xp = 0.5
                penalty_factor_wumpa = 0.25
            
            p_xp = int(TOTAL_POOL_XP * share * penalty_factor_xp)
            p_wumpa = int(TOTAL_POOL_WUMPA * share * penalty_factor_wumpa)
            
            # 2. Daily Limit: "Fatigue" (Affaticamento)
            # After 300 Wumpa, rewards are 10% harder to obtain (10% reduction)
            
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
                            eff_id = effect.get('effect') or effect.get('id')
                            if eff_id == 'stunned':
                                is_stunned = True
                                stun_attacker_id = effect.get('source_id')
                            elif eff_id == 'turbo':
                                has_turbo = True
                    except:
                        pass
                
                self.user_service.check_daily_reset(p_user_check)
                if (p_user_check.daily_wumpa_earned or 0) >= 300:
                    # Fatigue: 10% reduction (90% efficiency)
                    p_wumpa = int(p_wumpa * 0.9)
            
            # Check status and fleeing
            has_fled = getattr(p, 'has_fled', False)
            user_hp = p_user_check.current_hp if p_user_check.current_hp is not None else p_user_check.health
            is_dead = (user_hp <= 0)

            # Apply Status Effects and Flee/Death rules
            if has_fled:
                # Fled players receive NO rewards
                p_xp = 0
                p_wumpa = 0
            elif is_stunned:
                # Redirect rewards
                if stun_attacker_id:
                    if stun_attacker_id not in redirected_rewards:
                        redirected_rewards[stun_attacker_id] = {'xp': 0, 'wumpa': 0}
                    redirected_rewards[stun_attacker_id]['xp'] += p_xp
                    redirected_rewards[stun_attacker_id]['wumpa'] += p_wumpa
                
                p_xp = 0
                p_wumpa = 0
            elif is_dead:
                # Dead players receive Wumpa but NO EXP
                p_xp = 0
            
            if has_turbo and not has_fled and not is_stunned and not is_dead:
                p_xp = int(p_xp * 1.2)
            
            actual_total_wumpa += p_wumpa
            actual_total_xp += p_xp
            
            # Add redirected rewards if this user was a stunner
            if p.user_id in redirected_rewards:
                p_xp += redirected_rewards[p.user_id]['xp']
                p_wumpa += redirected_rewards[p.user_id]['wumpa']
                # Note: We don't add to actual_total_wumpa/xp again because it was already counted (just redirected)
            
            # Add rewards and check for level-up
            level_up_info = self.user_service.add_exp_by_id(p.user_id, p_xp, session=session)
            self.user_service.add_points_by_id(p.user_id, p_wumpa, is_drop=True, session=session)
            # Handle seasonal exp
            season_result = self.season_manager.add_seasonal_exp(p.user_id, p_xp)
            # We don't use the rewards/msg here for boss distribution yet, but we must handle the return to avoid errors if it was unpacking
            # Actually, we might want to show the season end msg?
            # For now, just consume it safely.
            
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
            
            if has_fled:
                reward_line += " 🏃 (Fuggito)"
            elif is_dead:
                reward_line += " 💀 (Morto)"
            elif is_stunned:
                reward_line += " 💫 (Stordito)"
            
            # Add level-up notification if applicable
            if level_up_info['leveled_up']:
                reward_line += f"\n   🎉 **LEVEL UP!** Ora sei livello {level_up_info['new_level']}!"
                if level_up_info['next_level_exp']:
                    reward_line += f" (Prossimo livello: {level_up_info['next_level_exp']} Exp)"
                reward_line += f" (+2 punti statistica)"
            
            reward_details.append(reward_line)
        
        if local_session:
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
        if not mob:
            session.close()
            return None
        
        result = {
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
        session.close()
        return result
    
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
        
        # Check in consolidated images folder
        for ext in ['.png', '.jpg', '.jpeg']:
            path = f"images/{safe_name}{ext}"
            if os.path.exists(path):
                image_path = path
                break
                
        # Fallback to default if specific not found
        if not image_path:
             # Try generic default
             if os.path.exists("images/default.png"):
                 image_path = "images/default.png"
                 
        return image_path

    def get_status_card(self, entity, is_user=False, user_id=None, session=None):
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
        
        # HP Display Logic
        if is_user:
             card += f" ❤️ **Vita**: {hp}/{max_hp}\n"
        else:
            # Check Scouter
            has_scouter = False
            if user_id:
                equipped = self.equipment_service.get_equipped_items(user_id, session=session)
                for ui, item in equipped:
                    if item.special_effect_id == 'scouter_scan':
                        has_scouter = True
                        break
            
            if has_scouter:
                card += f" ❤️ **Vita**: {hp}/{max_hp} (Scouter Active)\n"
            else:
                # Percentage Bar
                safe_hp = hp if hp is not None else 0
                safe_max_hp = max_hp if max_hp is not None else 1
                if safe_max_hp <= 0: safe_max_hp = 1
                
                percent = int((safe_hp / safe_max_hp) * 100)
                bar_len = 10
                filled = int((percent / 100) * bar_len)
                bar = "█" * filled + "░" * (bar_len - filled)
                card += f" ❤️ **Vita**: {bar} {percent}%\n"

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
    
    def update_participation(self, mob_id, user_id, damage, is_crit=False, session=None):
        """Update combat participation with damage dealt (creates if missing)"""
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
            
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
            
            if local_session:
                session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error updating participation: {e}")
        finally:
            if local_session:
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
    
    def get_combat_participants(self, mob_id, session=None):
        """Get all participants for a mob fight"""
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
        try:
            participants = session.query(CombatParticipation).filter_by(
                mob_id=mob_id
            ).all()
            return participants
        finally:
            if local_session:
                session.close()

    def apply_pending_effects(self, mob_id, chat_id, session=None):
        """Apply pending effects (Nitro/TNT) to a newly spawned mob"""
        if chat_id not in self.pending_mob_effects or not self.pending_mob_effects[chat_id]:
            return []
            
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
            
        mob = session.query(Mob).filter_by(id=mob_id).first()
        if not mob:
            if local_session: session.close()
            return []
            
        applied = []
        effects_to_apply = self.pending_mob_effects[chat_id][:]
        self.pending_mob_effects[chat_id] = [] # Clear pending
        
        for effect_name in effects_to_apply:
            # Nitro/TNT deal 10% max HP damage
            damage = int(mob.max_health * 0.10)
            mob.health = max(0, mob.health - damage)
            
            applied.append({
                'effect': effect_name,
                'damage': damage,
                'percent': 0.15
            })
            
        if local_session:
            session.commit()
            session.close()
        else:
            session.flush()
            
        return applied
