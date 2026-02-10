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
        """Get all raw and refined resources for a user"""
        session = self.db.get_session()
        try:
            # Raw resources
            raw = session.execute(text("""
                SELECT r.id, r.name, r.rarity, COALESCE(ur.quantity, 0) as quantity
                FROM resources r
                LEFT JOIN user_resources ur ON r.id = ur.resource_id AND ur.user_id = :uid
                WHERE (COALESCE(ur.quantity, 0) > 0 OR r.rarity = 1)
                ORDER BY r.rarity ASC, r.name
            """), {"uid": user_id}).fetchall()
            
            # Refined materials (Aggregated to handle duplicates gracefully)
            refined = session.execute(text("""
                SELECT rm.id, rm.name, rm.rarity, SUM(COALESCE(urm.quantity, 0)) as quantity
                FROM refined_materials rm
                LEFT JOIN user_refined_materials urm ON rm.id = urm.material_id AND urm.user_id = :uid
                GROUP BY rm.id, rm.name, rm.rarity
                ORDER BY rm.rarity ASC
            """), {"uid": user_id}).fetchall()
            
            return {
                'raw': [{
                    'resource_id': row[0],
                    'name': row[1],
                    'rarity': row[2],
                    'quantity': row[3]
                } for row in raw],
                'refined': [{
                    'material_id': row[0],
                    'name': row[1],
                    'rarity': row[2],
                    'quantity': row[3]
                } for row in refined]
            }
        finally:
            session.close()

    def upgrade_material(self, user_id, source_id, target_id, count=1):
        """Convert low-tier materials into high-tier (10:1 rate)"""
        if count <= 0:
            return {"success": False, "error": "Quantità non valida!"}
            
        # Allowed upgrades
        valid_upgrades = {
            1: 2, # Rottami -> Pregiato
            2: 3  # Pregiato -> Diamante
        }
        
        if valid_upgrades.get(source_id) != target_id:
            return {"success": False, "error": "Upgrade non valido!"}
            
        cost_per_unit = 10
        total_cost = count * cost_per_unit
        
        session = self.db.get_session()
        try:
            # Check source quantity
            user_qty = session.execute(text("""
                SELECT quantity FROM user_refined_materials
                WHERE user_id = :uid AND material_id = :mid
            """), {"uid": user_id, "mid": source_id}).scalar() or 0
            
            if user_qty < total_cost:
                # Get names for error message
                names = session.execute(text("SELECT id, name FROM refined_materials WHERE id IN (:s, :t)"), 
                                       {"s": source_id, "t": target_id}).fetchall()
                names_dict = {row[0]: row[1] for row in names}
                return {"success": False, "error": f"Non hai abbastanza {names_dict.get(source_id, 'materiali')}! (Richiesti: {total_cost}, Possiedi: {user_qty})"}
            
            # Consume source
            session.execute(text("""
                UPDATE user_refined_materials SET quantity = quantity - :q
                WHERE user_id = :uid AND material_id = :mid
            """), {"q": total_cost, "uid": user_id, "mid": source_id})
            
            # Add target (Atomic UPSERT)
            session.execute(text("""
                INSERT INTO user_refined_materials (user_id, material_id, quantity)
                VALUES (:uid, :mid, :q)
                ON CONFLICT (user_id, material_id) 
                DO UPDATE SET quantity = user_refined_materials.quantity + EXCLUDED.quantity
            """), {"uid": user_id, "mid": target_id, "q": count})
                
            session.commit()
            
            # Get names for success message
            names = session.execute(text("SELECT id, name FROM refined_materials WHERE id IN (:s, :t)"), 
                                   {"s": source_id, "t": target_id}).fetchall()
            names_dict = {row[0]: row[1] for row in names}
            
            return {
                "success": True, 
                "source_name": names_dict.get(source_id),
                "target_name": names_dict.get(target_id),
                "count": count,
                "cost": total_cost
            }
        except Exception as e:
            session.rollback()
            return {"success": False, "error": str(e)}
        finally:
            session.close()

    def get_daily_refinable_resource(self, session=None):
        """Get today's refinable resource. Rotates daily."""
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
        
        try:
            now = datetime.now().date()
            # Check if we already have one for today
            daily = session.execute(text("""
                SELECT resource_id FROM refinery_daily
                WHERE DATE(date) = :today
            """), {"today": now}).fetchone()
            
            if daily:
                res_id = daily[0]
            else:
                # Pick a random resource (weighted by rarity - common more frequent)
                # For simplicity, just pick a random one for now
                all_res = session.execute(text("SELECT id FROM resources")).fetchall()
                if not all_res:
                    return None
                res_id = random.choice(all_res)[0]
                
                # Save it
                session.execute(text("""
                    INSERT INTO refinery_daily (date, resource_id)
                    VALUES (:today, :rid)
                    ON CONFLICT (date) DO UPDATE SET resource_id = :rid
                """), {"today": now, "rid": res_id})
                session.commit()
            
            # Get details
            resource = session.execute(text("""
                SELECT id, name FROM resources WHERE id = :id
            """), {"id": res_id}).fetchone()
            
            return {"id": resource[0], "name": resource[1]} if resource else None
        finally:
            if local_session:
                session.close()

    def start_refinement(self, guild_id, user_id, resource_id, quantity):
        """Start refining raw items into materials"""
        session = self.db.get_session()
        try:
            # 1. Check if resource is refinable today
            daily = self.get_daily_refinable_resource(session)
            if not daily or daily['id'] != resource_id:
                return {"success": False, "error": "Questo materiale non può essere raffinato oggi!"}
            
            # 2. Check if user has enough quantity
            user_qty = session.execute(text("""
                SELECT quantity FROM user_resources
                WHERE user_id = :uid AND resource_id = :rid
            """), {"uid": user_id, "rid": resource_id}).scalar() or 0
            
            if user_qty < quantity:
                return {"success": False, "error": f"Non hai abbastanza materiali! (Possiedi {user_qty})"}
            
            # 3. Calculate time based on Armory level
            armory_level = self.get_guild_armory_level(guild_id)
            # Base time: 30 seconds per unit?
            # Reduction: Level 1 = 100%, Level 2 = 90%, etc.
            base_time_per_unit = 30
            reduction = max(0.2, 1.0 - (armory_level * 0.1))
            total_time = int(quantity * base_time_per_unit * reduction)
            
            # 4. Consume raw materials
            session.execute(text("""
                UPDATE user_resources
                SET quantity = quantity - :qty
                WHERE user_id = :uid AND resource_id = :rid
            """), {"qty": quantity, "uid": user_id, "rid": resource_id})
            
            # 5. Add to queue
            completion_time = datetime.now() + timedelta(seconds=total_time)
            session.execute(text("""
                INSERT INTO refinery_queue (user_id, guild_id, resource_id, quantity, start_time, completion_time, status)
                VALUES (:uid, :gid, :rid, :qty, :start, :end, 'in_progress')
            """), {
                "uid": user_id,
                "gid": guild_id,
                "rid": resource_id,
                "qty": quantity,
                "start": datetime.now(),
                "end": completion_time
            })
            
            session.commit()
            return {"success": True, "completion_time": completion_time, "total_time": total_time}
            
        except Exception as e:
            session.rollback()
            return {"success": False, "error": str(e)}
        finally:
            session.close()

    def complete_refinement(self, queue_id, char_level, prof_level, armory_level):
        """Process completion and generate materials using a single session for atomicity"""
        session = self.db.get_session()
        try:
            job = session.execute(text("""
                SELECT user_id, quantity, resource_id FROM refinery_queue
                WHERE id = :id AND status = 'in_progress'
            """), {"id": queue_id}).fetchone()
            
            if not job:
                return {"success": False, "error": "Job non trovato o già processato"}
            
            user_id, raw_qty, res_id = job
            
            # Fetch resource rarity
            res_info = session.execute(text("SELECT rarity FROM resources WHERE id = :id"), {"id": res_id}).fetchone()
            resource_rarity = res_info[0] if res_info else 1
            
            # Formula (same as before)
            rarity_mult = 0.8 + (resource_rarity * 0.2)
            total_mass = int(raw_qty * (1 + armory_level * 0.05) * rarity_mult)
            total_mass = max(1, total_mass)
            
            t2_boost = 1.0 + (resource_rarity * 0.05)
            t3_boost = 1.0 + (resource_rarity * 0.03)
            
            t2_chance = min(15, (2 + (prof_level * 0.3) + (char_level * 0.05)) * t2_boost)
            t3_chance = min(5, (0.5 + (prof_level * 0.15) + (char_level * 0.02)) * t3_boost)
            
            qty_t3 = int(total_mass * (t3_chance / 100.0) * random.uniform(0.8, 1.2))
            remaining = total_mass - qty_t3
            qty_t2 = int(remaining * (t2_chance / (100.0 - t3_chance)) * random.uniform(0.8, 1.2))
            qty_t1 = max(0, total_mass - qty_t3 - qty_t2)
            
            results = {'Rottami': qty_t1, 'Materiale Pregiato': qty_t2, 'Diamante': qty_t3}
            
            # 2. Update job status to 'completed' and store results
            # NOTE: We NO LONGER add to inventory here, it's done during manual 'claim'
            session.execute(text("""
                UPDATE refinery_queue 
                SET status = 'completed', result_t1 = :t1, result_t2 = :t2, result_t3 = :t3
                WHERE id = :id
            """), {"id": queue_id, "t1": qty_t1, "t2": qty_t2, "t3": qty_t3})
            
            # 3. Award profession XP (this is fine to do here as it's proportional to work done)
            xp_gained = raw_qty * 5
            self.add_profession_xp(user_id, xp_gained)
            
            session.commit()
            return {"success": True, "materials": results, "xp_gained": xp_gained}
        except Exception as e:
            session.rollback()
            print(f"[REFINERY] Error in complete_refinement for job {queue_id}: {e}")
            return {"success": False, "error": str(e)}
        finally:
            session.close()

    def process_refinery_queue(self):
        """Check for completed refinement jobs"""
        session = self.db.get_session()
        results = []
        try:
            now = datetime.now()
            ready = session.execute(text("""
                SELECT rq.id, rq.user_id, rq.guild_id 
                FROM refinery_queue rq
                WHERE rq.status = 'in_progress' AND rq.completion_time <= :now
            """), {"now": now}).fetchall()
            
            from services.user_service import UserService
            from services.guild_service import GuildService
            user_service = UserService()
            guild_service = GuildService()
            
            for qid, uid, gid in ready:
                user = user_service.get_user(uid)
                if not user:
                    print(f"[REFINERY] User {uid} not found for job {qid}. Marking as cancelled.")
                    session.execute(text("UPDATE refinery_queue SET status = 'cancelled' WHERE id = :id"), {"id": qid})
                    continue
                    
                armory_level = self.get_guild_armory_level(gid)
                prof = self.get_profession_info(uid)
                
                res = self.complete_refinement(qid, user.livello, prof['level'], armory_level)
                if res['success']:
                    res['user_id'] = uid
                    results.append(res)
            
            session.commit()
            return results
        finally:
            session.close()

    def claim_user_refinements(self, user_id):
        """Claim all completed jobs for a user and add materials to inventory"""
        # 1. First, process any ready jobs
        self.process_refinery_queue()
        
        session = self.db.get_session()
        try:
            # 2. Find all 'completed' jobs
            jobs = session.execute(text("""
                SELECT id, result_t1, result_t2, result_t3 FROM refinery_queue
                WHERE user_id = :uid AND status = 'completed'
            """), {"uid": user_id}).fetchall()
            
            if not jobs:
                return {"success": False, "error": "Nessun materiale pronto da ritirare."}
            
            totals = {'Rottami': 0, 'Materiale Pregiato': 0, 'Diamante': 0}
            job_ids = []
            
            for jid, t1, t2, t3 in jobs:
                totals['Rottami'] += (t1 or 0)
                totals['Materiale Pregiato'] += (t2 or 0)
                totals['Diamante'] += (t3 or 0)
                job_ids.append(jid)
            
            # 3. Add to user_refined_materials
            for mat_name, total_qty in totals.items():
                if total_qty <= 0: continue
                
                mat_id = session.execute(text("SELECT id FROM refined_materials WHERE name = :n"), {"n": mat_name}).scalar()
                if not mat_id: continue
                
                session.execute(text("""
                    INSERT INTO user_refined_materials (user_id, material_id, quantity)
                    VALUES (:uid, :mid, :q)
                    ON CONFLICT (user_id, material_id) 
                    DO UPDATE SET quantity = user_refined_materials.quantity + EXCLUDED.quantity
                """), {"uid": user_id, "mid": mat_id, "q": total_qty})
            
            # 4. Mark jobs as claimed
            session.execute(text("""
                UPDATE refinery_queue SET status = 'claimed'
                WHERE id IN :ids
            """), {"ids": tuple(job_ids)})
            
            session.commit()
            return {"success": True, "totals": totals, "job_count": len(jobs)}
        except Exception as e:
            session.rollback()
            print(f"[REFINERY] Error claiming for user {user_id}: {e}")
            return {"success": False, "error": str(e)}
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
                # Get material ID by name
                material_id = session.execute(text("""
                    SELECT id FROM refined_materials WHERE name = :name
                """), {"name": resource_name}).scalar()
                
                if not material_id:
                    return {"success": False, "error": f"Material '{resource_name}' not found in database"}
                
                user_quantity = session.execute(text("""
                    SELECT quantity FROM user_refined_materials
                    WHERE user_id = :uid AND material_id = (SELECT id FROM refined_materials WHERE name = :name)
                """), {"uid": user_id, "name": resource_name}).scalar() or 0
                
                if user_quantity < quantity_needed:
                    missing_resources.append(f"{resource_name}: {user_quantity}/{quantity_needed}")
            
            # If missing resources, return detailed error
            if missing_resources:
                # Get emoji for resources
                emoji_map = {
                    "Rottami": "🔩",
                    "Materiale Pregiato": "💎",
                    "Diamante": "💍"
                }
                
                error_msg = f"❌ Risorse insufficienti per craftare {eq_name}!\n\n"
                error_msg += "📦 Costi:\n"
                for resource_name, quantity_needed in resources_needed.items():
                    emoji = emoji_map.get(resource_name, "📦")
                    user_qty = session.execute(text("""
                        SELECT quantity FROM user_refined_materials
                        WHERE user_id = :uid AND material_id = (SELECT id FROM refined_materials WHERE name = :name)
                    """), {"uid": user_id, "name": resource_name}).scalar() or 0
                    
                    status = "✅" if user_qty >= quantity_needed else "❌"
                    error_msg += f"{status} {emoji} {resource_name}: {user_qty}/{quantity_needed}\n"
                
                return {"success": False, "error": error_msg}
            
            # Consume resources
            for resource_name, quantity_needed in resources_needed.items():
                session.execute(text("""
                    UPDATE user_refined_materials
                    SET quantity = quantity - :qty
                    WHERE user_id = :uid AND material_id = (SELECT id FROM refined_materials WHERE name = :name)
                """), {"qty": quantity_needed, "uid": user_id, "name": resource_name})
            
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
        """
        Determine if resources should drop and which ones.
        Returns a list of (resource_id, quantity, image) tuples.
        """
        try:
            mob_level = int(mob_level)
        except (ValueError, TypeError):
            mob_level = 1

        # Base drop chance: 80% for normal mobs, 100% for bosses
        drop_chance = 100 if mob_is_boss else 80
        
        if random.random() * 100 > drop_chance:
            print(f"[DEBUG] CraftingService: Drop roll failed ({drop_chance}%)")
            return []
        
        # Mobs drop 1-2 resources, Bosses drop 3-5
        num_drops = random.randint(3, 5) if mob_is_boss else random.randint(1, 2)
        print(f"[DEBUG] CraftingService: Rolling {num_drops} resources")
        
        drops = []
        session = self.db.get_session()
        try:
            for _ in range(num_drops):
                # Standardized system: mostly common resources (IDs 1, 2, 3)
                # We can roll for specific ID directly to be faster, or use DB
                resource = session.execute(text("""
                    SELECT id, image FROM resources
                    ORDER BY RANDOM()
                    LIMIT 1
                """)).fetchone()
                
                if resource:
                    # Quantity: 1-3 for normal, 5-15 for boss
                    qty = random.randint(5, 15) if mob_is_boss else random.randint(1, 3)
                    drops.append((resource[0], qty, resource[1]))
            
            return drops
        finally:
            session.close()

    def roll_chat_drop(self, chance=20):
        """
        Determine if resources should drop from chat activity.
        Now much more common: 20% chance by default.
        Returns a list of (resource_id, quantity, image) tuples.
        """
        if random.random() * 100 > chance:
            return []
            
        session = self.db.get_session()
        try:
            # Chat drop: 1-2 items, quantity 1-5
            num_items = random.randint(1, 2)
            drops = []
            for _ in range(num_items):
                resource = session.execute(text("""
                    SELECT id, image FROM resources
                    ORDER BY RANDOM()
                    LIMIT 1
                """)).fetchone()
                
                if resource:
                    qty = random.randint(1, 5)
                    drops.append((resource[0], qty, resource[1]))
            
            return drops
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
        
        # Cap at level 50
        MAX_PROFESSION_LEVEL = 50
        if current_level >= MAX_PROFESSION_LEVEL:
            return False  # Already at max level, no XP gain
        
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
            if new_level >= MAX_PROFESSION_LEVEL:
                new_level = MAX_PROFESSION_LEVEL
                break
                
            xp_needed = 100 * (new_level * (new_level + 1) // 2)
            if new_xp >= xp_needed:
                new_level += 1
            else:
                break
        
        # Update stats in database
        session = self.db.get_session()
        try:
            # Update XP
            session.execute(text("""
                INSERT INTO user_stat (user_id, stat_key, value)
                VALUES (:uid, 'profession_xp', :xp)
                ON CONFLICT (user_id, stat_key) 
                DO UPDATE SET value = :xp
            """), {"uid": user_id, "xp": new_xp})
            
            # Update Level
            session.execute(text("""
                INSERT INTO user_stat (user_id, stat_key, value)
                VALUES (:uid, 'profession_level', :lvl)
                ON CONFLICT (user_id, stat_key) 
                DO UPDATE SET value = :lvl
            """), {"uid": user_id, "lvl": new_level})
            
            session.commit()
        finally:
            session.close()
        
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

