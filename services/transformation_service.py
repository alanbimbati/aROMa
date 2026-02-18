from database import Database
from models.system import CharacterTransformation, UserTransformation, Livello
from models.user import Utente
from datetime import datetime, timedelta

class TransformationService:
    def __init__(self):
        self.db = Database()
        from services.user_service import UserService
        self.user_service = UserService()
        from services.character_service import CharacterService
        self.CharacterService = CharacterService
    
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
            expires_at=datetime.now(),
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
        
        if transformation and (
            'Great Ape' in transformation.get('nome', '') or 
            'Scimmione' in transformation.get('nome', '') or
            transformation.get('id') == 500
        ):
            # Great Ape only at night (18:00-06:00)
            current_hour = datetime.now().hour
            # print(f"[DEBUG] Checking Great Ape Time: Hour={current_hour}. Allowed: 18-6")
            if not (current_hour >= 18 or current_hour < 6):
                return False, "🌙 Non puoi trasformarti in Scimmione ora! Devi aspettare le 18:00 per scatenare la furia!"

            # Great Ape requires specific Saiyan ownership if ID is 500 (Generic)
            if transformation.get('id') == 500:
                # Check if user owns at least one capable saiyan base
                # This prevents users who bought it but don't own the character from transforming
                # Logic: Check UserCharacters for valid bases
                session_to_use = session if session else self.db.get_session()
                try:
                    from models.system import CharacterTransformation, UserCharacter
                    valid_bases = session_to_use.query(CharacterTransformation.base_character_id).filter_by(transformed_character_id=500).all()
                    base_ids = [vb[0] for vb in valid_bases]
                    
                    has_base = session_to_use.query(UserCharacter).filter(
                        UserCharacter.user_id == user.id_telegram,
                        UserCharacter.character_id.in_(base_ids)
                    ).first()
                    
                    if not has_base:
                        if not session: session_to_use.close()
                        return False, "❌ Non possiedi un Saiyan capace di trasformarsi in Scimmione!"
                finally:
                    if not session: session_to_use.close()
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
        user_trans.activated_at = datetime.now()
        user_trans.expires_at = datetime.now() + timedelta(days=transformation.duration_days)

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
                    expiry = datetime.now() + timedelta(seconds=duration_seconds)
                    
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
            user_trans.expires_at = datetime.now() # Expire immediately
            
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
            if user_trans.expires_at and datetime.now() > user_trans.expires_at:
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
            if user_trans.expires_at and datetime.now() > user_trans.expires_at:
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
        
        now = datetime.now()
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
        reverted_count = 0
        users = []
        local_session = False
        if not session:
            session = self.db.get_session()
            local_session = True
            
        try:
            # Dynamic Great Ape Detection (requested by user to cover all cases)
            # We scan all loaded characters for "Scimmione" or "Great Ape" in their name.
            char_service = self.CharacterService()
            all_chars = char_service.char_loader.characters # Direct access to loaded dict
            
            ape_ids = []
            for cid, cdata in all_chars.items():
                cname = cdata.get('nome', '')
                if "Scimmione" in cname or "Great Ape" in cname or cid == 500:
                    ape_ids.append(cid)
            
            # Ensure we catch ANY of these IDs, even if current_transformation is NULL
            users = session.query(Utente).filter(
                (Utente.current_transformation != None) | 
                (Utente.livello_selezionato.in_(ape_ids))
            ).all()
            
            current_hour = datetime.now().hour
            is_night = (current_hour >= 18 or current_hour < 6)
            
            print(f"[TRANSFORMATION_CHECK] Checking {len(users)} users. Hour: {current_hour}, IsNight: {is_night}")
            
            for user in users:
                should_revert = False
                reason = ""
                
                # Check 1: Great Ape Day Check (Dynamic)
                is_scimmione_id = (user.livello_selezionato in ape_ids)
                
                if is_scimmione_id:
                    if not is_night:
                        should_revert = True
                        reason = f"ritorno del sole (Great Ape ID {user.livello_selezionato})"
                
                # Check 2: Duration Expiry
                elif user.transformation_expires_at and user.transformation_expires_at < datetime.now():
                    should_revert = True
                    reason = "scadenza durata"
                    
                # Check 3: Environmental Conditions (String based backup)
                # Must check both English "Great Ape" and Italian "Scimmione"
                elif user.current_transformation and (
                    'Great Ape' in user.current_transformation or 
                    'Scimmione' in user.current_transformation
                ):
                    if not is_night:
                        should_revert = True
                        reason = "ritorno del sole"
                        
                if should_revert:
                    print(f"[TRANSFORMATION_CHECK] Reverting User {user.id_telegram} ({user.nome}). Reason: {reason}")
                    
                    # LOGIC TO FIND BASE CHARACTER
                    base_id = 1 # Default fallback
                    
                    # 1. Try to find the correct base from UserTransformation record first (SAFER)
                    active_user_trans = session.query(UserTransformation).filter_by(
                        user_id=user.id_telegram,
                        is_active=True
                    ).first()
                    
                    trans_def = None
                    if active_user_trans:
                        trans_def = session.query(CharacterTransformation).filter_by(id=active_user_trans.transformation_id).first()
                        if trans_def:
                            base_id = trans_def.base_character_id
                    
                    # 2. Fallback: Deduce from character data (CSV)
                    if not trans_def:
                        char_data = all_chars.get(user.livello_selezionato)
                        if char_data and char_data.get('is_transformation'):
                            base_id = char_data.get('base_character_id', base_id)
                    
                    # 3. If still no active record and it's generic Great Ape (ID 500)
                    if not trans_def and user.livello_selezionato == 500:
                        # Find which Saiyan the user actually owns to revert to
                        potential_bases = session.query(CharacterTransformation).filter_by(transformed_character_id=500).all()
                        base_ids = [t.base_character_id for t in potential_bases]
                        
                        from models.system import UserCharacter
                        owned_base = session.query(UserCharacter).filter(
                            UserCharacter.user_id == user.id_telegram,
                            UserCharacter.character_id.in_(base_ids)
                        ).first()
                        
                        if owned_base:
                            base_id = owned_base.character_id
                        else:
                            # Fallback: Goku (1), Vegeta (30), Gohan (5) - try to guess or use safe default
                            base_id = 60 # Nappa default? Or Goku 1? Let's use 1 if unsure
                            # Actually, let's try to check their history or just set to 1 (Goku) safe.
                            pass
                            
                    # Apply Revert
                    user.livello_selezionato = base_id
                    user.current_transformation = None
                    user.transformation_expires_at = None
                    
                    # Deactivate in UserTransformation table too
                    if active_user_trans:
                        active_user_trans.is_active = False
                    else:
                        # Deactivate ALL active transformations for this user to be safe
                        session.query(UserTransformation).filter_by(user_id=user.id_telegram, is_active=True).update({'is_active': False})
                        
                    # Recalculate stats
                    self.user_service.recalculate_stats(user.id_telegram, session=session)
                    reverted_count += 1
                    print(f"[TRANSFORMATION_CHECK] SUCCESS: User {user.id_telegram} reverted to {base_id}.")
                        
        except Exception as e:
            print(f"[TRANSFORMATION_CHECK] Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if local_session:
                session.commit()
                session.close()
                
        return reverted_count
