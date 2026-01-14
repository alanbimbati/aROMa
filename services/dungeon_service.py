from database import Database
from models.dungeon import Dungeon, DungeonParticipant
from models.pve import Mob
from models.user import Utente
import datetime
import random

class DungeonService:
    def __init__(self):
        self.db = Database()

    def create_dungeon(self, chat_id, name, total_stages=5):
        """Starts dungeon registration"""
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
            name=name,
            chat_id=chat_id,
            total_stages=total_stages,
            status="registration"
        )
        session.add(new_dungeon)
        session.commit()
        d_id = new_dungeon.id
        session.close()
        return d_id, f"🏰 **Dungeon Creato: {name}**\n\nIscrivetevi usando `/join`!\nQuando siete pronti, l'admin può usare `/start_dungeon`."

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
        """Starts the dungeon and spawns the first mob"""
        session = self.db.get_session()
        
        dungeon = session.query(Dungeon).filter(
            Dungeon.chat_id == chat_id,
            Dungeon.status == "registration"
        ).first()
        
        if not dungeon:
            session.close()
            return False, "Non c'è nessun dungeon in fase di iscrizione."
            
        participants = session.query(DungeonParticipant).filter_by(dungeon_id=dungeon.id).all()
        if not participants:
            session.close()
            return False, "Nessun partecipante iscritto! Almeno una persona deve partecipare."
            
        dungeon.status = "active"
        dungeon.current_stage = 1
        d_id = dungeon.id
        total_stages_val = dungeon.total_stages # Capture before session close
        session.commit()
        session.close()
        
        # Spawn first mob
        from services.pve_service import PvEService
        pve = PvEService()
        
        success, msg, mob_id = pve.spawn_specific_mob(chat_id=chat_id)
        if success:
            session = self.db.get_session() # Re-open session
            mob = session.query(Mob).filter_by(id=mob_id).first()
            if mob:
                mob.dungeon_id = d_id
                session.commit()
            session.close() # Close re-opened session
            
        return True, f"🚀 **Dungeon Iniziato!**\nStage 1/{total_stages_val}\n\n{msg}"

    def advance_dungeon(self, dungeon_id):
        """Spawns the next mob or the boss"""
        session = self.db.get_session()
        dungeon = session.query(Dungeon).filter_by(id=dungeon_id).first()
        
        if not dungeon or dungeon.status != "active":
            session.close()
            return None
            
        dungeon.current_stage += 1
        current_stage = dungeon.current_stage
        total_stages = dungeon.total_stages
        chat_id = dungeon.chat_id
        print(f"[DEBUG] advance_dungeon: id={dungeon_id}, stage={current_stage}/{total_stages}")
        session.commit()
        session.close()
        
        from services.pve_service import PvEService
        pve = PvEService()
        
        if current_stage < total_stages:
            # Spawn next normal mob
            success, msg, mob_id = pve.spawn_specific_mob(chat_id=chat_id)
            if success:
                session = self.db.get_session()
                mob = session.query(Mob).filter_by(id=mob_id).first()
                if mob:
                    mob.dungeon_id = dungeon_id
                    session.commit()
                session.close()
            msg = f"✅ Stage completato! Passiamo al prossimo...\n\n**Stage {current_stage}/{total_stages}**\n{msg}"
        elif current_stage == total_stages:
            # Spawn Boss
            success, msg, mob_id = pve.spawn_boss(chat_id=chat_id)
            if success:
                session = self.db.get_session()
                mob = session.query(Mob).filter_by(id=mob_id).first()
                if mob:
                    mob.dungeon_id = dungeon_id
                    session.commit()
                session.close()
            msg = f"🔥 **ULTIMO STAGE!** 🔥\nIl boss finale è arrivato!\n\n{msg}"
        else:
            # Dungeon completed
            session = self.db.get_session()
            dungeon = session.query(Dungeon).filter_by(id=dungeon_id).first()
            dungeon.status = "completed"
            dungeon.completed_at = datetime.datetime.now()
            session.commit()
            session.close()
            return "🏆 **DUNGEON COMPLETATO!** 🏆\nAvete sconfitto tutti i nemici e il boss finale! Grandi guerrieri!"
            
        return msg

    def get_participants(self, dungeon_id):
        session = self.db.get_session()
        participants = session.query(DungeonParticipant).filter_by(dungeon_id=dungeon_id).all()
        uids = [p.user_id for p in participants]
        session.close()
        return uids

    def get_active_dungeon(self, chat_id):
        session = self.db.get_session()
        dungeon = session.query(Dungeon).filter(
            Dungeon.chat_id == chat_id,
            Dungeon.status == "active"
        ).first()
        session.close()
        return dungeon
