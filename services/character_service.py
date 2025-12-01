from database import Database
from models.system import Livello, UserCharacter
from services.user_service import UserService
from settings import PointsName
import datetime

class CharacterService:
    def __init__(self):
        self.db = Database()
        self.user_service = UserService()
    
    def get_available_characters(self, user):
        """Get characters user can select (unlocked by level or purchased)"""
        session = self.db.get_session()
        
        # 1. Level-based characters
        if user.premium == 1:
            level_chars = session.query(Livello).filter(
                Livello.livello <= user.livello
            ).all()
        else:
            level_chars = session.query(Livello).filter(
                Livello.livello <= user.livello,
                Livello.lv_premium == 0  # Only free ones by level for non-premium
            ).all()
            
        # 2. Purchased characters
        purchased_ids = session.query(UserCharacter.character_id).filter_by(user_id=user.id_telegram).all()
        purchased_ids = [pid[0] for pid in purchased_ids]
        
        purchased_chars = []
        if purchased_ids:
            purchased_chars = session.query(Livello).filter(Livello.id.in_(purchased_ids)).all()
            
        # Combine and deduplicate
        all_chars = {}
        for c in level_chars:
            all_chars[c.id] = c
        for c in purchased_chars:
            all_chars[c.id] = c
            
        result = list(all_chars.values())
        # Sort by level
        result.sort(key=lambda x: x.livello)
        
        session.close()
        return result
    
    def get_purchasable_characters(self):
        """Get all characters that can be bought with Wumpa"""
        session = self.db.get_session()
        characters = session.query(Livello).filter(Livello.lv_premium == 2, Livello.price > 0).all()
        session.close()
        return characters
    
    def purchase_character(self, user, char_id):
        """Purchase a character with Wumpa Fruits"""
        session = self.db.get_session()
        character = session.query(Livello).filter_by(id=char_id).first()
        
        if not character:
            session.close()
            return False, "Personaggio non trovato!"
        
        # Check if already owned
        owned = session.query(UserCharacter).filter_by(user_id=user.id_telegram, character_id=char_id).first()
        if owned:
            session.close()
            return False, "Possiedi già questo personaggio!"
        
        if character.lv_premium != 2:
            session.close()
            return False, "Questo personaggio non è acquistabile!"
        
        if user.points < character.price:
            session.close()
            return False, f"Non hai abbastanza {PointsName}! Serve: {character.price}"
        
        # Deduct points
        self.user_service.add_points(user, -character.price)
        
        # Add to owned characters
        new_ownership = UserCharacter(
            user_id=user.id_telegram,
            character_id=char_id,
            obtained_at=datetime.date.today()
        )
        session.add(new_ownership)
        session.commit()
        
        session.close()
        return True, f"Hai acquistato {character.nome} per {character.price} {PointsName}!"
    
    def equip_character(self, user, char_id):
        """Equip (select) a character"""
        session = self.db.get_session()
        character = session.query(Livello).filter_by(id=char_id).first()
        
        if not character:
            session.close()
            return False, "Personaggio non trovato!"
        
        # Check if user can use this character
        if character.livello > user.livello:
            session.close()
            return False, "Devi raggiungere un livello più alto!"
        
        # Check premium/purchased logic if needed, but usually if they have it in list it's fine
        # But for safety:
        if character.lv_premium == 1 and user.premium == 0:
            session.close()
            return False, "Questo personaggio richiede Premium!"
        
        self.user_service.update_user(user.id_telegram, {'livello_selezionato': char_id})
        session.close()
        return True, f"Personaggio {character.nome} equipaggiato!"
    
    def get_character(self, char_id):
        """Get character details"""
        session = self.db.get_session()
        character = session.query(Livello).filter_by(id=char_id).first()
        session.close()
        return character
    
    def get_special_attack_info(self, character):
        """Get formatted special attack info"""
        if not character or not character.special_attack_name:
            return None
        
        return {
            'name': character.special_attack_name,
            'damage': character.special_attack_damage,
            'mana_cost': character.special_attack_mana_cost,
            'description': f"{character.special_attack_name}: {character.special_attack_damage} danni, {character.special_attack_mana_cost} mana"
        }
