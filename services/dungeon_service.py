from database import Database
from models.dungeon import Dungeon, DungeonParticipant
from models.dungeon_progress import DungeonProgress
from models.pve import Mob
from models.user import Utente
from models.system_state import SystemState
import datetime
import random
import csv
import json
import os

class DungeonService:
    def __init__(self):
        self.db = Database()
        self.dungeons_cache = self.load_dungeons()

    def check_daily_dungeon_trigger(self, chat_id=None):
        """Checks if a dungeon should start or if hype phase is due. Run periodically."""
        if not chat_id:
            from settings import GRUPPO_AROMA
            chat_id = GRUPPO_AROMA
        
        session = self.db.get_session()
        try:
            now = datetime.datetime.now()
            today_date = now.date()
            
            # 1. Check if there is an ACTIVE dungeon (running, not registration)
            # If so, we NEVER start or schedule anything else.
            active_running = session.query(Dungeon).filter(
                Dungeon.chat_id == chat_id,
                Dungeon.status == "active"
            ).first()
            
            if active_running:
                return

            # 2. Check for a dungeon in 'registration' status
            reg = session.query(Dungeon).filter(
                Dungeon.chat_id == chat_id,
                Dungeon.status == "registration"
            ).first()
            
            if reg:
                # If active, check if in hype phase and ready to start
                if reg.is_hype_active:
                    # 5 minutes hype duration
                    trigger_time = reg.hype_start_time + datetime.timedelta(minutes=5)
                    if now >= trigger_time:
                        print(f"[DUNGEON] Hype finished. Starting dungeon!")
                        session.close()
                        return self.start_dungeon_auto(chat_id)
                else:
                    # If Hype is NOT active, check if it's time to start hype.
                    if reg.scheduled_for and now >= reg.scheduled_for:
                             print(f"[DUNGEON] Triggering Hype Phase for {reg.name}")
                             session.close()
                             return self.start_hype_phase(chat_id)

                session.close()
                return

            # 3. No active or registration dungeon. Schedule if needed.
            today_count = session.query(Dungeon).filter(
                Dungeon.chat_id == chat_id,
                Dungeon.created_at >= datetime.datetime.combine(today_date, datetime.time.min)
            ).count()
            
            if today_count < 3 and 8 <= now.hour < 22:
                 last = session.query(Dungeon).filter(Dungeon.chat_id == chat_id).order_by(Dungeon.created_at.desc()).first()
                 if not last or last.status in ["completed", "failed"]:
                     if last and last.completed_at:
                         if now < last.completed_at + datetime.timedelta(hours=3):
                             return
                     self.schedule_daily_dungeon(chat_id, session=session)
        except Exception as e:
            print(f"Error in check_daily_dungeon_trigger: {e}")
        finally:
            if 'session' in locals() and session: session.close()

    def schedule_daily_dungeon(self, chat_id, session=None):
        """Schedules a dungeon start in the near future (30-120 mins)"""
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
            
        try:
            now = datetime.datetime.now()
            
            # Determine next dungeon index from SystemState
            current_idx_str = SystemState.get_val(session, 'current_dungeon_index', '1')
            current_idx = int(current_idx_str)
            
            # Validation: cap at 20 or go random
            dungeon_def_id = current_idx
            if dungeon_def_id > 20:
                dungeon_def_id = random.randint(1, 20)
                
            dungeon_def = self.get_dungeon_def(dungeon_def_id)
            if not dungeon_def:
                print(f"[ERROR] Could find dungeon def {dungeon_def_id}. Resetting to 1.")
                dungeon_def_id = 1
                dungeon_def = self.get_dungeon_def(1)
            
            # Schedule for 30-120 minutes from now
            delay_mins = random.randint(30, 120)
            scheduled_time = now + datetime.timedelta(minutes=delay_mins)
            
            if scheduled_time.hour >= 23:
                return

            print(f"[DUNGEON] Scheduling next dungeon: {dungeon_def['name']} (ID {dungeon_def_id}) at {scheduled_time}")
            
            new_dungeon = Dungeon(
                name=dungeon_def['name'],
                chat_id=chat_id,
                total_stages=len(dungeon_def['steps']),
                status="registration",
                dungeon_def_id=dungeon_def_id,
                stats=json.dumps({'damage_taken': 0, 'deaths': 0, 'items_used': 0}),
                score=None,
                scheduled_for=scheduled_time,
                is_hype_active=False
            )
            session.add(new_dungeon)
            session.commit()
            
        except Exception as e:
            print(f"Error in schedule_daily_dungeon: {e}")
            session.rollback()
        finally:
            if local_session:
                session.close()

    def start_hype_phase(self, chat_id):
        """Sends the hype message and starts the countdown state"""
        session = self.db.get_session()
        dungeon = session.query(Dungeon).filter(
            Dungeon.chat_id == chat_id,
            Dungeon.status == "registration",
            Dungeon.is_hype_active == False
        ).first()
        
        if not dungeon:
            session.close()
            return
            
        dungeon.is_hype_active = True
        dungeon.hype_start_time = datetime.datetime.now()
        session.commit()
        session.close()
        
        # We need to send the message. Ideally return an event?
        # Or just print/return it here and let caller handle.
        # But `check_daily_dungeon_trigger` is called by scheduler.
        # We probably need a way to send messages from here or return events.
        # For now, let's return the event info.
        return "DUNGEON_PREANNOUNCED"

    def start_dungeon_auto(self, chat_id):
        """Automatically starts the dungeon and joins ALL users."""
        session = self.db.get_session()
        try:
            dungeon = session.query(Dungeon).filter(
                Dungeon.chat_id == chat_id,
                Dungeon.status == "registration"
            ).first()
            
            if not dungeon:
                print(f"[ERROR] start_dungeon_auto: No registration dungeon found for chat {chat_id}")
                session.close()
                return
                
            print(f"[DUNGEON] Starting Auto-Join for dungeon {dungeon.id} ({dungeon.name})")
            
            # Auto-Join Logic
            # Strategy: Join all users who have a record in Utente table.
            # Ideally we filter by those who are present in the chat, but we lack a strict mapping.
            # If we assume the bot is mono-group or primarily for this group:
            all_users = session.query(Utente).all()
            
            count = 0
            for user in all_users:
                # Check if already joined (shouldn't be, but safety first)
                exists = session.query(DungeonParticipant).filter_by(
                    dungeon_id=dungeon.id,
                    user_id=user.id_telegram
                ).first()
                
                if not exists:
                    dp = DungeonParticipant(
                        dungeon_id=dungeon.id, 
                        user_id=user.id_telegram
                    )
                    session.add(dp)
                    count += 1
            
            session.flush()
            print(f"[DUNGEON] Auto-joined {count} users.")
            
            # Start Dungeon
            dungeon.status = "active"
            dungeon.current_stage = 1
            dungeon.start_time = datetime.datetime.now()
            
            # Spawn Step 1
            # We call spawn_step using the SAME session to ensure atomicity
            events, mob_ids = self.spawn_step(dungeon.id, 1, session=session)
            
            session.commit()
            
            # Return Event for Main to handle messaging
            return {
                "type": "DUNGEON_STARTED",
                "dungeon_name": dungeon.name,
                "participant_count": count,
                "events": events
            }
            
        except Exception as e:
            print(f"[ERROR] start_dungeon_auto failed: {e}")
            session.rollback()
            return None
        finally:
            session.close()

    def load_dungeons(self):
        """Load dungeons from CSV"""
        dungeons = {}
        try:
            with open('data/dungeons.csv', 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, skipinitialspace=True)
                for row in reader:
                    # Strip whitespace from all string values
                    row = {k: v.strip() if isinstance(v, str) else v for k, v in row.items()}
                    
                    row['id'] = int(row['id'])
                    row['difficulty'] = int(row['difficulty'])
                    # Parse rewards JSON
                    try:
                        raw_rewards = row['rewards'].strip()
                        # If it's wrapped in literal double quotes from CSV export, strip them
                        while raw_rewards.startswith('"') and raw_rewards.endswith('"'):
                            raw_rewards = raw_rewards[1:-1].strip()
                        # Handle escaped double quotes
                        raw_rewards = raw_rewards.replace('""', '"')
                        
                        if not raw_rewards or raw_rewards == '{}':
                            row['rewards'] = {}
                        else:
                            row['rewards'] = json.loads(raw_rewards)
                    except Exception as e:
                        print(f"[ERROR] Failed to parse rewards for dungeon {row['id']}: {e}. Raw: {row['rewards']}")
                        row['rewards'] = {}
                    # Parse steps JSON
                    try:
                        raw_steps = row['steps'].strip()
                        while raw_steps.startswith('"') and raw_steps.endswith('"'):
                            raw_steps = raw_steps[1:-1].strip()
                        raw_steps = raw_steps.replace('""', '"')
                        row['steps'] = json.loads(raw_steps)
                    except Exception as e:
                        # print(f"[ERROR] Failed to parse steps for dungeon {row['id']}: {e}. Raw: {row['steps']}")
                        row['steps'] = []
                    dungeons[row['id']] = row
        except Exception as e:
            print(f"Error loading dungeons: {e}")
        return dungeons

    def get_dungeon_def(self, dungeon_def_id):
        return self.dungeons_cache.get(dungeon_def_id)

    def get_user_progress(self, user_id, session=None):
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
        progress = session.query(DungeonProgress).filter_by(user_id=user_id).all()
        if local_session:
            session.close()
        return progress

    def can_access_dungeon(self, user_id, dungeon_def_id, session=None):
        if dungeon_def_id == 1:
            return True
        
        # Check if previous dungeon is completed
        prev_id = dungeon_def_id - 1
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
            
        completed = session.query(DungeonProgress).filter_by(
            user_id=user_id, 
            dungeon_def_id=prev_id
        ).first()
        
        if local_session:
            session.close()
        
        return completed is not None

    def create_dungeon(self, chat_id, dungeon_def_id, creator_id, session=None):
        """Starts dungeon registration for a specific dungeon definition"""
        dungeon_def = self.get_dungeon_def(dungeon_def_id)
        if not dungeon_def:
            return None, "Dungeon non trovato."

        # Check access for creator
        # We need session for can_access_dungeon if we want to be safe, but it handles its own session if None
        # However, if we are in a transaction, we should pass it.
        
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
            
        if not self.can_access_dungeon(creator_id, dungeon_def_id, session=session):
            print(f"[DEBUG] create_dungeon: Access denied for user {creator_id} to dungeon {dungeon_def_id}")
            if local_session:
                session.close()
            return None, "Non hai ancora sbloccato questo dungeon! Completa prima i precedenti."
        
        # Cleanup ghost dungeons first
        self._cleanup_ghost_dungeons(chat_id, session)
        
        # Check if there's already an active dungeon in this chat
        active = session.query(Dungeon).filter(
            Dungeon.chat_id == chat_id,
            Dungeon.status.in_(["registration", "active"])
        ).first()
        
        if active:
            print(f"[DEBUG] create_dungeon: Active dungeon already exists in chat {chat_id}: {active.name} (status: {active.status})")
            if local_session:
                session.close()
            return None, f"C'è già un dungeon attivo in questo gruppo: **{active.name}**"
            
        new_dungeon = Dungeon(
            name=dungeon_def['name'],
            chat_id=chat_id,
            total_stages=len(dungeon_def['steps']),
            status="registration",
            dungeon_def_id=dungeon_def_id,
            stats=json.dumps({'damage_taken': 0, 'deaths': 0, 'items_used': 0}),
            score=None
        )
        session.add(new_dungeon)
        if local_session:
            session.commit()
        else:
            session.flush()
            
        d_id = new_dungeon.id
        
        # Add creator as participant automatically
        participant = DungeonParticipant(dungeon_id=d_id, user_id=creator_id)
        session.add(participant)
        
        if local_session:
            session.commit()
            session.close()
        else:
            session.flush()
        
        return d_id, f"🏰 **Dungeon Creato: {dungeon_def['name']}** (Difficoltà: {dungeon_def['difficulty']})\n\n{dungeon_def['description']}\n\nIscrivetevi usando `/join`!\nQuando siete pronti, l'admin può usare `/start_dungeon`."

    def join_dungeon(self, chat_id, user_id, session=None):
        """Adds a participant to the current registration"""
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
        
        dungeon = session.query(Dungeon).filter(
            Dungeon.chat_id == chat_id,
            Dungeon.status == "registration"
        ).first()
        
        if not dungeon:
            if local_session:
                session.close()
            return False, "Non c'è nessuna iscrizione aperta per un dungeon in questo gruppo."
            
        # Check access for joiner
        if dungeon.dungeon_def_id:
            if not self.can_access_dungeon(user_id, dungeon.dungeon_def_id, session=session):
                if local_session:
                    session.close()
                return False, "🔒 Non hai ancora sbloccato questo dungeon! Completa i precedenti."

        # Check if already joined
        exists = session.query(DungeonParticipant).filter_by(
            dungeon_id=dungeon.id,
            user_id=user_id
        ).first()
        
        if exists:
            if local_session:
                session.close()
            return False, "Ti sei già iscritto a questo dungeon!"
            
        participant = DungeonParticipant(dungeon_id=dungeon.id, user_id=user_id)
        session.add(participant)
        
        if local_session:
            session.commit()
        else:
            session.flush()
        
        # Verify persistence
        check = session.query(DungeonParticipant).filter_by(dungeon_id=dungeon.id, user_id=user_id).first()
        if not check:
            print(f"[ERROR] join_dungeon: Participant {user_id} NOT found after commit!")
            if local_session:
                session.close()
            return False, "Errore di sistema: iscrizione non salvata."
            
        if local_session:
            session.close()
        return True, "Ti sei iscritto con successo al dungeon! ⚔️"

    def start_dungeon(self, chat_id, session=None):
        """Starts the dungeon and spawns the first step mobs"""
        print(f"[DEBUG] start_dungeon called for chat_id: {chat_id}")
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
        
        dungeon = session.query(Dungeon).filter(
            Dungeon.chat_id == chat_id,
            Dungeon.status == "registration"
        ).first()
        
        if not dungeon:
            if local_session:
                session.close()
            return False, "Non c'è nessun dungeon in fase di iscrizione.", []
            
        participants = session.query(DungeonParticipant).filter_by(dungeon_id=dungeon.id).all()
        if not participants:
            if local_session:
                session.close()
            return False, "Nessun partecipante iscritto! Almeno una persona deve partecipare.", []
            
        dungeon.status = "active"
        dungeon.current_stage = 1
        dungeon.start_time = datetime.datetime.now()
        d_id = dungeon.id
        d_def_id = dungeon.dungeon_def_id
        
        if local_session:
            session.flush()
        else:
            session.flush()
        
        # Spawn first step
        # Note: spawn_step creates its own session if not passed, but we should pass it if we are in a transaction
        # However, spawn_step calls pve.spawn_specific_mob which might commit.
        # Let's check spawn_step.
        
        events, mob_ids = self.spawn_step(d_id, 1, session=session)
        
        if local_session:
            session.commit()
            session.close()
        
        return True, "Dungeon Iniziato", events

    def spawn_step(self, dungeon_id, stage_num, session=None):
        """Spawns mobs for the specific stage"""
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
            
        dungeon = session.query(Dungeon).filter_by(id=dungeon_id).first()
        if not dungeon or not dungeon.dungeon_def_id:
            if local_session:
                session.close()
            return "Errore dungeon."
            
        dungeon_def = self.get_dungeon_def(dungeon.dungeon_def_id)
        if not dungeon_def:
            if local_session:
                session.close()
            return "Definizione dungeon non trovata."
            
        steps = dungeon_def['steps']
        if stage_num > len(steps):
            if local_session:
                session.close()
            return "Errore stage."
            
        step_data = steps[stage_num - 1]
        
        from services.pve_service import PvEService
        pve = PvEService()
        
        events = []
        
        # Handle Dialogue
        if 'dialogue' in step_data:
            diag = step_data['dialogue']
            events.append({
                'type': 'message',
                'content': diag.get('text', '')
            })
            events.append({
                'type': 'delay',
                'seconds': diag.get('delay', 3)
            })

        # Refactoring to capture IDs correctly
        mob_ids = []
        final_msgs = []
        
        # Handle Mobs
        if 'mobs' in step_data:
            for mob_entry in step_data['mobs']:
                name = mob_entry['name']
                count = mob_entry.get('count', 1)
                for _ in range(count):
                    success, m, mob_id = pve.spawn_specific_mob(mob_name=name, chat_id=dungeon.chat_id, ignore_limit=True, session=session)
                    print(f"[DEBUG] spawn_specific_mob result: success={success}, mob_id={mob_id}, name={name}, chat_id={dungeon.chat_id}")
                    if success:
                        self._assign_mob_to_dungeon(mob_id, dungeon_id, session=session)
                        # Apply pending effects
                        applied = pve.apply_pending_effects(mob_id, dungeon.chat_id, session=session)
                        # We don't send messages here, they should be handled by the caller or added to events
                        for app in applied:
                            events.append({
                                'type': 'message',
                                'content': f"💥 **{app['effect']}** esplode su {name}! Danni: {app['damage']}"
                            })
                        final_msgs.append(m)
                        mob_ids.append(mob_id)
        
        # Handle Boss
        if 'boss' in step_data:
            boss_name = step_data['boss']
            success, m, mob_id = pve.spawn_boss(boss_name=boss_name, chat_id=dungeon.chat_id, ignore_limit=True, session=session)
            print(f"[DEBUG] spawn_boss result: success={success}, mob_id={mob_id}, name={boss_name}, chat_id={dungeon.chat_id}")
            if success:
                self._assign_mob_to_dungeon(mob_id, dungeon_id, session=session)
                final_msgs.append(m)
                mob_ids.append(mob_id)
                
        if final_msgs:
            events.append({
                'type': 'spawn',
                'content': "\n".join(final_msgs),
                'mob_ids': mob_ids
            })
        
        if local_session:
            session.commit()
            session.close()
        else:
            session.flush()
                
        return events, mob_ids

    def _assign_mob_to_dungeon(self, mob_id, dungeon_id, session=None):
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
            
        mob = session.query(Mob).filter_by(id=mob_id).first()
        if mob:
            mob.dungeon_id = dungeon_id
            if local_session:
                session.commit()
            else:
                session.flush()
            print(f"[DEBUG] Assigned mob {mob_id} to dungeon {dungeon_id}. Mob dungeon_id: {mob.dungeon_id}")
            
        if local_session:
            session.close()

    def check_step_completion(self, dungeon_id, session=None):
        """Checks if all mobs in the current step are dead. If so, advances."""
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
        
        # Check if any live mob exists for this dungeon
        live_mobs = session.query(Mob).filter_by(dungeon_id=dungeon_id, is_dead=False).count()
        
        if live_mobs > 0:
            if local_session:
                session.close()
            return [], [] # Not done yet
            
        # All dead, advance
        dungeon = session.query(Dungeon).filter_by(id=dungeon_id).first()
        if not dungeon or dungeon.status != "active":
            if local_session:
                session.close()
            return [], []
            
        events, mob_ids = self.advance_dungeon(dungeon_id, session=session)
        
        if local_session:
            session.close()
        return events, mob_ids

    def advance_dungeon(self, dungeon_id, session=None):
        """Moves to next stage or completes dungeon"""
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
            
        dungeon = session.query(Dungeon).filter_by(id=dungeon_id).first()
        
        dungeon.current_stage += 1
        current_stage = dungeon.current_stage
        total_stages = dungeon.total_stages
        
        if local_session:
            session.commit()
            session.close()
        else:
            session.flush()
        
        if current_stage <= total_stages:
            # Pass session if shared? spawn_step creates its own if not passed.
            # But we closed local session above if local.
            # If shared, we can pass it.
            events, mob_ids = self.spawn_step(dungeon_id, current_stage, session=session if not local_session else None)
            # Prepend stage completion message
            events.insert(0, {
                'type': 'message',
                'content': f"✅ **Stage Completato!**\nPreparatevi per il prossimo scontro!\n\n**Stage {current_stage}/{total_stages}**"
            })
            return events, mob_ids
        else:
            completion_msg = self.complete_dungeon(dungeon_id, session=session if not local_session else None)
            return [{'type': 'message', 'content': completion_msg}], []

    def complete_dungeon(self, dungeon_id, session=None):
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
            
        dungeon = session.query(Dungeon).filter_by(id=dungeon_id).first()
        dungeon.status = "completed"
        dungeon.completed_at = datetime.datetime.now()
        
        # Calculate Score
        score, details = self.calculate_score(dungeon)
        dungeon.score = score
        
        # Save Progress for all participants
        participants = session.query(DungeonParticipant).filter_by(dungeon_id=dungeon_id).all()
        for p in participants:
            # Update DungeonProgress
            prog = session.query(DungeonProgress).filter_by(
                user_id=p.user_id, 
                dungeon_def_id=dungeon.dungeon_def_id
            ).first()
            
            if not prog:
                prog = DungeonProgress(
                    user_id=p.user_id,
                    dungeon_def_id=dungeon.dungeon_def_id,
                    best_rank=score,
                    times_completed=1
                )
                session.add(prog)
            else:
                prog.times_completed += 1
                # Update rank if better (Z > S > A > B > C > D > E > F)
                ranks = ['F', 'E', 'D', 'C', 'B', 'A', 'S', 'Z']
                current_rank_idx = ranks.index(prog.best_rank) if prog.best_rank in ranks else -1
                new_rank_idx = ranks.index(score) if score in ranks else -1
                
                if new_rank_idx > current_rank_idx:
                    prog.best_rank = score
                    
        # Cleanup: Mark all mobs in this dungeon as dead
        mobs = session.query(Mob).filter_by(dungeon_id=dungeon_id, is_dead=False).all()
        for m in mobs:
            m.is_dead = True
            m.health = 0

        # Distribute Rewards
        d_def = self.get_dungeon_def(dungeon.dungeon_def_id)
        rewards = d_def.get('rewards', {}) if d_def else {}
        wumpa = rewards.get('wumpa', 0)
        exp = rewards.get('exp', 0)
        
        from services.user_service import UserService
        us = UserService()
        
        for p in participants:
            us.add_points_by_id(p.user_id, wumpa, session=session)
            us.add_exp_by_id(p.user_id, exp, session=session)
            
        if local_session:
            session.commit()
            
        # NEW: Advance global index upon successful completion
        try:
             current_idx_str = SystemState.get_val(session, 'current_dungeon_index', '1')
             current_idx = int(current_idx_str)
             if current_idx <= 20:
                 SystemState.set_val(session, 'current_dungeon_index', current_idx + 1)
                 print(f"[DUNGEON] Advanced global index to {current_idx + 1}")
        except Exception as e:
             print(f"[ERROR] Failed to advance dungeon index: {e}")

        if local_session:
            session.close()
        else:
            session.flush()
        
        return f"🏆 **DUNGEON COMPLETATO!** 🏆\n\n**Rango: {score}**\n{details}\n\nRicompense:\n+{wumpa} Wumpa, +{exp} EXP a tutti!"

    def calculate_score(self, dungeon):
        """Calculate F-Z score based on time, deaths, items"""
        # Load stats
        try:
            stats = json.loads(dungeon.stats)
        except:
            stats = {'damage_taken': 0, 'deaths': 0, 'items_used': 0}
            
        deaths = stats.get('deaths', 0)
        items = stats.get('items_used', 0)
        
        # Time
        start = dungeon.start_time
        end = dungeon.completed_at
        duration_mins = (end - start).total_seconds() / 60 if start and end else 999
        
        # Base Score Points
        # Start with 100
        points = 100
        
        # Penalties
        points -= (deaths * 10)
        points -= (items * 5)
        
        # Time penalty: -1 point per minute over expected time (e.g. 5 mins per stage)
        expected_time = dungeon.total_stages * 5
        if duration_mins > expected_time:
            points -= int(duration_mins - expected_time)
            
        # Rank mapping
        if points >= 100: rank = 'Z'
        elif points >= 95: rank = 'S'
        elif points >= 85: rank = 'A'
        elif points >= 75: rank = 'B'
        elif points >= 60: rank = 'C'
        elif points >= 40: rank = 'D'
        elif points >= 20: rank = 'E'
        else: rank = 'F'
        
        details = f"Tempo: {int(duration_mins)}m (Atteso: {expected_time}m)\nMorti: {deaths}\nOggetti: {items}\nPunteggio: {points}"
        return rank, details

    def record_death(self, dungeon_id, session=None):
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
            
        dungeon = session.query(Dungeon).filter_by(id=dungeon_id).first()
        if dungeon:
            try:
                stats = json.loads(dungeon.stats)
            except:
                stats = {'damage_taken': 0, 'deaths': 0, 'items_used': 0}
            
            # Note: This seems to track mob deaths if called from pve_service? 
            # Or player deaths if called from elsewhere? 
            # Given pve_service calls it for dead_mobs, it counts mob deaths as 'deaths'?
            stats['deaths'] = stats.get('deaths', 0) + 1
            dungeon.stats = json.dumps(stats)
            
            if local_session:
                session.commit()
        
        if local_session:
            session.close()

    def record_item_use(self, dungeon_id):
        session = self.db.get_session()
        dungeon = session.query(Dungeon).filter_by(id=dungeon_id).first()
        if dungeon:
            try:
                stats = json.loads(dungeon.stats)
            except:
                stats = {'damage_taken': 0, 'deaths': 0, 'items_used': 0}
            stats['items_used'] += 1
            dungeon.stats = json.dumps(stats)
            session.commit()
        session.close()

    def get_dungeon_participants(self, dungeon_id, session=None):
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
        participants = session.query(DungeonParticipant).filter_by(dungeon_id=dungeon_id).all()
        if local_session:
            session.close()
        return participants

    def _cleanup_ghost_dungeons(self, chat_id, session):
        """Internal helper to fail dungeons with 0 participants"""
        ghosts = session.query(Dungeon).filter(
            Dungeon.chat_id == chat_id,
            Dungeon.status.in_(["registration", "active"])
        ).all()
        
        for dungeon in ghosts:
            participant_count = session.query(DungeonParticipant).filter_by(dungeon_id=dungeon.id).count()
            if participant_count == 0:
                print(f"[DEBUG] _cleanup_ghost_dungeons: Failing ghost dungeon {dungeon.id} ({dungeon.name}) in chat {chat_id}")
                dungeon.status = "failed"
                dungeon.end_time = datetime.datetime.now()
                # Mark associated mobs as dead
                session.query(Mob).filter_by(dungeon_id=dungeon.id, is_dead=False).update({'is_dead': True})
        
        session.commit()

    def get_active_dungeon(self, chat_id, session=None):
        """Returns the active or registering dungeon for the chat"""
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
        
        # Cleanup ghost dungeons first
        self._cleanup_ghost_dungeons(chat_id, session)
        
        dungeon = session.query(Dungeon).filter(
            Dungeon.chat_id == chat_id,
            Dungeon.status.in_(["registration", "active"])
        ).first()
        
        if local_session:
            session.close()
        return dungeon

    def get_user_active_dungeon(self, user_id, session=None):
        """Returns the active dungeon the user is participating in, if any"""
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
            
        dungeon = session.query(Dungeon).join(DungeonParticipant).filter(
            DungeonParticipant.user_id == user_id,
            Dungeon.status == "active"
        ).first()
        
        if local_session:
            session.close()
        return dungeon

    def leave_dungeon(self, chat_id, user_id, session=None):
        """Allows a user to leave the active dungeon"""
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
            
        dungeon = session.query(Dungeon).filter(
            Dungeon.chat_id == chat_id,
            Dungeon.status.in_(["registration", "active"])
        ).first()
        
        if not dungeon:
            if local_session:
                session.close()
            return False, "Nessun dungeon attivo."
            
        participant = session.query(DungeonParticipant).filter_by(
            dungeon_id=dungeon.id,
            user_id=user_id
        ).first()
        
        if not participant:
            if local_session:
                session.close()
            return False, "Non sei un partecipante di questo dungeon."
            
        # Remove participant
        session.delete(participant)
        if local_session:
            session.commit()
        else:
            session.flush()
        
        # Check if any participants remain
        remaining = session.query(DungeonParticipant).filter_by(dungeon_id=dungeon.id).count()
        
        msg = "Sei fuggito dal dungeon!"
        
        if remaining == 0:
            dungeon.status = "failed"
            dungeon.end_time = datetime.datetime.now()
            
            # Mark all mobs in this dungeon as dead so they disappear
            mobs = session.query(Mob).filter_by(dungeon_id=dungeon.id, is_dead=False).all()
            for m in mobs:
                m.is_dead = True
                m.health = 0
                
            if local_session:
                session.commit()
            else:
                session.flush()
            msg += "\n\n💀 **Dungeon Fallito!** Tutti i partecipanti sono fuggiti o morti."
            
        if local_session:
            session.close()
        return True, msg

    def check_dungeon_failure(self, dungeon_id, session=None):
        """Checks if all dungeon participants are dead. If so, fails the dungeon."""
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
            
        dungeon = session.query(Dungeon).filter_by(id=dungeon_id).first()
        
        if not dungeon or dungeon.status != "active":
            if local_session:
                session.close()
            return False, None

        participants = session.query(DungeonParticipant).filter_by(dungeon_id=dungeon.id).all()
        all_dead = True
        
        for p in participants:
            user = session.query(Utente).filter_by(id_telegram=p.user_id).first()
            # Check if user is alive (hp > 0)
            # Note: We assume damage_health has already committed the HP change or we are reading from DB
            current_hp = user.current_hp if user.current_hp is not None else user.health
            if user and current_hp > 0:
                all_dead = False
                break
        
        msg = None
        if all_dead:
            dungeon.status = "failed"
            dungeon.end_time = datetime.datetime.now()
            
            # Mark all mobs in this dungeon as dead so they disappear
            mobs = session.query(Mob).filter_by(dungeon_id=dungeon.id, is_dead=False).all()
            for m in mobs:
                m.is_dead = True
                m.health = 0
            
            if local_session:
                session.commit()
            msg = "\n\n💀 **GAME OVER!**\nTutti gli eroi sono caduti. Il dungeon è fallito!"
            
        if local_session:
            session.close()
        return all_dead, msg
