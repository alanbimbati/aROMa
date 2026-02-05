import csv
import os
from typing import List, Dict, Any, Optional
from database import Database
from models.skins import UserSkin
from sqlalchemy import and_

class SkinService:
    _instance = None
    _skins_cache = []
    _skins_by_id = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SkinService, cls).__new__(cls)
            cls._instance.db = Database()
            cls._instance.load_skins()
        return cls._instance

    def load_skins(self):
        """Load skins from CSV with caching"""
        self._skins_cache = []
        self._skins_by_id = {}
        
        path = 'data/skins.csv'
        if not os.path.exists(path):
            with open(path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['id', 'character_id', 'name', 'price', 'gif_path'])
            return

        try:
            with open(path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    skin = {
                        'id': int(row['id']),
                        'character_id': int(row['character_id']),
                        'name': row['name'],
                        'price': int(row['price']),
                        'gif_path': row['gif_path']
                    }
                    self._skins_cache.append(skin)
                    self._skins_by_id[skin['id']] = skin
        except Exception as e:
            print(f"[ERROR] Failed to load skins.csv: {e}")

    def get_available_skins(self, character_id: int) -> List[Dict[str, Any]]:
        """Get all skins available for a specific character"""
        return [s for s in self._skins_cache if s['character_id'] == character_id]

    def get_skin_by_id(self, skin_id: int) -> Optional[Dict[str, Any]]:
        """Get skin details by ID"""
        return self._skins_by_id.get(skin_id)

    def get_user_skins(self, user_id: int, character_id: Optional[int] = None) -> List[UserSkin]:
        """Get skins owned by a user, optionally filtered by character"""
        session = self.db.get_session()
        query = session.query(UserSkin).filter(UserSkin.user_id == user_id)
        if character_id:
            query = query.filter(UserSkin.character_id == character_id)
        skins = query.all()
        session.close()
        return skins

    def purchase_skin(self, user_id: int, skin_id: int) -> (bool, str):
        """Purchase a skin for a user"""
        skin = self.get_skin_by_id(skin_id)
        if not skin:
            return False, "Skin non trovata."

        # Check if already owned
        session = self.db.get_session()
        owned = session.query(UserSkin).filter(
            and_(UserSkin.user_id == user_id, UserSkin.skin_id == skin_id)
        ).first()
        
        if owned:
            session.close()
            return False, "Possiedi già questa skin!"

        # Check Wumpa
        from services.user_service import UserService
        user_service = UserService()
        user = user_service.get_user(user_id)
        
        if user.points < skin['price']:
            session.close()
            return False, f"Non hai abbastanza Wumpa! Costo: {skin['price']}"

        try:
            # Deduct points
            user.points -= skin['price']
            
            # Create UserSkin
            new_skin = UserSkin(
                user_id=user_id,
                character_id=skin['character_id'],
                skin_id=skin_id,
                skin_name=skin['name'],
                gif_path=skin['gif_path'],
                is_equipped=False
            )
            session.add(new_skin)
            session.commit()
            return True, f"Hai acquistato la skin **{skin['name']}**!"
        except Exception as e:
            session.rollback()
            return False, f"Errore durante l'acquisto: {e}"
        finally:
            session.close()

    def equip_skin(self, user_id: int, skin_id: Optional[int]) -> (bool, str):
        """Equip a skin (passing None unequips all for that character)"""
        session = self.db.get_session()
        try:
            if skin_id is None:
                # Need character_id to unequip all for THAT character?
                # Actually, let's just unequip ALL skins for the user or for a specific character.
                # User is usually using one character at a time.
                from services.user_service import UserService
                user = UserService().get_user(user_id)
                char_id = user.livello_selezionato
                session.query(UserSkin).filter(
                    and_(UserSkin.user_id == user_id, UserSkin.character_id == char_id)
                ).update({"is_equipped": False})
                session.commit()
                return True, "Skin rimosse. Ora usi l'immagine classica."

            skin_to_equip = session.query(UserSkin).filter(
                and_(UserSkin.user_id == user_id, UserSkin.skin_id == skin_id)
            ).first()

            if not skin_to_equip:
                return False, "Non possiedi questa skin!"

            # Unequip others for same character
            session.query(UserSkin).filter(
                and_(UserSkin.user_id == user_id, UserSkin.character_id == skin_to_equip.character_id)
            ).update({"is_equipped": False})
            
            skin_to_equip.is_equipped = True
            session.commit()
            return True, f"Skin **{skin_to_equip.skin_name}** equipaggiata!"
        except Exception as e:
            session.rollback()
            return False, f"Errore durante l'equipaggiamento: {e}"
        finally:
            session.close()

    def get_equipped_skin(self, user_id: int, character_id: int) -> Optional[UserSkin]:
        """Get the currently equipped skin for a character"""
        session = self.db.get_session()
        skin = session.query(UserSkin).filter(
            and_(
                UserSkin.user_id == user_id, 
                UserSkin.character_id == character_id,
                UserSkin.is_equipped == True
            )
        ).first()
        session.close()
        return skin

    def add_new_skin(self, character_id: int, name: str, price: int, gif_path: str) -> int:
        """Add a new skin to CSV (Admin only logic)"""
        self.load_skins() # Ensure fresh
        new_id = 1
        if self._skins_cache:
            new_id = max(s['id'] for s in self._skins_cache) + 1
            
        try:
            with open('data/skins.csv', 'a', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([new_id, character_id, name, price, gif_path])
            
            self.load_skins() # Refresh cache
            return new_id
        except Exception as e:
            print(f"[ERROR] Failed to add skin to CSV: {e}")
            return -1
