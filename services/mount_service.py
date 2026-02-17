import csv
import os
from database import Database
from models.mount import Mount, UserMount
from models.user import Utente
from sqlalchemy.orm import joinedload
import datetime

class MountService:
    def __init__(self):
        self.db = Database()
        
    def get_mount(self, mount_id, session=None):
        """Get mount details by ID"""
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
            
        try:
            return session.query(Mount).filter_by(id=mount_id).first()
        finally:
            if local_session:
                session.close()

    def get_all_mounts(self, session=None):
        """Get all available mounts"""
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
            
        try:
            return session.query(Mount).order_by(Mount.min_level).all()
        finally:
            if local_session:
                session.close()

    def get_user_mounts(self, user_id, session=None):
        """Get all mounts owned by a user"""
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
            
        try:
            user_mounts = session.query(UserMount).filter_by(user_id=user_id).options(joinedload(UserMount.mount)).all()
            return [um.mount for um in user_mounts]
        finally:
            if local_session:
                session.close()

    def buy_mount(self, user_id, mount_id, session=None):
        """Purchase a mount for a user"""
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
            
        try:
            user = session.query(Utente).filter_by(id_telegram=user_id).first()
            mount = session.query(Mount).filter_by(id=mount_id).first()
            
            if not user or not mount:
                return False, "Utente o Mount non trovato."
                
            if user.livello < mount.min_level:
                return False, f"Livello insufficiente! Richiesto: {mount.min_level}"
                
            if user.points < mount.price:
                return False, "Wumpa insufficienti!"
                
            # Check if already owned
            exists = session.query(UserMount).filter_by(user_id=user_id, mount_id=mount_id).first()
            if exists:
                return False, "Possiedi già questa mount!"
                
            # Deduct points
            user.points -= mount.price
            
            # Add to user mounts
            new_um = UserMount(user_id=user_id, mount_id=mount_id)
            session.add(new_um)
            
            if local_session:
                session.commit()
            return True, f"Hai acquistato {mount.name}!"
        except Exception as e:
            if local_session:
                session.rollback()
            return False, f"Errore durante l'acquisto: {e}"
        finally:
            if local_session:
                session.close()

    def equip_mount(self, user_id, mount_id, session=None):
        """Equip (mount) a specific mount"""
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
            
        try:
            user = session.query(Utente).filter_by(id_telegram=user_id).first()
            if not user:
                return False, "Utente non trovato."
                
            if mount_id is None:
                user.current_mount_id = None
                if local_session:
                    session.commit()
                return True, "Sei sceso dalla mount."
                
            # Check ownership
            owned = session.query(UserMount).filter_by(user_id=user_id, mount_id=mount_id).first()
            if not owned:
                return False, "Non possiedi questa mount!"
                
            user.current_mount_id = mount_id
            
            if local_session:
                session.commit()
            return True, "Ora sei in sella!"
        except Exception as e:
            if local_session:
                session.rollback()
            return False, f"Errore durante l'equipaggiamento: {e}"
        finally:
            if local_session:
                session.close()

    def get_user_speed_bonus(self, user_id, session=None):
        """Calculate total speed including mount bonus"""
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
            
        try:
            user = session.query(Utente).filter_by(id_telegram=user_id).first()
            if not user or not user.current_mount_id:
                return 0
                
            mount = session.query(Mount).filter_by(id=user.current_mount_id).first()
            return mount.speed_bonus if mount else 0
        finally:
            if local_session:
                session.close()
