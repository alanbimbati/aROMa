"""
Transformation Service
Handles character transformations (e.g., Goku SSJ, Ichigo Bankai)
"""
from database import Database
from models.system import CharacterTransformation, UserTransformation, Livello
from models.user import Utente
import datetime

class TransformationService:
    def __init__(self):
        self.db = Database()
        from services.user_service import UserService
        self.user_service = UserService()
    
    def get_available_transformations(self, user, character_id):
        """Get all transformations available for a character"""
        session = self.db.get_session()
        
        # Get all transformations for this character
        transformations = session.query(CharacterTransformation).filter_by(
            base_character_id=character_id
        ).all()
        
        available = []
        for trans in transformations:
            # Check level requirement
            # BYPASS: If user is already using the base character of this transformation,
            # we allow it even if level is too low (incentive to use that char).
            level_bypass = (user.livello_selezionato == trans.base_character_id)
            
            if not level_bypass and trans.required_level and user.livello < trans.required_level:
                continue
            
            # Check if progressive and requires previous transformation
            if trans.is_progressive and trans.previous_transformation_id:
                # Check if user has purchased the previous transformation
                prev_purchased = session.query(UserTransformation).filter_by(
                    user_id=user.id_telegram,
                    transformation_id=trans.previous_transformation_id
                ).first()
                if not prev_purchased:
                    continue
            
            available.append(trans)
        
        session.close()
        return available
    
    def purchase_transformation(self, user, transformation_id, session=None):
        """Purchase a transformation"""
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
        
        transformation = session.query(CharacterTransformation).filter_by(id=transformation_id).first()
        if not transformation:
            if local_session:
                session.close()
            return False, "Trasformazione non trovata."
        
        # Check if already purchased
        existing = session.query(UserTransformation).filter_by(
            user_id=user.id_telegram,
            transformation_id=transformation_id
        ).first()
        
        if existing:
            if local_session:
                session.close()
            return False, "Hai già acquistato questa trasformazione!"
        
        # Check level requirement
        if transformation.required_level and user.livello < transformation.required_level:
            if local_session:
                session.close()
            return False, f"Livello {transformation.required_level} richiesto!"
        
        # Check progressive requirement
        if transformation.is_progressive and transformation.previous_transformation_id:
            prev_purchased = session.query(UserTransformation).filter_by(
                user_id=user.id_telegram,
                transformation_id=transformation.previous_transformation_id
            ).first()
            if not prev_purchased:
                if local_session:
                    session.close()
                return False, "Devi prima acquistare la trasformazione precedente!"
        
        # Check Wumpa cost
        if user.points < transformation.wumpa_cost:
            if local_session:
                session.close()
            return False, f"Servono {transformation.wumpa_cost} Wumpa Fruits!"
        
        # Deduct cost
        db_user = session.query(Utente).filter_by(id_telegram=user.id_telegram).first()
        db_user.points -= transformation.wumpa_cost
        
        # Add to user transformations (not active yet)
        user_trans = UserTransformation(
            user_id=user.id_telegram,
            transformation_id=transformation_id,
            activated_at=None,
            expires_at=datetime.datetime.now(),
            is_active=False
        )
        session.add(user_trans)
        if local_session:
            session.commit()
            session.close()
        else:
            session.flush() # Ensure ID is generated but don't commit transaction
        
        return True, f"Trasformazione '{transformation.transformation_name}' acquistata per {transformation.wumpa_cost} Wumpa!"
    
    def activate_transformation(self, user, transformation_id, session=None):
        """Activate a purchased transformation"""
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
        
        # Check if user owns this transformation
        user_trans = session.query(UserTransformation).filter_by(
            user_id=user.id_telegram,
            transformation_id=transformation_id
        ).first()
        
        if not user_trans:
            if local_session:
                session.close()
            return False, "Non possiedi questa trasformazione!"
        
        transformation = session.query(CharacterTransformation).filter_by(id=transformation_id).first()
        
        # Deactivate any currently active transformations
        active_trans = session.query(UserTransformation).filter_by(
            user_id=user.id_telegram,
            is_active=True
        ).all()
        
        for trans in active_trans:
            trans.is_active = False
        
        # Activate this transformation
        user_trans.is_active = True
        user_trans.activated_at = datetime.datetime.now()
        user_trans.expires_at = datetime.datetime.now() + datetime.timedelta(days=transformation.duration_days)
        
        if local_session:
            session.commit()
            session.close()
        else:
            session.flush()
        
        # Recalculate stats to apply bonuses/caps
        self.user_service.recalculate_stats(user.id_telegram, session=session)
        
        return True, f"Trasformazione '{transformation.transformation_name}' attivata per {transformation.duration_days} giorni!"
    
    def get_active_transformation(self, user, session=None):
        """Get user's currently active transformation"""
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
        
        user_trans = session.query(UserTransformation).filter_by(
            user_id=user.id_telegram,
            is_active=True
        ).first()
        
        if not user_trans:
            if local_session:
                session.close()
            return None
        
        # Check if expired
        if user_trans.expires_at and datetime.datetime.now() > user_trans.expires_at:
            user_trans.is_active = False
            if local_session:
                session.commit()
                session.close()
            else:
                session.flush()
            return None
        
        transformation = session.query(CharacterTransformation).filter_by(id=user_trans.transformation_id).first()
        if transformation and local_session:
            session.expunge(transformation)
        
        if local_session:
            session.close()
        
        return transformation
        
    def get_transformation_bonuses(self, user, session=None):
        """Get stat bonuses from active transformation"""
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
        try:
            user_trans = session.query(UserTransformation).filter_by(
                user_id=user.id_telegram,
                is_active=True
            ).first()
            
            if not user_trans:
                return {"health": 0, "mana": 0, "damage": 0}
                
            # Check expiration
            if user_trans.expires_at and datetime.datetime.now() > user_trans.expires_at:
                user_trans.is_active = False
                if local_session:
                    session.commit()
                else:
                    session.flush()
                return {"health": 0, "mana": 0, "damage": 0}
                
            transformation = session.query(CharacterTransformation).filter_by(id=user_trans.transformation_id).first()
            
            if not transformation:
                return {"health": 0, "mana": 0, "damage": 0}
            
            bonuses = {
                "health": int(transformation.health_bonus or 0),
                "mana": int(transformation.mana_bonus or 0),
                "damage": int(transformation.damage_bonus or 0)
            }
            return bonuses
        except Exception as e:
            print(f"Error in get_transformation_bonuses: {e}")
            raise e
        finally:
            if local_session:
                session.close()

    def activate_temporary_transformation(self, user, transformation_id, duration_minutes=5):
        """Activate a transformation temporarily (e.g. Potara Fusion)"""
        session = self.db.get_session()
        
        transformation = session.query(CharacterTransformation).filter_by(id=transformation_id).first()
        if not transformation:
            session.close()
            return False, "Trasformazione non trovata."
            
        # Deactivate current
        active_trans = session.query(UserTransformation).filter_by(
            user_id=user.id_telegram,
            is_active=True
        ).all()
        for trans in active_trans:
            trans.is_active = False
            
        # Check if user already has an entry for this transformation
        user_trans = session.query(UserTransformation).filter_by(
            user_id=user.id_telegram,
            transformation_id=transformation_id
        ).first()
        
        now = datetime.datetime.now()
        expires = now + datetime.timedelta(minutes=duration_minutes)
        
        if user_trans:
            user_trans.is_active = True
            user_trans.activated_at = now
            user_trans.expires_at = expires
        else:
            # Create temporary entry
            user_trans = UserTransformation(
                user_id=user.id_telegram,
                transformation_id=transformation_id,
                activated_at=now,
                expires_at=expires,
                is_active=True
            )
            session.add(user_trans)
            
        trans_name = transformation.transformation_name
        session.commit()
        session.close()
        
        # Recalculate stats to apply bonuses/caps
        self.user_service.recalculate_stats(user.id_telegram, session=session)
        return True, f"Trasformazione '{trans_name}' attivata per {duration_minutes} minuti!"

    def get_transformation_id_by_name(self, name):
        """Get transformation ID by name"""
        session = self.db.get_session()
        trans = session.query(CharacterTransformation).filter_by(transformation_name=name).first()
        session.close()
        return trans.id if trans else None
