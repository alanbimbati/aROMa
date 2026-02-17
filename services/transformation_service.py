"""
Transformation Service
Handles character transformations (e.g., Goku SSJ, Ichigo Bankai)
"""
from database import Database
from models.system import CharacterTransformation, UserTransformation, Livello
from models.user import Utente
from datetime import datetime as dt, timedelta

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
            # BYPASS: If Saiyan, always available regardless of level.
            # Also if using base character.
            from services.character_loader import get_character_loader
            loader = get_character_loader()
            char_data = loader.get_character_by_id(character_id)
            is_saiyan = char_data.get('subgroup') == 'Saiyan' if char_data else False
            
            level_bypass = (user.livello_selezionato == trans.base_character_id) or is_saiyan
            
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
            
            # Add fields for UI
            available.append({
                'id': trans.id,
                'name': trans.transformation_name,
                'wumpa_cost': trans.wumpa_cost,
                'mana_cost': trans.mana_cost,
                'can_activate': user.points >= trans.wumpa_cost
            })
        
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
        from services.character_loader import get_character_loader
        loader = get_character_loader()
        char_data = loader.get_character_by_id(transformation.base_character_id)
        is_saiyan = char_data.get('subgroup') == 'Saiyan' if char_data else False

        if not is_saiyan and transformation.required_level and user.livello < transformation.required_level:
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
            expires_at=dt.now(),
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
        
        # Check if transformation is time-restricted (e.g. Great Ape at night only)
        from services.character_loader import get_character_loader
        loader = get_character_loader()
        transformation = loader.get_character_by_id(transformation_id)
        
        if transformation and 'Great Ape' in transformation.get('nome', ''):
            # Great Ape only at night (18:00-06:00)
            current_hour = dt.now().hour
            print(f"[DEBUG] Checking Great Ape Time: Hour={current_hour}. Allowed: 18-6")
            if not (current_hour >= 18 or current_hour < 6):
                return False, "🌙 Le trasformazioni Great Ape sono disponibili solo di notte (18:00-06:00)!"
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
        user_trans.activated_at = dt.now()
        user_trans.expires_at = dt.now() + timedelta(days=transformation.duration_days)

        # Deduct mana cost
        mana_cost = getattr(transformation, 'mana_cost', 0) or 0
        if mana_cost > 0:
            db_user = session.query(Utente).filter_by(id_telegram=user.id_telegram).first()
            if db_user:
                db_user.mana = max(0, (db_user.mana or 0) - mana_cost)
                db_user.current_mana = max(0, (db_user.current_mana or 0) - mana_cost)
                print(f"[TRANSFORMATION] Deducted {mana_cost} mana from user {user.id_telegram}")
        
        # Set transformation expiry in user table for SSJ
        if transformation:
            from services.character_loader import get_character_loader
            loader = get_character_loader()
            trans_char = loader.get_character_by_id(transformation_id)
            
            if trans_char:
                transformation_name = trans_char.get('nome', '')
                
                # Super Saiyan transformations have 6h duration
                if 'SSJ' in transformation_name or 'Super Saiyan' in transformation_name:
                    duration_seconds = 21600  # 6 hours
                    expiry = dt.now() + timedelta(seconds=duration_seconds)
                    
                    # Update user with transformation expiry
                    db_user = session.query(Utente).filter_by(id_telegram=user.id_telegram).first()
                    if db_user:
                        db_user.transformation_expires_at = expiry
                        db_user.current_transformation = transformation_name
                        db_user.livello_selezionato = transformation_id
        
        if local_session:
            session.commit()
            session.close()
        else:
            session.flush()
        
        # Recalculate stats to apply bonuses/caps
        self.user_service.recalculate_stats(user.id_telegram, session=session)
        
        # Check if SSJ and return special message
        if transformation:
            from services.character_loader import get_character_loader
            loader = get_character_loader()
            trans_char = loader.get_character_by_id(transformation_id)
            if trans_char and ('SSJ' in trans_char.get('nome', '') or 'Super Saiyan' in trans_char.get('nome', '')):
                return True, f"⚡ Trasformazione {trans_char['nome']} attivata! Dura 6 ore."
        
        return True, f"✨ Trasformazione '{transformation.transformation_name}' attivata per {transformation.duration_days} giorni!"

    def revert_transformation(self, user):
        """Manually revert active transformation"""
        session = self.db.get_session()
        try:
            # 1. Get active user transformation
            user_trans = session.query(UserTransformation).filter_by(
                user_id=user.id_telegram,
                is_active=True
            ).first()
            
            if not user_trans:
                # FALLBACK: Check if user is physically transformed (ID 500+) even if no active trans record
                # This fixes the "stuck as Great Ape" bug
                from services.character_loader import get_character_loader
                loader = get_character_loader()
                current_char = loader.get_character_by_id(user.livello_selezionato)
                
                # If current char is a transformation (has base_character_id in CSV/DB), try to revert
                base_id = current_char.get('base_character_id')
                
                # SPECIAL CASE: Great Ape (ID 500) is shared.
                # If base_id is generic or we want to be sure, check which base char the user actually OWNS.
                # Valid base chars for Great Ape: Gohan (5), Nappa (60), Vegeta (30), Bardock (XX), etc.
                # We need to find which of these the user has in UserCharacter.
                
                if user.livello_selezionato == 500: # Great Ape
                    # Find which Saiyan the user actually owns to revert to
                    potential_bases = session.query(CharacterTransformation).filter_by(transformed_character_id=500).all()
                    base_ids = [t.base_character_id for t in potential_bases]
                    
                    # Check ownership from models.system (UserCharacter is imported there)
                    from models.system import UserCharacter
                    owned_base = session.query(UserCharacter).filter(
                        UserCharacter.user_id == user.id_telegram,
                        UserCharacter.character_id.in_(base_ids)
                    ).first()
                    
                    if owned_base:
                        base_id = owned_base.character_id
                    else:
                        # Fallback to Goku if nothing found
                        base_id = 60
                
                # Force revert on user object
                db_user = session.query(Utente).filter_by(id_telegram=user.id_telegram).first()
                if db_user:
                    db_user.current_transformation = None
                    db_user.transformation_expires_at = None
                    db_user.livello_selezionato = base_id
                    session.commit()
                    
                    base_char_name = loader.get_character_by_id(base_id)['nome']
                    session.close()
                    return True, f"Stato corretto manualmente. Sei tornato {base_char_name}."
                
                session.close()
                return False, "Nessuna trasformazione attiva da annullare."
                
            # 2. Get Transformation details to find base character
            trans_def = session.query(CharacterTransformation).filter_by(id=user_trans.transformation_id).first()
            if not trans_def:
                session.close()
                return False, "Dati trasformazione corrotti."
            
            # 3. Deactivate
            user_trans.is_active = False
            user_trans.expires_at = dt.now() # Expire immediately
            
            # 4. Update User object
            # We need to re-fetch user in this session to ensure update
            db_user = session.query(Utente).filter_by(id_telegram=user.id_telegram).first()
            if db_user:
                db_user.current_transformation = None
                db_user.transformation_expires_at = None
                # Revert level selected to base char
                db_user.livello_selezionato = trans_def.base_character_id
            
            session.commit()
            
            # 5. Recalculate stats
            self.user_service.recalculate_stats(user.id_telegram, session=session)
            
            # 6. Get base char name for message
            from services.character_loader import get_character_loader
            loader = get_character_loader()
            base_char = loader.get_character_by_id(trans_def.base_character_id)
            base_name = base_char['nome'] if base_char else "Base"
            
            session.close()
            return True, f"Trasformazione annullata. Sei tornato {base_name}."
            
        except Exception as e:
            session.rollback()
            session.close()
            print(f"Error reverting transformation: {e}")
            return False, "Errore durante l'annullamento della trasformazione."
    
    def get_active_transformation(self, user, session=None):
        """Get user's currently active transformation as a dictionary with expiry info"""
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
                return None
            
            # Check if expired
            if user_trans.expires_at and dt.now() > user_trans.expires_at:
                user_trans.is_active = False
                if local_session:
                    session.commit()
                else:
                    session.flush()
                return None
            
            transformation = session.query(CharacterTransformation).filter_by(id=user_trans.transformation_id).first()
            
            if transformation:
                # Return dictionary with mixed data
                return {
                    'id': transformation.id,
                    'name': transformation.transformation_name,
                    'expires_at': user_trans.expires_at,
                    'duration_days': transformation.duration_days,
                    'health_bonus': transformation.health_bonus,
                    'damage_bonus': transformation.damage_bonus
                }
            
            return None
        finally:
            if local_session:
                session.close()
        
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
            if user_trans.expires_at and dt.now() > user_trans.expires_at:
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
                "damage": int(transformation.damage_bonus or 0),
                "resistance": int(transformation.resistance_bonus or 0)
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
        
        now = dt.now()
        expires = now + timedelta(minutes=duration_minutes)
        
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
    
    def check_expired_transformations(self, session=None):
        """
        Check for expired transformations (time duration or environmental conditions)
        and revert users to their base form.
        """
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
            
        try:
            # Get all users with an active transformation
            users = session.query(Utente).filter(Utente.current_transformation != None).all()
            
            reverted_count = 0
            current_hour = dt.now().hour
            is_night = (current_hour >= 18 or current_hour < 6)
            
            for user in users:
                should_revert = False
                reason = ""
                
                # Check 1: Duration Expiry
                if user.transformation_expires_at and user.transformation_expires_at < dt.now():
                    should_revert = True
                    reason = "scadenza durata"
                    
                # Check 2: Environmental Conditions (Great Ape only at night)
                elif user.current_transformation and 'Great Ape' in user.current_transformation:
                    if not is_night:
                        should_revert = True
                        reason = "ritorno del sole"
                        
                if should_revert:
                    # Find base character
                    # We assume user.livello_selezionato is the transformed character ID
                    # We need to find which transformation leads to this char, or check CharacterTransformation
                    
                    # 1. Try to find the correct base from UserTransformation record first (SAFER)
                    active_user_trans = session.query(UserTransformation).filter_by(
                        user_id=user.id_telegram,
                        is_active=True
                    ).first()
                    
                    trans_def = None
                    if active_user_trans:
                        trans_def = session.query(CharacterTransformation).filter_by(id=active_user_trans.transformation_id).first()
                    
                    # 2. Fallback to shared ID mapping (UNSAFE for Great Ape, but better than nothing)
                    if not trans_def:
                        trans_def = session.query(CharacterTransformation).filter_by(
                            transformed_character_id=user.livello_selezionato
                        ).first()
                    
                    if trans_def:
                        # Revert to base
                        base_id = trans_def.base_character_id
                        
                        # SPECIAL CASE: For Great Ape (500), double check ownership to avoid Goku/Vegeta swap
                        if user.livello_selezionato == 500:
                            potential_bases = session.query(CharacterTransformation).filter_by(transformed_character_id=500).all()
                            base_ids = [t.base_character_id for t in potential_bases]
                            from models.system import UserCharacter
                            owned_base = session.query(UserCharacter).filter(
                                UserCharacter.user_id == user.id_telegram,
                                UserCharacter.character_id.in_(base_ids)
                            ).first()
                            if owned_base:
                                base_id = owned_base.character_id
                        
                        user.livello_selezionato = base_id
                        user.current_transformation = None
                        user.transformation_expires_at = None
                        
                        # Deactivate in UserTransformation table too
                        active_user_trans = session.query(UserTransformation).filter_by(
                            user_id=user.id_telegram,
                            transformation_id=trans_def.id,
                            is_active=True
                        ).first()
                        
                        if active_user_trans:
                            active_user_trans.is_active = False
                            
                        # Recalculate stats
                        self.user_service.recalculate_stats(user.id_telegram, session=session)
                        reverted_count += 1
                        print(f"Reverted user {user.id_telegram} from {trans_def.transformation_name} due to {reason}.")
                        
        except Exception as e:
            print(f"Error checking expired transformations: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if local_session:
                session.commit()
                session.close()
                
        return reverted_count
