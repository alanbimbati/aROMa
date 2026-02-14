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
import json
import random
from datetime import datetime, timedelta
from sqlalchemy import text, func
from models.resources import Resource, UserResource, RefinedMaterial, UserRefinedMaterial, RefineryDaily, RefineryQueue
from models.equipment import Equipment, UserEquipment

class CraftingService:
    """Manages equipment crafting and resources"""
    
    def __init__(self):
        self.db = Database()
        from services.event_dispatcher import EventDispatcher
        self.event_dispatcher = EventDispatcher()
    
    def add_resource_drop(self, user_id, resource_id, quantity=1, source="mob", session=None):
        """Add a resource to user's inventory"""
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
            
        try:
            # Check if user already has this resource
            existing = session.query(UserResource).filter_by(
                user_id=user_id, 
                resource_id=resource_id
            ).first()
            
            if existing:
                # Update quantity
                existing.quantity += quantity
            else:
                # Insert new
                new_res = UserResource(
                    user_id=user_id,
                    resource_id=resource_id,
                    quantity=quantity,
                    source=source
                )
                session.add(new_res)
            
            if local_session:
                session.commit()
            
            # Log event for achievements
            self.event_dispatcher.log_event(
                event_type="RESOURCE_DROP",
                user_id=user_id,
                value=quantity,
                context={"resource_id": resource_id, "source": source},
                session=session
            )
            return True
        except Exception as e:
            if local_session:
                session.rollback()
            print(f"Error adding resource drop: {e}")
            return False
        finally:
            if local_session:
                session.close()
    
    def get_user_resources(self, user_id):
        """Get all raw and refined resources for a user"""
        session = self.db.get_session()
        try:
            # Raw resources
            raw_data = session.query(
                Resource.id, Resource.name, Resource.rarity, func.coalesce(UserResource.quantity, 0)
            ).outerjoin(
                UserResource, (Resource.id == UserResource.resource_id) & (UserResource.user_id == user_id)
            ).filter(
                (func.coalesce(UserResource.quantity, 0) > 0) | (Resource.rarity == 1)
            ).order_by(Resource.rarity.asc(), Resource.name.asc()).all()
            
            # Refined materials
            refined_data = session.query(
                RefinedMaterial.id, RefinedMaterial.name, RefinedMaterial.rarity, func.sum(func.coalesce(UserRefinedMaterial.quantity, 0))
            ).outerjoin(
                UserRefinedMaterial, (RefinedMaterial.id == UserRefinedMaterial.material_id) & (UserRefinedMaterial.user_id == user_id)
            ).group_by(
                RefinedMaterial.id, RefinedMaterial.name, RefinedMaterial.rarity
            ).order_by(RefinedMaterial.rarity.asc()).all()
            
            return {
                'raw': [{
                    'resource_id': row[0],
                    'name': row[1],
                    'rarity': row[2],
                    'quantity': row[3]
                } for row in raw_data],
                'refined': [{
                    'material_id': row[0],
                    'name': row[1],
                    'rarity': row[2],
                    'quantity': row[3]
                } for row in refined_data]
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
            2: 3, # Pregiato -> Diamante
            4: 5, # Frammenti -> Estratto
            5: 6, # Estratto -> Elisir
            7: 8, # Compost -> Concime
            8: 9  # Concime -> Essenza
        }
        
        if valid_upgrades.get(source_id) != target_id:
            return {"success": False, "error": "Upgrade non valido!"}
            
        cost_per_unit = 10
        total_cost = count * cost_per_unit
        
        session = self.db.get_session()
        try:
            # Check source quantity
            user_mat = session.query(UserRefinedMaterial).filter_by(
                user_id=user_id, 
                material_id=source_id
            ).first()
            user_qty = user_mat.quantity if user_mat else 0
            
            if user_qty < total_cost:
                # Get names for error message
                names = session.query(RefinedMaterial).filter(
                    RefinedMaterial.id.in_([source_id, target_id])
                ).all()
                names_dict = {m.id: m.name for m in names}
                return {"success": False, "error": f"Non hai abbastanza {names_dict.get(source_id, 'materiali')}! (Richiesti: {total_cost}, Possiedi: {user_qty})"}
            
            # Consume source
            user_mat.quantity -= total_cost
            
            # Add target (Atomic UPSERT style)
            target_mat = session.query(UserRefinedMaterial).filter_by(
                user_id=user_id, 
                material_id=target_id
            ).first()
            
            if target_mat:
                target_mat.quantity += count
            else:
                new_target = UserRefinedMaterial(
                    user_id=user_id,
                    material_id=target_id,
                    quantity=count
                )
                session.add(new_target)
                
            session.commit()
            
            # Get names for success message
            names = session.query(RefinedMaterial).filter(
                RefinedMaterial.id.in_([source_id, target_id])
            ).all()
            names_dict = {m.id: m.name for m in names}
            
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

    def get_daily_refinable_resources(self, category=None, session=None):
        """Get the refinable resources for today, optionally filtered by category"""
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
            
        try:
            now = datetime.now().date()
            # We check for today's entries.
            entries = session.query(RefineryDaily).filter(
                func.date(RefineryDaily.date) == now
            ).all()
            
            # Define categories by ID ranges
            categories = {
                'equipment': [1, 2, 3, 6, 7],
                'alchemy': [4, 5],
                'garden': [8] # Semi di Wumpa
            }
            
            # If category is provided, only look at that one
            if category and category in categories:
                target_categories = {category: categories[category]}
            else:
                target_categories = categories
            
            selected_ids = [e.resource_id for e in entries]
            final_resources = []
            
            # Ensure we have one for each target category
            for cat_name, cat_ids in target_categories.items():
                # Check if this category is represented
                category_entry = next((e for e in entries if e.category == cat_name), None)
                if category_entry:
                    res_id = category_entry.resource_id
                else:
                    # Pick new for this category
                    available = session.query(Resource.id).filter(Resource.id.in_(cat_ids)).all()
                    if available:
                        res_id = random.choice([r[0] for r in available])
                        # Save it
                        new_daily = RefineryDaily(date=datetime.now(), category=cat_name, resource_id=res_id)
                        session.add(new_daily)
                        session.flush() # Ensure it's in the session
                    else:
                        continue
                
                # Fetch details
                res = session.query(Resource).filter_by(id=res_id).first()
                if res:
                    final_resources.append({"id": res.id, "name": res.name, "category": cat_name})

            if not entries and final_resources:
                session.commit()
                
            return final_resources
        finally:
            if local_session:
                session.close()

    def get_daily_refinable_resource(self, category=None, session=None):
        """Legacy compatibility/Helper: returns one resource for the given category"""
        res = self.get_daily_refinable_resources(category=category, session=session)
        return res[0] if res else None

    def start_refinement(self, guild_id, user_id, resource_id, quantity, category='equipment'):
        """Start refining raw items into materials. Defaults to equipment category."""
        session = self.db.get_session()
        try:
            # 1. Check if resource is refinable today in its category
            daily = self.get_daily_refinable_resource(category=category, session=session)
            if not daily or daily['id'] != resource_id:
                return {"success": False, "error": "Questo materiale non può essere lavorato oggi!"}
            
            # 2. Check if user has enough quantity
            user_res = session.query(UserResource).filter_by(
                user_id=user_id, 
                resource_id=resource_id
            ).first()
            user_qty = user_res.quantity if user_res else 0
            
            if user_qty < quantity:
                return {"success": False, "error": f"Non hai abbastanza materiali! (Possiedi {user_qty})"}
            
            # 3. Calculate time based on Armory level
            armory_level = self.get_guild_armory_level(guild_id)
            base_time_per_unit = 30
            reduction = max(0.2, 1.0 - (armory_level * 0.1))
            total_time = int(quantity * base_time_per_unit * reduction)
            
            # 4. Consume raw materials
            user_res.quantity -= quantity
            
            # 5. Add to queue
            completion_time = datetime.now() + timedelta(seconds=total_time)
            new_job = RefineryQueue(
                user_id=user_id,
                guild_id=guild_id,
                resource_id=resource_id,
                quantity=quantity,
                start_time=datetime.now(),
                completion_time=completion_time,
                status='in_progress'
            )
            session.add(new_job)
            
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
            job = session.query(RefineryQueue).filter_by(
                id=queue_id, 
                status='in_progress'
            ).first()
            
            if not job:
                return {"success": False, "error": "Job non trovato o già processato"}
            
            user_id = job.user_id
            raw_qty = job.quantity
            res_id = job.resource_id
            
            # Fetch resource rarity
            res_info = session.query(Resource).filter_by(id=res_id).first()
            resource_rarity = res_info.rarity if res_info else 1
            
            # Formula (same as before)
            rarity_mult = 0.8 + (resource_rarity * 0.2)
            total_mass = int(raw_qty * (1 + armory_level * 0.05) * rarity_mult)
            total_mass = max(1, total_mass)
            
            t2_boost = 1.0 + (resource_rarity * 0.05)
            t3_boost = 1.0 + (resource_rarity * 0.03)
            
            t2_chance = min(15, (2 + (prof_level * 0.3) + (char_level * 0.05)) * t2_boost)
            t3_chance = min(5, (0.5 + (prof_level * 0.15) + (char_level * 0.02)) * t3_boost)
            
            # Determine Category and Material IDs
            # Ranges: 1-3, 6, 7 -> Equip (1,2,3); 4, 5 -> Alchemy (4,5,6); 8+ -> Garden (7,8,9)
            if res_id in [1, 2, 3, 6, 7]:
                mat_ids = [1, 2, 3] # Rottami, Pregiato, Diamante
                mat_names = ['Rottami', 'Materiale Pregiato', 'Diamante']
            elif res_id in [4, 5]:
                mat_ids = [4, 5, 6] # Frammenti, Estratto, Elisir
                mat_names = ['Frammenti Alchemici', 'Estratto Puro', 'Elisir Primordiale']
            else:
                mat_ids = [7, 8, 9] # Compost, Concime, Essenza
                mat_names = ['Compost Organico', 'Concime Arricchito', 'Essenza Botanica']
            
            qty_t3 = int(total_mass * (t3_chance / 100.0) * random.uniform(0.8, 1.2))
            remaining = total_mass - qty_t3
            qty_t2 = int(remaining * (t2_chance / (100.0 - t3_chance)) * random.uniform(0.8, 1.2))
            qty_t1 = max(0, total_mass - qty_t3 - qty_t2)
            
            results = {mat_names[0]: qty_t1, mat_names[1]: qty_t2, mat_names[2]: qty_t3}
            
            # 2. Update job status to 'completed' and store results
            job.status = 'completed'
            job.result_t1 = qty_t1
            job.result_t2 = qty_t2
            job.result_t3 = qty_t3
            # Store the mat_ids for claiming later if needed (though we currently rely on job.result_t1/2/3)
            # We'll use the IDs to look up the materials in claim_user_refinements.
            
            # 3. Award profession XP
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
            ready = session.query(RefineryQueue).filter(
                RefineryQueue.status == 'in_progress',
                RefineryQueue.completion_time <= now
            ).all()
            
            from services.user_service import UserService
            user_service = UserService()
            
            for job in ready:
                uid = job.user_id
                gid = job.guild_id
                qid = job.id
                
                user = user_service.get_user(uid)
                if not user:
                    print(f"[REFINERY] User {uid} not found for job {qid}. Marking as cancelled.")
                    job.status = 'cancelled'
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

    def claim_user_refinements(self, user_id, category=None):
        """Claim all completed jobs for a user and add materials to inventory. Optionally filtered by category."""
        # 1. First, process any ready jobs
        self.process_refinery_queue()
        
        session = self.db.get_session()
        try:
            # 2. Find all 'completed' jobs
            query = session.query(RefineryQueue).filter_by(
                user_id=user_id, 
                status='completed'
            )
            
            # Filter by category if requested
            if category:
                res_ids = {
                    'equipment': [1, 2, 3, 6, 7],
                    'alchemy': [4, 5],
                    'garden': [8]
                }.get(category, [])
                query = query.filter(RefineryQueue.resource_id.in_(res_ids))
            
            jobs = query.all()
            
            if not jobs:
                return {"success": False, "error": "Nessun materiale pronto da ritirare per questa categoria." if category else "Nessun materiale pronto da ritirare."}
            
            totals = {} # Dynamic totals
            
            for job in jobs:
                # Determine Category and Material Names (match complete_refinement mapping)
                if job.resource_id in [1, 2, 3, 6, 7]:
                    mat_names = ['Rottami', 'Materiale Pregiato', 'Diamante']
                elif job.resource_id in [4, 5]:
                    mat_names = ['Frammenti Alchemici', 'Estratto Puro', 'Elisir Primordiale']
                else:
                    mat_names = ['Compost Organico', 'Concime Arricchito', 'Essenza Botanica']

                # Accumulate
                for i, name in enumerate(mat_names):
                    val = getattr(job, f"result_t{i+1}") or 0
                    totals[name] = totals.get(name, 0) + val
                
                job.status = 'claimed'
            
            # 3. Add to user_refined_materials
            for mat_name, total_qty in totals.items():
                if total_qty <= 0: continue
                
                mat = session.query(RefinedMaterial).filter_by(name=mat_name).first()
                if not mat: continue
                
                user_mat = session.query(UserRefinedMaterial).filter_by(
                    user_id=user_id, 
                    material_id=mat.id
                ).first()
                
                if user_mat:
                    user_mat.quantity += total_qty
                else:
                    new_user_mat = UserRefinedMaterial(
                        user_id=user_id,
                        material_id=mat.id,
                        quantity=total_qty
                    )
                    session.add(new_user_mat)
            
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
            equipment = session.query(Equipment).filter_by(id=equipment_id).first()
            
            if not equipment:
                return {"success": False, "error": "Equipment not found"}
            
            eq_name = equipment.name
            eq_rarity = equipment.rarity
            crafting_time = equipment.crafting_time
            crafting_requirements = equipment.crafting_requirements
            
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
            active_jobs = session.query(func.count(RefineryQueue.id)).filter(
                RefineryQueue.guild_id == guild_id,
                RefineryQueue.status == 'in_progress'
            ).scalar() or 0
            
            if active_jobs >= armory_level:
                return {
                    "success": False,
                    "error": f"Tutti gli slot di crafting sono occupati ({active_jobs}/{armory_level}). Attendi che un crafting finisca!"
                }
            
            # Check if user has required resources (by name)
            missing_resources = []
            for resource_name, quantity_needed in resources_needed.items():
                # Get material ID by name
                material = session.query(RefinedMaterial).filter_by(name=resource_name).first()
                
                if not material:
                    return {"success": False, "error": f"Material '{resource_name}' not found in database"}
                
                user_mat = session.query(UserRefinedMaterial).filter_by(
                    user_id=user_id, 
                    material_id=material.id
                ).first()
                user_quantity = user_mat.quantity if user_mat else 0
                
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
                    material = session.query(RefinedMaterial).filter_by(name=resource_name).first()
                    user_mat = session.query(UserRefinedMaterial).filter_by(
                        user_id=user_id, 
                        material_id=material.id
                    ).first() if material else None
                    user_qty = user_mat.quantity if user_mat else 0
                    
                    status = "✅" if user_qty >= quantity_needed else "❌"
                    error_msg += f"{status} {emoji} {resource_name}: {user_qty}/{quantity_needed}\n"
                
                return {"success": False, "error": error_msg}
            
            # Consume resources
            for resource_name, quantity_needed in resources_needed.items():
                material = session.query(RefinedMaterial).filter_by(name=resource_name).first()
                if material:
                    user_mat = session.query(UserRefinedMaterial).filter_by(
                        user_id=user_id, 
                        material_id=material.id
                    ).first()
                    if user_mat:
                        user_mat.quantity -= quantity_needed
            
            # Add to crafting queue
            completion_time = datetime.now() + timedelta(seconds=crafting_time)
            
            # Wait, the model for crafting_queue is CraftingQueue, imported as such
            from models.crafting import CraftingQueue
            new_job = CraftingQueue(
                guild_id=guild_id,
                user_id=user_id,
                equipment_id=equipment_id,
                start_time=datetime.now(),
                completion_time=completion_time,
                status='in_progress'
            )
            session.add(new_job)
            
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
            from models.crafting import CraftingQueue
            job = session.query(CraftingQueue).filter_by(id=crafting_queue_id).first()
            
            if not job:
                return {"success": False, "error": "Crafting job not found"}
            
            user_id = job.user_id
            equipment_id = job.equipment_id
            completion_time = job.completion_time
            status = job.status
            
            if status != 'in_progress':
                return {"success": False, "error": "Job already completed or cancelled"}
            
            if datetime.now() < completion_time:
                return {"success": False, "error": "Crafting not yet complete"}
            
            # Get base equipment rarity
            equipment = session.query(Equipment).filter_by(id=equipment_id).first()
            base_rarity = equipment.rarity if equipment else 1
            
            # Calculate final rarity based on armory and profession level
            upgrade_chance = (profession_level * 0.5) + (armory_level * 1.0)
            
            final_rarity = base_rarity
            if random.random() * 100 < upgrade_chance:
                final_rarity = min(5, base_rarity + 1)  # Max legendary
            
            # Add item to user's equipment
            # Generate Stats
            import json
            slot = equipment.slot if equipment else 'chest'
            new_stats = self.generate_random_stats(final_rarity, slot)
            
            new_user_eq = UserEquipment(
                user_id=user_id,
                equipment_id=equipment_id,
                equipped=False,
                stats_json=json.dumps(new_stats)
            )
            session.add(new_user_eq)
            
            # Mark crafting as complete
            job.status = 'completed'
            job.actual_rarity = final_rarity
            
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
            from models.guild import Guild
            guild = session.query(Guild).filter_by(id=guild_id).first()
            return guild.armory_level if guild else 1
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
                resource = session.query(Resource).order_by(func.random()).first()
                
                if resource:
                    # Quantity: 1-3 for normal, 5-15 for boss
                    qty = random.randint(5, 15) if mob_is_boss else random.randint(1, 3)
                    drops.append((resource.id, qty, resource.image))
            
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
        from models.stats import UserStat
        session = self.db.get_session()
        try:
            xp_stat = session.query(UserStat).filter_by(
                user_id=user_id, 
                stat_key='profession_xp'
            ).first()
            
            level_stat = session.query(UserStat).filter_by(
                user_id=user_id, 
                stat_key='profession_level'
            ).first()
            
            return {
                "level": int(level_stat.value) if level_stat else 1, 
                "xp": int(xp_stat.value) if xp_stat else 0
            }
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
        from models.stats import UserStat
        session = self.db.get_session()
        try:
            # Update XP (Atomic UPSERT style)
            xp_entry = session.query(UserStat).filter_by(
                user_id=user_id, 
                stat_key='profession_xp'
            ).first()
            if xp_entry:
                xp_entry.value = new_xp
            else:
                xp_entry = UserStat(user_id=user_id, stat_key='profession_xp', value=new_xp)
                session.add(xp_entry)
            
            # Update Level
            lvl_entry = session.query(UserStat).filter_by(
                user_id=user_id, 
                stat_key='profession_level'
            ).first()
            if lvl_entry:
                lvl_entry.value = new_level
            else:
                lvl_entry = UserStat(user_id=user_id, stat_key='profession_level', value=new_level)
                session.add(lvl_entry)
            
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
            from models.crafting import CraftingQueue
            from datetime import datetime
            now = datetime.now()
            ready_jobs = session.query(CraftingQueue).filter(
                CraftingQueue.status == 'in_progress',
                CraftingQueue.completion_time <= now
            ).all()
            
            from services.guild_service import GuildService
            guild_service = GuildService()
            
            for job in ready_jobs:
                job_id = job.id
                user_id = job.user_id
                eq_id = job.equipment_id
                
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
                    equipment = session.query(Equipment).filter_by(id=eq_id).first()
                    res['item_name'] = equipment.name if equipment else "Oggetto"
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

