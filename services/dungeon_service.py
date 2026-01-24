from database import Database
from models.dungeon import Dungeon, DungeonParticipant
from models.dungeon_progress import DungeonProgress
from models.pve import Mob
from models.user import Utente
import datetime
import random
import csv
import json
import os

class DungeonService:
    def __init__(self):
        self.db = Database()
        self.dungeons_cache = self.load_dungeons()

    def load_dungeons(self):
        """Load dungeons from CSV"""
        dungeons = {}
        try:
            with open('data/dungeons.csv', 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    row['id'] = int(row['id'])
                    row['difficulty'] = int(row['difficulty'])
                    # Parse steps JSON
                    try:
                        row['steps'] = json.loads(row['steps'])
                    except:
                        row['steps'] = []
                    # Parse rewards JSON
                    try:
                        row['rewards'] = json.loads(row['rewards'])
                    except:
                        row['rewards'] = {}
                    dungeons[row['id']] = row
        except Exception as e:
            print(f"Error loading dungeons: {e}")
        return dungeons

    def get_dungeon_def(self, dungeon_def_id):
        return self.dungeons_cache.get(dungeon_def_id)

    def get_user_progress(self, user_id):
        session = self.db.get_session()
        progress = session.query(DungeonProgress).filter_by(user_id=user_id).all()
        session.close()
        return progress

    def can_access_dungeon(self, user_id, dungeon_def_id):
        if dungeon_def_id == 1:
            return True
        
        # Check if previous dungeon is completed
        prev_id = dungeon_def_id - 1
        session = self.db.get_session()
        completed = session.query(DungeonProgress).filter_by(
            user_id=user_id, 
            dungeon_def_id=prev_id
        ).first()
        session.close()
        
        return completed is not None

    def create_dungeon(self, chat_id, dungeon_def_id, creator_id):
        """Starts dungeon registration for a specific dungeon definition"""
        dungeon_def = self.get_dungeon_def(dungeon_def_id)
        if not dungeon_def:
            return None, "Dungeon non trovato."

        # Check access for creator
        if not self.can_access_dungeon(creator_id, dungeon_def_id):
            return None, "Non hai ancora sbloccato questo dungeon! Completa prima i precedenti."

        session = self.db.get_session()
        
        # Check if there's already an active dungeon in this chat
        active = session.query(Dungeon).filter(
            Dungeon.chat_id == chat_id,
            Dungeon.status.in_(["registration", "active"])
        ).first()
        
        if active:
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
        session.commit()
        d_id = new_dungeon.id
        
        # Add creator as participant automatically
        participant = DungeonParticipant(dungeon_id=d_id, user_id=creator_id)
        session.add(participant)
        session.commit()
        
        session.close()
        return d_id, f"🏰 **Dungeon Creato: {dungeon_def['name']}** (Difficoltà: {dungeon_def['difficulty']})\n\n{dungeon_def['description']}\n\nIscrivetevi usando `/join`!\nQuando siete pronti, l'admin può usare `/start_dungeon`."

    def join_dungeon(self, chat_id, user_id):
        """Adds a participant to the current registration"""
        session = self.db.get_session()
        
        dungeon = session.query(Dungeon).filter(
            Dungeon.chat_id == chat_id,
            Dungeon.status == "registration"
        ).first()
        
        if not dungeon:
            session.close()
            return False, "Non c'è nessuna iscrizione aperta per un dungeon in questo gruppo."
            
        # Check access for joiner
        if dungeon.dungeon_def_id:
            if not self.can_access_dungeon(user_id, dungeon.dungeon_def_id):
                session.close()
                return False, "🔒 Non hai ancora sbloccato questo dungeon! Completa i precedenti."

        # Check if already joined
        exists = session.query(DungeonParticipant).filter_by(
            dungeon_id=dungeon.id,
            user_id=user_id
        ).first()
        
        if exists:
            session.close()
            return False, "Ti sei già iscritto a questo dungeon!"
            
        participant = DungeonParticipant(dungeon_id=dungeon.id, user_id=user_id)
        session.add(participant)
        session.commit()
        session.close()
        return True, "Ti sei iscritto con successo al dungeon! ⚔️"

    def start_dungeon(self, chat_id):
        """Starts the dungeon and spawns the first step mobs"""
        print(f"[DEBUG] start_dungeon called for chat_id: {chat_id}")
        session = self.db.get_session()
        
        dungeon = session.query(Dungeon).filter(
            Dungeon.chat_id == chat_id,
            Dungeon.status == "registration"
        ).first()
        
        if not dungeon:
            session.close()
            return False, "Non c'è nessun dungeon in fase di iscrizione.", []
            
        participants = session.query(DungeonParticipant).filter_by(dungeon_id=dungeon.id).all()
        if not participants:
            session.close()
            return False, "Nessun partecipante iscritto! Almeno una persona deve partecipare.", []
            
        dungeon.status = "active"
        dungeon.current_stage = 1
        dungeon.start_time = datetime.datetime.now()
        d_id = dungeon.id
        d_def_id = dungeon.dungeon_def_id
        session.commit()
        session.close()
        
        # Spawn first step
        msg, mob_ids = self.spawn_step(d_id, 1)
            
        return True, f"🚀 **Dungeon Iniziato!**\n\n{msg}", mob_ids

    def spawn_step(self, dungeon_id, stage_num):
        """Spawns mobs for the specific stage"""
        session = self.db.get_session()
        dungeon = session.query(Dungeon).filter_by(id=dungeon_id).first()
        if not dungeon or not dungeon.dungeon_def_id:
            session.close()
            return "Errore dungeon."
            
        dungeon_def = self.get_dungeon_def(dungeon.dungeon_def_id)
        if not dungeon_def:
            session.close()
            return "Definizione dungeon non trovata."
            
        steps = dungeon_def['steps']
        if stage_num > len(steps):
            session.close()
            return "Errore stage."
            
        step_data = steps[stage_num - 1]
        session.close()
        
        from services.pve_service import PvEService
        pve = PvEService()
        
        # Refactoring to capture IDs correctly
        mob_ids = []
        final_msgs = []
        
        # Handle Mobs
        if 'mobs' in step_data:
            for mob_entry in step_data['mobs']:
                name = mob_entry['name']
                count = mob_entry.get('count', 1)
                for _ in range(count):
                    success, m, mob_id = pve.spawn_specific_mob(mob_name=name, chat_id=dungeon.chat_id, ignore_limit=True)
                    print(f"[DEBUG] spawn_specific_mob result: success={success}, mob_id={mob_id}, name={name}, chat_id={dungeon.chat_id}")
                    if success:
                        self._assign_mob_to_dungeon(mob_id, dungeon_id)
                        final_msgs.append(m)
                        mob_ids.append(mob_id)
        
        # Handle Boss
        if 'boss' in step_data:
            boss_name = step_data['boss']
            success, m, mob_id = pve.spawn_boss(boss_name=boss_name, chat_id=dungeon.chat_id, ignore_limit=True)
            print(f"[DEBUG] spawn_boss result: success={success}, mob_id={mob_id}, name={boss_name}, chat_id={dungeon.chat_id}")
            if success:
                self._assign_mob_to_dungeon(mob_id, dungeon_id)
                final_msgs.append(m)
                mob_ids.append(mob_id)
                
        return "\n".join(final_msgs), mob_ids

    def _assign_mob_to_dungeon(self, mob_id, dungeon_id):
        session = self.db.get_session()
        mob = session.query(Mob).filter_by(id=mob_id).first()
        if mob:
            mob.dungeon_id = dungeon_id
            session.commit()
        session.close()

    def check_step_completion(self, dungeon_id):
        """Checks if all mobs in the current step are dead. If so, advances."""
        session = self.db.get_session()
        
        # Check if any live mob exists for this dungeon
        live_mobs = session.query(Mob).filter_by(dungeon_id=dungeon_id, is_dead=False).count()
        
        if live_mobs > 0:
            session.close()
            return None, None # Not done yet
            
        # All dead, advance
        dungeon = session.query(Dungeon).filter_by(id=dungeon_id).first()
        if not dungeon or dungeon.status != "active":
            session.close()
            return None, None
            
        msg, mob_ids = self.advance_dungeon(dungeon_id)
        session.close()
        return msg, mob_ids

    def advance_dungeon(self, dungeon_id):
        """Moves to next stage or completes dungeon"""
        session = self.db.get_session()
        dungeon = session.query(Dungeon).filter_by(id=dungeon_id).first()
        
        dungeon.current_stage += 1
        current_stage = dungeon.current_stage
        total_stages = dungeon.total_stages
        
        session.commit()
        session.close()
        
        if current_stage <= total_stages:
            msg, mob_ids = self.spawn_step(dungeon_id, current_stage)
            return f"✅ **Stage Completato!**\nPreparatevi per il prossimo scontro!\n\n**Stage {current_stage}/{total_stages}**\n{msg}", mob_ids
        else:
            return self.complete_dungeon(dungeon_id), []

    def complete_dungeon(self, dungeon_id):
        session = self.db.get_session()
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
            
        session.commit()
        
        # Distribute Rewards (Daily limit check needed?)
        # For now, just give rewards defined in CSV
        dungeon_def = self.get_dungeon_def(dungeon.dungeon_def_id)
        rewards = dungeon_def.get('rewards', {})
        wumpa = rewards.get('wumpa', 0)
        exp = rewards.get('exp', 0)
        
        from services.user_service import UserService
        us = UserService()
        
        reward_msg = []
        for p in participants:
            us.add_points_by_id(p.user_id, wumpa)
            us.add_exp_by_id(p.user_id, exp)
            reward_msg.append(f"User {p.user_id}: +{wumpa} Wumpa, +{exp} EXP")
            
        session.close()
        
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

    def record_death(self, dungeon_id):
        session = self.db.get_session()
        dungeon = session.query(Dungeon).filter_by(id=dungeon_id).first()
        if dungeon:
            try:
                stats = json.loads(dungeon.stats)
            except:
                stats = {'damage_taken': 0, 'deaths': 0, 'items_used': 0}
            stats['deaths'] += 1
            dungeon.stats = json.dumps(stats)
            session.commit()
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

    def get_dungeon_participants(self, dungeon_id):
        session = self.db.get_session()
        participants = session.query(DungeonParticipant).filter_by(dungeon_id=dungeon_id).all()
        session.close()
        return participants

    def get_active_dungeon(self, chat_id):
        """Returns the active or registering dungeon for the chat"""
        session = self.db.get_session()
        dungeon = session.query(Dungeon).filter(
            Dungeon.chat_id == chat_id,
            Dungeon.status.in_(["registration", "active"])
        ).first()
        session.close()
        return dungeon

    def get_user_active_dungeon(self, user_id):
        """Returns the active dungeon the user is participating in, if any"""
        session = self.db.get_session()
        dungeon = session.query(Dungeon).join(DungeonParticipant).filter(
            DungeonParticipant.user_id == user_id,
            Dungeon.status == "active"
        ).first()
        session.close()
        return dungeon

    def leave_dungeon(self, chat_id, user_id):
        """Allows a user to leave the active dungeon"""
        session = self.db.get_session()
        dungeon = session.query(Dungeon).filter(
            Dungeon.chat_id == chat_id,
            Dungeon.status.in_(["registration", "active"])
        ).first()
        
        if not dungeon:
            session.close()
            return False, "Nessun dungeon attivo."
            
        participant = session.query(DungeonParticipant).filter_by(
            dungeon_id=dungeon.id,
            user_id=user_id
        ).first()
        
        if not participant:
            session.close()
            return False, "Non sei un partecipante di questo dungeon."
            
        # Remove participant
        session.delete(participant)
        session.commit()
        
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
                
            session.commit()
            msg += "\n\n💀 **Dungeon Fallito!** Tutti i partecipanti sono fuggiti o morti."
            
        session.close()
        return True, msg

    def check_dungeon_failure(self, dungeon_id):
        """Checks if all dungeon participants are dead. If so, fails the dungeon."""
        session = self.db.get_session()
        dungeon = session.query(Dungeon).filter_by(id=dungeon_id).first()
        
        if not dungeon or dungeon.status != "active":
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
            
            session.commit()
            msg = "\n\n💀 **GAME OVER!**\nTutti gli eroi sono caduti. Il dungeon è fallito!"
            
        session.close()
        return all_dead, msg
