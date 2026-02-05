import unittest
import sys
import os
from unittest.mock import MagicMock, patch, ANY

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.market_service import MarketService
from services.user_service import UserService
from services.item_service import ItemService
from models.user import Utente
from models.items import Collezionabili
from models.market import MarketListing
from models.resources import UserResource
from models.dungeon import DungeonParticipant
from database import Database
import datetime

class TestMarket(unittest.TestCase):
    def setUp(self):
        self.db = Database()
        self.market_service = MarketService()
        self.user_service = UserService()
        self.item_service = ItemService()
        
        # Create test users
        session = self.db.get_session()
        self.seller_id = 888888888
        self.buyer_id = 999999999
        
        # Clean up existing test data
        session.query(Collezionabili).filter(Collezionabili.id_telegram.in_([str(self.seller_id), str(self.buyer_id)])).delete()
        session.query(MarketListing).filter(MarketListing.seller_id.in_([self.seller_id, self.buyer_id])).delete()
        session.query(Utente).filter_by(id_telegram=self.seller_id).delete()
        session.query(Utente).filter_by(id_telegram=self.buyer_id).delete()
        session.commit()
        
        # Create seller
        seller = Utente(
            id_telegram=self.seller_id,
            username="TestSeller",
            livello=1,
            exp=0,
            points=1000  # Have points for testing
        )
        session.add(seller)
        
        # Create buyer
        buyer = Utente(
            id_telegram=self.buyer_id,
            username="TestBuyer",
            livello=1,
            exp=0,
            points=500
        )
        session.add(buyer)
        
        session.commit()
        session.close()

    def tearDown(self):
        session = self.db.get_session()
        session.query(Collezionabili).filter(Collezionabili.id_telegram.in_([str(self.seller_id), str(self.buyer_id)])).delete()
        session.query(MarketListing).filter(MarketListing.seller_id.in_([self.seller_id, self.buyer_id])).delete()
        session.query(DungeonParticipant).filter(DungeonParticipant.user_id.in_([self.seller_id, self.buyer_id])).delete()
        session.query(UserResource).filter(UserResource.user_id.in_([self.seller_id, self.buyer_id])).delete()
        session.query(Utente).filter_by(id_telegram=self.seller_id).delete()
        session.query(Utente).filter_by(id_telegram=self.buyer_id).delete()
        session.commit()
        session.close()

    def test_list_item_success(self):
        """Test listing an item for sale"""
        # Add item to seller's inventory
        self.item_service.add_item(self.seller_id, "Pozione", 5)
        
        # List 3 potions
        success, msg = self.market_service.list_item(
            user_id=self.seller_id,
            item_name="Pozione",
            quantity=3,
            price_per_unit=50
        )
        
        self.assertTrue(success)
        self.assertIn("Annuncio creato", msg)
        
        # Verify inventory was reduced
        session = self.db.get_session()
        remaining = session.query(Collezionabili).filter_by(
            id_telegram=str(self.seller_id),
            oggetto="Pozione",
            data_utilizzo=None
        ).count()
        self.assertEqual(remaining, 2)  # 5 - 3 = 2
        session.close()

    def test_list_item_insufficient_quantity(self):
        """Test listing more items than available"""
        # Add only 2 items
        self.item_service.add_item(self.seller_id, "Pozione", 2)
        
        # Try to list 3
        success, msg = self.market_service.list_item(
            user_id=self.seller_id,
            item_name="Pozione",
            quantity=3,
            price_per_unit=50
        )
        
        self.assertFalse(success)
        self.assertIn("Non hai abbastanza", msg)

    def test_buy_item_success(self):
        """Test successfully buying an item"""
        # Seller lists item
        self.item_service.add_item(self.seller_id, "Spada Epica", 1)
        success, msg = self.market_service.list_item(
            user_id=self.seller_id,
            item_name="Spada Epica",
            quantity=1,
            price_per_unit=200
        )
        
        # Get listing ID
        session = self.db.get_session()
        listing = session.query(MarketListing).filter_by(seller_id=self.seller_id, status='active').first()
        listing_id = listing.id
        session.close()
        
        # Buyer purchases
        success, msg = self.market_service.buy_item(
            buyer_id=self.buyer_id,
            listing_id=listing_id
        )
        
        self.assertTrue(success)
        self.assertIn("Acquistato", msg)
        
        # Verify buyer received item
        session = self.db.get_session()
        buyer_items = session.query(Collezionabili).filter_by(
            id_telegram=str(self.buyer_id),
            oggetto="Spada Epica"
        ).count()
        self.assertEqual(buyer_items, 1)
        
        # Verify seller received points
        seller = session.query(Utente).filter_by(id_telegram=self.seller_id).first()
        self.assertEqual(seller.points, 1200)  # 1000 + 200
        
        # Verify buyer lost points
        buyer = session.query(Utente).filter_by(id_telegram=self.buyer_id).first()
        self.assertEqual(buyer.points, 300)  # 500 - 200
        
        session.close()

    def test_buy_item_insufficient_funds(self):
        """Test buying without enough Wumpa"""
        # Seller lists expensive item
        self.item_service.add_item(self.seller_id, "Arma Leggendaria", 1)
        success, msg = self.market_service.list_item(
            user_id=self.seller_id,
            item_name="Arma Leggendaria",
            quantity=1,
            price_per_unit=1000  # More than buyer has
        )
        
        session = self.db.get_session()
        listing = session.query(MarketListing).filter_by(seller_id=self.seller_id, status='active').first()
        listing_id = listing.id
        session.close()
        
        # Buyer tries to purchase
        success, msg = self.market_service.buy_item(
            buyer_id=self.buyer_id,
            listing_id=listing_id
        )
        
        self.assertFalse(success)
        self.assertIn("Non hai abbastanza", msg)

    def test_buy_own_item(self):
        """Test that users cannot buy their own listings"""
        self.item_service.add_item(self.seller_id, "Pozione", 1)
        success, msg = self.market_service.list_item(
            user_id=self.seller_id,
            item_name="Pozione",
            quantity=1,
            price_per_unit=50
        )
        
        session = self.db.get_session()
        listing = session.query(MarketListing).filter_by(seller_id=self.seller_id, status='active').first()
        listing_id = listing.id
        session.close()
        
        # Try to buy own item
        success, msg = self.market_service.buy_item(
            buyer_id=self.seller_id,  # Same as seller
            listing_id=listing_id
        )
        
        self.assertFalse(success)
        self.assertIn("Non puoi acquistare i tuoi oggetti", msg)

    def test_cancel_listing(self):
        """Test cancelling a listing"""
        # List item
        self.item_service.add_item(self.seller_id, "Pozione", 3)
        success, msg = self.market_service.list_item(
            user_id=self.seller_id,
            item_name="Pozione",
            quantity=3,
            price_per_unit=50
        )
        
        session = self.db.get_session()
        listing = session.query(MarketListing).filter_by(seller_id=self.seller_id, status='active').first()
        listing_id = listing.id
        session.close()
        
        # Cancel listing
        success, msg = self.market_service.cancel_listing(
            user_id=self.seller_id,
            listing_id=listing_id
        )
        
        self.assertTrue(success)
        self.assertIn("cancellato", msg)
        
        # Verify listing is cancelled
        session = self.db.get_session()
        listing = session.query(MarketListing).filter_by(id=listing_id).first()
        self.assertEqual(listing.status, 'cancelled')
        
        # Verify items returned to inventory
        items = session.query(Collezionabili).filter_by(
            id_telegram=str(self.seller_id),
            oggetto="Pozione",
            data_utilizzo=None
        ).count()
        self.assertEqual(items, 3)  # All returned
        session.close()

    def test_get_active_listings(self):
        """Test retrieving active market listings"""
        # Create multiple listings
        self.item_service.add_item(self.seller_id, "Pozione", 5)
        self.market_service.list_item(self.seller_id, "Pozione", 2, 50)
        self.market_service.list_item(self.seller_id, "Pozione", 2, 60)
        
        # Get listings
        listings, total = self.market_service.get_active_listings(page=1, limit=10)
        
        self.assertGreaterEqual(len(listings), 2)
        self.assertGreaterEqual(total, 2)


    def test_market_achievement_events(self):
        """Verify that market actions trigger achievement events"""
        # Mock EventDispatcher
        self.market_service.event_dispatcher = MagicMock()
        
        # 1. Test Listing Event
        self.item_service.add_item(self.seller_id, "Pozione", 5)
        self.market_service.list_item(
            user_id=self.seller_id,
            item_name="Pozione",
            quantity=1,
            price_per_unit=50
        )
        
        # Verify ITEM_LISTED event
        self.market_service.event_dispatcher.log_event.assert_any_call(
            event_type='ITEM_LISTED',
            user_id=self.seller_id,
            value=1,
            context=ANY
        )
        
        # 2. Test Buying Event
        session = self.db.get_session()
        listing = session.query(MarketListing).filter_by(seller_id=self.seller_id, status='active').first()
        listing_id = listing.id
        session.close()
        
        self.market_service.buy_item(
            buyer_id=self.buyer_id,
            listing_id=listing_id
        )
        
        # Verify ITEM_BOUGHT and ITEM_SOLD events
        self.market_service.event_dispatcher.log_event.assert_any_call(
            event_type='ITEM_BOUGHT',
            user_id=self.buyer_id,
            value=50, # Price
            context=ANY
        )
        self.market_service.event_dispatcher.log_event.assert_any_call(
            event_type='ITEM_SOLD',
            user_id=self.seller_id,
            value=50, # Price
            context=ANY
        )

if __name__ == '__main__':
    unittest.main()
