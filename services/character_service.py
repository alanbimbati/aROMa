from database import Database
from models.system import Livello, UserCharacter
from models.character_ownership import CharacterOwnership
from models.user import Utente
from services.user_service import UserService
from services.character_loader import get_character_loader
from services.event_dispatcher import EventDispatcher
from settings import PointsName
import datetime

class CharacterService:
    def __init__(self):
        self.db = Database()
        self.user_service = UserService()
        self.char_loader = get_character_loader()
        self.event_dispatcher = EventDispatcher()
    
    def get_available_characters(self, user):
        """Get characters user can select (unlocked by level or purchased)"""
        session = self.db.get_session()
        
        # 1. Level-based characters from CSV
        if user.premium == 1:
            level_chars = self.char_loader.filter_characters(level=user.livello)
        else:
            # Only non-premium characters for non-premium users
            level_chars = [c for c in self.char_loader.filter_characters(level=user.livello) 
                          if c['lv_premium'] == 0]
            
        # 2. Purchased characters
        purchased_ids = session.query(UserCharacter.character_id).filter_by(user_id=user.id_telegram).all()
        purchased_ids = [pid[0] for pid in purchased_ids]
        
        purchased_chars = []
        if purchased_ids:
            for char_id in purchased_ids:
                char = self.char_loader.get_character_by_id(char_id)
                if char:
                    purchased_chars.append(char)
            
        # Combine and deduplicate by ID
        all_chars_dict = {}
        for c in level_chars:
            all_chars_dict[c['id']] = c
        for c in purchased_chars:
            all_chars_dict[c['id']] = c
            
        result = list(all_chars_dict.values())
        # Sort by level
        result.sort(key=lambda x: x['livello'])
        
        session.close()
        return result
    
    def get_purchasable_characters(self):
        """Get all characters that can be bought with Wumpa"""
        return self.char_loader.filter_characters(purchasable_only=True)
    
    def purchase_character(self, user, char_id):
        """Purchase a character with Wumpa Fruits (with premium discount)"""
        session = self.db.get_session()
        character = self.char_loader.get_character_by_id(char_id)
        
        if not character:
            session.close()
            return False, "Personaggio non trovato!"
        
        # Check if already owned
        owned = session.query(UserCharacter).filter_by(user_id=user.id_telegram, character_id=char_id).first()
        if owned:
            session.close()
            return False, "Possiedi già questo personaggio!"
        
        if character['lv_premium'] != 2:
            session.close()
            return False, "Questo personaggio non è acquistabile!"
            
        # Check max ownership limit (Family Check)
        max_owners = character.get('max_concurrent_owners', 1)
        if max_owners != -1:
            # Get all IDs in the family (Base + Transformations)
            family_ids = self.char_loader.get_character_family_ids(char_id)
            
            # Check if ANY of these are owned by ANYONE
            # Note: We check CharacterOwnership (Equipped) as per previous logic, 
            # but for strict uniqueness we might want to check UserCharacter (Owned).
            # However, sticking to "Active/Equipped" uniqueness for now as per context.
            # WAIT: If I buy it, I want to own it. If someone else has it equipped, I can't buy it?
            # The user said "un personaggio non può avere la mia trasformazione".
            # This implies if I HAVE (Equipped/Owned?) Vegeta, you can't have Vegeta SSJ.
            # Let's check CharacterOwnership for all family IDs.
            
            current_owners_count = session.query(CharacterOwnership).filter(
                CharacterOwnership.character_id.in_(family_ids)
            ).count()
            
            if current_owners_count >= max_owners:
                session.close()
                return False, f"❌ Questo personaggio (o una sua trasformazione) è già in uso da qualcun altro!"
        
        # Check evolution requirement
        if character.get('required_character_id'):
            required_owned = session.query(UserCharacter).filter_by(
                user_id=user.id_telegram, 
                character_id=character['required_character_id']
            ).first()
            
            if not required_owned:
                req_char = self.char_loader.get_character_by_id(character['required_character_id'])
                req_name = req_char['nome'] if req_char else "Unknown"
                session.close()
                return False, f"Devi possedere {req_name} per sbloccare questo personaggio!"

        # Apply premium discount (50%)
        price = character['price']
        if user.premium == 1:
            price = int(price * 0.5)
        
        if user.points < price:
            session.close()
            return False, f"Non hai abbastanza {PointsName}! Serve: {price}"
        
        # Deduct points
        self.user_service.add_points(user, -price)
        
        # Add to owned characters
        new_ownership = UserCharacter(
            user_id=user.id_telegram,
            character_id=char_id,
            obtained_at=datetime.date.today()
        )
        session.add(new_ownership)
        session.commit()
        
        # Extract data before closing session
        char_name = character['nome']
        char_price = character['price']
        
        # Log character unlock event
        self.event_dispatcher.log_event(
            event_type='character_unlock',
            user_id=user.id_telegram,
            value=1,
            context={'char_id': char_id, 'char_name': char_name}
        )
        
        return True, f"Hai acquistato {char_name} per {price} {PointsName}!{premium_msg}"
    
    def equip_character(self, user, char_id):
        """Equip a character (with exclusivity checks)"""
        session = self.db.get_session()
        character = self.char_loader.get_character_by_id(char_id)
        
        if not character:
            session.close()
            return False, "Personaggio non trovato."
        
        # Check if user can unlock this character
        if not self.is_character_unlocked(user, char_id):
            session.close()
            return False, "Non puoi usare questo personaggio! Livello insufficiente o personaggio non acquistato."
        
        # Check character exclusivity
        
        # Get max owners for this character (-1 = unlimited)
        max_owners = character.get('max_concurrent_owners', 1)
        char_name = character['nome']  # Extract name for error msg
        
        if max_owners != -1:  # If not unlimited
            # Get family IDs
            family_ids = self.char_loader.get_character_family_ids(char_id)
            
            # Count current owners of ANY family member
            current_owners = session.query(CharacterOwnership).filter(
                CharacterOwnership.character_id.in_(family_ids)
            ).count()
            
            # Check if character is already at max capacity
            if current_owners >= max_owners:
                # Check if user already owns one of them (re-equipping same or switching form)
                user_owns = session.query(CharacterOwnership).filter(
                    CharacterOwnership.character_id.in_(family_ids),
                    CharacterOwnership.user_id == user.id_telegram
                ).first()
                
                if not user_owns:
                    session.close()
                    return False, f"❌ {char_name} (o una sua forma) è già in uso da qualcun altro!"
        
        # Release user's current character
        self._release_user_character(user.id_telegram, session)
        
        # Add ownership record
        ownership = CharacterOwnership(
            character_id=char_id,
            user_id=user.id_telegram,
            equipped_at=datetime.datetime.now(),
            last_change_date=datetime.date.today()
        )
        session.add(ownership)
        
        # Update user's selected character
        db_user = session.query(Utente).filter_by(id_telegram=user.id_telegram).first()
        if db_user:
            db_user.livello_selezionato = char_id
            # last_character_change update removed to allow unlimited changes
        
        session.commit()
        
        # Extract name again just in case
        char_name = character['nome']
        
        # Log character equip event
        self.event_dispatcher.log_event(
            event_type='character_equip',
            user_id=user.id_telegram,
            value=1,
            context={'char_id': char_id, 'char_name': char_name}
        )
        
        return True, f"Hai equipaggiato {char_name}!"
    
    def _release_user_character(self, user_id, session):
        """Release user's current character ownership"""
        # Remove any existing ownership for this user
        session.query(CharacterOwnership).filter_by(user_id=user_id).delete()
        # Note: Don't commit here, let the caller handle it
    
    def get_character(self, char_id):
        """Get character details"""
        return self.char_loader.get_character_by_id(char_id)
    
    def get_special_attack_info(self, character):
        """Get formatted special attack info"""
        if not character or not character.get('special_attack_name'):
            return None
        
        return {
            'name': character['special_attack_name'],
            'damage': character['special_attack_damage'],
            'mana_cost': character['special_attack_mana_cost'],
            'description': f"{character['special_attack_name']}: {character['special_attack_damage']} danni, {character['special_attack_mana_cost']} mana"
        }
    
    def format_character_card(self, character, show_price=False, is_equipped=False, show_all_skills=True):
        """
        Format character details for display in UI
        Returns formatted message string
        """
        # Character name with saga
        saga_info = f" - {character['character_group']}" if character.get('character_group') else ""
        msg = f"**{character['nome']}{saga_info}**"
        
        if is_equipped:
            msg += " ⭐ *EQUIPAGGIATO*"
        
        msg += f"\n\n"
        
        # Group info (already in title, but keep for consistency)
        # msg += f"🎮 Serie: *{character.character_group}*\n" if character.character_group else ""
        
        # Level requirement
        msg += f"📊 Livello Richiesto: {character['livello']}\n"
        
        # Premium/Price info
        if character['lv_premium'] == 1:
            msg += f"👑 Richiede Premium\n"
        elif character['lv_premium'] == 2 and show_price:
            msg += f"💰 Prezzo: {character['price']} {PointsName}\n"
        
        # Skills section
        if show_all_skills:
            from services.skill_service import SkillService
            skill_service = SkillService()
            abilities = skill_service.get_character_abilities(character['id'])
            
            if abilities:
                msg += f"\n✨ **Abilità:**\n"
                for ability in abilities:
                    msg += f"\n🔮 **{ability['name']}**\n"
                    msg += f"   ⚔️ Danno: {ability['damage']}\n"
                    msg += f"   💙 Mana: {ability['mana_cost']}\n"
                    msg += f"   🎯 Crit: {ability['crit_chance']}% (x{ability['crit_multiplier']})\n"
                    if ability.get('elemental_type') and ability['elemental_type'] != 'Normal':
                        msg += f"   ⚡ Tipo: {ability['elemental_type']}\n"
                    
                    # Status Effects & Buffs
                    if ability.get('status_effect'):
                        effect_type = ability['status_effect']
                        chance = ability.get('status_chance', 0)
                        duration = ability.get('status_duration', 0)
                        
                        effect_icon = "✨"
                        if effect_type == 'stun': effect_icon = "💫"
                        elif effect_type == 'poison': effect_icon = "☠️"
                        elif effect_type == 'burn': effect_icon = "🔥"
                        elif effect_type == 'freeze': effect_icon = "❄️"
                        elif effect_type == 'life_drain': effect_icon = "🩸"
                        elif effect_type == 'wumpa_steal': effect_icon = "🥭"
                        elif 'buff' in effect_type: effect_icon = "💪"
                        
                        msg += f"   {effect_icon} Effetto: {effect_type.replace('_', ' ').title()} ({chance}% prob.)"
                        if duration > 0:
                            msg += f" per {duration} turni"
                        msg += "\n"
            elif character.get('special_attack_name'):
                # Fallback to legacy special attack if no abilities defined
                msg += f"\n✨ **Abilità Speciale:**\n"
                msg += f"🔮 {character['special_attack_name']}\n"
                msg += f"⚔️ Danno: {character['special_attack_damage']}\n"
                msg += f"💙 Costo Mana: {character['special_attack_mana_cost']}\n"
                # Use character-level crit stats as fallback
                if character.get('crit_chance'):
                    msg += f"🎯 Crit: {character['crit_chance']}% (x{character['crit_multiplier']})\n"
        
        # Description
        if character.get('description'):
            msg += f"\n📝 {character['description']}"
        
        return msg
    
    def get_characters_paginated(self, user, page=0, per_page=1):
        """
        Get available characters with pagination
        Returns (characters, total_pages, current_page)
        """
        all_chars = self.get_available_characters(user)
        
        total = len(all_chars)
        total_pages = max(1, (total + per_page - 1) // per_page)
        current_page = max(0, min(page, total_pages - 1))
        
        start_idx = current_page * per_page
        end_idx = min(start_idx + per_page, total)
        
        page_chars = all_chars[start_idx:end_idx]
        
        return page_chars, total_pages, current_page
    
    def get_all_characters(self):
        """Get all characters in the system"""
        return self.char_loader.get_all_characters()
    
    def is_character_unlocked(self, user, char_id):
        """Check if user has unlocked/can use this character"""
        session = self.db.get_session()
        character = self.char_loader.get_character_by_id(char_id)
        
        if not character:
            session.close()
            return False
        
        # CRITICAL: Always enforce level requirement
        if character['livello'] > user.livello:
            session.close()
            return False
            
        # Check level unlock (for free/premium level-based characters)
        # Check premium requirement
        if character['lv_premium'] == 1:
            if user.premium == 1:
                session.close()
                return True
            else:
                session.close()
                return False
        
        # If it's a standard level-unlocked character (lv_premium == 0)
        if character['lv_premium'] == 0:
            session.close()
            return True
            
        # Check if purchased or seasonal (lv_premium == 2)
        purchased = session.query(UserCharacter).filter_by(
            user_id=user.id_telegram,
            character_id=char_id
        ).first()
        
        session.close()
        return purchased is not None
    
    def get_character_levels(self):
        """Get unique character levels for filtering"""
        return self.char_loader.get_character_levels()
    
    def get_closest_level(self, target_level):
        """Find the closest character level to the target level"""
        levels = self.get_character_levels()
        if not levels:
            return 1
        
        closest = levels[0]
        min_diff = abs(target_level - closest)
        
        for level in levels:
            diff = abs(target_level - level)
            if diff < min_diff:
                min_diff = diff
                closest = level
            # If we passed the target, no need to check further (levels are sorted)
            if level > target_level:
                break
                
        return closest
    
    def get_all_characters_paginated(self, user, page=0, per_page=1, level_filter=None, max_level_visible=None):
        """Get all characters (locked and unlocked) with pagination and optional level filter"""
        all_chars = self.get_all_characters()
        
        # Apply max level restriction (unless admin)
        if max_level_visible is not None:
            all_chars = [c for c in all_chars if c['livello'] <= max_level_visible]
        
        # Apply level filter
        if level_filter is not None:
            all_chars = [c for c in all_chars if c['livello'] == level_filter]
        
        total = len(all_chars)
        total_pages = max(1, (total + per_page - 1) // per_page)
        current_page = max(0, min(page, total_pages - 1))
        
        start_idx = current_page * per_page
        end_idx = min(start_idx + per_page, total)
        
        page_chars = all_chars[start_idx:end_idx]
        
        return page_chars, total_pages, current_page

    def get_characters_by_level(self, level):
        """Get all characters for a specific level"""
        return self.char_loader.get_characters_by_level(level)

    def get_character_owner_name(self, char_id):
        """Get the name of the current owner of a character (if unique)"""
        session = self.db.get_session()
        try:
            character = self.char_loader.get_character_by_id(char_id)
            if not character:
                return None
                
            # Only relevant for unique characters
            if character.get('max_concurrent_owners', 1) == -1:
                return None
                
            ownership = session.query(CharacterOwnership).filter_by(character_id=char_id).first()
            if ownership:
                user = session.query(Utente).filter_by(id_telegram=ownership.user_id).first()
                if user:
                    return user.nome if user.username is None else user.username
            return None
        finally:
            session.close()
