from database import Database
from models.pve import Mob
from models.combat import CombatParticipation
from models.system import Livello
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
from settings import PointsName

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
        self.achievement_tracker = AchievementTracker()
        self.mob_ai = MobAI()
        self.boss_phase_manager = BossPhaseManager()
        self.season_manager = SeasonManager()
        
        self.mob_data = self.load_mob_data()
        self.boss_data = self.load_boss_data()
        self.recent_mobs = [] # Track last 5 spawned mobs to avoid repetition

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
        success, msg, mob_id = self.spawn_specific_mob()
        if success and mob_id:
            # Immediate attack
            attack_events = self.mob_random_attack(specific_mob_id=mob_id, chat_id=chat_id)
            return mob_id, attack_events
        # Return None if spawn failed (e.g., too many mobs)
        return None, None

    def _allocate_mob_stats(self, level, is_boss=False):
        """
        Allocate stats based on level.
        Mobs: Speed 1-20
        Bosses: Speed 20-50
        """
        # Base stats
        if is_boss:
            base_points = 50 + (level * 10)
            min_speed = 20
            max_speed = 50
        else:
            base_points = 20 + (level * 5)
            min_speed = 1
            max_speed = 20
            
        # Allocate Speed first (random within range)
        speed = random.randint(min_speed, max_speed)
        
        # Allocate Resistance (0-50%)
        # Higher level -> higher resistance chance and value
        resistance = 0
        if random.random() < 0.5 + (level * 0.01):
            max_res = min(50, level * 2)
            resistance = random.randint(0, max_res)
            
        return speed, resistance

    def spawn_specific_mob(self, mob_name=None):
        """Spawn a specific mob or random if None. Returns (success, msg, mob_id)"""
        session = self.db.get_session()
        
        # Limit: max 5 active mobs at once (to prevent spam)
        active_mobs_count = session.query(Mob).filter_by(is_dead=False, is_boss=False).count()
        if active_mobs_count >= 5:
            session.close()
            return False, f"Troppi mob attivi ({active_mobs_count}/5)! Elimina alcuni nemici prima di spawnarne altri.", None
            
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
                return False, f"Mob '{mob_name}' non trovato."
        else:
            # Random mob, 70% chance for themed mob if available
            if not self.mob_data:
                session.close()
                return False, "Nessun dato mob caricato."
            
            # Filter by theme if available (robust matching)
            themed_mobs = [m for m in self.mob_data if theme and m.get('saga', '').strip().lower() == theme]
            
            # Repetition avoidance: filter out recent mobs if possible
            def get_random_non_recent(pool):
                if not pool: return None
                available = [m for m in pool if m['nome'] not in self.recent_mobs]
                if not available: # If all are recent, just pick any
                    return random.choice(pool)
                return random.choice(available)

            if themed_mobs and random.random() < 0.7:
                mob_data = get_random_non_recent(themed_mobs)
            else:
                # Fallback to any mob (30% chance or if no themed mobs)
                mob_data = get_random_non_recent(self.mob_data)
            
        # Update recent mobs list
        if mob_data:
            self.recent_mobs.append(mob_data['nome'])
            if len(self.recent_mobs) > 5:
                self.recent_mobs.pop(0)
            
        # Create Mob
        # Ensure HP is correct
        hp = int(mob_data['hp'])
        
        # Determine level (default 1 if not specified)
        level = int(mob_data.get('level', mob_data.get('difficulty', 1)))
        
        # Allocate dynamic stats
        speed, resistance = self._allocate_mob_stats(level, is_boss=False)
        
        # Adjust HP and Damage based on level slightly (if not already scaled in CSV)
        # Assuming CSV has base values, we can scale them a bit
        hp = int(hp * (1 + level * 0.1))
        damage = int(int(mob_data['attack_damage']) * (1 + level * 0.05))
        
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
            last_attack_time=datetime.datetime.now() # Just spawned
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

    def spawn_boss(self, boss_name=None):
        """Spawn a boss (Mob with is_boss=True). Returns (success, msg, mob_id)"""
        session = self.db.get_session()
        
        # Check if there's already an active boss
        active_boss = session.query(Mob).filter_by(is_boss=True, is_dead=False).first()
        if active_boss:
            session.close()
            return False, f"C'è già un boss attivo: {active_boss.name}!", None
        
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
            themed_bosses = [b for b in self.boss_data if theme and b.get('saga') == theme]
            
            if themed_bosses and random.random() < 0.7:
                boss_data = random.choice(themed_bosses)
            else:
                # Fallback to any boss (30% chance or if no themed bosses)
                boss_data = random.choice(self.boss_data)
        
        # Create Mob with is_boss=True
        hp = int(boss_data['hp'])
        level = int(boss_data.get('level', boss_data.get('difficulty', 5))) # Bosses default high level
        
        # Allocate dynamic stats
        speed, resistance = self._allocate_mob_stats(level, is_boss=True)
        
        # Scale HP and Damage
        hp = int(hp * (1 + level * 0.15))
        damage = int(int(boss_data['attack_damage']) * (1 + level * 0.08))
        
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
            mob_level=level,
            last_attack_time=datetime.datetime.now(),
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

    def attack_mob(self, user, base_damage=0, use_special=False, ability=None, mob_id=None):
        """Attack current mob using BattleService"""
        session = self.db.get_session()
        
        if mob_id:
            # Attack specific mob by ID
            mob = session.query(Mob).filter_by(id=mob_id).first()
            if not mob:
                session.close()
                return False, "Mostro non trovato."
            if mob.is_dead:
                session.close()
                return False, "Questo mostro è già morto!"
        else:
            # Attack first alive mob
            mob = session.query(Mob).filter_by(is_dead=False).first()
            if not mob:
                session.close()
                return False, "Nessun mostro nei paraggi."
        
        # Check fatigue
        if self.user_service.check_fatigue(user):
            session.close()
            return False, "Sei troppo affaticato per combattere! Riposa."
            
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
                return False, f"⏳ Sei stanco! Devi riposare ancora per {minutes}m {seconds}s."
        
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
                char_crit = char.get('crit_chance', 5) if char else 5
                allocated_crit = getattr(user, 'allocated_crit_rate', 0)
                self.crit_chance = char_crit + allocated_crit
                
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
        mob.health -= damage
        
        # NEW: Update combat participation
        self.update_participation(mob.id, user.id_telegram, damage, combat_result['is_crit'])
        
        # NEW: Log damage event
        self.event_dispatcher.log_event('damage_dealt', user.id_telegram, {
            'damage': damage,
            'is_crit': combat_result['is_crit'],
            'mob_id': mob.id,
            'mob_name': mob.name,
            'mob_level': getattr(mob, 'mob_level', 1),
            'effectiveness': combat_result.get('effectiveness', 1.0)
        }, mob_id=mob.id)
        
        # Build message
        msg = ""
        if combat_result['is_crit']:
            msg += "🔥 **CRITICO!** "
        
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
        
        if mob.health <= 0:
            mob.health = 0
            mob.is_dead = True
            mob.killer_id = user.id_telegram
            msg += f"\n💀 **{mob.name} è stato sconfitto!**"
            
            # NEW: Log mob kill event
            participants = self.get_combat_participants(mob.id)
            solo_kill = len(participants) == 1
            participation = next((p for p in participants if p.user_id == user.id_telegram), None)
            
            self.event_dispatcher.log_event('mob_kill', user.id_telegram, {
                'mob_name': mob.name,
                'mob_level': getattr(mob, 'mob_level', 1),
                'is_boss': mob.is_boss,
                'damage_dealt': participation.damage_dealt if participation else damage,
                'was_last_hit': True,
                'solo_kill': solo_kill,
                'player_level': user.livello
            }, mob_id=mob.id)
            
            # Rewards based on difficulty and level
            difficulty = mob.difficulty_tier if mob.difficulty_tier else 1
            level = mob.mob_level if hasattr(mob, 'mob_level') and mob.mob_level else 1
            
            # Bosses give much better rewards
            if mob.is_boss:
                # Boss rewards are much higher
                base_xp = random.randint(200, 400) * difficulty
                base_wumpa = random.randint(100, 200) * difficulty
                xp = int(base_xp * (1 + level * 0.5))
                wumpa = int(base_wumpa * (1 + level * 0.5))
                
                # Distribute rewards to all participants if it's a boss
                self.distribute_boss_rewards(mob.id, user, damage)
                msg += "\n🏆 Ricompense distribuite ai partecipanti!"
            else:
                # Normal mob rewards distributed among participants
                difficulty = mob.difficulty_tier if mob.difficulty_tier else 1
                level = mob.mob_level if hasattr(mob, 'mob_level') and mob.mob_level else 1
                
                # Total pool for the mob (~200 Wumpa as requested)
                TOTAL_POOL_WUMPA = random.randint(150, 250) * difficulty
                TOTAL_POOL_XP = random.randint(50, 100) * difficulty
                
                total_damage = sum(p.damage_dealt for p in participants)
                for p in participants:
                    share = p.damage_dealt / total_damage if total_damage > 0 else 1/len(participants)
                    p_xp = int(TOTAL_POOL_XP * share * (1 + level * 0.3))
                    p_wumpa = int(TOTAL_POOL_WUMPA * share * (1 + level * 0.3))
                    
                    # Add rewards
                    self.user_service.add_exp_by_id(p.user_id, p_xp)
                    self.user_service.add_points_by_id(p.user_id, p_wumpa)
                    self.season_manager.add_seasonal_exp(p.user_id, p_xp)
                
                msg += f"\n💰 **RICOMPENSE DISTRIBUITE!** ({TOTAL_POOL_WUMPA} 🍑 totali)"
            
            # Item reward (2% chance for normal mobs, 10% for bosses)
            item_chance = 0.10 if mob.is_boss else 0.02
            if random.random() < item_chance:
                items_data = self.item_service.load_items_from_csv()
                if items_data:
                    weights = [1/float(item['rarita']) for item in items_data]
                    reward_item = random.choices(items_data, weights=weights, k=1)[0]
                    self.item_service.add_item(user.id_telegram, reward_item['nome'])
                    if not mob.is_boss:
                        msg += f"\n🏆 Ricompensa: {xp} Exp, {wumpa} {PointsName}, {reward_item['nome']}!"
                    else:
                        msg += f"\n🎁 Oggetto raro: {reward_item['nome']}!"
                elif not mob.is_boss:
                    msg += f"\n🏆 Ricompensa: {xp} Exp, {wumpa} {PointsName}!"
            elif not mob.is_boss:
                msg += f"\n🏆 Ricompensa: {xp} Exp, {wumpa} {PointsName}!"
        else:
            msg += f"\n❤️ Vita rimanente: {mob.health}/{mob.max_health}"
            msg += f"\n⏳ Cooldown: {int(cooldown_seconds)}s"

        session.commit()
        session.close()
        
        # NEW: Process achievements
        self.achievement_tracker.process_pending_events(limit=10)
        
        return True, msg

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
            targets = []
            
            if not recent_users:
                # No active users in this chat to attack
                continue

            if is_aoe and recent_users:
                # Attack 2-10 recent users
                max_targets = min(10, len(recent_users))
                if max_targets < 2:
                    target_count = 1
                else:
                    target_count = random.randint(2, max_targets)
                
                target_ids = random.sample(recent_users, target_count)
                for tid in target_ids:
                    t = self.user_service.get_user(tid)
                    if t: targets.append(t)
            else:
                # Single target
                target = None
                if recent_users:
                    target_id = random.choice(recent_users)
                    target = self.user_service.get_user(target_id)
                
                # REMOVED FALLBACK TO RANDOM DB USER
                # We only want to attack people in the group
                
                if target:
                    targets.append(target)
            
            if not targets:
                continue
                
            base_damage = mob.attack_damage if mob.attack_damage else 10
            
            # Collect damage info for each target
            damage_results = []
            for target in targets:
                # Add damage variance (±20%)
                damage = int(base_damage * random.uniform(0.8, 1.2))
                
                # Apply Target Resistance
                user_res = getattr(target, 'allocated_resistance', 0)
                if user_res > 0:
                    reduction_factor = 100 / (100 + user_res)
                    damage = int(damage * reduction_factor)
                
                self.user_service.damage_health(target, damage)
                
                # Fix double @ issue
                username = target.username.lstrip('@') if target.username else None
                tag = f"@{username}" if username else target.nome
                
                damage_results.append({'tag': tag, 'damage': damage})
            
            # Create consolidated message
            if mob.is_boss:
                # Boss messages
                boss_name_escaped = mob.name.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)')
                if is_aoe:
                    tags = ", ".join([r['tag'] for r in damage_results])
                    avg_damage = sum([r['damage'] for r in damage_results]) // len(damage_results)
                    msg = f"☠️ **BOSS ATTACK!**\n**{boss_name_escaped}** ha scatenato un attacco ad area!\n🎯 Colpiti: {tags}\n💥 Danni inflitti: **{avg_damage}** (media)"
                else:
                    tag = damage_results[0]['tag']
                    damage = damage_results[0]['damage']
                    msg = f"☠️ **BOSS ATTACK!**\n**{boss_name_escaped}** ha attaccato {tag}\n💥 Danni inflitti: **{damage}**"
            else:
                # Normal mob messages
                if is_aoe:
                    tags = ", ".join([r['tag'] for r in damage_results])
                    avg_damage = sum([r['damage'] for r in damage_results]) // len(damage_results)
                    msg = f"🔥 **ATTACCO AD AREA!**\n**{mob.name}** ha colpito: {tags}\n💥 Danni inflitti: **{avg_damage}** (media)"
                else:
                    tag = damage_results[0]['tag']
                    damage = damage_results[0]['damage']
                    msg = f"⚠️ **{mob.name}** ha attaccato {tag}\n💥 Danni inflitti: **{damage}**"
            
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
            
            # Single event per mob (not per target)
            attack_events.append({
                'message': msg,
                'image': image_path,
                'mob_name': mob.name
            })
            
            # Update mob last attack
            session = self.db.get_session()
            mob_to_update = session.query(Mob).filter_by(id=mob.id).first()
            if mob_to_update:
                mob_to_update.last_attack_time = datetime.datetime.now()
                session.commit()
            session.close()
            
        return attack_events

    def distribute_boss_rewards(self, mob_id, killer_user, final_damage):
        """Distribute rewards to all participants who attacked this boss"""
        session = self.db.get_session()
        boss = session.query(Mob).filter_by(id=mob_id).first()
        
        if not boss or not boss.is_boss:
            session.close()
            return
        
        # Get boss loot from data
        boss_info = next((b for b in self.boss_data if b['nome'] == boss.name), None)
        if boss_info:
            TOTAL_POOL_WUMPA = int(boss_info.get('loot_wumpa', 5000))
            TOTAL_POOL_XP = int(boss_info.get('loot_exp', 1000))
        else:
            # Default boss rewards
            difficulty = boss.difficulty_tier if boss.difficulty_tier else 5
            level = boss.mob_level if hasattr(boss, 'mob_level') and boss.mob_level else 1
            TOTAL_POOL_WUMPA = random.randint(2000, 5000) * difficulty
            TOTAL_POOL_XP = random.randint(500, 1500) * difficulty
        
        # Distribute rewards based on damage dealt
        participants = self.get_combat_participants(mob_id)
        total_damage = sum(p.damage_dealt for p in participants)
        
        for p in participants:
            share = p.damage_dealt / total_damage if total_damage > 0 else 1/len(participants)
            p_xp = int(TOTAL_POOL_XP * share)
            p_wumpa = int(TOTAL_POOL_WUMPA * share)
            
            self.user_service.add_exp_by_id(p.user_id, p_xp)
            self.user_service.add_points_by_id(p.user_id, p_wumpa)
            self.season_manager.add_seasonal_exp(p.user_id, p_xp)
        
        session.close()

    def get_current_mob_status(self):
        """Get current mob info for display"""
        session = self.db.get_session()
        mob = session.query(Mob).filter_by(is_dead=False).first()
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
        """Update combat participation with damage dealt"""
        session = self.db.get_session()
        try:
            participation = session.query(CombatParticipation).filter_by(
                mob_id=mob_id,
                user_id=user_id
            ).first()
            
            if participation:
                participation.damage_dealt += damage
                participation.hits_landed += 1
                if is_crit:
                    participation.critical_hits += 1
                participation.last_hit_time = datetime.datetime.now()
                session.commit()
        finally:
            session.close()
    
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

