#!/usr/bin/env python3
"""
Crafting Service - Handles equipment crafting via Guild Armory
Features:
- Resource drops from mobs/chat
- Recipe-based crafting
- Real-time crafting queues
- Guild Armory level affects success rate
"""

from database import Database
from sqlalchemy import text
import json
import random
from datetime import datetime, timedelta
from sqlalchemy import text

class CraftingService:
    """Manages equipment crafting and resources"""
    
    def __init__(self):
        self.db = Database()
        from services.event_dispatcher import EventDispatcher
        self.event_dispatcher = EventDispatcher()
    
    def add_resource_drop(self, user_id, resource_id, quantity=1, source="mob"):
        """Add a resource to user's inventory"""
        session = self.db.get_session()
        try:
            # Check if user already has this resource
            existing = session.execute(text("""
                SELECT id, quantity FROM user_resources
                WHERE user_id = :uid AND resource_id = :rid
            """), {"uid": user_id, "rid": resource_id}).fetchone()
            
            if existing:
                # Update quantity
                session.execute(text("""
                    UPDATE user_resources
                    SET quantity = quantity + :qty
                    WHERE id = :id
                """), {"qty": quantity, "id": existing[0]})
            else:
                # Insert new
                session.execute(text("""
                    INSERT INTO user_resources (user_id, resource_id, quantity, source)
                    VALUES (:uid, :rid, :qty, :source)
                """), {"uid": user_id, "rid": resource_id, "qty": quantity, "source": source})
            
            session.commit()
            
            # Log event for achievements
            self.event_dispatcher.log_event(
                event_type="RESOURCE_DROP",
                user_id=user_id,
                value=quantity,
                context={"resource_id": resource_id, "source": source}
            )
            return True
        except Exception as e:
            print(f"Error adding resource drop: {e}")
            session.rollback()
            return False
        finally:
            session.close()
    
    def get_user_resources(self, user_id):
        """Get all resources for a user (including 0 quantity)"""
        session = self.db.get_session()
        try:
            # Modified query to show ALL resources, even if user has 0
            resources = session.execute(text("""
                SELECT r.id, r.name, r.rarity, COALESCE(ur.quantity, 0) as quantity
                FROM resources r
                LEFT JOIN user_resources ur ON r.id = ur.resource_id AND ur.user_id = :uid
                ORDER BY r.rarity DESC, r.name
            """), {"uid": user_id}).fetchall()
            
            return [{
                'resource_id': row[0],
                'name': row[1],
                'rarity': row[2],
                'quantity': row[3]
            } for row in resources]
        finally:
            session.close()
    
    def start_crafting(self, guild_id, user_id, equipment_id):
        """Start crafting an item (equipment_id directly, no recipe table)"""
        session = self.db.get_session()
        try:
            # Get equipment info
            equipment = session.execute(text("""
                SELECT id, name, rarity, crafting_time, crafting_requirements
                FROM equipment
                WHERE id = :eid
            """), {"eid": equipment_id}).fetchone()
            
            if not equipment:
                return {"success": False, "error": "Equipment not found"}
            
            eq_id, eq_name, eq_rarity, crafting_time, crafting_requirements = equipment
            
            # Check if item has crafting recipe
            if not crafting_requirements or crafting_requirements.strip() in ['', '{}', 'null']:
                return {"success": False, "error": f"{eq_name} cannot be crafted"}
            
            resources_needed = json.loads(crafting_requirements) if crafting_requirements else {}
            
            # Check armory level requirement (armory level must >= rarity)
            armory_level = self.get_guild_armory_level(guild_id)
            rarity_names = ['', 'Comune', 'Non Comune', 'Raro', 'Epico', 'Leggendario']
            rarity_symbols = {1: '●', 2: '◆', 3: '★', 4: '✦', 5: '✪'}
            
            if armory_level < eq_rarity:
                symbol = rarity_symbols.get(eq_rarity, '●')
                return {
                    "success": False, 
                    "error": f"⚠️ Armeria Lv.{eq_rarity} richiesta!\n\n{symbol} {eq_name} è {rarity_names[eq_rarity]}\n\n🔨 Armeria attuale: Lv.{armory_level}\n❌ Richiesta: Lv.{eq_rarity}\n\nUpgrada l'armeria per craftare questo item!"
                }
            
            # Check crafting slots (armory_level = number of parallel crafts allowed)
            active_jobs = session.execute(text("""
                SELECT COUNT(*) FROM crafting_queue
                WHERE guild_id = :gid AND status = 'in_progress'
            """), {"gid": guild_id}).scalar() or 0
            
            if active_jobs >= armory_level:
                return {
                    "success": False,
                    "error": f"Tutti gli slot di crafting sono occupati ({active_jobs}/{armory_level}). Attendi che un crafting finisca!"
                }
            
            # Check if user has required resources (by name)
            missing_resources = []
            for resource_name, quantity_needed in resources_needed.items():
                # Get resource ID by name
                resource_id = session.execute(text("""
                    SELECT id FROM resources WHERE name = :name
                """), {"name": resource_name}).scalar()
                
                if not resource_id:
                    return {"success": False, "error": f"Resource '{resource_name}' not found in database"}
                
                user_quantity = session.execute(text("""
                    SELECT quantity FROM user_resources
                    WHERE user_id = :uid AND resource_id = :rid
                """), {"uid": user_id, "rid": resource_id}).scalar() or 0
                
                if user_quantity < quantity_needed:
                    missing_resources.append(f"{resource_name}: {user_quantity}/{quantity_needed}")
            
            # If missing resources, return detailed error
            if missing_resources:
                # Get emoji for resources
                emoji_map = {
                    "Rottami": "🔩",
                    "Ferro": "⚒️",
                    "Cuoio": "🦴",
                    "Mithril": "✨",
                    "Seta": "🧵",
                    "Essenza Elementale": "🔮",
                    "Nucleo Stellare": "⭐"
                }
                
                error_msg = f"❌ Risorse insufficienti per craftare {eq_name}!\n\n"
                error_msg += "📦 Costi:\n"
                for resource_name, quantity_needed in resources_needed.items():
                    emoji = emoji_map.get(resource_name, "📦")
                    user_qty = session.execute(text("""
                        SELECT quantity FROM user_resources
                        WHERE user_id = :uid AND resource_id = (SELECT id FROM resources WHERE name = :name)
                    """), {"uid": user_id, "name": resource_name}).scalar() or 0
                    
                    status = "✅" if user_qty >= quantity_needed else "❌"
                    error_msg += f"{status} {emoji} {resource_name}: {user_qty}/{quantity_needed}\n"
                
                return {"success": False, "error": error_msg}
            
            # Consume resources
            for resource_name, quantity_needed in resources_needed.items():
                resource_id = session.execute(text("""
                    SELECT id FROM resources WHERE name = :name
                """), {"name": resource_name}).scalar()
                
                session.execute(text("""
                    UPDATE user_resources
                    SET quantity = quantity - :qty
                    WHERE user_id = :uid AND resource_id = :rid
                """), {"qty": quantity_needed, "uid": user_id, "rid": resource_id})
            
            # Add to crafting queue
            completion_time = datetime.now() + timedelta(seconds=crafting_time)
            
            session.execute(text("""
                INSERT INTO crafting_queue (guild_id, user_id, equipment_id, 
                                           start_time, completion_time, status)
                VALUES (:gid, :uid, :eid, :start, :end, 'in_progress')
            """), {
                "gid": guild_id,
                "uid": user_id,
                "eid": equipment_id,
                "start": datetime.now(),
                "end": completion_time
            })
            
            session.commit()
            
            return {
                "success": True,
                "equipment_name": eq_name,
                "completion_time": completion_time,
                "crafting_time": crafting_time
            }
            
        except Exception as e:
            print(f"Error starting crafting: {e}")
            import traceback
            traceback.print_exc()
            session.rollback()
            return {"success": False, "error": str(e)}
        finally:
            session.close()
    
    def complete_crafting(self, crafting_queue_id, armory_level=1, profession_level=1):
        """Complete a crafting job and determine quality"""
        session = self.db.get_session()
        try:
            # Get crafting job
            job = session.execute(text("""
                SELECT user_id, equipment_id, completion_time, status
                FROM crafting_queue
                WHERE id = :id
            """), {"id": crafting_queue_id}).fetchone()
            
            if not job:
                return {"success": False, "error": "Crafting job not found"}
            
            user_id, equipment_id, completion_time, status = job
            
            if status != 'in_progress':
                return {"success": False, "error": "Job already completed or cancelled"}
            
            if datetime.now() < completion_time:
                return {"success": False, "error": "Crafting not yet complete"}
            
            # Get base equipment rarity
            base_rarity = session.execute(text("""
                SELECT rarity FROM equipment WHERE id = :eid
            """), {"eid": equipment_id}).scalar()
            
            # Calculate final rarity based on armory and profession level
            # Formula: base chance + (profession * 0.5%) + (armory * 1%)
            upgrade_chance = (profession_level * 0.5) + (armory_level * 1.0)
            
            final_rarity = base_rarity
            if random.random() * 100 < upgrade_chance:
                final_rarity = min(5, base_rarity + 1)  # Max legendary
            
            # Add item to user's equipment
            # Generate Stats
            import json
            slot = session.execute(text("SELECT slot FROM equipment WHERE id = :eid"), {"eid": equipment_id}).scalar()
            new_stats = self.generate_random_stats(final_rarity, slot)
            
            session.execute(text("""
                INSERT INTO user_equipment (user_id, equipment_id, equipped, stats_json)
                VALUES (:uid, :eid, FALSE, :stats)
            """), {"uid": user_id, "eid": equipment_id, "stats": json.dumps(new_stats)})
            
            # Mark crafting as complete
            session.execute(text("""
                UPDATE crafting_queue
                SET status = 'completed', actual_rarity = :rarity
                WHERE id = :id
            """), {"id": crafting_queue_id, "rarity": final_rarity})
            
            session.commit()
            
            # Log event for achievements
            self.event_dispatcher.log_event(
                event_type="CRAFTING_COMPLETE",
                user_id=user_id,
                value=1,
                context={"equipment_id": equipment_id, "rarity": final_rarity}
            )
            
            # Add profession XP
            xp_gain = 10 * (base_rarity + 1)
            self.add_profession_xp(user_id, xp_gain)
            
            return {
                "success": True,
                "equipment_id": equipment_id,
                "base_rarity": base_rarity,
                "final_rarity": final_rarity,
                "upgraded": final_rarity > base_rarity,
                "xp_gain": xp_gain
            }
            
        except Exception as e:
            print(f"Error completing crafting: {e}")
            import traceback
            traceback.print_exc()
            session.rollback()
            return {"success": False, "error": str(e)}
        finally:
            session.close()
    
    def get_guild_armory_level(self, guild_id):
        """Get guild's armory level"""
        session = self.db.get_session()
        try:
            level = session.execute(text("""
                SELECT armory_level FROM guilds
                WHERE id = :gid
            """), {"gid": guild_id}).scalar()
            
            return level or 1  # Default level 1
        finally:
            session.close()
    
    def roll_resource_drop(self, mob_level, mob_is_boss=False):
        """Determine if a resource should drop and which one"""
        # Base drop chance: 20% for normal mobs, 100% for bosses
        drop_chance = 100 if mob_is_boss else 20
        
        if random.random() * 100 > drop_chance:
            return None, None
        
        # Determine rarity based on mob level
        # Higher level mobs drop better resources
        if mob_level < 10:
            rarity = random.choices([1, 2], weights=[80, 20])[0]
        elif mob_level < 30:
            rarity = random.choices([1, 2, 3], weights=[50, 35, 15])[0]
        elif mob_level < 50:
            rarity = random.choices([2, 3, 4], weights=[40, 40, 20])[0]
        else:
            rarity = random.choices([3, 4, 5], weights=[40, 40, 20])[0]
        
        # Get a random resource of that rarity
        session = self.db.get_session()
        try:
            resources = session.execute(text("""
                SELECT id, image FROM resources
                WHERE rarity = :rarity AND drop_source IN ('mob', 'both')
                ORDER BY RANDOM()
                LIMIT 1
            """), {"rarity": rarity}).fetchone()
            
            if resources:
                return resources[0], resources[1] # Return id, image
            return None, None
        finally:
            session.close()

    def roll_chat_drop(self, chance=5):
        """
        Determine if a resource should drop from chat activity.
        Logic: 5% chance (default)
        Rarity: mostly common/uncommon, rare chance for rare.
        """
        if random.random() * 100 > chance:
            return None, None
            
        # Determine rarity for chat drops
        # 80% Common, 19% Uncommon, 1% Rare
        rarity = random.choices([1, 2, 3], weights=[80, 19, 1])[0]
        
        session = self.db.get_session()
        try:
            resources = session.execute(text("""
                SELECT id, image FROM resources
                WHERE rarity = :rarity AND drop_source IN ('chat', 'both')
                ORDER BY RANDOM()
                LIMIT 1
            """), {"rarity": rarity}).fetchone()
            
            if resources:
                return resources[0], resources[1]
            return None, None
        finally:
            session.close()

    def get_profession_info(self, user_id):
        """Get user profession level and XP from UserStats"""
        from services.stat_aggregator import StatAggregator
        aggregator = StatAggregator()
        session = self.db.get_session()
        try:
            # We use UserStat to avoid adding columns to utente table
            xp_stat = session.execute(text("""
                SELECT value FROM user_stat 
                WHERE user_id = :uid AND stat_key = 'profession_xp'
            """), {"uid": user_id}).scalar() or 0
            
            level_stat = session.execute(text("""
                SELECT value FROM user_stat 
                WHERE user_id = :uid AND stat_key = 'profession_level'
            """), {"uid": user_id}).scalar() or 1
            
            return {"level": int(level_stat), "xp": int(xp_stat)}
        finally:
            session.close()

    def add_profession_xp(self, user_id, amount):
        """Add XP to user's profession and check for level up"""
        info = self.get_profession_info(user_id)
        current_xp = info['xp']
        current_level = info['level']
        
        new_xp = current_xp + amount
        
        # Calculate level: 100 * (level * (level + 1) / 2) is the XP needed for NEXT level
        # Level 1 -> 2: 100 * 1 = 100 xp
        # Level 2 -> 3: 100 * (2+1) = 300 xp
        # Level 3 -> 4: 100 * (3+3) = 600 xp
        # new_level = 1
        # while new_xp >= 100 * (new_level * (new_level + 1) // 2):
        #     new_level += 1
        
        # Simpler check:
        new_level = current_level
        while True:
            xp_needed = 100 * (new_level * (new_level + 1) // 2)
            if new_xp >= xp_needed:
                new_level += 1
            else:
                break
        
        # Log XP gain event
        self.event_dispatcher.log_event(
            event_type="PROFESSION_XP",
            user_id=user_id,
            value=amount,
            context={"total_xp": new_xp, "old_level": current_level, "new_level": new_level}
        )
        
        if new_level > current_level:
            # Log level up event for achievements
            self.event_dispatcher.log_event(
                event_type="PROFESSION_LEVELUP",
                user_id=user_id,
                value=new_level,
                context={"old_level": current_level}
            )
            return True
        return False

    def process_queue(self):
        """Process all pending crafting jobs that are ready"""
        session = self.db.get_session()
        results = []
        try:
            # Find jobs that are 'in_progress' and past completion time
            from sqlalchemy import text
            from datetime import datetime
            now = datetime.now()
            ready_jobs = session.execute(text("""
                SELECT id, guild_id, user_id, equipment_id
                FROM crafting_queue
                WHERE status = 'in_progress' AND completion_time <= :now
            """), {"now": now}).fetchall()
            
            from services.guild_service import GuildService
            guild_service = GuildService()
            
            for job_id, guild_id, user_id, eq_id in ready_jobs:
                # Get context info
                guild = guild_service.get_user_guild(user_id)
                armory_level = guild['armory_level'] if guild else 1
                
                prof_info = self.get_profession_info(user_id)
                prof_level = prof_info['level']
                
                # Complete the job
                res = self.complete_crafting(job_id, armory_level, prof_level)
                
                # Add extra info for notification
                if res['success']:
                    # Get item name for notification
                    eq_name = session.execute(text("SELECT name FROM equipment WHERE id = :id"), {"id": eq_id}).scalar()
                    res['item_name'] = eq_name
                    res['user_id'] = user_id
                    results.append(res)
            
            
            return results

        finally:
            session.close()

    def generate_random_stats(self, rarity, slot):
        """Generate random stats based on rarity point budget"""
        import random
        
        RARITY_BUDGET = {1: 2, 2: 3, 3: 4, 4: 6, 5: 8}
        budget = RARITY_BUDGET.get(rarity, 2)
        
        STATS_VALUE = {'health': 25, 'mana': 10, 'defense': 1, 'speed': 1, 'crit_chance': 1}
        
        SLOT_PREFS = {
            'head': ['mana', 'crit_chance', 'defense'],
            'chest': ['health', 'defense'],
            'legs': ['health', 'speed', 'defense'],
            'feet': ['speed', 'defense'],
            'main_hand': ['crit_chance', 'speed'],
            'off_hand': ['defense', 'health'],
            'accessory1': ['mana', 'crit_chance', 'speed']
        }
        
        prefs = SLOT_PREFS.get(slot, list(STATS_VALUE.keys()))
        valid_prefs = [p for p in prefs if p in STATS_VALUE]
        if not valid_prefs: valid_prefs = list(STATS_VALUE.keys())
        
        new_stats = {}
        remaining = budget
        
        while remaining > 0:
            stat = random.choice(valid_prefs)
            new_stats[stat] = new_stats.get(stat, 0) + STATS_VALUE[stat]
            remaining -= 1
            
        return new_stats

