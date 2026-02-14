import datetime
import random
from database import Database
from models.cultivation import GardenSlot
from models.user import Utente
from models.resources import UserResource
from sqlalchemy import text
from services.event_dispatcher import EventDispatcher

class CultivationService:
    def __init__(self):
        self.db = Database()
        self.event_dispatcher = EventDispatcher()

    def get_garden_slots(self, user_id):
        """Get all garden slots for a user"""
        session = self.db.get_session()
        try:
            slots = session.query(GardenSlot).filter_by(user_id=user_id).order_by(GardenSlot.slot_id).all()
            
            # Check guild level for max slots
            from services.guild_service import GuildService
            guild_service = GuildService()
            guild = guild_service.get_user_guild(user_id)
            
            max_slots = 2 # Default
            if guild:
                # Formula: 2 + (Guild Garden Level // 2) -> Lv 1=2, Lv 2=3, Lv 10=7?
                # Or simplier: Lv 1=3, Lv 10=5?
                # Proposal: 3 base + 1 every 2 levels?
                # Let's say: 
                # Lv 1: 3 Slots
                # Lv 5: 4 Slots
                # Lv 10: 5 Slots
                garden_lvl = guild.get('garden_level', 1) or 1
                if garden_lvl >= 10:
                    max_slots = 5
                elif garden_lvl >= 5:
                    max_slots = 4
                else:
                    max_slots = 3
            
            # Create missing slots if needed
            current_count = len(slots)
            if current_count < max_slots:
                for i in range(current_count + 1, max_slots + 1):
                    new_slot = GardenSlot(user_id=user_id, slot_id=i, status='empty')
                    session.add(new_slot)
                    slots.append(new_slot)
                session.commit()
                
            # Convert to dict to avoid DetachedInstanceError
            result_slots = []
            for s in slots:
                result_slots.append({
                    'slot_id': s.slot_id,
                    'status': s.status,
                    'seed_type': s.seed_type,
                    'completion_time': s.completion_time,
                    'moisture': s.moisture,
                    'rot_time': s.rot_time
                })
                
            return result_slots, max_slots
        finally:
            session.close()

    def plant_seed(self, user_id, slot_id, seed_type):
        """Plant a seed in a slot"""
        session = self.db.get_session()
        try:
            slot = session.query(GardenSlot).filter_by(user_id=user_id, slot_id=slot_id).first()
            if not slot:
                return False, "Slot non trovato"
                
            if slot.status != 'empty':
                return False, "Lo slot non è vuoto!"
                
            # Check if user has seed
            # Use item service or resource? Let's use resources for seeds
            res_id = session.execute(text("SELECT id FROM resources WHERE name = :name"), {"name": seed_type}).scalar()
            if not res_id:
                return False, "Tipo di seme non valido."
                
            user_res = session.query(UserResource).filter_by(user_id=user_id, resource_id=res_id).first()
            if not user_res or user_res.quantity < 1:
                return False, f"Non hai {seed_type}!"
                
            # Consume seed
            user_res.quantity -= 1
            
            # Plant
            now = datetime.datetime.now()
            growth_time = 4 * 3600 # 4 hours in seconds
            
            slot.seed_type = seed_type
            slot.planted_at = now
            slot.completion_time = now + datetime.timedelta(seconds=growth_time)
            slot.status = 'growing'
            slot.moisture = 100
            slot.last_watered_at = now
            
            session.commit()
            session.commit()
            
            # Log event
            self.event_dispatcher.log_event(
                event_type="garden_plant",
                user_id=user_id,
                value=1,
                context={"seed_type": seed_type}
            )
            
            return True, f"Hai piantato {seed_type}! Sarà pronto tra 4 ore."
        except Exception as e:
            session.rollback()
            return False, f"Errore: {e}"
        finally:
            session.close()

    def check_growth(self, user_id):
        """Update status of growing plants for a user"""
        session = self.db.get_session()
        try:
            slots = session.query(GardenSlot).filter_by(user_id=user_id, status='growing').all()
            now = datetime.datetime.now()
            count = 0
            
            for slot in slots:
                # Decay moisture: -5% every check (approx) or based on time?
                # For simplicity, if checked, it decays a bit. 
                # Better: calculate decay based on time since last check/water.
                
                # Check for maturity
                if slot.completion_time and slot.completion_time <= now:
                    if slot.moisture > 0:
                        slot.status = 'ready'
                        # Set rot_time: 2 hours after ready
                        slot.rot_time = now + datetime.timedelta(hours=2)
                        count += 1
                    else:
                        # Stalled growth if no moisture
                        slot.completion_time += datetime.timedelta(minutes=10)
            
            if count > 0:
                session.commit()
            return count
        finally:
            session.close()

    def process_all_growth(self):
        """Find all plants that matured and mark as ready. Return user_ids for notification."""
        session = self.db.get_session()
        try:
            now = datetime.datetime.now()
            matured_info = []
            
            # 1. Update Growing Plants
            growing_slots = session.query(GardenSlot).filter(GardenSlot.status == 'growing').all()
            for slot in growing_slots:
                # Decay moisture: -10% per hour (approx)
                if slot.last_watered_at:
                    hours_since = (now - slot.last_watered_at).total_seconds() / 3600
                    decay = int(hours_since * 10)
                    slot.moisture = max(0, 100 - decay)
                
                if slot.completion_time <= now:
                    if slot.moisture > 0:
                        slot.status = 'ready'
                        slot.rot_time = now + datetime.timedelta(hours=2) # Rot in 2 hours
                        matured_info.append({
                            'user_id': slot.user_id,
                            'seed_type': slot.seed_type,
                            'event': 'ready'
                        })
                    else:
                        # Penalty: stalled growth
                        slot.completion_time += datetime.timedelta(minutes=30)

            # 2. Update Ready Plants (Rotting)
            ready_slots = session.query(GardenSlot).filter(GardenSlot.status == 'ready').all()
            for slot in ready_slots:
                # Decay moisture even when ready
                if slot.last_watered_at:
                    hours_since = (now - slot.last_watered_at).total_seconds() / 3600
                    decay = int(hours_since * 10)
                    slot.moisture = max(0, 100 - decay)

                if slot.rot_time and slot.rot_time <= now:
                    slot.status = 'rotting'
                    slot.rot_time = now + datetime.timedelta(hours=1) # Full rot in another hour
                    matured_info.append({
                        'user_id': slot.user_id,
                        'seed_type': slot.seed_type,
                        'event': 'rotting'
                    })

            # 3. Update Rotting to Rotten
            rotting_slots = session.query(GardenSlot).filter(GardenSlot.status == 'rotting').all()
            for slot in rotting_slots:
                if slot.rot_time and slot.rot_time <= now:
                    slot.status = 'rotten'
                    matured_info.append({
                        'user_id': slot.user_id,
                        'seed_type': slot.seed_type,
                        'event': 'rotten'
                    })
            
            session.commit()
            return matured_info
        except Exception as e:
            print(f"Error processing global garden growth: {e}")
            return []
        finally:
            session.close()

    def harvest_plant(self, user_id, slot_id):
        """Harvest a ready plant"""
        session = self.db.get_session()
        try:
            slot = session.query(GardenSlot).filter_by(user_id=user_id, slot_id=slot_id).first()
            if not slot:
                return False, "Slot non trovato"
            
            if slot.status == 'growing':
                # Check directly if time passed (in case job didn't run)
                if slot.completion_time <= datetime.datetime.now():
                    slot.status = 'ready'
                else:
                    remaining = slot.completion_time - datetime.datetime.now()
                    minutes = int(remaining.total_seconds() / 60)
                    return False, f"La pianta sta ancora crescendo! Torna tra {minutes} minuti."
                    
            if slot.status != 'ready':
                return False, "Non c'è nulla da raccogliere qui."
                
            # Rewards based on seed type and moisture
            wumpa_gain = 0
            special_drops = [] # List of (name, qty)
            
            seed_type = slot.seed_type
            status = slot.status
            moisture = slot.moisture
            
            # Calculate quality multiplier
            quality_mult = 1.0
            if status == 'ready':
                if moisture >= 70:
                    quality_mult = 1.5 # Juicy!
                    drop_msg = "\n✨ **Il raccolto è incredibilmente succoso!** (+50% Wumpa)"
                elif moisture < 20:
                    quality_mult = 0.7 # Dry
                    drop_msg = "\n🏜️ **Il raccolto è secco.** (-30% Wumpa)"
                else:
                    drop_msg = ""
            elif status == 'rotting':
                quality_mult = 0.5
                drop_msg = "\n🤢 **Il raccolto sta marcendo!** (-50% premi)"
            elif status == 'rotten':
                quality_mult = 0.1
                drop_msg = "\n💀 **Il raccolto è marcio.** (-90% premi)"
            else:
                drop_msg = ""

            if seed_type == 'Semi di Wumpa':
                wumpa_gain = random.randint(100, 200)
                roll = random.random()
                if roll < 0.05 * quality_mult:
                    special_drops.append(("Erba Gialla", 1))
                elif roll < 0.25 * quality_mult:
                    special_drops.append(("Erba Verde", 1))
                elif roll < 0.45 * quality_mult:
                    special_drops.append(("Erba Blu", 1))
            
            elif seed_type == 'Seme d\'Erba Verde':
                special_drops.append(("Erba Verde", max(1, int(random.randint(3, 5) * quality_mult))))
                wumpa_gain = random.randint(10, 30)
                
            elif seed_type == 'Seme d\'Erba Blu':
                special_drops.append(("Erba Blu", max(1, int(random.randint(3, 5) * quality_mult))))
                wumpa_gain = random.randint(10, 30)
                
            elif seed_type == 'Seme d\'Erba Gialla':
                special_drops.append(("Erba Gialla", max(1, int(random.randint(1, 2) * quality_mult))))
                wumpa_gain = random.randint(20, 50)
                
            else:
                wumpa_gain = random.randint(20, 50)

            wumpa_gain = int(wumpa_gain * quality_mult)

            # Update User
            user = session.query(Utente).filter_by(id_telegram=user_id).first()
            if wumpa_gain > 0:
                user.points += wumpa_gain
            
            drop_msg = ""
            if special_drops:
                # Add resources
                from services.crafting_service import CraftingService
                cs = CraftingService()
                
                for drop_name, qty in special_drops:
                    res_id = session.execute(text("SELECT id FROM resources WHERE name = :name"), {"name": drop_name}).scalar()
                    if res_id:
                        ur = session.query(UserResource).filter_by(user_id=user_id, resource_id=res_id).first()
                        if ur:
                            ur.quantity += qty
                        else:
                            ur = UserResource(user_id=user_id, resource_id=res_id, quantity=qty)
                            session.add(ur)
                        drop_msg += f"\nHai trovato anche: **{drop_name}** x{qty}!"
            
            # Reset Slot
            slot.status = 'empty'
            slot.seed_type = None
            slot.planted_at = None
            slot.completion_time = None
            
            session.commit()
            
            session.commit()
            
            # Log event for harvest
            self.event_dispatcher.log_event(
                event_type="garden_harvest",
                user_id=user_id,
                value=wumpa_gain,
                context={"seed_type": seed_type}
            )
            
            # Log event for herb discovery/collection
            for drop_name, qty in special_drops:
                 self.event_dispatcher.log_event(
                    event_type="herb_discovery",
                    user_id=user_id,
                    value=1,
                    context={"herb_name": drop_name}
                )

            main_msg = f"Hai raccolto {wumpa_gain} Frutti Wumpa! 🥭" if wumpa_gain > 0 else "Raccolto completato!"
            return True, f"{main_msg}{drop_msg}"
            
        except Exception as e:
            session.rollback()
            return False, f"Errore raccolta: {e}"
        finally:
            session.close()

    def water_plant(self, user_id, slot_id):
        """Restore moisture to 100%"""
        session = self.db.get_session()
        try:
            slot = session.query(GardenSlot).filter_by(user_id=user_id, slot_id=slot_id).first()
            if not slot:
                return False, "Slot non trovato"
                
            if slot.status == 'empty':
                return False, "Non c'è nulla da irrigare qui!"
                
            if slot.moisture >= 100:
                return False, "La terra è già molto umida!"
                
            slot.moisture = 100
            slot.last_watered_at = datetime.datetime.now()
            
            session.commit()
            return True, "Hai irrigato il terreno! 💦 L'umidità è al 100%."
        except Exception as e:
            session.rollback()
            return False, f"Errore irrigazione: {e}"
        finally:
            session.close()
