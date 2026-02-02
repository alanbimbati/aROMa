
import unittest
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from services.item_service import ItemService
from services.user_service import UserService
from models.user import Utente
from models.item import Item
from models.items import Collezionabili
from database import Database

class TestItems(unittest.TestCase):
    def setUp(self):
        self.db = Database()
        self.session = self.db.get_session()
        self.item_service = ItemService()
        self.user_service = UserService()
        
        self.user = Utente(
            id_telegram=19001, 
            nome="ItemTester", 
            username="itemtester", 
            livello=10,
            health=100,
            max_health=100
        )
        self.session.add(self.user)
        self.session.commit()
        
    def tearDown(self):
        self.session.query(Utente).filter_by(id_telegram=19001).delete()
        self.session.commit()
        self.session.close()
        
    def test_use_potion(self):
        """Test using a health potion"""
        # Create potion item if not exists logic? 
        # ItemService usually works with item IDs or names.
        # Let's assume standard items exist or mock them.
        # Actually, ItemService.use_item logic depends on implementation.
        # Let's check if we can add an item to user inventory first.
        
        # Mock inventory addition
        # user.inventory is usually a JSON or separate table?
        # Let's check User model... assume simple dict for now or check ItemService.
        
        # For now, let's test the effect logic if exposed, or add item to DB.
        # Let's assume we have a "Pozione Curativa" in DB.
        
        # Create a test item in DB
        potion = Item(
            name="Pozione Grande", 
            description="Heals 100 HP", 
            rarity="Common",
            slot="Consumable",
            stats={"health": 100},
            special_effect_id="heal_hp",
            price=10
        )
        self.session.add(potion)
        self.session.commit()
        
        # Add to user inventory
        import datetime
        potion_inv = Collezionabili(
            id_telegram=str(self.user.id_telegram),
            oggetto=potion.name,
            quantita=1,
            data_acquisizione=datetime.datetime.now()
        )
        self.session.add(potion_inv)
        self.session.commit()
        
        # Damage user
        self.user.current_hp = 50
        self.session.commit()
        
        # Patch PotionService to recognize the potion
        from unittest.mock import patch
        
        test_potions = [{
            'nome': 'Pozione Grande',
            'tipo': 'health_potion',
            'effetto_valore': 100, # Should restore 50 (capped at max 100)
            'prezzo': 10,
            'descrizione': 'Heals 100 HP',
            'rarita': 1
        }]
        
        with patch('services.potion_service.PotionService.load_potions', return_value=test_potions):
            # Use item
            result = self.item_service.use_item(self.user.id_telegram, potion.name, session=self.session)
            
            if isinstance(result, tuple):
                success, msg = result
            else:
                success, msg = result, ""
            
            self.assertTrue(success, f"Item use failed: {msg}")
            
            self.session.refresh(self.user)
            self.assertEqual(self.user.current_hp, 100, f"HP not restored. Current: {self.user.current_hp}") # 50 + 50
        
        # Check quantity reduced (data_utilizzo set)
        inv = self.session.query(Collezionabili).filter_by(id_telegram=str(self.user.id_telegram), oggetto=potion.name).first()
        self.assertIsNotNone(inv.data_utilizzo)
        
        # Cleanup item
        self.session.delete(potion)
        self.session.delete(potion_inv)
        self.session.commit()
